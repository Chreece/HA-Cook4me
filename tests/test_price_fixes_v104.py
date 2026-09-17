"""Prevent unrelated piece prices while preserving real household/reference costs."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import patch

import test_price_gaps_v87 as previous


class PriceFixTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(previous.PriceGapTests.setUpClass.__func__)
    setUp = previous.PriceGapTests.setUp
    asyncTearDown = previous.PriceGapTests.asyncTearDown
    store = previous.PriceGapTests.store

    def test_piece_benchmarks_require_a_sourced_mass(self):
        benchmarks = importlib.import_module(self.prices.__package__ + '.price_benchmarks')
        for name in ('Mint', 'Fresh mint', 'Shimeji mushrooms', 'Chestnuts', 'Daikon radish'):
            with self.subTest(name=name):
                item = {'name': name, 'quantity': 20, 'unit': 'pcs', 'priceCatalogMatched': True}
                self.assertIsNone(benchmarks.fallback_estimate(item, country='DE', currency='EUR'))
        # Unlike pieces must not be compared even inside one broad food group.
        item = {'name': 'Mint', 'quantity': 20, 'unit': 'pcs', 'priceCatalogMatched': True}
        with patch.object(benchmarks, '_group', return_value={'id': 'vegetables'}), patch.object(
                benchmarks, '_pools', return_value={('vegetables', 'pcs'): [{'rate': .94}]}):
            self.assertIsNone(benchmarks.fallback_estimate(item, country='DE', currency='EUR'))
        estimate = benchmarks.fallback_estimate({'name': 'Mint', 'quantity': 2, 'unit': 'tbsp',
            'priceCatalogMatched': True}, country='DE', currency='EUR')
        self.assertEqual(estimate['unit'], 'g')
        self.assertAlmostEqual(estimate['quantity'], 11.4)
        self.assertEqual(estimate['quantityEstimate']['fdcId'], 173475)

    async def test_screenshot_mint_is_missing_not_eighteen_euros_or_free(self):
        recipe = next(v for family in self.catalog['recipes'] for v in family['variants']
                      if str(v.get('variantId')) == '314559')
        original = deepcopy(recipe)
        result = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        self.assertEqual(result['budgetTotalsByCurrency'], {'EUR': 2.12})
        self.assertEqual(result['budgetPerServingByCurrency'], {'EUR': .53})
        self.assertFalse(result['budgetComplete'])
        self.assertEqual(result['priceConfidence'], 'partial')
        mint = next(row for row in result['ingredients'] if row['name'] == 'M_FOOD_308')
        self.assertEqual(mint['coverage'], 0)
        self.assertFalse(mint.get('costsByCurrency'))
        self.assertNotIn('fallbackEstimate', mint)
        self.assertNotIn('zeroCostAllowance', mint)
        self.assertEqual(recipe, original)

    async def test_brushchetta_no_longer_prices_four_slices_as_four_grocery_items(self):
        recipe = next(v for family in self.catalog['recipes'] for v in family['variants']
                      if str(v.get('variantId')) == '321369')
        result = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        self.assertEqual(result['budgetTotalsByCurrency'], {'EUR': 4.9})
        self.assertFalse(result['budgetComplete'])
        self.assertFalse(any(row.get('fallbackEstimate', {}).get('unit') == 'pcs' for row in result['ingredients']))

    async def test_native_piece_prices_and_manual_prices_remain_valid(self):
        recipe = {'ingredients': [{'name': 'Leaf gelatine', 'quantity': 2, 'unit': 'Blatt', 'unitKey': 'UNIT_24'}]}
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(result['complete'])
        self.assertGreater(result['totalsByCurrency']['EUR'], 0)
        recipe = {'ingredients': [{'name': 'Mint', 'quantity': 20, 'unit': 'pcs'}]}
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        store = await self.store()
        await store.async_set_reference(result['ingredients'][0]['identity'], amount=.5, currency='EUR',
            basis_quantity=20, basis_unit='pcs', country='DE', source='manual')
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(result['complete'])
        self.assertEqual(result['totalsByCurrency'], {'EUR': .5})

    async def test_old_price_cache_and_browser_token_are_invalidated(self):
        recipe = {'ingredients': [{'name': 'Mint', 'quantity': 20, 'unit': 'pcs'}]}
        cache = self.cache
        hash_value = cache._canonical_hash
        def old_hash(value):
            old = deepcopy(value)
            for key in ('quantityEvidenceVersion', 'calculatorVersion', 'evidenceVersion'):
                if key in old: old[key] = 103
            return hash_value(old)
        with patch.object(cache, '_canonical_hash', side_effect=old_hash):
            old = await self.prices.offline_recipe_price(self.bridge, recipe, [])
            old_token = await cache.preview_cache_token(self.bridge)
        current = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertFalse(current['costCacheHit'])
        self.assertNotEqual(current['pricingFingerprint'], old['pricingFingerprint'])
        self.assertNotEqual(await cache.preview_cache_token(self.bridge), old_token)
        again = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertTrue(again['costCacheHit'])


if __name__ == '__main__':
    unittest.main()
