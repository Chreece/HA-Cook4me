"""Production route bodies with controlled HA/network/storage boundaries."""
import ast
import asyncio
from copy import deepcopy
from functools import wraps
import importlib.util
import inspect
from pathlib import Path
from types import SimpleNamespace
import unittest
from uuid import uuid4
from test_receipts_v195 import m, Memory, receipt

ROOT=Path(__file__).resolve().parents[1]
COMP=ROOT/'custom_components/cook4me'

def functions(path,names,ns):
    tree=ast.parse(path.read_text())
    nodes=[]
    for node in tree.body:
        if getattr(node,'name',None) in names:
            node=deepcopy(node)
            if hasattr(node,'decorator_list'):node.decorator_list=[]
            nodes.append(node)
    assert {node.name for node in nodes}==set(names)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(path),'exec'),ns)
    return ns

class Routes(unittest.IsolatedAsyncioTestCase):
    def environment(self,ai=None):
        calls=[];out=[];errors=[];disk=Memory();store=m.ReceiptDraftStore(disk)
        bridge=SimpleNamespace(recipe_hub=SimpleNamespace(profile={'scannerAiTaskEntityId':'ai_task.fixture'}))
        class Photo:
            name='private-fixture.jpg'
            def unlink(self,missing_ok):calls.append('unlink')
        class Hass:
            config=SimpleNamespace(media_dirs={'local':'fixture'})
            async def async_add_executor_job(self,fn,*args):return await asyncio.to_thread(fn,*args)
        connection=SimpleNamespace(user=SimpleNamespace(id='alice'),send_result=lambda i,r:out.append(r),send_error=lambda i,c,msg:errors.append((c,msg)))
        def authorize(*args):calls.append('authorize');return bridge
        async def generate(*args,**kwargs):calls.append(kwargs);return SimpleNamespace(data=ai or receipt())
        async def get_store(bridge):return store
        async def catalog(*args):return [{'key':'carrot','name':'Καρότο'}]
        def suggestions(product,catalog):calls.append(product);return [{'ingredient':catalog[0]}]
        async def release(ident):calls.append(('release',ident))
        bridge.recipe_hub.async_release_receipt_requests=release
        scanner=SimpleNamespace(_authorized=authorize,_ai_choices=lambda *a:[{'id':'ai_task.fixture'}],
          _image_bytes=lambda value:b'fixture',_write_photo=lambda *a:Photo(),
          v5=SimpleNamespace(_default_ai_task_entity_id=lambda h:'ai_task.default',_parse_ai_json=lambda data:data),
          _catalog=catalog,suggest_catalog_matches=suggestions)
        ns={'asyncio':asyncio,'inspect':inspect,'scanner':scanner,'text':m.text,'normalize_receipt':m.normalize_receipt,
            'ReceiptConflict':m.ReceiptConflict,'receipt_store_for_bridge':get_store,
            'ai_task':SimpleNamespace(async_generate_data=generate),
            'legacy':SimpleNamespace(_send_error=lambda c,msg,exc:errors.append((type(exc).__name__,str(exc))))}
        functions(COMP/'websocket_receipts.py',['_owner','receipt_instructions','ws_receipt_recognize','ws_receipt_suggestions','ProductError','_ProductReply','_add_reviewed_product','ws_receipt_drafts'],ns)
        return ns,Hass(),connection,bridge,store,disk,calls,out,errors

    async def test_recognition_is_review_only_and_cleans_photo(self):
        ns,h,c,b,store,disk,calls,out,errors=self.environment()
        await ns['ws_receipt_recognize'](h,c,{'id':1,'entry_id':'e','image':'fixture','language':'el'})
        self.assertFalse(errors,errors);self.assertFalse(out[0]['saved']);self.assertEqual(disk.writes,0)
        self.assertEqual(out[0]['receipt']['items'][0]['ingredientLinks'],[])
        self.assertIn('unlink',calls);self.assertEqual(calls.count('authorize'),2)
        prompt=next(x for x in calls if isinstance(x,dict) and 'instructions' in x)
        self.assertIn('untrusted data',prompt['instructions']);self.assertIn('payment card',prompt['instructions'])
        self.assertIn('media-source://',prompt['attachments'][0]['media_content_id'])

    async def test_provider_error_cleans_photo_without_draft(self):
        ns,h,c,b,store,disk,calls,out,errors=self.environment()
        async def fail(*args,**kwargs):raise OSError('provider fixture')
        ns['ai_task'].async_generate_data=fail
        await ns['ws_receipt_recognize'](h,c,{'id':1,'entry_id':'e','image':'fixture'})
        self.assertIn('unlink',calls);self.assertFalse(out);self.assertTrue(errors);self.assertEqual(disk.writes,0)

    async def test_unauthorized_or_anonymous_user_cannot_scan(self):
        for anonymous in (False,True):
            ns,h,c,b,store,disk,calls,out,errors=self.environment()
            if anonymous:c.user.id=''
            else:
                def deny(*a):raise PermissionError('denied')
                ns['scanner']._authorized=deny
            await ns['ws_receipt_recognize'](h,c,{'id':1,'entry_id':'e','image':'fixture'})
            self.assertTrue(errors);self.assertFalse(out);self.assertNotIn('unlink',calls)

    async def test_permission_revoked_while_queued_prevents_ai(self):
        ns,h,c,b,store,disk,calls,out,errors=self.environment();count=0
        def authorize(*a):
            nonlocal count
            count+=1
            if count==2:raise PermissionError('revoked')
            return b
        ns['scanner']._authorized=authorize
        await ns['ws_receipt_recognize'](h,c,{'id':1,'entry_id':'e','image':'fixture'})
        self.assertTrue(errors);self.assertFalse(any(isinstance(x,dict) and 'instructions' in x for x in calls))

    async def test_suggestions_reuse_matcher_without_caller_categories(self):
        ns,h,c,b,store,disk,calls,out,errors=self.environment()
        await ns['ws_receipt_suggestions'](h,c,{'id':1,'entry_id':'e','language':'el','product':{'productName':'Karotten','ingredientName':'carrot','categories':['milk'],'key':'evil'}})
        self.assertFalse(errors);evidence=next(x for x in calls if isinstance(x,dict))
        self.assertEqual(set(evidence),{'productName','genericName','brand'});self.assertIsNone(out[0]['match'])

    async def test_draft_routes_keep_owner_private_and_reject_stale_updates(self):
        ns,h,c,b,store,disk,calls,out,errors=self.environment()
        await ns['ws_receipt_drafts'](h,c,{'id':1,'entry_id':'e','action':'save','receipt':receipt()})
        saved=out.pop()['receipt'];c.user.id='bob'
        await ns['ws_receipt_drafts'](h,c,{'id':1,'entry_id':'e','action':'get','receipt_id':saved['id']})
        self.assertTrue(errors);errors.clear();c.user.id='alice'
        await ns['ws_receipt_drafts'](h,c,{'id':1,'entry_id':'e','action':'save','receipt':saved,'receipt_id':saved['id'],'revision':0})
        self.assertEqual(errors[0][0],'receipt_conflict')

    async def test_discard_releases_only_deleted_draft_retry_records(self):
        ns,h,c,b,store,disk,calls,out,errors=self.environment();saved=await store.save('alice',receipt())
        await ns['ws_receipt_drafts'](h,c,{'id':1,'entry_id':'e','action':'discard','receipt_id':saved['id'],'revision':1})
        self.assertFalse(errors);self.assertIn(('release',saved['id']),calls)

    async def test_adapter_executes_full_schema_and_original_handler_once(self):
        ns,h,c,b,store,disk,calls,out,errors=self.environment()
        async def original(hass,connection,msg):
            self.assertIs(connection.user,c.user);calls.append(('handler',msg));connection.send_result(msg['id'],{'status':'added','lotId':'lot','warnings':[]})
        @wraps(original)
        def wrapped(*args):raise AssertionError('Scheduling wrapper must not be invoked')
        def schema(msg):calls.append(('schema',msg));return {**msg,'schema_default':True}
        wrapped._ws_schema=schema;ns['scanner'].ws_product_add=wrapped
        result=await ns['_add_reviewed_product'](h,c,{'entry_id':'entry','request_id':'request'})
        self.assertEqual(result['lotId'],'lot');self.assertEqual(len([x for x in calls if isinstance(x,tuple) and x[0]=='handler']),1)
        self.assertTrue(next(x[1] for x in calls if isinstance(x,tuple) and x[0]=='handler')['schema_default'])

    async def test_adapter_preserves_validation_error_code(self):
        ns,h,c,b,store,disk,calls,out,errors=self.environment()
        async def handler(h,c,m):c.send_error(m['id'],'product_validation','Bad ingredient')
        handler._ws_schema=lambda msg:msg;ns['scanner'].ws_product_add=handler
        with self.assertRaises(ns['ProductError']) as context:await ns['_add_reviewed_product'](h,c,{})
        self.assertEqual(context.exception.code,'product_validation')

    async def test_adapter_does_not_accept_missing_success(self):
        ns,h,c,b,store,disk,calls,out,errors=self.environment()
        async def handler(h,c,m):c.send_result(m['id'],{})
        handler._ws_schema=lambda msg:msg;ns['scanner'].ws_product_add=handler
        with self.assertRaises(RuntimeError):await ns['_add_reviewed_product'](h,c,{})

    def test_three_routes_registered_and_panel_import_cache_busted(self):
        source=(COMP/'websocket_receipts.py').read_text();panel=(COMP/'panel.py').read_text()
        self.assertIn('for command in (ws_receipt_recognize, ws_receipt_suggestions, ws_receipt_drafts)',source)
        self.assertIn('async_register_receipts(hass)',panel);self.assertIn('&receipt=195',panel)


class DurableScannerLedger(unittest.IsolatedAsyncioTestCase):
    def hub(self):
        source=ast.parse((COMP/'recipe_hub.py').read_text());cls=next(n for n in source.body if isinstance(n,ast.ClassDef) and any(getattr(x,'name','')=='async_scanner_add' for x in n.body))
        nodes=[deepcopy(n) for n in cls.body if getattr(n,'name','') in {'async_scanner_add','async_release_receipt_requests'}]
        ns={'deepcopy':deepcopy,'uuid4':uuid4,'inventory_identity':lambda row:row.get('key')}
        ns['validate_location']=lambda profile,meta:deepcopy(meta or {})
        def add(stock,ingredient,**kwargs):
            return [*(stock or []),{**ingredient,'lots':[kwargs['lot_metadata']]}]
        ns['add_inventory_item']=add
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'recipe_hub.py','exec'),ns)
        class Hub:
            _normalize_profile=staticmethod(deepcopy)
        hub=Hub();hub._data={'profile':{'houseIngredients':[]}};hub._store=Memory();hub._lock=asyncio.Lock()
        for node in nodes:setattr(Hub,node.name,ns[node.name])
        return hub

    async def test_receipt_retry_survives_250_ordinary_scans(self):
        h=self.hub();request='receipt-'+'a'*32+'-'+'b'*32
        first=await h.async_scanner_add(request,{'key':'carrot','name':'Carrot'},quantity=500,unit='g',fingerprint='same')
        for i in range(250):await h.async_scanner_add(str(i),{'key':str(i),'name':'Other'},quantity=1,unit='pcs',fingerprint=str(i))
        again=await h.async_scanner_add(request,{'key':'carrot','name':'Carrot'},quantity=500,unit='g',fingerprint='same')
        self.assertEqual(first,again);self.assertEqual(len(h._data['profile']['houseIngredients']),251)
        self.assertEqual(len(h._data['scannerReceipts']),200);self.assertIn(request,h._data['receiptScannerReceipts'])

    async def test_ledger_capacity_refuses_new_write_not_eviction(self):
        h=self.hub();h._data['receiptScannerReceipts']={str(i):{} for i in range(8192)}
        with self.assertRaises(ValueError):await h.async_scanner_add('receipt-new',{'key':'r','name':'R'},quantity=1,unit='g')
        self.assertEqual(h._store.writes,0)

    async def test_cleanup_only_removes_matching_receipt(self):
        h=self.hub();h._data['receiptScannerReceipts']={'receipt-one-item':{},'receipt-two-item':{}}
        await h.async_release_receipt_requests('one');self.assertEqual(list(h._data['receiptScannerReceipts']),['receipt-two-item'])

    def test_restart_preserves_pinned_ledger(self):
        tree=ast.parse((COMP/'recipe_hub.py').read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and any(getattr(x,'name','')=='async_scanner_add' for x in n.body))
        load=next(n for n in cls.body if getattr(n,'name','')=='async_load')
        self.assertIn('saved.get(\'receiptScannerReceipts\')',ast.unparse(load))

if __name__=='__main__':unittest.main()
