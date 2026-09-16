"""Review-first capture, durable retries and storage referential integrity."""
import asyncio
import base64
from copy import deepcopy
import hashlib
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock

import test_runtime_audit_v74 as runtime


class ProductCaptureTests(unittest.IsolatedAsyncioTestCase):
    setUp = runtime.AuditTests.setUp
    asyncTearDown = runtime.AuditTests.asyncTearDown

    async def add(self, request_id='a'*20, **kwargs):
        return await self.bridge.recipe_hub.async_scanner_add(request_id, {"key": "rice", "name": "Rice"},
            quantity=kwargs.pop('quantity', 500), unit='g', lot_metadata={"storageLocationId": "pantry", **kwargs}, fingerprint='same')

    async def test_reviewed_add_persists_location_and_retry_receipt(self):
        first = await self.add()
        second = await self.add()
        self.assertEqual(first, second)
        hub = self.bridge.recipe_hub
        self.assertEqual(hub.profile['houseIngredients'][0]['quantity'], 500)
        lot = hub.profile['houseIngredients'][0]['lots'][0]
        self.assertEqual(lot['storageLocationId'], 'pantry')
        self.assertEqual(lot['storage'], 'pantry')
        restored = type(hub)(self.hass, 'one')
        restored._store.saved = hub._store.saved
        await restored.async_load()
        self.bridge.recipe_hub = restored
        self.assertEqual(await self.add(), first)
        self.assertEqual(restored.profile['houseIngredients'][0]['quantity'], 500)

    async def test_parallel_retries_commit_one_lot(self):
        await asyncio.gather(*(self.add() for _ in range(8)))
        lots = self.bridge.recipe_hub.profile['houseIngredients'][0]['lots']
        self.assertEqual(len(lots), 1)

    async def test_storage_rename_preserves_id_and_used_place_cannot_be_deleted(self):
        await self.add()
        hub = self.bridge.recipe_hub
        await hub.async_storage_location(action='save', identity='pantry', name='Hall cupboard', kind='pantry')
        self.assertEqual(next(r for r in hub.profile['storageLocations'] if r['id']=='pantry')['name'], 'Hall cupboard')
        with self.assertRaisesRegex(ValueError, 'Move the stock'):
            await hub.async_storage_location(action='delete', identity='pantry')
        row = hub.profile['houseIngredients'][0]
        lots = row['lots'];lots[0]['storageLocationId']='fridge'
        await hub.async_inventory_update('k:rice', unit='g', lots=lots)
        await hub.async_storage_location(action='delete', identity='pantry')
        self.assertEqual(hub.profile['houseIngredients'][0]['lots'][0]['storage'], 'fridge')

    async def test_storage_update_checks_deleted_places_and_duplicate_names(self):
        hub = self.bridge.recipe_hub
        await hub.async_storage_location(action='delete', identity='pantry')
        with self.assertRaisesRegex(ValueError, 'no longer exists'):
            await self.add()
        with self.assertRaisesRegex(ValueError, 'already has this name'):
            await hub.async_storage_location(action='save', name='fridge', kind='other')
        self.assertEqual(hub.profile['houseIngredients'], [])

    async def test_failed_stock_or_place_persistence_rolls_back_memory(self):
        hub = self.bridge.recipe_hub
        before = deepcopy(hub._data)
        hub._store.async_save = AsyncMock(side_effect=OSError('disk full'))
        with self.assertRaises(OSError): await self.add()
        self.assertEqual(hub._data, before)
        with self.assertRaises(OSError):
            await hub.async_storage_location(action='save', identity='fridge', name='Changed', kind='other')
        self.assertEqual(hub._data, before)

    async def test_profile_save_cannot_bypass_place_delete_checks(self):
        await self.add()
        await self.bridge.recipe_hub.async_set_profile({'storageLocations': [], 'diet': 'vegetarian'})
        self.assertEqual(len(self.bridge.recipe_hub.profile['storageLocations']), 3)
        self.assertEqual(self.bridge.recipe_hub.profile['diet'], 'vegetarian')

    async def test_request_id_cannot_be_reused_for_different_product(self):
        await self.add()
        with self.assertRaisesRegex(ValueError, 'already saved'):
            await self.bridge.recipe_hub.async_scanner_add('a'*20, {'name':'Rice'}, quantity=500, unit='g', fingerprint='different')

    async def test_invalid_date_does_not_commit_stock(self):
        with self.assertRaises(ValueError):
            await self.bridge.recipe_hub.async_scanner_add('a'*20, {'name':'Rice'}, quantity=500, unit='g', best_before='2026-02-31', lot_metadata={'storageLocationId':'pantry'})
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'], [])

    def api(self):
        nutrition=importlib.import_module(runtime.PREFIX+'.nutrition')
        inventory=importlib.import_module(runtime.PREFIX+'.inventory')
        locations=importlib.import_module(runtime.PREFIX+'.storage_locations')
        self.results=[];self.errors=[]
        self.connection=runtime.NS(user=runtime.NS(id='user'),send_result=lambda _id,r:self.results.append(r),send_error=lambda _id,code,error:self.errors.append((code,error)))
        self.mapping=runtime.NS(get=lambda code:{'ingredient':{'key':'rice','name':'Rice'},'quantity':500,'unit':'g'},async_set=AsyncMock())
        ns={'asyncio':asyncio,'hashlib':hashlib,'json':json,'base64':base64,'io':io,'Path':Path,'tempfile':tempfile,
            '_authorized':lambda *args:self.bridge,
            '_catalog':AsyncMock(return_value=[{'key':'rice','name':'Rice'}]),
            'normalize_barcode':lambda code:code,
            'suggest_catalog_matches':lambda *args:[],
            'normalize_nutrition':nutrition.normalize_nutrition,
            'inventory_identity':inventory.inventory_identity,'_quantity':inventory._quantity,'_best_before':inventory._best_before,
            'v15':runtime.NS(_store=AsyncMock(return_value=self.mapping)),
            'v23':runtime.NS(_cached_product=AsyncMock(return_value={'found':True,'productName':'Rice','quantity':500,'unit':'g'})),
            'legacy':runtime.NS(_send_error=lambda c,m,e:c.send_error(m['id'],'cook4me_error',str(e))),
            '_state':lambda *args:{'houseIngredients':self.bridge.recipe_hub.profile['houseIngredients']},
            'nutrition_store_for_bridge':AsyncMock(return_value=object()),
            'async_save_lot_nutrition':AsyncMock(), 'async_reconcile_nutrition_inventory':AsyncMock(),
            'update_expiry_notification':lambda bridge:None}
        runtime.functions('websocket_v33.py',{'ws_barcode_lookup','ws_product_add','_draft','_image_bytes'},ns)
        return ns

    async def test_known_barcode_lookup_never_adds_stock_or_remembers_mapping(self):
        ns=self.api()
        await ns['ws_barcode_lookup'](self.hass,self.connection,{'id':1,'entry_id':'one','barcode':'12345678'})
        self.assertEqual(self.results[0]['status'],'review')
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'],[])
        self.mapping.async_set.assert_not_awaited()

    async def test_unknown_catalog_ingredient_is_rejected_before_mutation(self):
        ns=self.api()
        await ns['ws_product_add'](self.hass,self.connection,{'id':1,'entry_id':'one','request_id':'a'*20,'ingredient':{'name':'Fake'},'quantity':1,'unit':'g'})
        self.assertEqual(self.errors[0][0],'product_validation')
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'],[])

    async def test_nutrition_failure_can_retry_without_duplicate_stock(self):
        ns=self.api();ns['async_save_lot_nutrition'].side_effect=OSError('disk full')
        msg={'id':1,'entry_id':'one','request_id':'a'*20,'ingredient':{'key':'rice','name':'Forged label'},'quantity':500,'unit':'g',
             'lot_metadata':{'storageLocationId':'pantry'},'nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':0}}}
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertEqual(self.results[0]['status'],'added');self.assertTrue(self.results[0]['warnings'])
        ns['async_save_lot_nutrition'].side_effect=None
        await ns['ws_product_add'](self.hass,self.connection,msg)
        self.assertFalse(self.results[1]['warnings'])
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'][0]['quantity'],500)
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'][0]['name'],'Rice')
        self.assertEqual(ns['async_save_lot_nutrition'].await_args.kwargs['nutrition']['values']['protein'],0)

    async def test_bad_nutrition_basis_or_negative_values_do_not_add_stock(self):
        ns=self.api()
        for nutrition in [{'values':{'protein':1}}, {'basisQuantity':100,'basisUnit':'g','values':{'protein':-1}}]:
            await ns['ws_product_add'](self.hass,self.connection,{'id':1,'entry_id':'one','request_id':'a'*20,'ingredient':{'key':'rice'},'quantity':500,'unit':'g','lot_metadata':{'storageLocationId':'pantry'},'nutrition':nutrition})
        self.assertEqual(len(self.errors),2)
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'],[])

    async def test_ai_output_is_allowlisted_and_never_guesses_invalid_date(self):
        ns=self.api();draft=ns['_draft']({'productName':'Rice','bestBefore':'2026-02-31','quantity':-1,'unit':'g','ingredient':{'key':'fake'},'nutrition':{'basisQuantity':30,'basisUnit':'g','values':{'protein':9}}})
        self.assertEqual(draft['bestBefore'],'');self.assertNotIn('ingredient',draft);self.assertNotIn('nutrition',draft);self.assertNotIn('quantity',draft)

    async def test_photo_validates_content_and_rejects_oversized_payloads(self):
        ns=self.api()
        for value in ['https://example.com/photo.jpg','data:image/jpeg;base64,'+base64.b64encode(b'not a jpeg').decode(),'data:image/jpeg;base64,'+'a'*4_000_000]:
            with self.assertRaises(ValueError): ns['_image_bytes'](value)

    async def test_unlimited_stock_does_not_report_a_nonexistent_package(self):
        hub=self.bridge.recipe_hub
        await hub.async_inventory_add({'key':'rice','name':'Rice'},unlimited=True)
        with self.assertRaisesRegex(ValueError,'unlimited stock'): await self.add()
        self.assertNotIn('scannerReceipts',hub._data)

    async def test_real_jpeg_is_accepted(self):
        from PIL import Image
        stream=io.BytesIO();Image.new('RGB',(16,16),'white').save(stream,format='JPEG')
        value='data:image/jpeg;base64,'+base64.b64encode(stream.getvalue()).decode()
        self.assertEqual(self.api()['_image_bytes'](value),stream.getvalue())

    async def test_ai_attachment_is_private_and_removed_on_success_and_failure(self):
        ns=self.api()
        with tempfile.TemporaryDirectory() as root:
            async def execute(fn,*args): return fn(*args)
            self.hass.async_add_executor_job=execute
            self.hass.config=runtime.NS(media_dirs={'local':root})
            generated=AsyncMock(return_value=runtime.NS(data={'productName':'Rice','bestBefore':'2030-01-01','nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':9}}}))
            ns.update(_ai_choices=lambda *args:[{'id':'ai_task.images'}],v5=runtime.NS(_default_ai_task_entity_id=lambda h:'ai_task.images',_parse_ai_json=lambda data:data),ai_task=runtime.NS(async_generate_data=generated),_image_bytes=lambda value:b'image')
            runtime.functions('websocket_v33.py',{'_write_photo','ws_recognize_photo'},ns)
            msg={'id':1,'entry_id':'one','mode':'product','image':'image'}
            await ns['ws_recognize_photo'](self.hass,self.connection,msg)
            self.assertFalse(self.errors)
            attachment=generated.await_args.kwargs['attachments'][0]
            self.assertTrue(attachment['media_content_id'].startswith('media-source://media_source/local/cook4me-scan-'))
            self.assertEqual(attachment['media_content_type'],'image/jpeg')
            self.assertNotIn('nutrition',self.results[0]['product'])
            self.assertNotIn('bestBefore',self.results[0]['product'])
            self.assertEqual(list(Path(root).iterdir()),[])
            generated.side_effect=RuntimeError('provider failed')
            await ns['ws_recognize_photo'](self.hass,self.connection,msg)
            self.assertTrue(self.errors)
            self.assertEqual(list(Path(root).iterdir()),[])

    async def test_unauthorized_requests_cannot_lookup_or_add(self):
        ns=self.api()
        def deny(*args): raise PermissionError('forbidden')
        ns['_authorized']=deny
        for command in ['ws_barcode_lookup','ws_product_add']:
            await ns[command](self.hass,self.connection,{'id':1,'entry_id':'one'})
        self.assertEqual(len(self.errors),2)
        ns['_catalog'].assert_not_awaited()
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'],[])
