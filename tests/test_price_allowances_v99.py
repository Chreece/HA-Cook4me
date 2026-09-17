"""Zero allowances must never masquerade as measured quantities or price evidence."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import patch

import test_price_gaps_v87 as previous


class PriceAllowanceTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(previous.PriceGapTests.setUpClass.__func__)
    setUp = previous.PriceGapTests.setUp
    asyncTearDown = previous.PriceGapTests.asyncTearDown
    store = previous.PriceGapTests.store

    async def test_basics_are_explicit_zero_budget_without_known_coverage(self):
        recipe = {'servings': 2, 'ingredients': [{'name': name} for name in
                  ['Salt', 'Pepper', 'Ground black pepper', 'Salt and pepper', 'Water']]}
        original = deepcopy(recipe)
        store = await self.store()
        saved = deepcopy(store._data['references'])
        for method in [self.prices.offline_recipe_price, self.prices.recipe_price]:
            result = await method(self.bridge, recipe, [])
            self.assertEqual(result['budgetTotalsByCurrency'], {'EUR': 0})
            self.assertEqual(result['budgetPerServingByCurrency'], {'EUR': 0})
            self.assertTrue(result['budgetComplete'])
            self.assertEqual(result['zeroCostIngredientCount'], 5)
            self.assertEqual(result['priceConfidence'], 'assumed')
            self.assertEqual(result['coverage'], 0)
            self.assertFalse(result['complete'])
            self.assertEqual(result['totalsByCurrency'], {})
            self.assertNotIn('fallbackIngredientCount', result)
            for row in result['ingredients']:
                self.assertFalse(row['priced'])
                self.assertEqual(row['priceStatus'], 'unmeasured_basic_zero')
                self.assertEqual(row['costsByCurrency'], {'EUR': 0})
                self.assertFalse(row['zeroCostAllowance']['quantityInferred'])
                self.assertFalse(row.get('references'))
        self.assertEqual(recipe, original)
        self.assertEqual(store._data['references'], saved)

    async def test_measured_duplicate_salt_and_weights_keep_saved_prices(self):
        store = await self.store()
        await store.async_set_reference('n:salt', amount=2, currency='EUR', basis_quantity=100,
                                        basis_unit='g', country='DE', source='manual')
        recipe = {'ingredients': [{'name': 'Salt'}, {'name': 'Salt', 'quantity': 10, 'unit': 'g'},
                                   {'name': 'Salt', 'weight': {'quantity': 5, 'unit': 'g'}}]}
        original = deepcopy(recipe)
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(result['budgetTotalsByCurrency'], {'EUR': .30})
        self.assertEqual(result['totalsByCurrency'], {'EUR': .30})
        self.assertEqual(result['zeroCostIngredientCount'], 1)
        self.assertEqual([row['coverage'] for row in result['ingredients']], [0, 1, 1])
        self.assertEqual(recipe, original)

    async def test_unknown_units_invalid_numbers_and_other_foods_are_not_free(self):
        items = [{'name': name} for name in ['Salted butter', 'Salt cod', 'Olive oil', 'Saffron',
                 'Watercress', 'Watermelon', 'Bell pepper', 'Salt, pepper and oil', 'Water or stock']]
        items += [{'name': 'Salt', 'quantity': value} for value in [1, 0, -1, True, 'bad', float('inf')]]
        items += [{'name': 'Pepper', 'ingredientId': key} for key in ['M_FOOD_377', 'M_FOOD_389']]
        result = await self.prices.offline_recipe_price(self.bridge, {'ingredients': items}, self.catalog['ingredients'])
        self.assertFalse(any(row.get('zeroCostAllowance') for row in result['ingredients']))
        self.assertFalse(result.get('budgetComplete'))
        self.assertEqual(result['priceConfidence'], 'unavailable')

    async def test_catalog_identity_and_seasoning_units_are_authoritative(self):
        recipe = {'ingredients': [
            {'name': 'Πιπέρι', 'ingredientId': 'M_FOOD_388'},
            {'name': 'Pepper', 'ingredientId': 'M_FOOD_377', 'unitKey': 'UNIT_42'},
            {'name': 'Pepper', 'ingredientId': 'M_FOOD_377'}]}
        result = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        self.assertEqual([bool(row.get('zeroCostAllowance')) for row in result['ingredients']], [True, True, False])
        self.assertEqual(result['priceConfidence'], 'partial')

    async def test_disabled_external_estimates_still_allow_basics_in_selected_currency(self):
        store = await self.store()
        await store.async_set_settings(auto_global_prices=False, currency='USD', country='US')
        result = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [{'name': 'Water'}]}, [])
        self.assertEqual(result['budgetTotalsByCurrency'], {'USD': 0})
        self.assertEqual(result['priceConfidence'], 'assumed')

    async def test_purchase_currency_is_preserved_and_excluded_items_are_not_basics(self):
        await self.bridge.recipe_hub.async_inventory_add({'name': 'Rice'}, quantity=100, unit='g')
        lot = self.bridge.recipe_hub.profile['houseIngredients'][0]['lots'][0]
        store = await self.store()
        await store.async_set_reference('lot:' + lot['id'], amount=2, currency='USD', basis_quantity=100,
                                        basis_unit='g', country='US', source='purchase', confidence='exact_purchase')
        recipe = {'ingredients': [{'name': 'Rice', 'quantity': 100, 'unit': 'g'}]}
        exact = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(exact['priceConfidence'], 'personal')
        self.assertEqual(exact['totalsByCurrency'], {'USD': 2})
        recipe['ingredients'].append({'name': 'Salt'})
        result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(result['budgetTotalsByCurrency'], {'USD': 2, 'EUR': 0})
        self.assertEqual(result['priceConfidence'], 'assumed')
        self.assertFalse(result['currencyConversionApplied'])
        for classification in ['equipment', 'other']:
            result = await self.prices.offline_recipe_price(self.bridge,
                {'ingredients': [{'ingredientId': 'excluded', 'name': 'Salt'}]},
                [{'id': 'excluded', 'canonicalName': 'Salt', 'classification': classification}])
            self.assertFalse(result['ingredients'][0].get('zeroCostAllowance'))

    async def test_confidence_distinguishes_saved_reference_assumed_and_partial(self):
        store = await self.store()
        recipe = {'ingredients': [{'name': 'Rice', 'quantity': 100, 'unit': 'g'}]}
        reference = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(reference['priceConfidence'], 'reference')
        await store.async_set_reference('n:rice', amount=1, currency='EUR', basis_quantity=100,
                                        basis_unit='g', country='DE', source='manual')
        saved = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertEqual(saved['priceConfidence'], 'personal')
        for name, confidence in [('Salt', 'assumed'), ('Saffron', 'partial')]:
            result = await self.prices.offline_recipe_price(self.bridge,
                {'ingredients': [*recipe['ingredients'], {'name': name}]}, [])
            self.assertEqual(result['priceConfidence'], confidence)
        estimate = await self.prices.offline_recipe_price(self.bridge,
            {'ingredients': [{'ingredientId': 'basic-seasoning', 'name': 'Salt and pepper', 'quantity': 1, 'unit': 'g'}]}, [{'id': 'basic-seasoning', 'canonicalName': 'Salt and pepper', 'classification': 'food'}])
        self.assertEqual(estimate['priceConfidence'], 'assumed')
        self.assertTrue(estimate['fallbackIngredientCount'])

    async def test_real_translated_cards_and_persistent_cache_retain_allowances(self):
        release = importlib.import_module(self.prices.__package__ + '.release_catalog')
        await release.async_warm_release_catalog(self.hass)
        recipe = release.recipe_by_variant('288189', language='el', configured_language='el', country='DE')
        original = deepcopy(recipe)
        result = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        self.assertTrue(result['zeroCostIngredientCount'])
        self.assertTrue(result['budgetComplete'])
        self.assertEqual(result['priceConfidence'], 'assumed')
        existing = await self.cache.recipe_cost_cache_for_bridge(self.bridge)
        fresh = self.cache.Cook4MeRecipeCostCache(self.bridge)
        fresh._store.saved = deepcopy(existing._store.saved)
        await fresh.async_load()
        self.bridge._recipe_cost_cache_v1 = fresh
        with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('persistent cache missed')):
            again = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        self.assertTrue(again['costCacheHit'])
        self.assertEqual(again['budgetTotalsByCurrency'], result['budgetTotalsByCurrency'])
        self.assertEqual(recipe, original)


if __name__ == '__main__':
    unittest.main()
