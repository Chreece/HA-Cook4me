"""Run the real worker/matcher/normalizers with controlled HA and HTTP boundaries."""
import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
from test_receipts_v195 import m, Memory, receipt

ROOT=Path(__file__).resolve().parents[1]/'custom_components/cook4me'

class Worker(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        package=ModuleType('receipt232');package.__path__=[str(ROOT)]
        modules={'receipt232':package,'homeassistant':ModuleType('homeassistant'),
                 'homeassistant.helpers':ModuleType('homeassistant.helpers'),
                 'homeassistant.core':SimpleNamespace(HomeAssistant=object),
                 'homeassistant.helpers.storage':SimpleNamespace(Store=object)}
        self.modules=patch.dict(sys.modules,modules);self.modules.start();self.addCleanup(self.modules.stop)
        self.worker=importlib.import_module('receipt232.receipt_processing')
        self.disk=Memory();self.store=m.ReceiptDraftStore(self.disk)
        self.queries=[];self.lookups=[];self.mappings={};self.permitted=True
        self.catalog=[{'key':'carrot','name':'Καρότο','canonicalName':'carrot','searchAliases':['Karotten','carrot']}]
        self.product={'barcode':'4000000000001','productName':'Karotten','brand':'Test','quantity':500,'unit':'g',
                      'nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':1}}}
        self.products=[self.product]
        async def executor(fn,*args):return fn(*args)
        async def user(owner):return SimpleNamespace(is_active=True)
        hass=SimpleNamespace(data={},auth=SimpleNamespace(async_get_user=user),async_add_executor_job=executor,
             async_create_background_task=lambda coro,name:asyncio.create_task(coro,name=name))
        self.bridge=SimpleNamespace(hass=hass)
        async def get_store(bridge):return self.store
        async def catalog(*args):return self.catalog
        async def mappings(*args):return SimpleNamespace(all=lambda:deepcopy(self.mappings))
        async def lookup(hass,bridge,code):self.lookups.append(code);return deepcopy(self.product)
        def search(query):self.queries.append(query);return deepcopy(self.products)
        self.worker.receipt_store_for_bridge=get_store;self.worker.search_products=search
        sys.modules['receipt232.websocket_v33']=SimpleNamespace(_catalog=catalog)
        sys.modules['receipt232.websocket_v15']=SimpleNamespace(_store=mappings)
        sys.modules['receipt232.websocket_v23']=SimpleNamespace(_cached_product=lookup)
        sys.modules['receipt232.device_settings']=SimpleNamespace(device_access=lambda *a:self.permitted)
        self.processor=self.worker.ReceiptProcessor(self.bridge)
        async def immediate(callback):return await callback()
        self.processor.network=immediate

    async def queued(self, **item):
        raw=receipt();raw['items'][0].update(productName='Καρότο',originalName='Karotten',brand='Test',ingredientName='carrot',ingredientLinks=[],nutrition={},**item)
        return await self.store.save('alice',raw,processing_language='el')

    async def test_exact_product_supplies_barcode_nutrition_and_catalog(self):
        row=await self.queued();await self.processor.run()
        result=await self.store.get('alice',row['id']);i=result['items'][0]
        self.assertEqual(i['barcode'],'4000000000001');self.assertEqual(i['nutrition']['values']['protein'],1)
        self.assertEqual(i['ingredientLinks'][0]['key'],'carrot')
        self.assertEqual(result['processing']['state'],'ready');self.assertEqual(i['status'],'pending')
        self.assertEqual(self.queries,['Test Karotten'])
        self.assertNotIn('Example supermarket',self.queries[0])

    async def test_german_receipt_in_greek_ui_uses_printed_name_for_enrichment(self):
        raw=receipt();raw['items'][0].update(productName='Καρότο',originalName='Test Karotten',
                                           brand='Test',ingredientName='Καρότο')
        row=await self.store.save('alice',m.normalize_receipt(raw,model=True),processing_language='el')
        await self.processor.run()
        item=(await self.store.get('alice',row['id']))['items'][0]
        self.assertEqual(self.queries,['Test Karotten'])
        self.assertEqual(item['productName'],'Test Karotten')
        self.assertEqual(item['barcode'],self.product['barcode'])
        self.assertEqual(item['nutrition']['values']['protein'],1)
        self.assertEqual(item['ingredientLinks'][0]['name'],'Καρότο')

    def test_search_keeps_source_accents_variants_and_brand_without_duplicates(self):
        query=self.worker.receipt_product_query
        self.assertEqual(query({'originalName':'  Crème fraîche 30%  ', 'productName':'Cream', 'brand':'Example'}),
                         'Example Crème fraîche 30%')
        self.assertEqual(query({'originalName':'dmbio HAFERDRINK NATUR','brand':'dmBio'}),'dmbio HAFERDRINK NATUR')
        self.assertEqual(query({'originalName':'   ','productName':'ΦΕΤΑ ΠΟΠ','brand':''}),'ΦΕΤΑ ΠΟΠ')
        self.assertEqual(query({'productName':'BIOMILCH','brand':'Bio'}),'Bio BIOMILCH')
        self.assertEqual(query({'brand':'Example'}),'')

    async def test_ambiguous_barcode_and_different_size_are_not_guessed(self):
        self.products.append({**self.product,'barcode':'4000000000002'})
        row=await self.queued();await self.processor.run();i=(await self.store.get('alice',row['id']))['items'][0]
        self.assertEqual(i['barcode'],'');self.assertIn('barcode_ambiguous',i['enrichment']['notes'])
        self.assertFalse(self.worker.same_package({**self.product,'quantity':1,'unit':'kg'},self.product))
        self.assertFalse(self.worker.same_package({**self.product,'brand':''},self.product))
        self.assertTrue(self.worker.same_package({**self.product,'quantity':.5,'unit':'kg'},self.product))

    async def test_saved_barcode_mapping_is_used_without_name_search(self):
        self.mappings={self.product['barcode']:{**self.product,'ingredientLinks':[{'key':'carrot','name':'Καρότο'}]}}
        row=await self.queued();await self.processor.run()
        self.assertEqual(self.queries,[]);self.assertEqual(self.lookups,[self.product['barcode']])
        self.assertEqual((await self.store.get('alice',row['id']))['items'][0]['barcode'],self.product['barcode'])

    async def test_lookup_failure_keeps_parsed_data_and_still_matches_catalog(self):
        def fail(query):raise OSError('offline fixture')
        self.worker.search_products=fail
        row=await self.queued();await self.processor.run();i=(await self.store.get('alice',row['id']))['items'][0]
        self.assertEqual(i['lineTotal'],3.98);self.assertEqual(i['barcode'],'')
        self.assertIn('lookup_failed',i['enrichment']['notes']);self.assertEqual(i['ingredientLinks'][0]['key'],'carrot')

    async def test_manual_edit_during_lookup_wins_and_worker_does_not_mutate_stock(self):
        row=await self.queued();item=row['items'][0];original=self.processor.enrich
        async def edit_during(*args):
            result=await original(*args)
            await self.store.save_item('alice',row['id'],item['id'],0,{**item,'productName':'Manual correction'}, {})
            return result
        self.processor.enrich=edit_during;await self.processor.run()
        result=await self.store.get('alice',row['id']);self.assertEqual(result['items'][0]['productName'],'Manual correction')
        self.assertEqual(result['items'][0]['barcode'],'');self.assertEqual(result['items'][0]['status'],'pending')

    async def test_permission_revocation_stops_lookups(self):
        row=await self.queued();self.permitted=False;await self.processor.run()
        result=await self.store.get('alice',row['id']);self.assertEqual(result['processing']['stage'],'permission')
        self.assertEqual(self.queries,[])

    async def test_unload_cancels_and_new_worker_resumes_durable_queue(self):
        row=await self.queued();reached=asyncio.Event()
        async def blocked(*args):reached.set();await asyncio.Event().wait()
        self.processor.enrich=blocked;self.processor.start();await reached.wait();await self.processor.close()
        self.assertTrue(self.processor.task.done());self.assertEqual(len(await self.store.work()),1)
        next_worker=self.worker.ReceiptProcessor(self.bridge);next_worker.network=self.processor.network
        await next_worker.run();self.assertEqual((await self.store.get('alice',row['id']))['processing']['state'],'ready')


if __name__=='__main__':unittest.main()
