"""Household/member rules stay consistent from saved preferences to delivery."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import AsyncMock, Mock, patch
import sys
import test_runtime_audit_v74 as runtime
import test_diet_send_v77 as sending


class DietProfileTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = runtime.AuditTests.asyncTearDown
    prepare = sending.DietSendTests.prepare

    def setUp(self):
        runtime.AuditTests.setUp(self)
        self.rules = importlib.import_module(runtime.PREFIX + '.diet_profiles')
        self.filters = importlib.import_module(runtime.PREFIX + '.shared_recipe_filters')
        self.profiles = {'household': {'diet': 'vegetarian', 'proteinTarget': 25, 'excludedIngredients': []},
            'members': [{'id': 'alex', 'name': 'Alex', 'icon': 'star', 'diet': 'vegan', 'proteinTarget': 40,
                         'excludedIngredients': [{'ingredientId': 'rice', 'name': 'Rice', 'canonicalName': 'Rice', 'sourceIngredientIds': ['rice', 'rice-gr']}]}]}

    async def save(self):
        return await self.bridge.recipe_hub.async_set_profile({'dietProfiles': self.profiles})

    async def test_legacy_migration_preserves_all_exclusions_and_member_names(self):
        result = await self.bridge.recipe_hub.async_set_profile({'diet': 'vegetarian', 'allergies': 'nuts', 'avoid': 'onion', 'householdMembers': ['Alex', 'Sam']})
        self.assertEqual(result['dietProfiles']['household']['excludedTerms'], ['nuts', 'onion'])
        self.assertEqual([x['name'] for x in result['dietProfiles']['members']], ['Alex', 'Sam'])
        self.assertEqual(result['dietProfiles']['members'][0]['diet'], 'vegetarian')
        before = deepcopy(result['dietProfiles'])
        result = await self.bridge.recipe_hub.async_set_profile({'preferences': ['Quick meals']})
        self.assertEqual(result['dietProfiles'], before)
        self.assertEqual(self.bridge.recipe_hub._store.saved['profile']['dietProfiles'], before)

    async def test_profiles_are_independent_and_legacy_consumption_names_survive(self):
        result = await self.save()
        self.assertEqual(result['diet'], 'vegetarian'); self.assertEqual(result['householdMembers'], ['Alex'])
        household = self.rules.resolve_filters(result, {'dietProfile': 'household', 'diet': 'omnivore', 'proteinTarget': 1})
        member = self.rules.resolve_filters(result, {'dietProfile': 'member:alex', 'diet': 'omnivore', 'proteinTarget': 1})
        self.assertEqual((household['diet'], household['proteinTarget']), ('vegetarian', 25))
        self.assertEqual((member['diet'], member['proteinTarget']), ('vegan', 40))
        self.profiles['members'][0]['name'] = 'Alex renamed'
        saved = await self.save(); self.assertEqual(saved['dietProfiles']['members'][0]['id'], 'alex')
        self.assertEqual(saved['householdMembers'], ['Alex renamed'])

    async def test_exact_exclusions_follow_catalog_aliases_and_never_mutate_household(self):
        await self.save()
        recipe = {'title': 'Dish', 'ingredients': [{'ingredientId': 'rice-gr', 'name': 'Ρύζι'}]}
        member = self.bridge.recipe_hub.annotate(recipe, diet_filters={'dietProfile': 'member:alex'})
        household = self.bridge.recipe_hub.annotate(recipe, diet_filters={'dietProfile': 'household'})
        self.assertFalse(member['match']['safe']); self.assertIn('excluded:Rice', member['match']['violations'])
        self.assertTrue(household['match']['safe']); self.assertEqual(self.bridge.recipe_hub.profile['diet'], 'vegetarian')
        self.assertNotIn('match', recipe)

    async def test_manual_rules_keep_the_chosen_exclusions_but_allow_diet_edits(self):
        saved = await self.save()
        manual = self.rules.resolve_filters(saved, {'dietProfile': 'member:alex'})
        manual.update(dietProfile='manual', diet='omnivore')
        rice = self.bridge.recipe_hub.annotate({'ingredients': [{'ingredientId': 'rice', 'name': 'Rice'}]}, diet_filters=manual)
        beef = self.bridge.recipe_hub.annotate({'ingredients': ['beef']}, diet_filters=manual)
        self.assertFalse(rice['match']['safe']); self.assertTrue(beef['match']['safe'])

    async def test_selected_rules_reject_excluded_substitution_candidates(self):
        self.profiles['members'][0].update(excludedIngredients=[], excludedTerms=['soy', 'mushrooms', 'chickpeas'])
        await self.save()
        row = self.bridge.recipe_hub.annotate({'ingredients': ['beef']}, diet_filters={'dietProfile': 'member:alex'})
        self.assertFalse(row['match']['safe']); self.assertFalse(row['match']['eligibleWithSubstitutions'])

    def test_limits_and_unknown_nutrients_are_preserved(self):
        value=self.rules.normalize_diet({'calorieTarget': 'nan', 'proteinTarget': True, 'fiberTarget': -1, 'saltTarget': 2, 'fatTarget': 20})
        self.assertIsNone(value['calorieTarget']); self.assertIsNone(value['proteinTarget']); self.assertIsNone(value['fiberTarget'])
        self.assertEqual(value['saltTarget'], 2)
        broad = self.rules.scoring_profile({}, {'dietProfile':'manual','excludedIngredients':[
            {'ingredientId':str(i),'name':'Food '+str(i)} for i in range(300)]})
        self.assertEqual(len(broad['avoid']),300)
        settings=self.filters.normalize_filters({'dietProfile':'member:alex','fatTarget':20,'saltTarget':2})
        self.assertEqual(settings['dietProfile'],'member:alex'); self.assertEqual(settings['fatTarget'],20)
        rows=[{'title':'near','nutrition':{'perServing':{'fat':21}},'ingredients':[]}, {'title':'far','nutrition':{'perServing':{'fat':50}},'ingredients':[]}, {'title':'unknown','ingredients':[]}]
        found=self.filters.apply_filters(rows,settings)
        self.assertEqual(found[0]['title'],'near');self.assertEqual(next(x for x in found if x['title']=='unknown')['nutrition'],{})
        rows=[{'title':'zero','nutrition':{'perServing':{'sugarsG':0}}}, {'title':'sugar','nutrition':{'perServing':{'sugarsG':12}}}]
        self.assertEqual(self.filters.apply_filters(rows,{'sugarsTarget':0})[0]['title'],'zero')

    async def test_authorized_endpoint_preserves_stock_and_rejects_denied_access(self):
        result, errors=[],[]
        authorize=Mock(return_value=self.bridge)
        ns={'_authorized':authorize,'legacy':runtime.NS(_send_error=lambda *args:errors.append(args))}
        runtime.functions('websocket_v35.py',{'ws_diet_profiles'},ns)
        connection=runtime.NS(send_result=lambda _id,row:result.append(row))
        await ns['ws_diet_profiles'](self.hass,connection,{'id':1,'profiles':self.profiles})
        self.assertEqual(result[0]['profile']['dietProfiles']['members'][0]['name'],'Alex')
        before=self.bridge.recipe_hub.profile
        authorize.side_effect=PermissionError('denied')
        await ns['ws_diet_profiles'](self.hass,connection,{'id':2,'profiles':{}})
        self.assertEqual(len(errors),1);self.assertEqual(self.bridge.recipe_hub.profile,before)

    async def test_shared_recipe_pipeline_resolves_members_before_ranking(self):
        await self.save()
        hub = importlib.import_module(runtime.PREFIX + '.recipe_hub')
        namespace = {name: getattr(hub, name) for name in ('deepcopy', 'dt_util', 'score_recipe',
            'enrich_match_with_house_keys', 'recipe_quantity_feasibility', 'recipe_expiry_priority', 'DEFAULT_EXPIRY_WARNING_DAYS')}
        namespace['__package__'] = runtime.PREFIX
        runtime.functions('websocket_v13.py', {'_rank_filtered'}, namespace)
        async def executor(fn, *args): return fn(*args)
        self.hass.async_add_executor_job = executor
        self.bridge._nutrition_store = runtime.NS(generic={}, stock_lots={})
        self.bridge._meal_history_store = runtime.NS(recent=lambda _: [])
        modules = {runtime.PREFIX + '.websocket_v13': runtime.NS(_rank_filtered=namespace['_rank_filtered']),
                   runtime.PREFIX + '.websocket_v18': runtime.NS(_recent_identities=lambda *args, **kwargs: set())}
        with patch.dict(sys.modules, modules):
            pipeline = importlib.import_module(runtime.PREFIX + '.shared_recipe_runtime')
            process = await pipeline.processor(self.bridge, {'dietProfile':'member:alex', 'diet':'omnivore'})
            rows = process([{'title':'Excluded rice', 'ingredients':[{'ingredientId':'rice-gr','name':'Ρύζι','quantity':100,'unit':'g'}]},
                            {'title':'Potato', 'ingredients':[{'ingredientId':'potato','name':'Potato','quantity':100,'unit':'g'}]}])
        self.assertEqual([r['title'] for r in rows], ['Potato'])
        self.assertEqual(rows[0]['match']['diet'],'vegan')
        self.assertIn('dietRulesSignature',rows[0]['match'])

    async def test_send_and_queue_recheck_the_current_member_rules(self):
        await self.prepare([{'ingredientId':'rice','name':'Rice'}]); await self.save()
        blocked=await self.send(self.bridge,{'sendVariantId':'original-variant','sendFilters':{'dietProfile':'member:alex'}})
        self.assertFalse(blocked['sent']);self.assertFalse(blocked['queued']);self.bridge._run_client_json.assert_not_awaited()
        self.profiles['members'][0]['excludedIngredients']=[];await self.save();self.bridge.data={'connected':False}
        queued=await self.send(self.bridge,{'sendVariantId':'original-variant','sendFilters':{'dietProfile':'member:alex'}})
        self.assertTrue(queued['queued']);self.assertEqual(self.store.queued_send['dietFilters']['dietProfile'],'member:alex')
        self.profiles['members'][0]['excludedIngredients']=[{'ingredientId':'rice','name':'Rice'}];await self.save();self.bridge.data={'connected':True}
        await self.flush(self.bridge);self.bridge._run_client_json.assert_not_awaited();self.assertIsNotNone(self.store.queued_send)
        self.profiles['members'][0]['excludedIngredients']=[];await self.save();await self.flush(self.bridge)
        self.bridge._run_client_json.assert_awaited_once();self.assertIsNone(self.store.queued_send)

    async def test_deleted_member_cannot_silently_send_as_household(self):
        await self.prepare(['rice']);await self.save()
        self.profiles['members']=[];await self.save()
        result=await self.send(self.bridge,{'sendVariantId':'original-variant','sendFilters':{'dietProfile':'member:alex'}})
        self.assertEqual(result['reason'],'dietary_profile');self.assertFalse(result['queued']);self.bridge._run_client_json.assert_not_awaited()


if __name__=='__main__': unittest.main()
