"""The displayed recipes, recovered units and cache reuse affected by v92."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import patch

import test_price_gaps_v87 as previous


class PriceOptimizationTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(previous.PriceGapTests.setUpClass.__func__)
    setUp = previous.PriceGapTests.setUp
    asyncTearDown = previous.PriceGapTests.asyncTearDown
    store = previous.PriceGapTests.store

    async def test_screenshot_recipes_through_the_actual_card_endpoint(self):
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
        expected = {'357993': (4, 1, 10), '341615': (7, 0, 9), '487446': (7, 0, 7),
                    '834652': (7, 0, 8), '331197': (4, 0, 7), '317075': (6, 0, 7),
                    '307808': (4, 0, 5), '816820': (3, 1, 8), '862912': (5, 1, 7),
                    '252627': (5, 1, 6), '834656': (7, 0, 8), '734674': (7, 0, 8),
                    '287823': (6, 0, 7), '826311': (5, 0, 6)}
        for ident, counts in expected.items():
            with self.subTest(variant=ident):
                # First render sends only the ID; expanding a card sends its
                # displayed/localized ingredients. Both paths must agree.
                payloads = [{'variantFunctionalId': ident},
                            release.recipe_by_variant(ident, language='el', configured_language='el', country='DE')]
                original = deepcopy(payloads)
                for recipe in payloads:
                    await ns['ws_recipe_cost'](self.hass, connection,
                        {'id': 1, 'offline_only': True, 'recipe': recipe})
                    self.assertFalse(errors, errors)
                    result = results[-1]
                    self.assertEqual((sum(row['coverage'] == 1 for row in result['ingredients']),
                                      result.get('fallbackIngredientCount', 0), len(result['ingredients'])), counts)
                self.assertEqual(results[-1]['totalsByCurrency'], results[-2]['totalsByCurrency'])
                self.assertEqual(results[-1].get('budgetTotalsByCurrency'), results[-2].get('budgetTotalsByCurrency'))
                self.assertEqual(payloads, original)
                with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('reopening recalculated')):
                    await ns['ws_recipe_cost'](self.hass, connection,
                        {'id': 1, 'offline_only': True, 'recipe': payloads[-1]})
                self.assertFalse(errors, errors)
                self.assertTrue(results[-1]['costCacheHit'])

    async def test_recipe_specific_curry_unit_and_half_onion(self):
        recipe = next(v for f in self.catalog['recipes'] for v in f['variants'] if v['variantId'] == '487446')
        original = deepcopy(recipe)
        fixed = self.prices.canonical_recipe(recipe, self.catalog['ingredients'])
        curry = next(r for r in fixed['ingredients'] if r['ingredientId'] == 'M_FOOD_161')
        onion = next(r for r in fixed['ingredients'] if r['ingredientId'] == 'M_FOOD_341')
        self.assertEqual((curry['canonicalName'], curry['quantity'], curry['unit']), ('red curry paste', 1, 'tbsp'))
        self.assertEqual(onion['quantity'], .5)
        self.assertEqual(recipe, original)
        result = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        self.assertTrue(result['complete'])
        for other in [{**recipe, 'variantId': 'another-recipe'},
                      {**recipe, 'ingredients': [{'ingredientId': 'M_FOOD_161', 'quantity': 3, 'unit': 'g'}]}]:
            unchanged = self.prices.canonical_recipe(other, self.catalog['ingredients'])
            row = next(r for r in unchanged['ingredients'] if r['ingredientId'] == 'M_FOOD_161')
            self.assertEqual(row['canonicalName'], 'Curry')

    async def test_explicit_translated_units_and_embedded_spoons(self):
        for name, quantity, unit, extra in [
                ('Olive oil', 1, 'EL', {}), ('Sugar', 2, 'càc', {}),
                ('Egg', 2, 'darab', {'unitKey': 'UNIT_36'}),
                ('Onion', 1, 'Stück', {'unitKey': 'UNIT_36'}),
                ('Tablespoons of oil', 2, '', {}), ('Tablespoons of icing sugar', 2, '', {})]:
            with self.subTest(name=name, unit=unit):
                result = await self.prices.offline_recipe_price(self.bridge,
                    {'ingredients': [{'name': name, 'quantity': quantity, 'unit': unit, **extra}]}, [])
                self.assertTrue(result['complete'] or result.get('budgetComplete'))
        for item in [{'name': 'Salt'}, {'name': 'Oil', 'quantity': 1},
                     {'name': 'Onion', 'quantity': 1, 'unit': 'morceau', 'unitKey': 'UNIT_36'},
                     {'name': 'Oil', 'quantity': 1, 'unit': 'cuillère', 'unitKey': 'UNIT_18'}]:
            self.assertFalse(any(o['unit'] in {'g', 'ml', 'pcs'} for o in self.measures.price_options(item)))

    async def test_green_asparagus_uses_its_retail_reference_and_user_price_wins(self):
        recipe = {'ingredients': [{'name': 'Green asparagus', 'quantity': 450, 'unit': 'g'}]}
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(result['totalsByCurrency'], {'EUR': 5.99})
        self.assertNotIn('fallbackIngredientCount', result)
        self.assertIn('12094-spargel-gruen-bund', result['ingredients'][0]['references'][0]['sourceUrl'])
        store = await self.store()
        await store.async_set_reference('n:green asparagus', amount=3, currency='EUR', basis_quantity=450,
                                       basis_unit='g', country='DE', source='manual')
        changed = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(changed['totalsByCurrency'], {'EUR': 3})
        self.assertFalse(changed['costCacheHit'])

    async def test_cache_persists_after_new_cache_instance(self):
        recipe = {'ingredients': [{'name': 'Onion', 'quantity': 2, 'unit': 'Stück'}]}
        first = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        existing = await self.cache.recipe_cost_cache_for_bridge(self.bridge)
        fresh = self.cache.Cook4MeRecipeCostCache(self.bridge)
        fresh._store.saved = deepcopy(existing._store.saved)
        await fresh.async_load()
        self.bridge._recipe_cost_cache_v1 = fresh
        with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('persistent cache missed')):
            again = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(again['costCacheHit'])
        self.assertEqual(first['totalsByCurrency'], again['totalsByCurrency'])


if __name__ == '__main__':
    unittest.main()
