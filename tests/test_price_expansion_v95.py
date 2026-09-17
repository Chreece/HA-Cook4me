"""Offline references, food portions and cache behavior changed in v95."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import patch

import test_price_gaps_v87 as previous


class PriceExpansionTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(previous.PriceGapTests.setUpClass.__func__)
    setUp = previous.PriceGapTests.setUp
    asyncTearDown = previous.PriceGapTests.asyncTearDown
    store = previous.PriceGapTests.store

    async def test_twenty_new_references_are_reachable_offline(self):
        names = ['Tahini', 'Buckwheat', 'Millet', 'Bicarbonate of soda', 'Sesame seed',
                 'Icing sugar', 'Fennel', 'Celeriac', 'Butternut squash', 'Green cabbage',
                 'Brussels sprouts', 'Bay', 'Groundnut oil', 'Chicory', 'Chard',
                 'Green pepper', 'Fromage frais', 'Tomato coulis', 'Brown rice', 'Turnip']
        recipe = {'ingredients': [{'name': name, 'quantity': 100,
                  'unit': 'ml' if name == 'Groundnut oil' else 'g'} for name in names]}
        original = deepcopy(recipe)
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(result['complete'], [(r['name'], r['priceStatus']) for r in result['ingredients'] if r['coverage'] < 1])
        self.assertNotIn('fallbackIngredientCount', result)
        self.assertTrue(all(r['costsByCurrency']['EUR'] > 0 for r in result['ingredients']))
        self.assertTrue(all(any(ref.get('observationId') for ref in r['references']) for r in result['ingredients']))
        # Existing eligible receipt observations still outrank retail references.
        sesame = next(r for r in result['ingredients'] if r['name'] == 'Sesame seed')
        self.assertEqual(sesame['references'][0]['source'], 'open_prices_category')
        self.assertEqual(recipe, original)
        added = [r for r in self.evidence['observations'] if 'v95-20260916' in str(r['id'])]
        self.assertEqual(len(added), 20)
        for ref in added:
            self.assertTrue(ref['sourceUrl'].startswith('https://'))
            with patch.object(self.snapshot, '_load', return_value={'observations': added}):
                self.assertTrue(any(r['id'] == ref['id'] for r in self.snapshot.snapshot_observations(
                    category=ref['categories'][0], country='DE', currency='EUR', unit=ref['basisUnit'])))
                self.assertFalse(self.snapshot.snapshot_observations(category=ref['categories'][0], country='FR', currency='EUR', unit=ref['basisUnit']))
                self.assertFalse(self.snapshot.snapshot_observations(category=ref['categories'][0], country='DE', currency='USD', unit=ref['basisUnit']))

    async def test_changed_spoons_counts_and_densities_use_saved_prices(self):
        cases = [('Cumin', 1, 'tsp', 2), ('Garam masala', 2, 'tsp', 4),
                 ('Sesame seed', 2, 'tbsp', 18), ('Tahini', 1, 'tbsp', 15),
                 ('Icing sugar', 2, 'tbsp', 16), ('Sour cream', 3, 'tbsp', 36),
                 ('Bicarbonate of soda', 1, 'tsp', 4.6), ('Fromage frais', 2, 'tbsp', 29),
                 ('Yoghurt', 100, 'ml', 103.1), ('Asparagus', 4, '', 64),
                 ('Fennel', 1, '', 234), ('Turnip', 2, '', 244), ('Green pepper', 1, '', 119)]
        for name, quantity, unit, grams in cases:
            with self.subTest(name=name):
                item = {'name': name, 'quantity': quantity, 'unit': unit}
                options = self.measures.price_options(item)
                self.assertTrue(any(o['unit'] == 'g' and abs(o['quantity'] - grams) < .0001 for o in options), options)
                cost = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [item]}, [])
                self.assertTrue(cost['complete'], cost)
                self.assertNotIn('fallbackIngredientCount', cost)
                self.assertTrue(cost['ingredients'][0]['quantityEstimate']['sourceUrl'].startswith('https://'))

    async def test_leaf_and_sprig_quantities_do_not_become_bunches(self):
        for name, quantity, key, unit, grams in [
                ('Parsley', 2, 'UNIT_10', 'gałązka', 2), ('Dill', 5, 'UNIT_10', 'brin', 1),
                ('Coriander', 9, 'UNIT_10', 'Zweig', 20), ('Basil', 5, 'UNIT_24', 'feuille', 2.5),
                ('Mint', 2, 'UNIT_24', 'foglia', .3)]:
            with self.subTest(name=name):
                item = {'name': name, 'quantity': quantity, 'unitKey': key, 'unit': unit}
                cost = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [item]}, [])
                self.assertTrue(cost['complete'])
                estimate = cost['ingredients'][0]['quantityEstimate']
                self.assertAlmostEqual(estimate['quantity'], grams)
                self.assertEqual(estimate['unit'], 'g')
                self.assertIn(estimate['sourceUnit'], {'leaf', 'sprig'})
        for item in [{'name': 'Parsley', 'quantity': 1, 'unitKey': 'UNIT_6', 'unit': 'Bund'},
                     {'name': 'Basil', 'quantity': 1, 'unit': 'pot'},
                     {'name': 'Salt', 'quantity': 2, 'unit': 'sprig'},
                     {'name': 'Dill'}, {'name': 'Unknown spice', 'quantity': 1, 'unit': 'leaf'}]:
            self.assertFalse(any(o['unit'] in {'g', 'ml', 'pcs'} for o in self.measures.price_options(item)))
        self.assertIsNone(self.prices.category_for({'name': 'Pickled turnip'}))
        self.assertNotEqual(self.prices.category_for({'name': 'Swede'}), self.prices.category_for({'name': 'Turnip'}))
        self.assertNotEqual(self.prices.category_for({'name': 'Tomato paste'}), self.prices.category_for({'name': 'Tomato coulis'}))

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
        for ident, ingredient in [('245258', 'Cumin'), ('581276', 'Sesame seed'),
                                  ('270810', 'Fennel'), ('411745', 'Turnip'),
                                  ('277623', 'Asparagus'), ('326471', 'Fromage frais'),
                                  ('343259', 'Butternut squash')]:
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

    async def test_saved_user_price_wins_and_persistent_cache_is_reused(self):
        recipe = {'ingredients': [{'name': 'Fennel', 'quantity': 2}]}
        cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(cost['totalsByCurrency'], {'EUR': 1.63})
        existing = await self.cache.recipe_cost_cache_for_bridge(self.bridge)
        fresh = self.cache.Cook4MeRecipeCostCache(self.bridge)
        fresh._store.saved = deepcopy(existing._store.saved)
        await fresh.async_load()
        self.bridge._recipe_cost_cache_v1 = fresh
        with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('persistent cache missed')):
            again = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(again['costCacheHit'])
        store = await self.store()
        await store.async_set_reference('n:fennel', amount=.50, currency='EUR', basis_quantity=1,
                                        basis_unit='pcs', country='DE', source='manual')
        actual = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(actual['totalsByCurrency'], {'EUR': 1})
        self.assertFalse(actual['costCacheHit'])


if __name__ == '__main__':
    unittest.main()
