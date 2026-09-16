"""Manual price refresh must fetch new evidence without replacing purchase facts."""
import asyncio
from copy import deepcopy
import time
import unittest
from unittest.mock import AsyncMock, patch

import test_automatic_prices_v79 as previous
import test_runtime_audit_v74 as runtime


class PriceRefreshTests(unittest.IsolatedAsyncioTestCase):
    setUp = previous.AutomaticPriceTests.setUp
    asyncTearDown = previous.AutomaticPriceTests.asyncTearDown
    store = previous.AutomaticPriceTests.store
    reference = previous.AutomaticPriceTests.reference
    observed = previous.AutomaticPriceTests.observed

    async def test_refresh_bypasses_fresh_observation_and_derived_cost_cache(self):
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed()]}) as lookup:
            first = await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient])
            lookup.return_value = {'ok': True, 'items': [self.observed(amount=6)]}
            cached = await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient])
            self.assertEqual(lookup.call_count, 1)
            self.assertEqual(cached['totalsByCurrency'], first['totalsByCurrency'])
            refreshed = await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient], refresh_since=time.monotonic())
            self.assertEqual(lookup.call_count, 2)
            self.assertEqual(refreshed['totalsByCurrency'], {'EUR': 2.4})
            self.assertTrue(refreshed['refreshed']); self.assertFalse(refreshed['costCacheHit'])
            self.assertEqual(refreshed['refreshPolicy']['observationsSeconds'], 86400)

    async def test_manual_refresh_bypasses_cached_miss_and_auto_off_without_changing_preference(self):
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': []}) as lookup:
            await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient])
            await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient])
            self.assertEqual(lookup.call_count, 2)
            store = await self.store(); await store.async_set_settings(auto_global_prices=False)
            lookup.return_value = {'ok': True, 'items': [self.observed()]}
            result = await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient], refresh_since=time.monotonic())
            self.assertTrue(result['complete']); self.assertEqual(lookup.call_count, 3)
            self.assertFalse(store.settings['autoGlobalPrices'])

    async def test_batch_coalesces_duplicate_ingredients_and_authenticates_once(self):
        results, errors = [], []
        connection = runtime.NS(send_result=lambda _id, value: results.append(value))
        authorize = unittest.mock.Mock(return_value=self.bridge)
        ns = {'preview_cache_token': self.cache.preview_cache_token, '_authorized': authorize, 'v11': runtime.NS(_ingredient_catalog=AsyncMock(return_value={'items': [self.ingredient]})),
              'asyncio': asyncio, 'time': time, 'recipe_price': self.prices.recipe_price,
              'legacy': runtime.NS(_send_error=lambda *args: errors.append(args))}
        runtime.functions('websocket_v34.py', {'ws_recipe_cost_refresh'}, ns)
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed()]}) as lookup:
            second = deepcopy(self.recipe); second['ingredients'][0]['quantity'] = 400
            await ns['ws_recipe_cost_refresh'](self.hass, connection, {'id': 1, 'entry_id': 'one', 'recipes': [self.recipe, second]})
            self.assertFalse(errors); self.assertEqual(authorize.call_count, 1); self.assertEqual(lookup.call_count, 1)
            self.assertEqual([x['totalsByCurrency'] for x in results[0]['costs']], [{'EUR': 1.2}, {'EUR': 2.4}])
            authorize.side_effect = PermissionError('denied')
            await ns['ws_recipe_cost_refresh'](self.hass, connection, {'id': 2, 'recipes': [self.recipe]})
            self.assertEqual(len(errors), 1); self.assertEqual(lookup.call_count, 1)

    async def test_local_catalog_id_product_price_is_accepted(self):
        results, errors = [], []
        ingredient = {'id': 'local:en:rice', 'ingredientId': 'local:en:rice', 'name': 'Rice', 'canonicalName': 'Rice'}
        ns = {'preview_cache_token': self.cache.preview_cache_token, '_authorized': lambda *args: self.bridge,
              'v11': runtime.NS(_ingredient_catalog=AsyncMock(return_value={'items': [ingredient]})),
              'inventory_identity': self.prices.inventory_identity, 'product_price': self.prices.product_price,
              'legacy': runtime.NS(_send_error=lambda *args: errors.append(args))}
        runtime.functions('websocket_v34.py', {'ws_product_price'}, ns)
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed()]}):
            await ns['ws_product_price'](self.hass, runtime.NS(send_result=lambda _id, result: results.append(result)),
                                         {'id': 1, 'ingredient': {'key': 'local:en:rice', 'name': 'Rice'}, 'quantity': 200, 'unit': 'g'})
        self.assertFalse(errors); self.assertEqual(results[0]['estimate'], 1.2)
        self.assertEqual(results[0]['reference']['identity'], 'k:local:en:rice')

    async def test_refresh_preserves_user_price_and_reports_provider_failure(self):
        store = await self.store()
        await store.async_set_reference('k:rice', amount=1, currency='EUR', basis_quantity=500,
                                       basis_unit='g', country='DE', source='manual', confidence='user_entered')
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed(amount=100)]}):
            result = await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient], refresh_since=time.monotonic())
        self.assertEqual(result['totalsByCurrency'], {'EUR': .4})
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': False, 'items': []}):
            result = await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient], refresh_since=time.monotonic())
        self.assertEqual(result['totalsByCurrency'], {'EUR': .4}); self.assertTrue(result['priceLookupIncomplete'])

    async def test_missing_price_reasons_are_specific(self):
        recipe = {'ingredients': [{'key': 'custom', 'name': 'Mystery dish', 'quantity': 5, 'unit': 'g'},
                                  {'key': 'rice', 'name': 'Rice', 'quantity': 2, 'unit': 'pcs'},
                                  {'key': 'no-amount', 'name': 'Salt'}]}
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed()]}):
            result = await self.prices.recipe_price(self.bridge, recipe, [self.ingredient])
        self.assertEqual([x['priceStatus'] for x in result['ingredients']], ['category_unmapped', 'basis_missing', 'recipe_amount_unknown'])
        self.assertFalse(result['complete'])

    def test_verified_taxonomy_tags_and_distinct_food_forms(self):
        for name, tag in [('tofu', 'en:plain-tofu'), ('zucchini', 'en:zucchini'), ('garlic', 'en:garlic'),
                          ('brown rice', 'en:brown-rices'), ('canned chickpeas', 'en:canned-chickpeas'),
                          ('extra virgin olive oil', 'en:extra-virgin-olive-oils')]:
            self.assertEqual(self.prices.category_for({'canonicalName': name})[0], tag)
        for name in ['Rice pudding', 'Cooked rice', 'Butter and olive oil', 'Cheese with salt and pepper']:
            self.assertIsNone(self.prices.category_for({'canonicalName': name}))
        row = self.prices.canonical_recipe({'ingredients': [{'id': 'local:en:rice', 'quantity': 2, 'unit': 'g'}]},
                                           [{'id': 'local:en:rice', 'name': 'Rice'}])['ingredients'][0]
        self.assertEqual(row['key'], 'local:en:rice'); self.assertEqual(row['canonicalName'], 'Rice')


if __name__ == '__main__': unittest.main()
