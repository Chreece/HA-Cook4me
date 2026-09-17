"""Offline references, food portions and individual sheet/pod counts in v97."""
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
                  for name, unit in [('Leaf gelatine', 'pcs'), ('Sake', 'ml'), ('Mirin', 'ml'),
                                     ('Swede', 'g'), ('Wasabi', 'g')]]}
        original = deepcopy(recipe)
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(result['complete'], result)
        self.assertNotIn('fallbackIngredientCount', result)
        self.assertTrue(all(row['references'] and row['costsByCurrency']['EUR'] > 0 for row in result['ingredients']))
        self.assertEqual(recipe, original)
        added = [row for row in self.evidence['observations'] if 'v97-20260917' in str(row['id'])]
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

    async def test_food_specific_portions_and_mayonnaise_mass_use_evidence(self):
        for name, amount, unit, grams in [('Caper', 2, 'tbsp', 17.2), ('Capers', 1, 'tbsp', 8.6),
                ('Peanut butter', 2, 'tbsp', 32), ('Smooth peanut butter', 1, 'tbsp', 16),
                ('Mayonnaise', 1, 'tbsp', 13.8), ('Swede', 1, '', 386), ('Rutabaga', 1, 'pcs', 386)]:
            with self.subTest(name=name, unit=unit):
                item = {'name': name, 'quantity': amount, 'unit': unit}
                options = self.measures.price_options(item)
                self.assertTrue(any(o['unit'] == 'g' and abs(o['quantity'] - grams) < .0001 for o in options), options)
                cost = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [item]}, [])
                self.assertTrue(cost['complete'], cost)
                self.assertTrue(cost['ingredients'][0]['references'])
        cost = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [
            {'name': 'Mayonnaise', 'quantity': 13.8, 'unit': 'g'}]}, [])
        row = cost['ingredients'][0]
        self.assertEqual((row['quantityEstimate']['quantity'], row['quantityEstimate']['unit']), (15, 'ml'))
        self.assertEqual(row['quantityEstimate']['fdcId'], 171009)
        self.assertEqual(cost['totalsByCurrency'], {'EUR': .08})

    async def test_gelatine_sheets_use_individual_counts_without_mass_or_pack_guesses(self):
        for amount, unit, key in [(2, 'Blatt', 'UNIT_24'), (2, 'lapka', 'UNIT_98'),
                (2, 'pcs', ''), (2, '', ''), (.5, 'sheet', '')]:
            recipe = {'ingredients': [{'name': 'Leaf gelatine', 'quantity': amount, 'unit': unit, 'unitKey': key}]}
            original = deepcopy(recipe)
            cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
            self.assertTrue(cost['complete'], cost)
            self.assertEqual(cost['totalsByCurrency'], {'EUR': .12 if amount == .5 else .48})
            estimate = cost['ingredients'][0]['quantityEstimate']
            self.assertEqual((estimate['quantity'], estimate['unit']), (amount, 'pcs'))
            self.assertEqual(recipe, original)
        for name, amount, unit, key in [('Leaf gelatine', 2, 'g', 'UNIT_27'),
                ('Leaf gelatine', 2, 'packet', ''), ('Leaf gelatine', 21, '', ''),
                ('Gelatin powder', 2, 'sheet', ''), ('Gelatin', 2, '', '')]:
            options = self.measures.price_options({'name': name, 'quantity': amount, 'unit': unit, 'unitKey': key})
            self.assertFalse(any(o['unit'] == 'pcs' for o in options), options)
        self.assertFalse(self.measures.price_options({'name': 'Leaf gelatine'}))

    async def test_vanilla_pods_use_saved_per_pod_prices_and_keep_other_forms_separate(self):
        seed = {'ingredients': [{'name': 'Vanilla pod', 'quantity': 2, 'unit': 'gousse', 'unitKey': 'UNIT_28'}]}
        unpriced = await self.prices.offline_recipe_price(self.bridge, seed, [])
        self.assertFalse(unpriced['ingredients'][0]['references'])
        store = await self.store()
        await store.async_set_reference(unpriced['ingredients'][0]['identity'], amount=1.10, currency='EUR',
                                        basis_quantity=1, basis_unit='pcs', country='DE', source='manual')
        for amount, unit, key in [(2, 'gousse', 'UNIT_28'), (2, 'Zehe', 'UNIT_28'), (.5, '', '')]:
            recipe = {'ingredients': [{'name': 'Vanilla pod', 'quantity': amount, 'unit': unit, 'unitKey': key}]}
            original = deepcopy(recipe)
            cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
            self.assertEqual(cost['totalsByCurrency'], {'EUR': round(amount * 1.10, 2)})
            self.assertEqual(cost['ingredients'][0]['quantityEstimate']['unit'], 'pcs')
            self.assertEqual(recipe, original)
        for name, unit in [('Vanilla pod', 'g'), ('Vanilla pod', 'tsp'), ('Vanilla pod', 'packet'),
                           ('Vanilla pod', 'seed'), ('Vanilla extract', 'pod'), ('Wasabi', 'cm'),
                           ('Wasabi', 'tsp'), ('Swede', 'bunch')]:
            options = self.measures.price_options({'name': name, 'quantity': 1, 'unit': unit})
            self.assertFalse(any(o['unit'] == 'pcs' for o in options), options)
            if name in {'Wasabi', 'Swede'}:
                self.assertFalse(any(o['unit'] == 'g' for o in options), options)
        for name in ['Fresh wasabi root', 'Wasabi powder', 'Cooked swede']:
            self.assertIsNone(self.prices.category_for({'name': name}))

    async def test_saved_user_price_wins_and_persistent_cache_is_reused(self):
        recipe = {'ingredients': [{'name': 'Swede', 'quantity': 1}]}
        cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(cost['totalsByCurrency'], {'EUR': 1.42})
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
        for ident, ingredient in [('350366', 'Sake'), ('743854', 'Mirin'), ('938579', 'Leaf gelatine'),
                                 ('951823', 'Mayonnaise'), ('285390', 'Caper'), ('345651', 'Swede'),
                                 ('271369', 'Wasabi')]:
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
