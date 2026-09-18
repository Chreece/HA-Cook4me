"""Multi-package capture, exact editable details and isolated durable edits."""
import asyncio
from copy import deepcopy
import importlib
import unittest
from unittest.mock import AsyncMock

import test_runtime_audit_v74 as runtime
import test_product_capture_v78 as capture


class PackageTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = runtime.AuditTests.asyncTearDown

    def setUp(self):
        runtime.AuditTests.setUp(self)
        self.hass.config = runtime.NS(country='DE')
        self.packages = importlib.import_module(runtime.PREFIX+'.product_packages')
        self.nutrition = importlib.import_module(runtime.PREFIX+'.nutrition')
        self.costs = importlib.import_module(runtime.PREFIX+'.costs')
        self.prices = importlib.import_module(runtime.PREFIX+'.automatic_prices')
        self.rice = {'key':'rice','name':'Rice'}
        self.oats = {'key':'oats','name':'Oats'}

    async def api(self):
        ns = capture.ProductCaptureTests.api(self)
        ns['_catalog'] = AsyncMock(return_value=[self.rice,self.oats])
        ns['nutrition_store_for_bridge'] = self.nutrition.nutrition_store_for_bridge
        ns['cost_store_for_bridge'] = self.costs.cost_store_for_bridge
        ns['save_product_prices'] = self.prices.save_product_prices
        ns['async_save_lot_nutrition'] = importlib.import_module(runtime.PREFIX+'.nutrition_label').async_save_lot_nutrition
        ns['replace_package_nutrition'] = self.packages.replace_package_nutrition
        ns['find_package'] = self.packages.find_package
        ns['package_version'] = self.packages.package_version
        runtime.functions('websocket_v33.py', {'ws_product_details','ws_product_remove'}, ns)
        return ns

    def message(self, **extra):
        return {'id':1,'entry_id':'one','request_id':'capture-112-package-0001','ingredient':self.rice,
                'quantity':500,'unit':'g','package_count':3,
                'lot_metadata':{'storageLocationId':'pantry','productName':'Rice package','brand':'Original','barcode':'12345678'},
                'nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':8,'salt':0}},
                'paid_price':{'amount':2.5,'currency':'EUR','country':'DE'}, **extra}

    async def create(self, ns, **extra):
        msg = self.message(**extra)
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertEqual(self.errors,[])
        self.assertFalse(self.results[-1]['warnings'])
        return msg, self.results[-1]['lotIds']

    async def details(self, ns, lot_id):
        await ns['ws_product_details'](self.hass,self.connection,{'id':2,'entry_id':'one','lot_id':lot_id})
        self.assertEqual(self.errors,[])
        return self.results[-1]

    async def test_one_scan_creates_three_distinct_packages_with_exact_nutrition_and_per_package_price(self):
        ns=await self.api();msg,ids=await self.create(ns)
        self.assertEqual(len(set(ids)),3)
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'][0]['quantity'],1500)
        for lot_id in ids:
            detail=await self.details(ns,lot_id)
            self.assertEqual(detail['lot']['quantity'],500)
            self.assertEqual(detail['nutrition']['values']['salt'],0)
            self.assertEqual(detail['paidPrice']['amount'],2.5)
            self.assertEqual(detail['paidPrice']['basisQuantity'],500)
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertEqual(self.results[-1]['lotIds'],ids)
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'][0]['quantity'],1500)

    async def test_batch_count_is_part_of_the_durable_retry_receipt(self):
        ns=await self.api();msg,ids=await self.create(ns)
        restored=type(self.bridge.recipe_hub)(self.hass,'one')
        restored._store.saved=self.bridge.recipe_hub._store.saved
        await restored.async_load();self.bridge.recipe_hub=restored
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertEqual(self.results[-1]['lotIds'],ids)
        await ns['ws_product_add'](self.hass,self.connection,{**msg,'package_count':4})
        self.assertEqual(self.errors[-1][0],'product_validation')
        self.assertEqual(restored.profile['houseIngredients'][0]['quantity'],1500)

    async def test_invalid_counts_cannot_change_stock(self):
        ns=await self.api()
        for count in (0,101,-1,1.5,True):
            await ns['ws_product_add'](self.hass,self.connection,self.message(package_count=count))
            self.assertEqual(self.errors[-1][0],'product_validation')
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'],[])

    async def test_partial_batch_detail_failure_retries_without_adding_packages(self):
        ns=await self.api();real=ns['async_save_lot_nutrition'];counter=0
        async def fail_second(*args,**kwargs):
            nonlocal counter
            counter+=1
            if counter==2: raise OSError('disk full')
            return await real(*args,**kwargs)
        ns['async_save_lot_nutrition']=fail_second
        await ns['ws_product_add'](self.hass,self.connection,self.message())
        self.assertTrue(self.results[-1]['warnings'])
        ids=self.results[-1]['lotIds']
        ns['async_save_lot_nutrition']=real
        await ns['ws_product_add'](self.hass,self.connection,self.message())
        self.assertFalse(self.results[-1]['warnings'])
        self.assertEqual(self.results[-1]['lotIds'],ids)
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        self.assertEqual(len(store.stock_lots['k:rice']),3)

    async def test_edit_moves_one_package_and_keeps_siblings_nutrition_prices_and_ids(self):
        ns=await self.api();_,ids=await self.create(ns)
        detail=await self.details(ns,ids[0])
        original=deepcopy(self.bridge.recipe_hub.profile['houseIngredients'][0]['lots'])
        msg=self.message(request_id='edit-package-112-00001',edit_lot_id=ids[0],expected_version=detail['version'],
            ingredient=self.oats,quantity=.25,unit='kg',package_count=1,best_before='2027-05-06',
            lot_metadata={'productName':'Corrected oats','brand':'New brand','storageLocationId':'fridge','barcode':'87654321'},
            nutrition={'basisQuantity':100,'basisUnit':'g','values':{'protein':0}},
            paid_price={'amount':0,'currency':'EUR','basisQuantity':500,'basisUnit':'g'})
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertEqual(self.errors,[]);self.assertFalse(self.results[-1]['warnings'])
        house=self.bridge.recipe_hub.profile['houseIngredients']
        rice=next(row for row in house if row['key']=='rice');oats=next(row for row in house if row['key']=='oats')
        self.assertEqual(rice['quantity'],1000);self.assertEqual(rice['lots'],original[1:])
        self.assertEqual(oats['quantity'],.25);self.assertEqual(oats['unit'],'kg');self.assertEqual(oats['lots'][0]['id'],ids[0])
        changed=await self.details(ns,ids[0])
        self.assertEqual(changed['nutrition']['values'],{'protein':0.0})
        self.assertEqual(changed['paidPrice']['amount'],0);self.assertEqual(changed['paidPrice']['basisQuantity'],500)
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        self.assertEqual(len(store.stock_lots['k:rice']),2);self.assertEqual(len(store.stock_lots['k:oats']),1)
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertFalse(self.results[-1]['warnings']);self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'],house)

    async def test_clear_exact_nutrition_and_price_preserves_other_packages(self):
        ns=await self.api();_,ids=await self.create(ns)
        detail=await self.details(ns,ids[0])
        msg=self.message(request_id='clear-label-112-00001',edit_lot_id=ids[0],expected_version=detail['version'],package_count=1)
        del msg['nutrition'];del msg['paid_price']
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertFalse(self.results[-1]['warnings'])
        changed=await self.details(ns,ids[0]);self.assertIsNone(changed['nutrition']);self.assertIsNone(changed['paidPrice'])
        other=await self.details(ns,ids[1]);self.assertIsNotNone(other['nutrition']);self.assertIsNotNone(other['paidPrice'])

    async def test_stale_edit_or_retry_cannot_overwrite_a_newer_package(self):
        ns=await self.api();_,ids=await self.create(ns)
        before=await self.details(ns,ids[0])
        first=self.message(request_id='edit-first-112-000001',edit_lot_id=ids[0],expected_version=before['version'],package_count=1,quantity=300)
        await ns['ws_product_add'](self.hass,self.connection,first)
        current=await self.details(ns,ids[0])
        second={**first,'request_id':'edit-second-112-00001','expected_version':current['version'],'quantity':200}
        await ns['ws_product_add'](self.hass,self.connection,second)
        await ns['ws_product_add'](self.hass,self.connection,first)
        self.assertEqual(self.errors[-1][0],'product_validation')
        await ns['ws_product_add'](self.hass,self.connection,{**first,'request_id':'stale-third-112-00001'})
        self.assertEqual(self.errors[-1][0],'product_validation')
        row,lot=self.packages.find_package(self.bridge.recipe_hub.profile['houseIngredients'],ids[0])
        self.assertEqual(lot['quantity'],200)

    async def test_failed_inventory_write_does_not_change_memory_or_package_ids(self):
        ns=await self.api();_,ids=await self.create(ns)
        before=deepcopy(self.bridge.recipe_hub._data);detail=await self.details(ns,ids[0])
        self.bridge.recipe_hub._store.async_save=AsyncMock(side_effect=OSError('disk full'))
        await ns['ws_product_add'](self.hass,self.connection,self.message(request_id='fail-edit-112-000001',edit_lot_id=ids[0],expected_version=detail['version'],package_count=1,quantity=100))
        self.assertEqual(self.bridge.recipe_hub._data,before)
        self.assertTrue(self.errors)

    async def test_exact_price_replacement_removes_old_currency_and_unit_references(self):
        ns=await self.api();_,ids=await self.create(ns);detail=await self.details(ns,ids[0])
        await ns['ws_product_add'](self.hass,self.connection,self.message(request_id='new-price-112-000001',edit_lot_id=ids[0],expected_version=detail['version'],package_count=1,
            paid_price={'amount':7,'currency':'USD','basisQuantity':1,'basisUnit':'kg'}))
        store=await self.costs.cost_store_for_bridge(self.bridge)
        refs=store._references_for('lot:'+ids[0]);self.assertEqual(len(refs),1);self.assertEqual(refs[0]['currency'],'USD')
        self.assertEqual(len(store._references_for('lot:'+ids[1])),1)

    async def test_package_removal_is_individual_and_retries_safely(self):
        ns=await self.api();_,ids=await self.create(ns);detail=await self.details(ns,ids[0])
        msg={'id':1,'entry_id':'one','lot_id':ids[0],'expected_version':detail['version']}
        await ns['ws_product_remove'](self.hass,self.connection,{**msg,'expected_version':'stale'})
        self.assertTrue(self.errors);self.errors.clear()
        await ns['ws_product_remove'](self.hass,self.connection,msg)
        await ns['ws_product_remove'](self.hass,self.connection,msg)
        self.assertEqual(self.errors,[])
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'][0]['quantity'],1000)
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        self.assertEqual(len(store.stock_lots['k:rice']),2)
        costs=await self.costs.cost_store_for_bridge(self.bridge)
        self.assertEqual(costs._references_for('lot:'+ids[0]),[])

    async def test_details_and_edit_require_authorization(self):
        ns=await self.api()
        def deny(*args): raise PermissionError('Unauthorized')
        ns['_authorized']=deny
        await ns['ws_product_details'](self.hass,self.connection,{'id':1,'lot_id':'nope'})
        await ns['ws_product_add'](self.hass,self.connection,self.message())
        self.assertEqual(len(self.errors),2);self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'],[])

if __name__=='__main__':
    unittest.main()
