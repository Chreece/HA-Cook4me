"""Price evidence, market boundaries, automatic updates and paid-price persistence."""
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import io
import json
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

import test_runtime_audit_v74 as runtime
import test_product_capture_v78 as capture


class AutomaticPriceTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = runtime.AuditTests.asyncTearDown

    def setUp(self):
        runtime.AuditTests.setUp(self)
        self.hass.config = runtime.NS(country='DE')
        async def executor(fn, *args):
            return fn(*args)
        self.hass.async_add_executor_job = executor
        self.costs = importlib.import_module(runtime.PREFIX + '.costs')
        self.calc = importlib.import_module(runtime.PREFIX + '.costing')
        self.prices = importlib.import_module(runtime.PREFIX + '.automatic_prices')
        self.cache = importlib.import_module(runtime.PREFIX + '.recipe_cost_cache')
        snapshot = importlib.import_module(runtime.PREFIX + '.price_snapshot')
        offline = patch.object(snapshot, '_load', return_value={})
        offline.start()
        self.addCleanup(offline.stop)
        self.today = datetime.now(timezone.utc).date().isoformat()
        self.ingredient = {'key': 'rice', 'name': 'Rice', 'canonicalName': 'rice'}
        self.recipe = {'servings': 2, 'ingredients': [{**self.ingredient, 'quantity': 200, 'unit': 'g'}]}

    async def store(self):
        await self.prices.price_settings(self.bridge)
        return await self.costs.cost_store_for_bridge(self.bridge)

    def observed(self, **changes):
        return {'id': 7, 'barcode': '12345678', 'amount': 3, 'currency': 'EUR', 'basisQuantity': 500,
                'basisUnit': 'g', 'pricePer': '', 'usable': True, 'date': self.today, 'country': 'DE',
                'location': 'Shop', 'source': 'open_prices', **changes}

    async def reference(self, identity='k:rice', **changes):
        store = await self.store()
        return await store.async_set_reference(identity, **dict(amount=3, currency='EUR', basis_quantity=500,
            basis_unit='g', country='DE', date=self.today, **changes))

    def raw(self, **changes):
        return {'id': 7, 'type': 'PRODUCT', 'product_code': '12345678', 'price': 3, 'currency': 'EUR',
                'date': self.today, 'price_per': None, 'location': {'osm_address_country_code': 'DE', 'osm_name': 'Shop'},
                'product': {'product_quantity': 500, 'product_quantity_unit': 'g', 'categories_tags': ['en:rices']}, **changes}

    def lookup(self, rows, **kwargs):
        with patch.object(self.costs.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps({'items': rows}).encode())) as call:
            result = self.costs.lookup_open_prices(**{'barcode':'12345678', 'country':'DE', 'currency':'EUR', **kwargs})
            self.url = call.call_args.args[0].full_url
            return result

    def test_real_api_package_null_basis_and_strict_country_currency_dates(self):
        rows = [self.raw(), self.raw(location={}), self.raw(location={'osm_address_country_code': 'FR'}),
                self.raw(currency='USD'), self.raw(date=None), self.raw(date='2001-01-01'), self.raw(date='2099-01-01'),
                self.raw(price_is_discounted=True), self.raw(duplicate_of=5), self.raw(product_code='other')]
        result = self.lookup(rows)
        self.assertEqual(result['usableCount'], 1)
        self.assertEqual(result['items'][0]['basisQuantity'], 500)
        params = parse_qs(urlparse(self.url).query)
        self.assertEqual(params['currency'], ['EUR'])
        self.assertIn('date__gte', params)
        self.assertNotIn('location_osm_address_country_code', params, 'Unsupported API filters must not be invented')

    def test_category_requires_exact_tag_and_explicit_measurement_basis(self):
        raw = self.raw(type='CATEGORY', product_code=None, category_tag='en:tomatoes', price_per='KILOGRAM', product=None)
        result = self.lookup([raw, {**raw, 'category_tag': 'en:potatoes'}, {**raw, 'price_per': None}], barcode='', category='en:tomatoes')
        self.assertEqual(result['usableCount'], 1)
        self.assertEqual(result['items'][0]['basisUnit'], 'kg')
        unit = self.lookup([{**raw, 'price_per': 'UNIT'}], barcode='', category='en:tomatoes')
        self.assertFalse(unit['items'][0]['usable'])
        unit = self.lookup([{**raw, 'price_per': 'UNIT', 'product_name': 'Tomate 1 Stück'}], barcode='', category='en:tomatoes')
        self.assertEqual(unit['items'][0]['basisUnit'], 'pcs')

    def test_packaged_category_checks_returned_product_taxonomy(self):
        result = self.lookup([self.raw(), self.raw(product={'categories_tags': ['en:rice-meals']})], barcode='', category='en:rices', category_type='PRODUCT')
        self.assertEqual(result['usableCount'], 1)
        missing = self.lookup([self.raw(product={})])
        self.assertEqual(missing['usableCount'], 0)

    async def test_defaults_follow_home_country_not_ui_language(self):
        self.assertEqual(await self.prices.price_settings(self.bridge), {'country': 'DE', 'currency': 'EUR', 'autoGlobalPrices': True})
        self.assertEqual(self.prices.country_currency('GB'), 'GBP')

    def test_country_currencies_work_without_optional_dependencies(self):
        for country, currency in {'DE': 'EUR', 'GR': 'EUR', 'BG': 'EUR', 'GB': 'GBP',
                                  'US': 'USD', 'CA': 'CAD', 'AU': 'AUD', 'CH': 'CHF', 'JP': 'JPY'}.items():
            self.assertEqual(self.prices.country_currency(country), currency)
            self.prices.validate_market(country, currency)
        with self.assertRaises(ValueError): self.prices.validate_market('XX', 'EUR')
        with self.assertRaises(ValueError): self.prices.validate_paid_price({'amount': 3, 'currency': 'ZZZ'})

    async def test_real_settings_handler_updates_country_currency_and_auto_preference(self):
        results, errors = [], []
        connection = runtime.NS(send_result=lambda _id, result: results.append(result),
                                send_error=lambda _id, code, error: errors.append(error))
        ns = {'_authorized': lambda *args: self.bridge, 'price_settings': self.prices.price_settings,
              'country_currency': self.prices.country_currency, 'validate_market': self.prices.validate_market,
              '_country': self.costs._country, '_currency': self.costs._currency,
              'cost_store_for_bridge': self.costs.cost_store_for_bridge,
              'legacy': runtime.NS(_send_error=lambda c,m,e:c.send_error(m['id'], 'error', str(e)))}
        runtime.functions('websocket_v34.py', {'ws_price_settings'}, ns)
        await ns['ws_price_settings'](self.hass, connection, {'id': 1, 'country': 'CA', 'auto_global_prices': False})
        self.assertEqual(results[0]['settings'], {'country': 'CA', 'currency': 'CAD', 'autoGlobalPrices': False})
        await ns['ws_price_settings'](self.hass, connection, {'id': 2, 'country': 'invalid'})
        self.assertTrue(errors)
        self.assertEqual((await self.store()).settings['country'], 'CA')

    async def test_unchanged_observation_preserves_recipe_cache(self):
        store = await self.store()
        first = await self.prices._store_observation(store, 'k:rice', self.observed())
        cache = await self.cache.recipe_cost_cache_for_bridge(self.bridge)
        await cache.async_cost(self.recipe, [], store)
        second = await self.prices._store_observation(store, 'k:rice', self.observed())
        self.assertEqual(first['updatedAt'], second['updatedAt'])
        self.assertTrue((await cache.async_cost(self.recipe, [], store))['costCacheHit'])

    async def test_real_catalog_id_without_name_resolves_and_costs(self):
        ingredient = {'id': 'M_FOOD_421', 'key': 'M_FOOD_421', 'name': 'Rice', 'canonicalName': 'Rice'}
        recipe = {'servings': 2, 'ingredients': [{'ingredientId': 'M_FOOD_421', 'quantity': 200, 'unit': 'g'}]}
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed()]}):
            result = await self.prices.recipe_price(self.bridge, recipe, [ingredient])
        self.assertEqual(result['ingredients'][0]['name'], 'Rice')
        self.assertEqual(result['totalsByCurrency'], {'EUR': 1.2})

    async def test_no_country_never_performs_global_lookup(self):
        self.hass.config.country = None
        with patch.object(self.prices, 'lookup_open_prices') as query:
            result = await self.prices.product_price(self.bridge, barcode='12345678', quantity=100, unit='g')
        query.assert_not_called()
        self.assertEqual(result['status'], 'choose_country')

    async def test_foreign_and_unknown_country_references_are_not_used(self):
        store = await self.store()
        await store.async_set_reference('k:rice', amount=3, currency='EUR', basis_quantity=500, basis_unit='g', country='FR')
        await store.async_set_reference('k:rice', amount=2, currency='EUR', basis_quantity=500, basis_unit='g')
        self.assertIsNone(store.best_reference('k:rice', country='DE', currency='EUR'))
        result = await self.calc.store_best_open_price(store, {'items': [self.observed(country='FR')]}, country='DE')
        self.assertIsNone(result)

    async def test_barcode_lookups_coalesce_and_scale_without_claiming_paid_price(self):
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed()]}) as query:
            results = await asyncio.gather(*(self.prices.product_price(self.bridge, barcode='12345678', quantity=200, unit='g') for _ in range(6)))
        self.assertEqual(query.call_count, 1)
        self.assertTrue(all(r['estimate'] == 1.2 for r in results))
        store = await self.store()
        self.assertFalse(any(row['identity'].startswith('lot:') for row in store._data['references'].values()))

    async def test_missing_observations_are_cached_and_failures_leave_cost_unknown(self):
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': False, 'reason': 'timeout', 'items': []}) as query:
            for _ in range(2):
                result = await self.prices.product_price(self.bridge, ingredient=self.ingredient, quantity=200, unit='g')
        self.assertEqual(query.call_count, 1)
        self.assertEqual(result['status'], 'source_unavailable')
        self.assertIsNone(result['estimate'])

    async def test_category_estimate_automatically_prices_recipe_and_servings(self):
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed()]}) as query:
            result = await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient])
        self.assertEqual(result['totalsByCurrency'], {'EUR': 1.2})
        self.assertEqual(result['perServingByCurrency'], {'EUR': .6})
        self.assertTrue(result['complete'])
        self.assertTrue(result['estimated'])
        self.assertEqual(query.call_args.kwargs['category'], 'en:rices')
        self.assertEqual(result['ingredients'][0]['references'][0]['source'], 'open_prices_category')

    def test_no_fuzzy_category_mapping_for_prepared_or_unknown_ingredients(self):
        self.assertIsNone(self.prices.category_for({'canonicalName': 'Rice pudding'}))
        self.assertIsNone(self.prices.category_for({'canonicalName': 'Cooked rice with seafood'}))
        self.assertEqual(self.prices.category_for({'canonicalName': 'Rice'}), ('en:rices', 'PRODUCT'))

    async def test_unpriced_stock_falls_back_to_generic_price_and_unknown_quantities_reduce_coverage(self):
        await self.reference()
        inventory = [{**self.ingredient, 'unit': 'g', 'quantity': 500, 'lots': [{'id': 'unpriced', 'quantity': 500}]}]
        recipe = {**self.recipe, 'ingredients': self.recipe['ingredients'] + [{'name': 'Salt to taste'}]}
        result = self.calc.calculate_recipe_cost(recipe, inventory, await self.store())
        self.assertEqual(result['totalsByCurrency'], {'EUR': 1.2})
        self.assertEqual(result['coverage'], .5)
        self.assertFalse(result['complete'])
        self.assertEqual(result['missingIngredientCount'], 1)

    async def test_actual_paid_price_zero_and_foreign_currency_remain_exact(self):
        msg = {'quantity': 500, 'unit': 'g', 'paid_price': {'amount': 0, 'currency': 'USD', 'country': 'US'}}
        await self.prices.save_product_prices(self.bridge, self.ingredient, 'paid', msg, {})
        inventory = [{**self.ingredient, 'unit': 'g', 'quantity': 500, 'lots': [{'id': 'paid', 'quantity': 500}]}]
        result = self.calc.calculate_recipe_cost(self.recipe, inventory, await self.store())
        self.assertEqual(result['totalsByCurrency'], {'USD': 0})
        self.assertEqual(result['exactPurchaseCoverage'], 1)
        self.assertFalse(result['estimated'])
        self.assertFalse(result['currencyConversionApplied'])

    async def test_manual_payment_persists_reusable_ingredient_estimate(self):
        msg = {'quantity': 500, 'unit': 'g', 'paid_price': {'amount': 2, 'currency': 'EUR'}}
        await self.prices.save_product_prices(self.bridge, self.ingredient, 'paid', msg, {})
        result = self.calc.calculate_recipe_cost(self.recipe, [], await self.store())
        self.assertEqual(result['totalsByCurrency'], {'EUR': .8})
        self.assertTrue(result['estimated'])

    async def test_cache_recalculates_for_composite_key_price_changes(self):
        await self.reference()
        store = await self.store()
        cache = await self.cache.recipe_cost_cache_for_bridge(self.bridge)
        first = await cache.async_cost(self.recipe, [], store)
        self.assertTrue((await cache.async_cost(self.recipe, [], store))['costCacheHit'])
        await store.async_set_reference('k:rice', amount=5, currency='EUR', basis_quantity=500, basis_unit='g', country='DE')
        second = await cache.async_cost(self.recipe, [], store)
        self.assertNotEqual(first['pricingFingerprint'], second['pricingFingerprint'])
        self.assertEqual(second['totalsByCurrency'], {'EUR': 2})
        self.assertFalse(second['costCacheHit'])

    async def test_price_write_failure_rolls_back_memory(self):
        store = await self.store()
        before = deepcopy(store._data)
        store._store.async_save = AsyncMock(side_effect=OSError('disk full'))
        with self.assertRaises(OSError):
            await store.async_set_reference('k:rice', amount=3, currency='EUR', basis_quantity=500, basis_unit='g')
        self.assertEqual(store._data, before)
        with self.assertRaises(OSError):
            await store.async_set_settings(country='GR')
        self.assertEqual(store._data, before)

    async def test_auto_off_uses_saved_prices_without_network(self):
        store = await self.store()
        await store.async_set_settings(auto_global_prices=False)
        await self.reference()
        with patch.object(self.prices, 'lookup_open_prices') as query:
            result = await self.prices.recipe_price(self.bridge, self.recipe, [])
        query.assert_not_called()
        self.assertEqual(result['totalsByCurrency'], {'EUR': 1.2})

    async def test_missing_mass_to_piece_conversion_never_invents_a_weight(self):
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed(basisUnit='pcs', basisQuantity=1)]}):
            result = await self.prices.product_price(self.bridge, ingredient=self.ingredient, quantity=200, unit='g')
        self.assertIsNone(result['estimate'])
        self.assertIsNone(result['reference'])

    async def test_old_external_price_refreshes_and_wrong_country_does_not_replace(self):
        store = await self.store()
        ref = await self.prices._store_observation(store, 'barcode:12345678', self.observed())
        for row in store._data['references'].values():
            row['updatedAt'] = (datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
        with patch.object(self.prices, 'lookup_open_prices', return_value={'ok': True, 'items': [self.observed(country='FR', amount=99)]}) as query:
            result = await self.prices.product_price(self.bridge, barcode='12345678', quantity=200, unit='g')
        self.assertEqual(query.call_count, 1)
        self.assertEqual(result['estimate'], 1.2)

    async def test_paid_price_validation_precedes_stock_and_retry_is_idempotent(self):
        ns = capture.ProductCaptureTests.api(self)
        ns['save_product_prices'] = self.prices.save_product_prices
        msg = {'id': 1, 'entry_id': 'one', 'request_id': 'paid-price-product-01', 'ingredient': self.ingredient,
               'quantity': 500, 'unit': 'g', 'lot_metadata': {'storageLocationId': 'pantry'},
               'paid_price': {'amount': -1, 'currency': 'EUR'}}
        await ns['ws_product_add'](self.hass, self.connection, msg)
        self.assertEqual(self.errors[0][0], 'product_validation')
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'], [])
        msg['paid_price']['amount'] = 2
        await ns['ws_product_add'](self.hass, self.connection, msg)
        await ns['ws_product_add'](self.hass, self.connection, msg)
        self.assertFalse(self.results[-1]['warnings'])
        self.assertEqual(self.results[0]['lotId'], self.results[1]['lotId'])
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'][0]['quantity'], 500)
        self.assertEqual((await self.store()).best_reference('lot:' + self.results[0]['lotId'])['amount'], 2)

    async def test_price_failure_after_stock_can_be_retried_without_duplicate_stock(self):
        ns = capture.ProductCaptureTests.api(self)
        ns['save_product_prices'].side_effect = OSError('disk full')
        msg = {'id': 1, 'entry_id': 'one', 'request_id': 'paid-price-product-02', 'ingredient': self.ingredient,
               'quantity': 500, 'unit': 'g', 'lot_metadata': {'storageLocationId': 'pantry'},
               'paid_price': {'amount': 2, 'currency': 'EUR'}}
        await ns['ws_product_add'](self.hass, self.connection, msg)
        self.assertIn('prices could not be saved', self.results[0]['warnings'][0])
        ns['save_product_prices'] = self.prices.save_product_prices
        await ns['ws_product_add'](self.hass, self.connection, msg)
        self.assertFalse(self.results[1]['warnings'])
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'][0]['quantity'], 500)

if __name__ == '__main__':
    unittest.main()
