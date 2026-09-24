"""Production store/route regressions with in-memory HA storage boundaries."""
import ast
import asyncio
from copy import deepcopy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/'custom_components/cook4me'
PKG='cook4me_general_audit_v208'
package=ModuleType(PKG);package.__path__=[str(COMPONENT)];sys.modules[PKG]=package

def load(name):
    path=COMPONENT/(name+'.py')
    tree=ast.parse(path.read_text())
    # Replace only imports of the HA service boundary, not any application code.
    tree.body=[n for n in tree.body if not (isinstance(n,ast.ImportFrom) and
               ((n.module or '').startswith('homeassistant') or n.module=='const'))]
    module=ModuleType(PKG+'.'+name);module.__package__=PKG;module.__file__=str(path);module.DOMAIN='cook4me'
    sys.modules[module.__name__]=module
    exec(compile(tree,str(path),'exec'),module.__dict__)
    return module

nutrition=load('nutrition');barcode=load('barcode')
from cook4me_general_audit_v208 import nutrition_label as label, product_packages as packages

class Storage:
    def __init__(self):self.saved=None;self.fail=False;self.started=asyncio.Event();self.release=None
    async def async_save(self,data):
        self.started.set()
        if self.release:await self.release.wait()
        if self.fail:raise OSError('disk full')
        self.saved=deepcopy(data)


def mapping_store():
    store=barcode.Cook4MeBarcodeMappingStore.__new__(barcode.Cook4MeBarcodeMappingStore)
    store._store=Storage();store._write_lock=asyncio.Lock();store._data={}
    return store

def nutrition_store():
    store=nutrition.Cook4MeNutritionStore.__new__(nutrition.Cook4MeNutritionStore)
    store._store=Storage();store._data={'generic':{},'stockLots':{}}
    return store

CODE='0123456789012'
INGREDIENT={'key':'rice','name':'Ρύζι'}
PROFILE={'basisQuantity':100,'basisUnit':'g','values':{'energyKcal':350,'protein':7}}
INVENTORY=[{**INGREDIENT,'unit':'g','lots':[{'id':'lot-a','quantity':500,'productName':'Rice','barcode':CODE}]}]

class NutritionWrites(unittest.IsolatedAsyncioTestCase):
    async def test_failed_label_save_leaves_memory_unchanged(self):
        s=nutrition_store();before=deepcopy(s._data);s._store.fail=True
        with self.assertRaises(OSError):await label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE)
        self.assertEqual(s._data,before)
    async def test_pending_label_write_does_not_publish_unsaved_values(self):
        s=nutrition_store();before=deepcopy(s._data);s._store.release=asyncio.Event()
        task=asyncio.create_task(label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE))
        await s._store.started.wait()
        try:self.assertEqual(s._data,before)
        finally:s._store.release.set();await task
        self.assertEqual(s._data,s._store.saved)
    async def test_cancelled_write_does_not_leave_phantom_nutrition(self):
        s=nutrition_store();before=deepcopy(s._data);s._store.release=asyncio.Event()
        task=asyncio.create_task(label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE))
        await s._store.started.wait();task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual(s._data,before)
    async def test_failed_retry_then_success_produces_one_exact_lot(self):
        s=nutrition_store();s._store.fail=True
        with self.assertRaises(OSError):await label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE)
        s._store.fail=False
        await label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE)
        await label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE)
        self.assertEqual(len(s._data['stockLots']['k:rice']),1);self.assertEqual(s._data,s._store.saved)
    async def test_existing_label_remains_unchanged_when_replacement_fails(self):
        s=nutrition_store();await label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE);before=deepcopy(s._data)
        s._store.fail=True
        with self.assertRaises(OSError):await label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition={**PROFILE,'values':{'protein':99}})
        self.assertEqual(s._data,before)
    async def test_package_edit_keeps_replacement_label_through_staging(self):
        s=nutrition_store();await label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE)
        await packages.replace_package_nutrition(s,INVENTORY,'lot-a',{**PROFILE,'values':{'protein':12}})
        self.assertEqual(s._data['stockLots']['k:rice'][0]['nutrition']['values']['protein'],12)
        self.assertEqual(s._data,s._store.saved)
    async def test_explicit_label_removal_still_works(self):
        s=nutrition_store();await label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE)
        await packages.replace_package_nutrition(s,INVENTORY,'lot-a',None)
        self.assertEqual(s._data['stockLots'],{})
    async def test_source_inventory_and_label_are_not_mutated(self):
        before=deepcopy((INVENTORY,PROFILE));s=nutrition_store();await label.async_save_lot_nutrition(s,INVENTORY,lot_id='lot-a',nutrition=PROFILE)
        self.assertEqual((INVENTORY,PROFILE),before)

# Execute the actual nested post-commit route operation with the actual mapping
# store. No handwritten replacement of the mapping mutation or normalization.
route=ast.parse((COMPONENT/'websocket_v33.py').read_text())
owner=next(n for n in route.body if getattr(n,'name',None)=='ws_product_add')
operation=next(deepcopy(n) for n in ast.walk(owner) if isinstance(n,ast.AsyncFunctionDef) and n.name=='save_barcode_mapping')
async def run_mapping(store,*,edit=False,unlimited=False,quantity=125):
    async def get_store(bridge):return store
    ns={'v15':SimpleNamespace(_store=get_store),'bridge':object(),'ingredient':INGREDIENT,'links':[INGREDIENT],
        'metadata':{'barcode':CODE,'productName':'Reviewed rice','brand':'Brand'},
        'msg':{'quantity':quantity,'unit':'g',**({'edit_lot_id':'lot-a'} if edit else {})},
        'unlimited':unlimited,'nutrition':PROFILE}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[operation],type_ignores=[])),str(COMPONENT/'websocket_v33.py'),'exec'),ns)
    await ns['save_barcode_mapping']()

class BarcodePackageSizes(unittest.IsolatedAsyncioTestCase):
    async def seed(self,store):await store.async_set(CODE,{'ingredient':INGREDIENT,'quantity':500,'unit':'g'})
    async def test_editing_remaining_stock_does_not_redefine_package_size(self):
        s=mapping_store();await self.seed(s);await run_mapping(s,edit=True,quantity=125)
        row=s.get(CODE);self.assertEqual(row['quantity'],500);self.assertEqual(row['unit'],'g');self.assertEqual(row['productName'],'Reviewed rice')
    async def test_unknown_original_package_size_is_not_invented_from_remaining_stock(self):
        s=mapping_store();await run_mapping(s,edit=True,quantity=125);row=s.get(CODE)
        self.assertIsNone(row['quantity']);self.assertEqual(row['unit'],'')
    async def test_new_measured_scan_can_set_package_size(self):
        s=mapping_store();await self.seed(s);await run_mapping(s,quantity=1000);self.assertEqual(s.get(CODE)['quantity'],1000)
    async def test_unlimited_pantry_does_not_erase_known_finite_barcode_package(self):
        s=mapping_store();await self.seed(s);await run_mapping(s,unlimited=True);self.assertEqual(s.get(CODE)['quantity'],500)
    async def test_failed_mapping_write_preserves_prior_mapping(self):
        s=mapping_store();await self.seed(s);before=s.get(CODE);s._store.fail=True
        with self.assertRaises(OSError):await run_mapping(s,edit=True)
        self.assertEqual(s.get(CODE),before)
    async def test_preserved_quantity_and_unit_remain_a_pair(self):
        s=mapping_store();await s.async_set(CODE,{'ingredient':INGREDIENT,'quantity':1,'unit':'kg'});await run_mapping(s,edit=True,quantity=250)
        self.assertEqual((s.get(CODE)['quantity'],s.get(CODE)['unit']),(1,'kg'))

if __name__=='__main__':unittest.main()
