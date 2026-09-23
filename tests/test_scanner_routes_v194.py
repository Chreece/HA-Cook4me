"""Execute actual scanner handlers with controlled HA/AI/lookup boundaries.

The catalog tests use the complete shipped release catalog, not miniature
language fixtures. No network, camera, user stock or AI provider is accessed.
"""
import ast
import asyncio
from copy import deepcopy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/'custom_components/cook4me'


def load(name, filename):
    spec=importlib.util.spec_from_file_location(name, COMPONENT/filename)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


matcher=load('scanner_matching_routes_v194','scanner_matching.py')
SOURCE=(COMPONENT/'websocket_v33.py').read_text(encoding='utf-8')
TREE=ast.parse(SOURCE)


def production_functions(names, namespace):
    functions=[]
    for node in TREE.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in names:
            node=deepcopy(node);node.decorator_list=[];functions.append(node)
    assert {node.name for node in functions}==set(names)
    exec(compile(ast.fix_missing_locations(ast.Module(body=functions,type_ignores=[])),str(COMPONENT/'websocket_v33.py'),'exec'),namespace)
    return namespace


class Routes(unittest.IsolatedAsyncioTestCase):
    def environment(self, product, count=75, known=None):
        catalog=[{'key':str(i),'name':'Καρότο','canonicalName':'carrot','searchAliases':['Karotten']} for i in range(count)]
        executions=[];responses=[];errors=[]
        bridge=SimpleNamespace(recipe_hub=SimpleNamespace(profile={'scannerAiTaskEntityId':'ai_task.fixture'}))
        class Hass:
            config=SimpleNamespace(media_dirs={'local':'/fixture'})
            async def async_add_executor_job(self,fn,*args):
                executions.append(fn.__name__)
                return await asyncio.to_thread(fn,*args)
        class Photo:
            name='fixture.jpg'
            def unlink(self,missing_ok): executions.append('photo_removed')
        async def store(bridge):return SimpleNamespace(get=lambda code:deepcopy(known))
        async def cached(hass,bridge,code):return deepcopy(product)
        async def get_catalog(hass,bridge,msg):return deepcopy(catalog)
        async def generate(*args,**kwargs):return SimpleNamespace(data=deepcopy(product))
        connection=SimpleNamespace(user=object(),send_result=lambda id,data:responses.append(data))
        ns={'asyncio':asyncio,'_authorized':lambda *args:bridge,
            'normalize_barcode':lambda code:code,'v15':SimpleNamespace(_store=store),
            'v23':SimpleNamespace(_cached_product=cached),'_catalog':get_catalog,
            'suggest_catalog_matches':matcher.suggest_catalog_matches,'confident_match':matcher.confident_match,
            'inventory_identity':lambda row:'k:'+str(row.get('key')),
            'legacy':SimpleNamespace(_send_error=lambda *args:errors.append(args[-1])),
            '_ai_choices':lambda *args:[{'id':'ai_task.fixture'}],
            'v5':SimpleNamespace(_default_ai_task_entity_id=lambda h:'ai_task.fixture',_parse_ai_json=lambda data:data),
            '_image_bytes':lambda value:b'fixture','_write_photo':lambda *args:Photo(),
            '_quantity':lambda value:float(value) if value is not None else None,
            '_best_before':lambda value:value or '', 'normalize_nutrition':deepcopy,
            'ai_task':SimpleNamespace(async_generate_data=generate)}
        production_functions(['ws_barcode_lookup','ws_recognize_photo','_draft'],ns)
        return ns,Hass(),connection,responses,errors,executions

    async def test_barcode_returns_every_candidate_without_assignment(self):
        ns,hass,connection,out,errors,calls=self.environment({'productName':'Bio Karotten'})
        await ns['ws_barcode_lookup'](hass,connection,{'id':1,'entry_id':'fixture','barcode':'1234567890123','language':'el'})
        self.assertFalse(errors,errors);self.assertEqual(len(out[0]['suggestions']),75)
        self.assertEqual(out[0]['status'],'review');self.assertIsNone(out[0]['match']);self.assertIsNone(out[0]['mapping'])
        self.assertIn('suggest_catalog_matches',calls)

    async def test_photo_uses_same_complete_review_matcher_and_cleans_up(self):
        ns,hass,connection,out,errors,calls=self.environment({'productName':'Bio Karotten','ingredientName':'Carrot','quantity':100,'unit':'g'})
        await ns['ws_recognize_photo'](hass,connection,{'id':1,'entry_id':'fixture','image':'fixture','mode':'product','language':'el'})
        self.assertFalse(errors,errors);self.assertEqual(len(out[0]['suggestions']),75)
        self.assertIsNone(out[0]['match']);self.assertEqual(out[0]['status'],'review')
        self.assertIn('suggest_catalog_matches',calls);self.assertIn('photo_removed',calls)

    async def test_date_and_nutrition_modes_do_not_suggest_or_reassign_ingredients(self):
        for mode in ['date','nutrition']:
            ns,hass,connection,out,errors,calls=self.environment({'ingredientName':'Carrot','bestBefore':'2026-10-01'})
            await ns['ws_recognize_photo'](hass,connection,{'id':1,'entry_id':'fixture','image':'fixture','mode':mode,'language':'el'})
            self.assertFalse(errors,errors);self.assertEqual(out[0]['suggestions'],[]);self.assertIn('photo_removed',calls)

    async def test_product_photo_does_not_infer_nutrients_or_expiry(self):
        ns,hass,connection,out,errors,calls=self.environment({'ingredientName':'Carrot','bestBefore':'2026-10-01','nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':1}}})
        await ns['ws_recognize_photo'](hass,connection,{'id':1,'entry_id':'fixture','image':'fixture','mode':'product','language':'el'})
        self.assertFalse(errors,errors);self.assertNotIn('bestBefore',out[0]['product']);self.assertNotIn('nutrition',out[0]['product'])

    def test_only_review_routes_use_new_matcher(self):
        imports=[node for node in TREE.body if isinstance(node,ast.ImportFrom) and node.module=='scanner_matching']
        self.assertEqual(len(imports),1)
        self.assertEqual({alias.name for alias in imports[0].names},{'suggest_catalog_matches','confident_match'})
        for name in ['ws_barcode_lookup','ws_recognize_photo']:
            node=next(node for node in TREE.body if getattr(node,'name',None)==name)
            calls={child.func.attr for child in ast.walk(node) if isinstance(child,ast.Call) and isinstance(child.func,ast.Attribute)}
            self.assertIn('async_add_executor_job',calls)
            self.assertFalse(calls & {'async_inventory_add','async_scanner_add','async_scanner_update','async_set'})


class ShippedCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=load('scanner_release_catalog_v194','release_catalog.py')
        cls.rows={lang:cls.catalog.ingredient_choices(lang) for lang in ('el','de')}
        for lang,rows in cls.rows.items():
            print('Shipped scanner catalog:',lang,len(rows),'choices',flush=True)

    def matches(self,product,lang='el'):
        results=matcher.suggest_catalog_matches(product,self.rows[lang])
        print('Scanner audit:',lang,product,'=>',[(r['ingredient']['canonicalName'],r['ingredient']['name']) for r in results],flush=True)
        return results

    def test_german_carrots_offer_greek_catalog_candidates(self):
        result=self.matches({'productName':'Bio Karotten','categories':['carrots','vegetables']})
        self.assertTrue(result)
        self.assertTrue(any('carrot' in r['ingredient']['canonicalName'].lower() for r in result))
        self.assertTrue(all(r['requiresConfirmation'] for r in result))

    def test_canned_chickpeas_exclude_dried_and_flour_in_complete_catalog(self):
        result=self.matches({'productName':'Canned chickpeas','categories':['chickpeas','canned chickpeas','legumes']})
        self.assertTrue(result)
        for entry in result:
            forms=matcher._forms(entry['ingredient']['canonicalName'])
            self.assertFalse(forms & {'dried','fresh','flour'},entry)

    def test_coconut_milk_does_not_return_dairy_milk(self):
        result=self.matches({'productName':'Coconut milk','categories':['coconut milks']})
        self.assertTrue(result)
        self.assertFalse(any(matcher._base(r['ingredient']['canonicalName']) in {'milk','whole milk','skimmed milk'} for r in result))

    def test_tomato_soup_does_not_return_raw_tomatoes(self):
        result=self.matches({'productName':'Tomato soup','categories':['soups']})
        for row in result:self.assertIn('soup',matcher._forms(row['ingredient']['canonicalName']))

    def test_greek_product_can_return_german_labels_without_changing_keys(self):
        result=self.matches({'productName':'Ρύζι','categories':['rices']},'de')
        self.assertTrue(result)
        allowed={str(row.get('key') or row.get('ingredientId') or row.get('id')) for row in self.rows['de']}
        self.assertTrue(all(row['ingredient']['key'] in allowed for row in result))
        self.assertTrue(any('reis' in row['ingredient']['name'].lower() for row in result))

    def test_uncertain_product_is_not_expanded_from_broad_category(self):
        self.assertEqual(self.matches({'productName':'Unidentified product','categories':['vegetables','foods']}),[])


if __name__=='__main__':unittest.main()
