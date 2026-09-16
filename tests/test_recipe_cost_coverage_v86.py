"""Recipe-level estimates, offline latency, evidence safety and migration."""
import asyncio
from copy import deepcopy
from datetime import date, timedelta
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_automatic_prices_v79 as previous


class RecipeCostCoverageTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = previous.AutomaticPriceTests.asyncTearDown
    store = previous.AutomaticPriceTests.store
    observed = previous.AutomaticPriceTests.observed

    def setUp(self):
        previous.AutomaticPriceTests.setUp(self)
        self.snapshot = importlib.import_module(previous.runtime.PREFIX + '.price_snapshot')
        self.measurements = importlib.import_module(previous.runtime.PREFIX + '.price_measurements')
        self.forms = importlib.import_module(previous.runtime.PREFIX + '.price_food_forms')

    def evidence(self):
        return {'schemaVersion': 1, 'observations': [self.observed(id=index, categories=[category],
            amount=price, basisQuantity=quantity, basisUnit=unit, barcode='')
            for index, (category, price, quantity, unit) in enumerate([
                ('en:olive-oils',4,1000,'ml'), ('en:garlic',2,100,'g'),
                ('en:onions',2,1000,'g'), ('en:eggs',2.4,6,'pcs'), ('en:rices',3,500,'g')],1)]}

    def meal(self):
        return {'servings':2, 'ingredients':[
            {'key':'oil','name':'Olive oil','quantity':2,'unit':'EL','unitKey':'UNIT_12'},
            {'key':'garlic','name':'Garlic','quantity':3,'unit':'Zehe','unitKey':'UNIT_28'},
            {'key':'onion','name':'Onion','quantity':1},
            {'key':'egg','name':'Egg','quantity':2},
            {'key':'rice','name':'Rice','quantity':200,'unit':'g'}]}

    async def test_complete_real_recipe_path_from_spoons_cloves_and_implicit_counts(self):
        recipe=self.meal();before=deepcopy(recipe)
        with patch.object(self.snapshot,'_load',return_value=self.evidence()), \
                patch.object(self.prices,'lookup_open_prices',side_effect=AssertionError('network')):
            result=await self.prices.recipe_price(self.bridge,recipe,[])
        self.assertEqual(recipe,before,'Cooking instructions and quantities must not be rewritten')
        self.assertTrue(result['complete']);self.assertTrue(result['estimated'])
        self.assertEqual(result['totalsByCurrency'],{'EUR':2.52})
        self.assertEqual(result['perServingByCurrency'],{'EUR':1.26})
        self.assertEqual(result['ingredients'][1]['quantityEstimate']['portionId'],84480)
        self.assertEqual(result['ingredients'][2]['quantityEstimate']['quantity'],110)
        self.assertIsNone(result['ingredients'][4]['quantityEstimate'])

    async def test_offline_preview_does_not_mutate_price_store_or_call_provider(self):
        store=await self.store();before=deepcopy(store._data)
        with patch.object(self.snapshot,'_load',return_value=self.evidence()), \
                patch.object(self.prices,'lookup_open_prices',side_effect=AssertionError('network')):
            result=await self.prices.offline_recipe_price(self.bridge,self.meal(),[])
        self.assertEqual(result['totalsByCurrency'],{'EUR':2.52})
        self.assertTrue(result['offlinePreview']);self.assertFalse(result['priceLookupPending'])
        self.assertEqual(store._data,before)

    async def test_offline_evidence_does_not_queue_behind_slow_provider_requests(self):
        self.bridge._price_slots=asyncio.Semaphore(0)
        self.bridge._price_query_lock=asyncio.Lock();self.bridge._price_queries={}
        with patch.object(self.snapshot,'_load',return_value=self.evidence()):
            result=await asyncio.wait_for(self.prices.recipe_price(self.bridge,self.meal(),[]),.5)
        self.assertTrue(result['complete'])

    async def test_native_paid_lot_wins_over_average_piece_weight(self):
        store=await self.store()
        await store.async_set_reference('lot:paid',amount=1,currency='EUR',basis_quantity=2,basis_unit='pcs',country='DE',source='purchase',confidence='exact_purchase')
        await store.async_set_reference('k:onion',amount=100,currency='EUR',basis_quantity=1000,basis_unit='g',country='DE')
        inventory=[{'key':'onion','name':'Onion','unit':'pcs','lots':[{'id':'paid','quantity':2}]}]
        recipe={'ingredients':[{'key':'onion','name':'Onion','canonicalName':'onion','quantity':1,'unit':'pcs'}]}
        cost=self.calc.calculate_recipe_cost(recipe,inventory,store,country='DE',currency='EUR')
        self.assertEqual(cost['totalsByCurrency'],{'EUR':.5});self.assertEqual(cost['exactPurchaseCoverage'],1)
        self.assertFalse(cost['estimated']);self.assertIsNone(cost['ingredients'][0]['quantityEstimate'])

    async def test_density_and_reverse_piece_estimates_require_food_specific_sources(self):
        store=await self.store()
        await store.async_set_reference('k:oil',amount=4,currency='EUR',basis_quantity=1000,basis_unit='ml',country='DE')
        await store.async_set_reference('k:aubergine',amount=1,currency='EUR',basis_quantity=1,basis_unit='pcs',country='DE')
        recipe={'ingredients':[{'key':'oil','name':'Olive oil','quantity':27,'unit':'g'},
                               {'key':'aubergine','name':'Aubergine','quantity':274,'unit':'g'}]}
        cost=self.calc.calculate_recipe_cost(recipe,[],store,country='DE',currency='EUR')
        self.assertTrue(cost['complete']);self.assertEqual(cost['totalsByCurrency'],{'EUR':.62})
        self.assertTrue(all(row['quantityEstimate']['sourceUrl'].startswith('https://fdc.nal.usda.gov/') for row in cost['ingredients']))

    def test_unknown_amounts_cups_packs_and_ambiguous_counts_remain_unknown(self):
        for row in [{'name':'Salt'}, {'name':'Onion','quantity':75}, {'name':'Garlic','quantity':2},
                    {'name':'Sugar','quantity':2}, {'name':'Water','quantity':2}]:
            self.assertEqual(self.measurements.price_options(row),[])
        for unit in ['cup','bunch','pinch','pack']:
            options=self.measurements.price_options({'name':'Onion','quantity':2,'unit':unit})
            self.assertEqual(options,[{'quantity':2,'unit':unit}])

    async def test_unspecified_seasoning_is_still_excluded_and_disclosed(self):
        recipe=self.meal();recipe['ingredients'].append({'name':'Salt'})
        with patch.object(self.snapshot,'_load',return_value=self.evidence()):
            result=await self.prices.offline_recipe_price(self.bridge,recipe,[])
        self.assertEqual(result['totalsByCurrency'],{'EUR':2.52});self.assertFalse(result['complete'])
        self.assertEqual(result['missingIngredientCount'],1)
        self.assertEqual(result['ingredients'][-1]['priceStatus'],'recipe_amount_unknown')

    async def test_disabled_automatic_and_country_boundaries_apply_to_previews(self):
        store=await self.store()
        with patch.object(self.snapshot,'_load',return_value=self.evidence()):
            await store.async_set_settings(auto_global_prices=False)
            result=await self.prices.offline_recipe_price(self.bridge,self.meal(),[])
            self.assertEqual(result['totalsByCurrency'],{})
            await store.async_set_settings(auto_global_prices=True,country='FR',currency='EUR')
            result=await self.prices.offline_recipe_price(self.bridge,self.meal(),[])
            self.assertEqual(result['totalsByCurrency'],{})

    def test_per_package_is_not_per_ingredient(self):
        for name,expected in [('Zwiebeln 2kg VKE',(2,'kg')),('Heidelbeeren 500g',(500,'g')),
                ('Tomate 1 Stück',(1,'pcs')),('Tomaten',(None,'')),('Zwiebeln 2 x 500g',(None,'')),
                ('400g (240g drained)',(None,'')),('1,000g',(None,''))]:
            self.assertEqual(self.forms.category_unit_basis({'category_tag':'en:tomatoes','product_name':name}),expected)
        self.assertFalse(self.forms.compatible_category_basis({'type':'PRODUCT'},'en:peas','pcs'))
        self.assertFalse(self.forms.consistent_package_basis({'type':'PRODUCT','product_name':'Vanillezucker 3X8g'},8,'g'))
        self.assertTrue(self.forms.consistent_package_basis({'type':'PRODUCT','product_name':'Vanillezucker 3X8g'},24,'g'))

    def test_prepared_foods_are_not_generic_raw_price_evidence(self):
        for category,tags,name in [('en:paprika',['en:crisps'],'Classic Paprika'),
                ('en:milks',['en:milks','en:condensed-milks'],'Kondensmilch'),
                ('en:garlic',['en:pickled-garlic'],'Knoblauch'),
                ('en:chickens',[],'Chicken Nuggets'),('en:sugars',['en:vanilla-sugars'],'Vanillezucker'),
                ('en:almonds',['en:almonds','en:hazelnuts'],'Mixed nuts')]:
            self.assertFalse(self.forms.compatible_food_form({'product':{'categories_tags':tags,'product_name':name}},category))
        self.assertTrue(self.forms.compatible_food_form({'product':{'categories_tags':['en:milks-liquid-and-powder','en:milks'],'product_name':'Vollmilch'}},'en:milks'))

    async def test_card_endpoint_resolves_real_offline_variant_without_fetching_cloud_catalog(self):
        catalog = importlib.import_module(previous.runtime.PREFIX + '.release_catalog')
        payload = await catalog.async_warm_release_catalog(self.hass)
        variant = next(v for recipe in payload['recipes'] for v in recipe['variants'] if v.get('language') == 'de')
        variant_id = variant.get('variantId') or variant.get('id')
        if not variant_id:
            variant_id = next(iter(payload['_runtimeRecipeByVariant']))
        results=[];errors=[]
        ns={'__name__':previous.runtime.PREFIX+'.websocket_v34','__package__':previous.runtime.PREFIX,
            '_authorized':lambda *args:self.bridge,'_country':self.costs._country,
            'offline_recipe_price':self.prices.offline_recipe_price,
            'legacy':previous.runtime.NS(_send_error=lambda *args:errors.append(str(args[-1])))}
        previous.runtime.functions('websocket_v34.py',{'ws_recipe_cost'},ns)
        with patch.object(self.prices,'lookup_open_prices',side_effect=AssertionError('network')):
            await ns['ws_recipe_cost'](self.hass,previous.runtime.NS(send_result=lambda _id,data:results.append(data)),
                {'id':1,'entry_id':'one','offline_only':True,'recipe':{'variantFunctionalId':variant_id}})
        self.assertFalse(errors);self.assertTrue(results[0]['ingredients']);self.assertTrue(results[0]['offlinePreview'])

    async def test_retail_gap_price_keeps_shop_source_and_expires(self):
        evidence = self.evidence()
        row = self.observed(id='dm-1454994', categories=['en:sugars'], amount=2.45,
            basisQuantity=500, source='retail_snapshot', productName='dmBio whole cane sugar',
            sourceUrl='https://www.dm.de/p/d/1454994/dmbio-vollrohrzucker', barcode='')
        evidence['observations'] = [row]
        recipe = {'ingredients':[{'key':'sugar','name':'Sugar','quantity':100,'unit':'g'}]}
        with patch.object(self.snapshot,'_load',return_value=evidence):
            result = await self.prices.recipe_price(self.bridge,recipe,[])
            ref = result['ingredients'][0]['references'][0]
            self.assertEqual(result['totalsByCurrency'],{'EUR':.49})
            self.assertEqual(ref['source'],'retail_snapshot')
            self.assertEqual(ref['sourceUrl'],row['sourceUrl'])
            store = await self.store()
            for saved in store._data['references'].values():
                saved['date']=(date.today()-timedelta(days=181)).isoformat()
            self.assertIsNone(store.best_reference('k:sugar',country='DE',currency='EUR'))
            evidence['observations'][0]['date']=(date.today()-timedelta(days=181)).isoformat()
            self.assertEqual(self.snapshot.snapshot_observations(category='en:sugars',country='DE',currency='EUR'),[])

    async def test_upgrade_rebuilds_external_prices_and_preserves_all_user_prices(self):
        store=await self.store()
        for source in ['manual','purchase','purchase_reference','open_prices','open_prices_category']:
            await store.async_set_reference(source,amount=1,currency='EUR',basis_quantity=1,basis_unit='g',source=source,country='DE')
        saved=deepcopy(store._data);saved.pop('priceEvidenceRevision')
        fresh=self.costs.Cook4MeCostStore(self.hass,'test');fresh._store.saved=saved
        await fresh.async_load()
        self.assertEqual({r['source'] for r in fresh._data['references'].values()},{'manual','purchase','purchase_reference'})
        self.assertEqual(fresh._store.saved['priceEvidenceRevision'],87)
        saved=fresh._store.saved
        fresh._loaded=False;await fresh.async_load();self.assertEqual(fresh._data,saved)


if __name__=='__main__':unittest.main()
