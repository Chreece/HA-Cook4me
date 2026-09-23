"""Actual weekly generator and shared processor; retain v200's controlled HA fixtures."""
import unittest
from copy import deepcopy
import types
from test_week_progress_v200 import setup_generation, module, functions, COMPONENT, NAME, Store, resolved, Hass


def guide():
    return {'id':'guide','title':'Rice','canonicalName':'Rice','ingredients':[{'name':'Rice','key':'rice'},{'name':'Water','key':'water'}],
            'mealTypes':['breakfast','main'],'match':{'safe':True,'score':9999}}


class AutoRoutes(unittest.IsolatedAsyncioTestCase):
    async def test_weekly_only_guides_leaves_slots_empty_instead_of_taxonomy_fallback(self):
        hass,bridge,life,store,ns,runtime,rows=setup_generation()
        rows[:]=[guide()]
        result=await ns['_generate_week'](hass,bridge,life,week_start='2026-09-23',languages=['en'],diet='vegetarian',query='',refresh=False,shared_filters={},progress=lambda *a,**kw:None)
        self.assertEqual(result['slotCount'],0);self.assertEqual(life.slots,[])
    async def test_weekly_all_days_and_regeneration_never_pick_a_guide(self):
        hass,bridge,life,store,ns,runtime,rows=setup_generation()
        rows.insert(0,guide())
        for _ in range(2):
            result=await ns['_generate_week'](hass,bridge,life,week_start='2026-09-23',languages=['en'],diet='vegetarian',query='',refresh=False,shared_filters={},progress=lambda *a,**kw:None)
            self.assertEqual(result['slotCount'],21)
            self.assertNotIn('guide',[slot['recipe']['id'] for slot in life.slots])
    async def test_weekly_replace_one_slot_never_selects_a_guide(self):
        hass,bridge,life,store,ns,runtime,rows=setup_generation()
        kwargs=dict(week_start='2026-09-23',languages=['en'],diet='vegetarian',query='',refresh=False,shared_filters={},progress=lambda *a,**kw:None)
        await ns['_generate_week'](hass,bridge,life,**kwargs)
        target=life.slots[0]['id'];before=deepcopy(life.slots[1:]);rows.insert(0,guide())
        await ns['_generate_week'](hass,bridge,life,replace_slot_id=target,**kwargs)
        self.assertEqual(life.slots[1:],before);self.assertNotIn('guide',[slot['recipe']['id'] for slot in life.slots])
    async def test_actual_processor_excludes_before_ranking_but_keeps_manual_search(self):
        store=Store();seen=[]
        def rank(bridge,rows,**kw):
            seen.append(([row['id'] for row in rows],kw['for_suggestions']));return rows
        module('websocket_v13',_rank_filtered=rank)
        module('websocket_v18',_recent_identities=lambda *a,**kw:set())
        module('costs',cost_store_for_bridge=lambda b:resolved(None))
        module('costing',calculate_recipe_cost=lambda *a,**kw:{})
        module('meal_history',meal_history_store_for_bridge=lambda b:resolved(types.SimpleNamespace(recent=lambda n:[])))
        module('nutrition',nutrition_store_for_bridge=lambda b:resolved(store))
        module('nutrition_fefo',calculate_recipe_nutrition_fefo=lambda *a,**kw:{})
        module('today_logic',recipe_identity=lambda row:row['id'])
        module('diet_profiles',resolve_filters=lambda profile,filters:filters)
        ns=dict(__name__=NAME+'.runtime',__package__=NAME,
            normalize_filters=lambda f:{'maxCost':None,'diet':'vegetarian','ingredients':[],'avoidRecentDays':0},
            apply_filters=lambda rows,settings,**kw:rows)
        functions(COMPONENT/'shared_recipe_runtime.py',{'processor'},ns)
        bridge=types.SimpleNamespace(recipe_hub=types.SimpleNamespace(profile={}))
        meal={'id':'meal','title':'Porridge','ingredients':[{'name':'Rice'},{'name':'Milk'}]};rows=[guide(),meal];before=deepcopy(rows)
        auto=await ns['processor'](bridge,{},for_suggestions=True)
        manual=await ns['processor'](bridge,{})
        self.assertEqual(await Hass().async_add_executor_job(auto,rows),[meal])
        self.assertEqual(await Hass().async_add_executor_job(manual,rows),rows)
        self.assertEqual(seen,[(['meal'],True),(['guide','meal'],False)])
        self.assertEqual(rows,before)
        self.assertEqual(store.reads,[2,2]) # one snapshot per pass, not per recipe

if __name__=='__main__':unittest.main()
