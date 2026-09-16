"""Only the screenshot's quantity recovery, density pricing and cache changes."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import patch

import test_price_gaps_v87 as previous


class PriceConversionTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(previous.PriceGapTests.setUpClass.__func__)
    setUp = previous.PriceGapTests.setUp
    asyncTearDown = previous.PriceGapTests.asyncTearDown
    store = previous.PriceGapTests.store

    def screenshot_recipe(self):
        return next(v for f in self.catalog['recipes'] for v in f['variants'] if v['variantId'] == '848764')

    async def test_screenshot_card_and_open_recipe_agree_and_cache(self):
        runtime = previous.previous.runtime
        release = importlib.import_module(self.prices.__package__ + '.release_catalog')
        await release.async_warm_release_catalog(self.hass)
        results, errors = [], []
        namespace = {'__name__':self.prices.__package__+'.websocket_v34','__package__':self.prices.__package__,'_authorized':lambda *args:self.bridge, '_country':self.costs._country,
                     'offline_recipe_price':self.prices.offline_recipe_price,
                     'preview_cache_token':self.cache.preview_cache_token,
                     'legacy':runtime.NS(_send_error=lambda *args:errors.append(str(args[-1])))}
        runtime.functions('websocket_v34.py', {'ws_recipe_cost'}, namespace)
        connection = runtime.NS(send_result=lambda _id, value:results.append(value))
        detailed = release.recipe_by_variant('848764', language='el', configured_language='el', country='DE')
        original = deepcopy(detailed)
        for recipe in [{'variantFunctionalId':'848764'}, detailed]:
            await namespace['ws_recipe_cost'](self.hass, connection, {'id':1,'offline_only':True,'recipe':recipe})
            self.assertFalse(errors, errors)
            cost = results[-1]
            self.assertEqual(sum(r['coverage']==1 for r in cost['ingredients']), 8)
            self.assertEqual((cost['fallbackIngredientCount'], cost['budgetIngredientCount']), (1, 9))
            self.assertTrue(cost['budgetComplete'])
            self.assertFalse(cost['complete'], 'The salt/pepper budget must remain separate from observed prices')
            self.assertEqual(len(cost['ingredients']), 9)
            self.assertTrue(all(r['coverage']==1 or r.get('fallbackEstimate') for r in cost['ingredients']))
        self.assertEqual(results[-1]['budgetTotalsByCurrency'], results[-2]['budgetTotalsByCurrency'])
        self.assertEqual(detailed, original, 'Cooking and nutrition quantities must not change')
        with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('reopening recalculated')):
            await namespace['ws_recipe_cost'](self.hass, connection, {'id':1,'offline_only':True,'recipe':detailed})
        self.assertFalse(errors, errors)
        self.assertTrue(results[-1]['costCacheHit'])

    async def test_oil_and_vinegar_use_food_specific_conversions_and_real_prices(self):
        for name, quantity, volume, price in [('Rapeseed oil',40,40/.92,.26),('Balsamic vinegar',20,18.75,.15)]:
            with self.subTest(name=name):
                result = await self.prices.offline_recipe_price(self.bridge, {'ingredients':[{'name':name,'quantity':quantity,'unit':'g'}]}, [])
                self.assertTrue(result['complete'])
                self.assertNotIn('fallbackIngredientCount', result)
                row = result['ingredients'][0]
                self.assertAlmostEqual(row['quantityEstimate']['quantity'],volume)
                self.assertEqual(row['quantityEstimate']['unit'],'ml')
                self.assertEqual(result['totalsByCurrency'],{'EUR':price})
                self.assertTrue(row['references'][0].get('sourceUrl') or row['references'][0].get('observationId'))
        for name in ['Mystery oil', 'Salt', 'Pumpkin']:
            self.assertEqual(self.measures.price_options({'name':name}), [])
        self.assertEqual(self.measures.price_options({'name':'Mystery sauce','quantity':40,'unit':'g'}), [{'quantity':40.,'unit':'g'}])

    async def test_recovered_source_details_are_specific_scaled_and_disclosed(self):
        recipe = self.screenshot_recipe()
        result = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        pumpkin, seasoning = result['ingredients'][1], result['ingredients'][7]
        self.assertEqual(pumpkin['costsByCurrency'],{'EUR':.86})
        self.assertEqual(pumpkin['quantityEstimate']['quantity'],400)
        self.assertIn('small Hokkaido',pumpkin['quantityEstimate']['label'])
        self.assertIn('848764',pumpkin['quantityEstimate']['recipeSource']['sourceUrl'])
        estimate = seasoning['fallbackEstimate']
        self.assertEqual(estimate['quantity'],1)
        self.assertEqual(estimate['group'],'spices')
        self.assertIn('mixture ratio unspecified',estimate['quantityEstimate']['label'])
        scaled = self.prices.canonical_recipe({**recipe,'servings':2},self.catalog['ingredients'])
        self.assertEqual(scaled['ingredients'][7]['quantity'],.5)
        other = self.prices.canonical_recipe({**recipe,'variantId':'unreviewed'},self.catalog['ingredients'])
        self.assertIsNone(other['ingredients'][7].get('quantity'))
        self.assertEqual(other['ingredients'][1]['canonicalName'],'Pumpkin')
        edited = deepcopy(recipe)
        edited['ingredients'][1].update(quantity=800,unit='g',unitKey='UNIT_27')
        edited['ingredients'][7].update(quantity=3,unit='g',unitKey='UNIT_27')
        retained = self.prices.canonical_recipe(edited,self.catalog['ingredients'])
        self.assertEqual(retained['ingredients'][1]['quantity'],800)
        self.assertEqual(retained['ingredients'][7]['quantity'],3)
        self.assertEqual(retained['ingredients'][7]['canonicalName'],'Salt')

    async def test_saved_user_price_wins_and_unknown_salt_stays_unknown(self):
        store = await self.store()
        await store.async_set_reference('n:rapeseed oil', amount=4,currency='EUR',basis_quantity=100,basis_unit='g',country='DE',source='manual')
        result = await self.prices.offline_recipe_price(self.bridge, {'ingredients':[{'name':'Rapeseed oil','quantity':40,'unit':'g'}]}, [])
        self.assertEqual(result['totalsByCurrency'],{'EUR':1.6})
        self.assertIsNone(result['ingredients'][0]['quantityEstimate'])
        result = await self.prices.offline_recipe_price(self.bridge, {'ingredients':[{'name':'Salt'}]}, [])
        self.assertEqual(result['ingredients'][0]['priceStatus'],'recipe_amount_unknown')
        self.assertNotIn('fallbackIngredientCount',result)

    async def test_market_scope_and_persisted_cache(self):
        recipe = self.screenshot_recipe()
        result = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        existing = await self.cache.recipe_cost_cache_for_bridge(self.bridge)
        fresh = self.cache.Cook4MeRecipeCostCache(self.bridge)
        fresh._store.saved = deepcopy(existing._store.saved)
        await fresh.async_load();self.bridge._recipe_cost_cache_v1 = fresh
        with patch.object(self.cache, 'calculate_recipe_cost', side_effect=AssertionError('persistent cache missed')):
            again = await self.prices.offline_recipe_price(self.bridge, recipe, self.catalog['ingredients'])
        self.assertTrue(again['costCacheHit']);self.assertEqual(result['budgetTotalsByCurrency'],again['budgetTotalsByCurrency'])
        self.assertFalse(self.snapshot.snapshot_observations(category='en:pumpkins',country='FR',currency='EUR',unit='g'))
        self.assertFalse(self.snapshot.snapshot_observations(category='en:pumpkins',country='DE',currency='USD',unit='g'))


if __name__ == '__main__':
    unittest.main()
