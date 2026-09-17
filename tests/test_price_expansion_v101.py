"""Offline references, food portions and package forms in v101."""
from copy import deepcopy
from datetime import date, timedelta
import importlib
import unittest
from unittest.mock import patch

import test_price_gaps_v87 as previous


class PriceExpansionTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(previous.PriceGapTests.setUpClass.__func__)
    setUp = previous.PriceGapTests.setUp
    asyncTearDown = previous.PriceGapTests.asyncTearDown
    store = previous.PriceGapTests.store

    async def test_new_references_are_reachable_dated_and_market_bound(self):
        recipe = {'ingredients': [{'name': name, 'quantity': 2, 'unit': unit}
                  for name, unit in [('Minced beef', 'g'), ('Cod', 'g'), ('Demerara sugar', 'g'),
                                     ('Vanilla pod', 'pcs')]]}
        original = deepcopy(recipe)
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(result['complete'], result)
        self.assertNotIn('fallbackIngredientCount', result)
        self.assertTrue(all(row['references'] and row['costsByCurrency']['EUR'] > 0 for row in result['ingredients']))
        self.assertEqual(recipe, original)
        added = [row for row in self.evidence['observations'] if 'v101-20260917' in str(row['id'])]
        self.assertEqual(len(added), 5)
        for ref in added:
            with self.subTest(reference=ref['id']):
                query = dict(category=ref['categories'][0], country='DE', currency='EUR', unit=ref['basisUnit'])
                with patch.object(self.snapshot, '_load', return_value={'observations': added}):
                    self.assertIn(ref['id'], [row['id'] for row in self.snapshot.snapshot_observations(**query)])
                    self.assertFalse(self.snapshot.snapshot_observations(**{**query, 'country': 'FR'}))
                    self.assertFalse(self.snapshot.snapshot_observations(**{**query, 'currency': 'USD'}))
                for age in [181, -1]:
                    expired = {**ref, 'date': (date.today() - timedelta(days=age)).isoformat()}
                    with patch.object(self.snapshot, '_load', return_value={'observations': [expired]}):
                        self.assertFalse(self.snapshot.snapshot_observations(**query))

    async def test_package_costs_and_vanilla_forms(self):
        for name, amount, unit, expected in [
                ('Minced beef', 200, 'g', 6.78), ('Ground beef', .5, 'kg', 16.95),
                ('Cod', 250, 'g', 11.45), ('Cod fillets', 500, 'g', 22.90),
                ('Demerara sugar', 100, 'g', .72), ('Vanilla pod', 1, 'pcs', 3.33),
                ('Vanilla pod', 2, 'g', 1.00), ('Vanilla pods', .5, '', 1.67)]:
            with self.subTest(name=name, amount=amount, unit=unit):
                recipe = {'ingredients': [{'name': name, 'quantity': amount, 'unit': unit}]}
                original = deepcopy(recipe)
                cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
                self.assertEqual(cost['totalsByCurrency'], {'EUR': expected})
                self.assertEqual(cost['priceConfidence'], 'reference')
                self.assertTrue(cost['complete'])
                self.assertEqual(recipe, original)
        for name, unit in [('Vanilla pod', 'packet'), ('Vanilla pod', 'tsp'),
                           ('Vanilla pod', 'seed'), ('Cod', 'fillet'), ('Cod', 'pcs')]:
            cost = await self.prices.offline_recipe_price(self.bridge,
                {'ingredients': [{'name': name, 'quantity': 2, 'unit': unit}]}, [])
            self.assertFalse(cost['ingredients'][0]['references'], cost)
        for name in ['Salt cod', 'Dried cod', 'Breaded cod', 'Mixed mince', 'Cooked ground beef',
                     'Vanilla seeds', 'Muscovado sugar']:
            self.assertIsNone(self.prices.category_for({'name': name}))

    async def test_unknown_quantities_and_basic_allowances_stay_distinct(self):
        recipe = {'ingredients': [{'name': name} for name in ['Minced beef', 'Cod', 'Vanilla pod', 'Demerara sugar', 'Salt', 'Water']]}
        cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertFalse(cost['complete'])
        self.assertFalse(cost['totalsByCurrency'])
        for row in cost['ingredients'][:4]:
            self.assertFalse(row.get('zeroCostAllowance'))
            self.assertFalse(row.get('references'))
        for row in cost['ingredients'][4:]:
            self.assertEqual(row['zeroCostAllowance']['amount'], 0)
            self.assertEqual(row['coverage'], 0)

    async def test_saved_user_price_wins_and_persistent_cache_is_reused(self):
        recipe = {'ingredients': [{'name': 'Vanilla pod', 'quantity': 1}]}
        cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(cost['totalsByCurrency'], {'EUR': 3.33})
        existing = await self.cache.recipe_cost_cache_for_bridge(self.bridge)
        fresh = self.cache.Cook4MeRecipeCostCache(self.bridge)
        fresh._store.saved = deepcopy(existing._store.saved)
        await fresh.async_load()
        self.bridge._recipe_cost_cache_v1 = fresh
        with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('persistent cache missed')):
            again = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(again['costCacheHit'])
        store = await self.store()
        await store.async_set_reference(cost['ingredients'][0]['identity'], amount=.50, currency='EUR',
                                        basis_quantity=1, basis_unit='pcs', country='DE', source='manual')
        actual = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(actual['totalsByCurrency'], {'EUR': .50})
        self.assertFalse(actual['costCacheHit'])

    async def test_real_cards_and_translated_recipes_agree_and_reuse_costs(self):
        runtime = previous.previous.runtime
        release = importlib.import_module(self.prices.__package__ + '.release_catalog')
        await release.async_warm_release_catalog(self.hass)
        results, errors = [], []
        ns = {'__name__': self.prices.__package__ + '.websocket_v34', '__package__': self.prices.__package__,
              '_authorized': lambda *args: self.bridge, '_country': self.costs._country,
              'offline_recipe_price': self.prices.offline_recipe_price,
              'preview_cache_token': self.cache.preview_cache_token,
              'legacy': runtime.NS(_send_error=lambda *args: errors.append(str(args[-1])))}
        runtime.functions('websocket_v34.py', {'ws_recipe_cost'}, ns)
        connection = runtime.NS(send_result=lambda _id, value: results.append(value))
        for ident, ingredient in [('330657', 'Ground beef'), ('270569', 'Minced beef'), ('326475', 'Vanilla pod'),
                                 ('258454', 'Cod'), ('681062', 'Demerara sugar')]:
            with self.subTest(variant=ident):
                expanded = release.recipe_by_variant(ident, language='el', configured_language='el', country='DE')
                original = deepcopy(expanded)
                for recipe in [{'variantFunctionalId': ident}, expanded]:
                    await ns['ws_recipe_cost'](self.hass, connection, {'id': 1, 'offline_only': True, 'recipe': recipe})
                    self.assertFalse(errors, errors)
                    row = next(row for row in results[-1]['ingredients'] if row['name'].casefold() == ingredient.casefold())
                    self.assertEqual(row['coverage'], 1, row)
                    self.assertTrue(row['references'])
                self.assertEqual(results[-1]['totalsByCurrency'], results[-2]['totalsByCurrency'])
                self.assertEqual(expanded, original)
                with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('reopening recalculated')):
                    await ns['ws_recipe_cost'](self.hass, connection, {'id': 1, 'offline_only': True, 'recipe': expanded})
                self.assertFalse(errors, errors)
                self.assertTrue(results[-1]['costCacheHit'])


if __name__ == '__main__':
    unittest.main()
