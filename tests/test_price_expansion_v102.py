"""Vegetarian offline references and food-specific quantity estimates in v102."""
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
                  for name, unit in [('Coconut cream', 'ml'), ('Split pea', 'g'), ('Shiitake mushroom', 'g'),
                                     ('Radish', 'g')]]}
        original = deepcopy(recipe)
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(result['complete'], result)
        self.assertNotIn('fallbackIngredientCount', result)
        self.assertTrue(all(row['references'] and row['costsByCurrency']['EUR'] > 0 for row in result['ingredients']))
        self.assertEqual(recipe, original)
        added = [row for row in self.evidence['observations'] if 'v102-20260917' in str(row['id'])]
        self.assertEqual(len(added), 4)
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

    async def test_package_costs_and_portion_estimates(self):
        for name, amount, unit, expected in [
                ('Coconut cream', 400, 'ml', 2.69), ('Unsweetened coconut cream', 2, 'tbsp', .20),
                ('Coconut cream', 15, 'g', .10), ('Split pea', 100, 'g', .60),
                ('Dried split peas', .5, 'kg', 2.99), ('Shiitake mushrooms', 2, 'pcs', .63),
                ('Fresh shiitake mushroom', 1, '', .32), ('Radish', 100, 'g', .38),
                ('Radishes', 10, 'pcs', .17)]:
            with self.subTest(name=name, amount=amount, unit=unit):
                recipe = {'ingredients': [{'name': name, 'quantity': amount, 'unit': unit}]}
                original = deepcopy(recipe)
                cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
                self.assertEqual(cost['totalsByCurrency'], {'EUR': expected})
                self.assertEqual(cost['priceConfidence'], 'reference')
                self.assertTrue(cost['complete'])
                self.assertEqual(recipe, original)
        for name, unit in [('Shiitake mushroom', 'packet'), ('Shiitake mushroom', 'slice'),
                           ('Radish', 'bunch'), ('Split pea', 'can'), ('Coconut cream', 'tin')]:
            cost = await self.prices.offline_recipe_price(self.bridge,
                {'ingredients': [{'name': name, 'quantity': 2, 'unit': unit}]}, [])
            self.assertFalse(cost['ingredients'][0].get('references'), cost)
        for name, category in [('Dried shiitake mushrooms', 'en:shiitake-mushrooms'),
                               ('Daikon radish', 'en:radishes'), ('Pickled radish', 'en:radishes'),
                               ('Cooked split peas', 'cook4me:dried-split-peas'),
                               ('Cream of coconut', 'en:coconut-creams'), ('Coconut butter', 'en:coconut-creams')]:
            found = self.prices.category_for({'name': name})
            self.assertNotEqual(found[0] if found else None, category)

    def test_portions_retain_primary_source_and_do_not_rewrite_amounts(self):
        for name, quantity, unit, expected, fdc in [
                ('Shiitake mushroom', 2, 'pcs', 38, '169242'),
                ('Fresh shiitake mushrooms', 1, '', 19, '169242'),
                ('Coconut cream', 2, 'tbsp', 30, '170580')]:
            ingredient = {'name': name, 'quantity': quantity, 'unit': unit}
            original = deepcopy(ingredient)
            option = next(row for row in self.measures.price_options(ingredient) if row['unit'] == 'g')
            self.assertAlmostEqual(option['quantity'], expected)
            self.assertIn(fdc, str(option['estimate']))
            self.assertEqual(ingredient, original)
        for amount in [None, 0, -1, True, float('nan'), float('inf')]:
            for name in ['Coconut cream', 'Split pea', 'Shiitake mushroom', 'Radish']:
                self.assertEqual(self.measures.price_options({'name': name, 'quantity': amount}), [])
        for unit_key in ['UNIT_49', 'UNIT_33']:
            options = self.measures.price_options({'name': 'Shiitake mushroom', 'quantity': 2,
                                                   'unit': '枚', 'unitKey': unit_key})
            self.assertFalse(any(row['unit'] == 'g' for row in options))

    async def test_unknown_quantities_and_basic_allowances_stay_distinct(self):
        recipe = {'ingredients': [{'name': name} for name in ['Coconut cream', 'Split pea', 'Shiitake mushroom', 'Radish', 'Salt', 'Water']]}
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
        recipe = {'ingredients': [{'name': 'Shiitake mushroom', 'quantity': 1}]}
        cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(cost['totalsByCurrency'], {'EUR': .32})
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
        for ident, ingredient in [('244633', 'Coconut cream'), ('237931', 'Coconut cream'), ('665704', 'Shiitake mushroom'),
                                 ('670760', 'Shiitake mushroom'), ('743854', 'Radish'),
                                 ('773948', 'Radish'), ('411575', 'Split pea')]:
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

    async def test_daikon_source_variants_do_not_use_red_radish_prices(self):
        release = importlib.import_module(self.prices.__package__ + '.release_catalog')
        await release.async_warm_release_catalog(self.hass)
        for ident in ['803230', '549806', '873706', '549973', '776826']:
            for language in ['ja', 'zh', 'el', 'de']:
                with self.subTest(variant=ident, language=language):
                    recipe = release.recipe_by_variant(ident, language=language, configured_language=language, country='DE')
                    original = deepcopy(recipe)
                    cost = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
                    row = next(row for row in cost['ingredients'] if row['name'] == 'Daikon radish')
                    self.assertFalse(any('frischekontor-radishes-v102' in ref['id'] for ref in row.get('references', [])))
                    self.assertEqual(recipe, original)
        raw = {'variantId': '873706', 'ingredients': [{'ingredientId': 'M_FOOD_412', 'quantity': .25}]}
        priced = self.prices.canonical_recipe(raw, self.catalog['ingredients'])
        self.assertFalse(any(row['unit'] == 'g' for row in self.measures.price_options(priced['ingredients'][0])))


if __name__ == '__main__':
    unittest.main()
