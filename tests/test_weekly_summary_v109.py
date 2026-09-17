"""Weekly views use current card evidence and the shared filter contract."""
from copy import deepcopy
from datetime import datetime
import importlib
import sys
import unittest
from unittest.mock import AsyncMock, patch

import test_runtime_audit_v74 as runtime
import test_price_gaps_v87 as prices


class WeeklySummaryTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(prices.PriceGapTests.setUpClass.__func__)
    asyncTearDown = prices.PriceGapTests.asyncTearDown
    store = prices.PriceGapTests.store

    def setUp(self):
        prices.PriceGapTests.setUp(self)
        self.week = importlib.import_module(runtime.PREFIX + '.weekly_plan')
        self.release = importlib.import_module(runtime.PREFIX + '.release_catalog')
        metrics = importlib.import_module(runtime.PREFIX + '.recipe_metrics_v60')
        self.payload = {**self.catalog, '_runtimeNutritionIndex': metrics.build_nutrition_index(self.catalog['ingredients'])}
        warm = patch.object(self.release, 'async_warm_release_catalog', AsyncMock(return_value=self.payload))
        warm.start(); self.addCleanup(warm.stop)
        hub = importlib.import_module(runtime.PREFIX + '.recipe_hub')
        ns = {name: getattr(hub, name) for name in ('deepcopy', 'dt_util', 'score_recipe',
            'enrich_match_with_house_keys', 'recipe_quantity_feasibility', 'recipe_expiry_priority', 'DEFAULT_EXPIRY_WARNING_DAYS')}
        ns['__package__'] = runtime.PREFIX
        runtime.functions('websocket_v13.py', {'_rank_filtered'}, ns)
        self.bridge._nutrition_store = runtime.NS(generic={}, stock_lots={})
        self.bridge._meal_history_store = runtime.NS(recent=lambda _: [])
        modules = patch.dict(sys.modules, {
            runtime.PREFIX + '.websocket_v13': runtime.NS(_rank_filtered=ns['_rank_filtered']),
            runtime.PREFIX + '.websocket_v18': runtime.NS(_recent_identities=lambda *a, **k: set())})
        modules.start(); self.addCleanup(modules.stop)

    def slot(self, name, **changes):
        recipe = {'title': name, 'id': name, 'language': 'de', 'mealTypes': ['main'], 'servings': 2,
                  'ingredients': [{'key': name.lower(), 'name': name, 'quantity': 200, 'unit': 'g'}]}
        recipe.update(changes)
        return {'id': name, 'date': '2026-09-17', 'mealType': 'dinner', 'recipe': recipe,
                'cost': {'totalsByCurrency': {'EUR': .01}}}

    async def test_real_week_prices_equal_current_cards_including_budget_assumptions(self):
        recipes = [deepcopy(v) for family in self.catalog['recipes'] for v in family['variants']
                   if str(v.get('variantId')) in {'321369', '314559'}]
        saved = {'slots': [{'id': str(i), 'date': '2026-09-17', 'mealType': 'dinner', 'recipe': recipe,
                            'cost': {'totalsByCurrency': {'EUR': .01}}} for i, recipe in enumerate(recipes)]}
        before = deepcopy(saved)
        view = await self.week.refresh_plan(self.bridge, deepcopy(saved))
        expected = 0
        for slot in view['slots']:
            card = await self.prices.offline_recipe_price(self.bridge, slot['recipe'], self.catalog['ingredients'])
            self.assertEqual(slot['cost']['budgetTotalsByCurrency'], card['budgetTotalsByCurrency'])
            self.assertEqual(slot['recipe']['cost'], slot['cost'])
            expected += card['budgetTotalsByCurrency']['EUR']
        self.assertEqual(view['weeklyCostByCurrency']['EUR'], round(expected, 2))
        self.assertGreater(expected, 5)
        self.assertFalse(view['weeklyCostComplete'])
        self.assertEqual(saved, before, 'Reading a plan must not persist presentation/filter changes')

    async def test_saved_purchase_change_refreshes_an_existing_slot(self):
        store = await self.store()
        saved = {'slots': [self.slot('Rice')]}
        async def set_price(amount):
            await store.async_set_reference('k:rice', amount=amount, currency='EUR', basis_quantity=100,
                                            basis_unit='g', country='DE', source='manual')
        await set_price(2)
        first = await self.week.refresh_plan(self.bridge, deepcopy(saved))
        await set_price(3)
        second = await self.week.refresh_plan(self.bridge, deepcopy(saved))
        self.assertEqual(first['weeklyCostByCurrency'], {'EUR': 4})
        self.assertEqual(second['weeklyCostByCurrency'], {'EUR': 6})

    async def test_shared_languages_meals_exclusions_and_cost_filter_saved_slots_without_deleting(self):
        saved = {'slots': [self.slot('Rice'), self.slot('Potato'), self.slot('Carrot', language='fr'),
                           self.slot('Oats', mealTypes=['breakfast'])]}
        filters = {'dietProfile': 'manual', 'diet': 'vegetarian', 'languages': ['de'], 'mealTypes': ['main'],
                   'excludedTerms': ['rice'], 'maxCost': 4, 'currency': 'EUR'}
        cost = {'totalsByCurrency': {'EUR': 6}, 'perServingByCurrency': {'EUR': 3}, 'coverage': 1, 'complete': True}
        with patch.object(self.prices, 'offline_recipe_price', AsyncMock(return_value=cost)):
            view = await self.week.refresh_plan(self.bridge, deepcopy(saved), filters=filters)
            self.assertEqual([row['id'] for row in view['slots']], ['Potato'])
            self.assertEqual(view['filteredSlotCount'], 3)
            self.assertEqual(view['reservations']['items'][0]['name'], 'Potato')
            self.assertEqual(view['slots'][0]['recipe']['match']['diet'], 'vegetarian')
            none = await self.week.refresh_plan(self.bridge, deepcopy(saved), filters={**filters, 'maxCost': 2})
            self.assertEqual(none['slots'], [])
            self.assertEqual(none['weeklyCostByCurrency'], {})
        self.assertEqual(len(saved['slots']), 4)

    async def test_leftover_uses_its_allocated_cost_and_nutrition(self):
        recipe = self.slot('Rice')['recipe']
        state = {'slots': [{'id': 'rest', 'date': '2026-09-17', 'mealType': 'dinner', 'leftoverId': 'left',
                           'servings': 1, 'nutrition': {'totals': {'energyKcal': 120}},
                           'cost': {'totalsByCurrency': {'EUR': 2}}}],
                 'leftovers': [{'id': 'left', 'recipe': recipe}]}
        with patch.object(self.prices, 'offline_recipe_price', AsyncMock()) as cost:
            view = await self.week.refresh_plan(self.bridge, state)
        cost.assert_not_awaited()
        self.assertEqual(view['weeklyCostByCurrency'], {'EUR': 2})
        self.assertEqual(view['slots'][0]['nutrition']['totals']['energyKcal'], 120)
        self.assertEqual(view['shoppingDelta'], [])

    def test_shared_meal_filters_override_obsolete_separate_schedule(self):
        self.assertEqual(self.week.meal_slots({'mealTypes': ['breakfast']}, ['dinner']), ['breakfast'])
        self.assertEqual(self.week.meal_slots({'mealTypes': ['main']}, ['breakfast']), ['lunch', 'dinner'])
        self.assertEqual(self.week.meal_slots({'mealTypes': ['dessert']}, ['breakfast']), ['snack'])
        self.assertEqual(self.week.meal_slots({}, ['snack']), ['breakfast', 'lunch', 'dinner'])
        self.assertEqual(self.week.meal_slots(None, ['snack']), ['snack'])

    async def test_generation_cost_filter_uses_the_same_local_evidence_as_cards(self):
        recipe = next(deepcopy(v) for family in self.catalog['recipes'] for v in family['variants']
                      if str(v.get('variantId')) == '805952')
        card = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        self.assertTrue(card['complete'])
        amount = card['perServingByCurrency']['EUR']
        pipeline = importlib.import_module(runtime.PREFIX + '.shared_recipe_runtime')
        inclusive = await pipeline.processor(self.bridge, {'diet': 'omnivore', 'maxCost': amount + .01, 'currency': 'EUR'})
        exclusive = await pipeline.processor(self.bridge, {'diet': 'omnivore', 'maxCost': max(0, amount - .01), 'currency': 'EUR'})
        self.assertEqual(len(inclusive([recipe])), 1)
        self.assertEqual(exclusive([recipe]), [])

    async def test_state_handler_refreshes_saved_totals_without_changing_history(self):
        state = {'slots': [self.slot('Rice')], 'leftovers': []}
        lifecycle = runtime.NS(snapshot=lambda *a, **k: deepcopy(state), settings={})
        history = runtime.NS(recent=lambda _: [], summary=lambda **k: {'meals': 0})
        ns = {'__package__': runtime.PREFIX, 'deepcopy': deepcopy,
              'meal_lifecycle_store_for_bridge': AsyncMock(return_value=lifecycle),
              'cost_store_for_bridge': self.costs.cost_store_for_bridge,
              'meal_history_store_for_bridge': AsyncMock(return_value=history),
              'dt_util': runtime.NS(now=datetime.now), '_text': str,
              '_nutrition_dashboard': lambda *a, **k: {'series': ['history remains separate']}}
        runtime.functions('websocket_v20.py', {'_state'}, ns)
        result = await ns['_state'](self.hass, self.bridge)
        self.assertGreater(result['weeklyCostByCurrency']['EUR'], .01)
        self.assertEqual(result['nutritionDashboard']['series'], ['history remains separate'])
        self.assertEqual(state['slots'][0]['cost']['totalsByCurrency'], {'EUR': .01})

    async def test_shopping_uses_the_filtered_view_instead_of_hidden_saved_meals(self):
        rows = [{'name': 'Rice', 'quantity': 200, 'unit': 'g'}]
        lifecycle = runtime.NS(snapshot=lambda *a, **k: {'slots': [], 'shoppingDelta': ['hidden item']})
        ns = {'legacy': runtime.NS(_bridge=lambda *a: self.bridge, _send_error=lambda *a: self.fail(str(a))),
              'meal_lifecycle_store_for_bridge': AsyncMock(return_value=lifecycle),
              'dt_util': runtime.NS(now=datetime.now),
              '_state': AsyncMock(return_value={'slots': [], 'shoppingDelta': rows}),
              '_shopping_add': AsyncMock(return_value={'added': rows})}
        runtime.functions('websocket_v20.py', {'ws_week_add_shopping'}, ns)
        filters = {'mealTypes': ['breakfast']}
        result = []
        await ns['ws_week_add_shopping'](self.hass, runtime.NS(send_result=lambda _id, value: result.append(value)),
                                       {'id': 1, 'entry_id': 'one', 'shared_filters': filters})
        self.assertEqual(ns['_state'].await_args.kwargs['shared_filters'], filters)
        self.assertEqual(ns['_shopping_add'].await_args.args[1], rows)


if __name__ == '__main__':
    unittest.main()
