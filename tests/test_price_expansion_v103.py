"""Plain miso, fresh shimeji and measured-water evidence in v103."""
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
        recipe = {'ingredients': [{'name': 'Miso', 'quantity': 100, 'unit': 'g'},
                                  {'name': 'Shimeji mushrooms', 'quantity': 150, 'unit': 'g'}]}
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(result['complete'])
        self.assertNotIn('fallbackIngredientCount', result)
        added = [row for row in self.evidence['observations'] if 'v103-20260917' in str(row['id'])]
        self.assertEqual(len(added), 2)
        for ref in added:
            query = dict(category=ref['categories'][0], country='DE', currency='EUR', unit='g')
            with patch.object(self.snapshot, '_load', return_value={'observations': added}):
                self.assertIn(ref['id'], [row['id'] for row in self.snapshot.snapshot_observations(**query)])
                self.assertFalse(self.snapshot.snapshot_observations(**{**query, 'country': 'FR'}))
                self.assertFalse(self.snapshot.snapshot_observations(**{**query, 'currency': 'USD'}))
            for age in [181, -1]:
                expired = {**ref, 'date': (date.today() - timedelta(days=age)).isoformat()}
                with patch.object(self.snapshot, '_load', return_value={'observations': [expired]}):
                    self.assertFalse(self.snapshot.snapshot_observations(**query))

    async def test_package_costs_and_miso_spoon_estimates(self):
        for name, amount, unit, expected in [
                ('Miso', 300, 'g', 3.49), ('Miso paste', 1, 'tbsp', .20),
                ('White miso', 2, 'tsp', .13), ('Shiro miso', 150, 'g', 1.75),
                ('Shimeji mushrooms', 150, 'g', 1.79), ('Fresh shimeji mushrooms', .3, 'kg', 3.58)]:
            with self.subTest(name=name, amount=amount, unit=unit):
                recipe = {'ingredients': [{'name': name, 'quantity': amount, 'unit': unit}]}
                original = deepcopy(recipe)
                cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
                self.assertEqual(cost['totalsByCurrency'], {'EUR': expected})
                self.assertEqual(cost['priceConfidence'], 'reference')
                self.assertTrue(cost['complete'])
                self.assertEqual(recipe, original)
        option = next(row for row in self.measures.price_options({'name': 'Miso', 'quantity': 2, 'unit': 'tbsp'}) if row['unit'] == 'g')
        self.assertEqual(option['quantity'], 34)
        self.assertEqual(option['estimate']['fdcId'], 172442)
        self.assertEqual(option['estimate']['portionId'], 90629)

    async def test_prepared_miso_and_mushroom_packages_do_not_infer_paste_or_weight(self):
        for name, quantity, unit, key in [('Miso', 600, 'ml', 'UNIT_35'), ('Miso', 1.2, 'l', 'UNIT_32'),
                                         ('Miso', 1, 'pcs', 'UNIT_41'), ('Shimeji mushrooms', 1, '袋', 'UNIT_100'),
                                         ('Shimeji mushrooms', 1, 'pcs', 'UNIT_41')]:
            ingredient = {'name': name, 'quantity': quantity, 'unit': unit, 'unitKey': key}
            self.assertFalse(any(row['unit'] == 'g' for row in self.measures.price_options(ingredient)))
            cost = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [ingredient]}, [])
            self.assertFalse(cost['ingredients'][0].get('references'))
        for name in ['Miso soup', 'Dashi miso', 'Dried shimeji mushrooms', 'Shimeji powder']:
            self.assertIsNone(self.prices.category_for({'name': name}))

    async def test_measured_water_uses_sourced_density_and_keeps_zero_allowances_distinct(self):
        for name in ['Water', 'Tap water']:
            for amount, unit, millilitres in [(350, 'g', 350), (2, 'kg', 2000)]:
                ingredient = {'name': name, 'quantity': amount, 'unit': unit}
                original = deepcopy(ingredient)
                options = self.measures.price_options(ingredient)
                conversion = next(row for row in options if row['unit'] == 'ml')
                self.assertEqual(conversion['quantity'], millilitres)
                self.assertIn('173647', conversion['estimate']['sourceUrl'])
                cost = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [ingredient]}, [])
                native = await self.prices.offline_recipe_price(self.bridge,
                    {'ingredients': [{'name': name, 'quantity': millilitres, 'unit': 'ml'}]}, [])
                self.assertEqual(cost['totalsByCurrency'], native['totalsByCurrency'])
                self.assertEqual(cost['ingredients'][0]['coverage'], 1)
                self.assertFalse(cost['ingredients'][0].get('zeroCostAllowance'))
                self.assertEqual(ingredient, original)
        for name in ['Water', 'Tap water', 'Miso', 'Shimeji mushrooms']:
            for amount in [None, 0, -1, True, float('nan'), float('inf')]:
                self.assertEqual(self.measures.price_options({'name': name, 'quantity': amount}), [])
        self.assertFalse(any(row['unit'] == 'ml' for row in self.measures.price_options({'name': 'Rose water', 'quantity': 100, 'unit': 'g'})))
        cost = await self.prices.offline_recipe_price(self.bridge,
            {'ingredients': [{'name': name} for name in ['Miso', 'Shimeji mushrooms', 'Salt', 'Water']]}, [])
        for row in cost['ingredients'][:2]:
            self.assertFalse(row.get('references'))
            self.assertFalse(row.get('zeroCostAllowance'))
        for row in cost['ingredients'][2:]:
            self.assertEqual(row['zeroCostAllowance']['amount'], 0)
            self.assertEqual(row['coverage'], 0)

    async def test_saved_user_price_wins_and_persistent_cache_is_reused(self):
        recipe = {'ingredients': [{'name': 'Miso', 'quantity': 100, 'unit': 'g'}]}
        cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(cost['totalsByCurrency'], {'EUR': 1.16})
        existing = await self.cache.recipe_cost_cache_for_bridge(self.bridge)
        fresh = self.cache.Cook4MeRecipeCostCache(self.bridge)
        fresh._store.saved = deepcopy(existing._store.saved)
        await fresh.async_load()
        self.bridge._recipe_cost_cache_v1 = fresh
        with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('persistent cache missed')):
            again = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(again['costCacheHit'])
        store = await self.store()
        await store.async_set_reference(cost['ingredients'][0]['identity'], amount=1.0, currency='EUR',
                                        basis_quantity=100, basis_unit='g', country='DE', source='manual')
        actual = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(actual['totalsByCurrency'], {'EUR': 1.0})
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
        for ident, ingredient, covered in [('396131', 'Miso', 1), ('670760', 'Miso', 1),
                                          ('349336', 'Shimeji mushrooms', 1), ('809878', 'Water', 1),
                                          ('337621', 'Miso', 0), ('669773', 'Miso', 0)]:
            with self.subTest(variant=ident):
                expanded = release.recipe_by_variant(ident, language='el', configured_language='el', country='DE')
                original = deepcopy(expanded)
                for recipe in [{'variantFunctionalId': ident}, expanded]:
                    await ns['ws_recipe_cost'](self.hass, connection, {'id': 1, 'offline_only': True, 'recipe': recipe})
                    self.assertFalse(errors, errors)
                    row = next(row for row in results[-1]['ingredients'] if row['name'].casefold() == ingredient.casefold())
                    self.assertEqual(row['coverage'], covered, row)
                    self.assertEqual(bool(row.get('references')), bool(covered))
                self.assertEqual(results[-1]['totalsByCurrency'], results[-2]['totalsByCurrency'])
                self.assertEqual(expanded, original)
                with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('reopening recalculated')):
                    await ns['ws_recipe_cost'](self.hass, connection, {'id': 1, 'offline_only': True, 'recipe': expanded})
                self.assertFalse(errors, errors)
                self.assertTrue(results[-1]['costCacheHit'])


if __name__ == '__main__':
    unittest.main()
