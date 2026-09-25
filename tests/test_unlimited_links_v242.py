"""Unlimited assignments: actual persistence, validation, coverage and removal."""
import ast
import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/'custom_components/cook4me'
PKG='unlimited_links_v242'
pkg=ModuleType(PKG);pkg.__path__=[str(COMPONENT)];sys.modules[PKG]=pkg
inventory=importlib.import_module(PKG+'.inventory')
food=importlib.import_module(PKG+'.food_intelligence')
catalog=ModuleType(PKG+'.ingredient_catalog');catalog.__package__=PKG
tree=ast.parse((COMPONENT/'ingredient_catalog.py').read_text())
tree.body=[node for node in tree.body if not (isinstance(node,ast.ImportFrom) and ((node.module or '').startswith('homeassistant') or node.module=='const'))]
catalog.DOMAIN='cook4me'
exec(compile(tree,str(COMPONENT/'ingredient_catalog.py'),'exec'),catalog.__dict__)


def functions(filename,names,namespace):
    nodes=[]
    for node in ast.parse((COMPONENT/filename).read_text()).body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list=[];nodes.append(node)
    assert len(nodes)==len(names)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),str(COMPONENT/filename),'exec'),namespace)
    return namespace

packages=ModuleType(PKG+'.product_packages');packages.__package__=PKG
packages.inventory_identity=inventory.inventory_identity
functions('product_packages.py',['resolve_ingredient_links'],packages.__dict__)
sys.modules[packages.__name__]=packages
scanner=ModuleType(PKG+'.websocket_v33')
async def get_catalog(hass,bridge,msg):return deepcopy(hass.catalog)
scanner._catalog=get_catalog;sys.modules[scanner.__name__]=scanner
LINKS=[{'key':'fine-salt','name':'Fine salt'},{'key':'sea-salt','name':'Sea salt'}]
BASE=[{'key':'salt','name':'Αλάτι','unlimited':True,'storageLocationId':'spices','storage':'pantry','productName':'Αλάτι κουζίνας','barcode':'12345670','bestBefore':'2027-01-02'}]


class UnlimitedLinks(unittest.TestCase):
    def test_mixed_finite_and_unlimited_assignments_consume_only_real_lots(self):
        saved=inventory.update_inventory_item(BASE,'k:salt',unlimited=True,ingredient_links=LINKS)
        saved.append({'key':'water','name':'Water','unit':'ml','lots':[{'id':'water-lot','quantity':100}]})
        requests=[{'identity':'k:fine-salt','quantity':5000,'unit':'g'},
                  {'identity':'k:water','quantity':40,'unit':'ml'}]
        after,report=inventory.apply_consumption(saved,requests)
        self.assertEqual(after[0],saved[0]);self.assertEqual(after[1]['quantity'],60)
        self.assertEqual(report['skipped'],[{'identity':'k:fine-salt','reason':'unlimited'}])
        self.assertEqual([(row['lotId'],row['quantity']) for row in report['deductedLots']],[('water-lot',40)])
        self.assertEqual(inventory.consumption_shortfalls(requests,report),[])
        with self.assertRaises(ValueError):
            inventory.apply_consumption(saved,[requests[0]|{'packageOpenings':[{'lotId':'water-lot'}]}])

    def test_replace_deduplicate_remove_links_and_normalize_without_lots(self):
        original=deepcopy(BASE)
        saved=inventory.update_inventory_item(BASE,'k:salt',unlimited=True,ingredient_links=LINKS+[LINKS[0]])
        self.assertEqual(BASE,original)
        self.assertEqual(saved[0]['ingredientLinks'],LINKS)
        self.assertEqual(inventory.normalize_inventory(saved),saved)
        for name in ('storageLocationId','storage','productName','barcode','bestBefore'):
            self.assertEqual(saved[0][name],BASE[0][name])
        self.assertNotIn('quantity',saved[0]);self.assertNotIn('lots',saved[0])
        changed=inventory.update_inventory_item(saved,'k:salt',unlimited=True,ingredient_links=LINKS[1:])
        self.assertIsNone(inventory.stock_for_ingredient(changed,LINKS[0]))
        self.assertTrue(inventory.stock_for_ingredient(changed,LINKS[1])['unlimited'])
        cleared=inventory.update_inventory_item(changed,'k:salt',unlimited=True,ingredient_links=[])
        self.assertNotIn('ingredientLinks',cleared[0]);self.assertTrue(inventory.stock_for_ingredient(cleared,BASE[0])['unlimited'])

    def test_omitted_links_preserve_existing_assignments_and_conversion(self):
        saved=inventory.update_inventory_item(BASE,'k:salt',unlimited=True,ingredient_links=LINKS)
        self.assertEqual(inventory.update_inventory_item(saved,'k:salt',unlimited=True,best_before='')[0]['ingredientLinks'],LINKS)
        finite=[{'key':'salt','name':'Salt','unit':'g','lots':[{'id':'one','quantity':50,'ingredientLinks':LINKS}]}]
        converted=inventory.update_inventory_item(finite,'k:salt',unlimited=True)
        self.assertEqual(converted[0]['ingredientLinks'],LINKS)
        for invalid in (None,{},'salt'):
            with self.assertRaises(ValueError):inventory.update_inventory_item(BASE,'k:salt',unlimited=True,ingredient_links=invalid)
        with self.assertRaises(ValueError):inventory.update_inventory_item(BASE,'k:salt',unlimited=False,ingredient_links=LINKS)

    def test_all_assignments_cover_recipes_and_never_deplete(self):
        saved=inventory.update_inventory_item(BASE,'k:salt',unlimited=True,ingredient_links=LINKS)
        recipe={'ingredients':[{'key':row['key'],'name':'Localized '+row['name'],'quantity':5000,'unit':'g'} for row in LINKS]}
        result=food.recipe_quantity_feasibility(recipe,saved)
        self.assertTrue(result['fullyAvailable']);self.assertEqual(result['quantityCoverage'],1)
        self.assertTrue(all(row.get('unlimited') and row['coverage']==1 for row in result['items']))
        matched=catalog.enrich_match_with_house_keys(recipe,{'missingIngredients':[row['name'] for row in recipe['ingredients']]},saved)
        self.assertEqual(matched['pantryCoverage'],1)
        self.assertEqual([row['status'] for row in matched['ingredientAvailability']],['at_home','at_home'])
        after,report=inventory.apply_consumption(saved,[{'identity':'k:'+row['key'],'name':row['name'],'quantity':5000,'unit':'g'} for row in LINKS])
        self.assertEqual(after,saved);self.assertFalse(report.get('deducted'))
        self.assertEqual(report['skipped'],[{'identity':'k:'+row['key'],'reason':'unlimited'} for row in LINKS])
        self.assertEqual(inventory.consumption_shortfalls([{'identity':'k:'+row['key'],'quantity':5000,'unit':'g'} for row in LINKS],report),[])
        self.assertIsNone(inventory.stock_for_ingredient(saved,{'key':'other','name':'Fine salt'}))
        removed=inventory.remove_inventory_item(saved,'k:salt')
        self.assertEqual(removed,[])
        self.assertFalse(food.recipe_quantity_feasibility(recipe,removed)['fullyAvailable'])


class Routes(unittest.IsolatedAsyncioTestCase):
    def environment(self):
        from test_recipe_hub_transactions_v212 import hub,hubmod
        h=hub();h._data['profile']['houseIngredients']=deepcopy(BASE)
        bridge=SimpleNamespace(recipe_hub=h)
        results=[];errors=[];reconciled=[]
        async def reconcile(bridge):reconciled.append(True)
        ns={'__package__':PKG,'Any':object,'legacy':SimpleNamespace(_bridge=lambda *_:bridge,_send_error=lambda c,m,e:errors.append(e)),
            '_reconcile_nutrition':reconcile,'update_expiry_notification':lambda b:None}
        functions('websocket_v14.py',['ws_inventory_update','_state'],ns)
        hass=SimpleNamespace(catalog=[*LINKS,{'key':'salt','name':'Αλάτι'},{'key':'water','name':'Νερό','sourceIngredientIds':['water-alias']}])
        connection=SimpleNamespace(send_result=lambda ident,data:results.append(data))
        patches=(patch.object(hubmod,'update_inventory_item',inventory.update_inventory_item),patch.object(hubmod,'normalize_inventory',inventory.normalize_inventory))
        return ns,hass,connection,h,results,errors,reconciled,patches

    async def run_request(self,extra,fail=False):
        ns,hass,connection,h,out,errors,reconciled,patches=self.environment()
        h._store.fail=fail
        with patches[0],patches[1]:
            await ns['ws_inventory_update'](hass,connection,{'id':1,'identity':'k:salt','unlimited':True,'ingredient_links':LINKS,'language':'el',**extra})
        return h,out,errors,reconciled

    async def test_real_route_durable_hub_and_localized_catalog_validation(self):
        h,out,errors,reconciled=await self.run_request({'ingredient_links':[LINKS[0],LINKS[0],{'key':'water-alias','name':'wrong label'}]})
        self.assertFalse(errors,errors);self.assertTrue(reconciled)
        links=out[0]['houseIngredients'][0]['ingredientLinks']
        self.assertEqual(links,[LINKS[0],{'key':'water','name':'Νερό'}])
        self.assertEqual(h._store.saved['profile']['houseIngredients'],out[0]['houseIngredients'])

    async def test_rejected_links_and_failed_save_leave_stock_unchanged(self):
        for extra,fail in (({'ingredient_links':[{'key':'missing','name':'Salt'}]},False),({'unlimited':False},False),({},True)):
            h,out,errors,reconciled=await self.run_request(extra,fail)
            self.assertTrue(errors);self.assertFalse(out);self.assertFalse(reconciled)
            self.assertEqual(h.profile['houseIngredients'],BASE)

    async def test_empty_assignment_list_clears_links_but_keeps_primary_unlimited(self):
        h,out,errors,_=await self.run_request({'ingredient_links':[]})
        self.assertFalse(errors,errors);self.assertTrue(out[0]['houseIngredients'][0]['unlimited'])
        self.assertNotIn('ingredientLinks',out[0]['houseIngredients'][0])


if __name__=='__main__':unittest.main()
