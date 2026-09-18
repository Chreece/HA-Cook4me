"""Form-specific offline references and quantity evidence added in v96."""
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

    async def test_new_references_are_reachable_and_market_bound(self):
        names = ['Tarragon', 'Dried tarragon', 'Ground nutmeg', 'Whole nutmeg',
                 'Fresh goat cheese', 'Allspice', 'Fish sauce', 'Green lentils',
                 'Salmon', 'Dried farfalle pasta', 'Dried dill']
        recipe = {'ingredients': [{'name': name, 'quantity': 1 if name == 'Whole nutmeg' else 100,
                  'unit': 'pcs' if name == 'Whole nutmeg' else 'ml' if name == 'Fish sauce' else 'g'} for name in names]}
        original = deepcopy(recipe)
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(result['complete'], result)
        self.assertNotIn('fallbackIngredientCount', result)
        self.assertTrue(all(r['references'] and r['costsByCurrency']['EUR'] > 0 for r in result['ingredients']))
        self.assertEqual(recipe, original)
        added = [r for r in self.evidence['observations'] if 'v96-20260916' in str(r['id'])]
        self.assertEqual(len(added), 11)
        for ref in added:
            with self.subTest(reference=ref['id']), patch.object(self.snapshot, '_load', return_value={'observations': added}):
                query = dict(category=ref['categories'][0], country='DE', currency='EUR', unit=ref['basisUnit'])
                self.assertIn(ref['id'], [r['id'] for r in self.snapshot.snapshot_observations(**query)])
                self.assertFalse(self.snapshot.snapshot_observations(**{**query, 'country': 'FR'}))
                self.assertFalse(self.snapshot.snapshot_observations(**{**query, 'currency': 'USD'}))

    async def test_published_portions_and_fish_sauce_mass_use_evidence(self):
        for name, amount, unit, grams in [('Dried tarragon', 1, 'tsp', .6),
                ('Dried tarragon', 2, 'tbsp', 3.6), ('Dried dill', 1, 'tsp', 1),
                ('Dried dill', 2, 'tbsp', 6.2), ('Nutmeg', 1, 'tsp', 2.2),
                ('Grated nutmeg', 1, 'tbsp', 7), ('Fish sauce', 1, 'tbsp', 18)]:
            with self.subTest(name=name, unit=unit):
                item = {'name': name, 'quantity': amount, 'unit': unit}
                options = self.measures.price_options(item)
                self.assertTrue(any(o['unit'] == 'g' and abs(o['quantity'] - grams) < .0001 for o in options), options)
                cost = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [item]}, [])
                self.assertTrue(cost['complete'], cost)
                self.assertTrue(cost['ingredients'][0]['quantityEstimate']['sourceUrl'].startswith('https://'))
        cost = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [
            {'name': 'Fish sauce', 'quantity': 18, 'unit': 'g'}]}, [])
        row = cost['ingredients'][0]
        self.assertTrue(cost['complete'])
        self.assertEqual(row['quantityEstimate']['quantity'], 15)
        self.assertEqual(row['quantityEstimate']['unit'], 'ml')
        self.assertEqual(row['quantityEstimate']['fdcId'], 174531)
        self.assertEqual(cost['totalsByCurrency'], {'EUR': .23})

    async def test_fresh_dried_whole_and_prepared_forms_stay_separate(self):
        for fresh, dried in [('Tarragon', 'Dried tarragon'), ('Dill', 'Dried dill'),
                             ('Whole nutmeg', 'Ground nutmeg')]:
            self.assertNotEqual(self.prices.category_for({'name': fresh}), self.prices.category_for({'name': dried}))
        for name, unit in [('Fresh tarragon', 'tsp'), ('Tarragon', 'tbsp'), ('Fresh dill', 'tbsp'),
                           ('Whole nutmeg', 'tbsp'), ('Ground nutmeg', 'pcs'), ('Allspice', 'pcs'),
                           ('Allspice', 'tsp'), ('Salmon', 'pcs'), ('Green lentils', 'can')]:
            with self.subTest(name=name, unit=unit):
                self.assertFalse(any(o['unit'] == 'g' for o in self.measures.price_options(
                    {'name': name, 'quantity': 1, 'unit': unit})))
        for name in ['Cooked green lentils', 'Cooked farfalle pasta', 'Ground tarragon', 'Ground allspice']:
            self.assertIsNone(self.prices.category_for({'name': name}))
        whole = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [
            {'name': 'Nutmeg', 'quantity': 1, 'unit': 'pcs'}]}, [])
        self.assertEqual(whole['totalsByCurrency'], {'EUR': 1.15})
        self.assertEqual(whole['ingredients'][0]['references'][0]['basisUnit'], 'pcs')
        self.assertFalse(self.measures.price_options({'name': 'Nutmeg'}))

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
        for ident, ingredient in [('244633', 'Fish sauce'), ('248445', 'Salmon'), ('632240', 'Nutmeg'),
                                 ('556145', 'Fresh goat cheese'), ('411044', 'Dried farfalle pasta'),
                                 ('454339', 'Green lentils'), ('297474', 'Allspice')]:
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
        recipe = {'ingredients': [{'name': 'Fish sauce', 'quantity': 100, 'unit': 'ml'}]}
        cost = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(cost['totalsByCurrency'], {'EUR': 1.56})
        existing = await self.cache.recipe_cost_cache_for_bridge(self.bridge)
        fresh = self.cache.Cook4MeRecipeCostCache(self.bridge)
        fresh._store.saved = deepcopy(existing._store.saved)
        await fresh.async_load()
        self.bridge._recipe_cost_cache_v1 = fresh
        with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('persistent cache missed')):
            again = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(again['costCacheHit'])
        store = await self.store()
        await store.async_set_reference(cost['ingredients'][0]['identity'], amount=1, currency='EUR',
                                        basis_quantity=100, basis_unit='ml', country='DE', source='manual')
        actual = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(actual['totalsByCurrency'], {'EUR': 1})
        self.assertFalse(actual['costCacheHit'])


if __name__ == '__main__':
    unittest.main()
