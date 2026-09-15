"""Exercise the active capability handlers and localized shopping boundaries."""
from __future__ import annotations
import ast
import asyncio
from copy import deepcopy
from datetime import date
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'cook4me_actions_v68'
package = types.ModuleType(PREFIX)
package.__path__ = [str(ROOT / 'custom_components/cook4me')]
sys.modules[PREFIX] = package


def production(filename, name, namespace):
    path = ROOT / 'custom_components/cook4me' / filename
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    node.decorator_list = []
    namespace.update(__package__=PREFIX)
    future = ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[])), str(path), 'exec'), namespace)
    return namespace[name]


def capability_fixture():
    const = types.SimpleNamespace(AITaskEntityFeature=types.SimpleNamespace(GENERATE_DATA=1), DATA_COMPONENT='component', DATA_PREFERENCES='preferences')
    entity = lambda id, platform: types.SimpleNamespace(entity_id=id, platform=types.SimpleNamespace(platform_name=platform), available=True, supported_features=1)
    entities = [entity('ai_task.local', 'ollama'), entity('ai_task.cloud', 'openai_conversation')]
    hass = types.SimpleNamespace(data={'component':types.SimpleNamespace(entities=entities), 'preferences':types.SimpleNamespace(gen_data_entity_id='ai_task.cloud')}, states={row.entity_id:types.SimpleNamespace(state='unknown') for row in entities})
    bridge = types.SimpleNamespace(recipe_hub=types.SimpleNamespace(ui_preferences={}))
    answers = {}
    namespace = dict(legacy=types.SimpleNamespace(_bridge=lambda *_:bridge, _send_error=lambda c,m,e:(_ for _ in ()).throw(e)),
        v5=types.SimpleNamespace(_default_ai_task_entity_id=lambda _: 'ai_task.cloud'),
        v11=types.SimpleNamespace(_device_language=lambda _: 'de'), _device_language=lambda _:'de',
        recipe_languages=types.SimpleNamespace(language_options=lambda:[{'code':'de'}]))
    with patch.dict(sys.modules, {'homeassistant.components.ai_task.const':const}):
        production('websocket_v11.py', 'ws_capabilities', namespace)(hass, types.SimpleNamespace(send_result=lambda id,row:answers.update(active=row)), {'id':1})
        answers['seed'] = production('websocket_v28.py', '_capabilities', namespace)(hass, bridge)
    return answers


class RecipeActionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shopping = importlib.import_module(f'{PREFIX}.shopping_presentation')
        cls.translation = importlib.import_module(f'{PREFIX}.recipe_translation')

    def test_active_capabilities_and_cached_seed_expose_unused_local_task(self):
        for result in capability_fixture().values():
            self.assertTrue(result['localAiTaskAvailable'])
            self.assertEqual(result['localAiTaskEntityId'], 'ai_task.local')
            self.assertEqual(result['localAiTaskEntityIds'], ['ai_task.local'])
            self.assertEqual(result['defaultAiTaskEntityId'], 'ai_task.cloud')

    def test_shopping_names_use_three_languages_and_exact_shortage(self):
        source = {'key':'M_FOOD_79', 'ingredientId':'M_FOOD_79', 'name':'Carottes', 'foodName':'Carottes', 'quantity':100, 'unit':'g', 'applicationDescription':'200 g Carottes épluchées'}
        before = deepcopy(source)
        row = self.shopping.shopping_rows([source], 'el-GR', 'DE')[0]
        self.assertEqual(row['name'], 'Καρότο (Karotten; Carottes)')
        self.assertEqual((row['quantity'], row['unit']), (100, 'g'))
        self.assertEqual(row['ingredientId'], source['ingredientId'])
        namespace = {'_text':lambda value:str(value or '').strip()}
        production('ingredient_catalog.py', 'ingredient_identity', namespace)
        format_name = production('ingredient_catalog.py', 'shopping_item_name', namespace)
        self.assertEqual(format_name(row), '100 g Καρότο (Karotten; Carottes)')
        self.assertNotIn('applicationDescription', row)
        self.assertEqual(source, before)
        self.assertEqual(self.shopping.shopping_rows([source], 'fr', 'FR')[0]['name'], 'Carotte (Carottes)')
        self.assertEqual(self.shopping.shopping_rows([{**source,'name':'Carotte'}], 'fr', 'FR')[0]['name'], 'Carotte')
        self.assertEqual(self.shopping.shopping_rows(['My handwritten item'], 'el', 'DE'), ['My handwritten item'])

    def test_plan_shopping_recovers_identity_and_all_original_names(self):
        rows = [{'identity':'k:M_FOOD_79', 'name':'Carottes', 'quantity':0.3, 'unit':'kg'}]
        sources = [{'key':'M_FOOD_79', 'name':name} for name in ('Carottes','Carrots','Carottes')]
        result = self.shopping.shopping_rows(rows, 'el', 'DE', sources)[0]
        self.assertEqual(result['name'], 'Καρότο (Karotten; Carottes; Carrots)')
        self.assertEqual((result['quantity'], result['unit']), (0.3,'kg'))

    def test_actual_shopping_handlers_forward_localized_rows(self):
        ingredient = {'key':'M_FOOD_79','name':'Carottes','quantity':100,'unit':'g'}
        bridge = types.SimpleNamespace(recipe_hub=types.SimpleNamespace(profile={}))
        store = types.SimpleNamespace(snapshot=lambda *_args, **_kw:{'shoppingDelta':[{'identity':'k:M_FOOD_79',**ingredient}], 'slots':[{'recipe':{'ingredients':[ingredient]}}]})
        async def executor(fn, *args): return fn(*args)
        hass = types.SimpleNamespace(config=types.SimpleNamespace(country='DE'), async_add_executor_job=executor)
        sink = AsyncMock(return_value={'count':1})
        namespace = dict(legacy=types.SimpleNamespace(_bridge=lambda *_:bridge, _send_error=lambda c,m,e:(_ for _ in ()).throw(e)),
            _add_to_shopping_list=sink, _shopping_add=sink, meal_lifecycle_store_for_bridge=AsyncMock(return_value=store),
            dt_util=types.SimpleNamespace(now=lambda:types.SimpleNamespace(date=lambda:date(2026,9,15))))
        connection = types.SimpleNamespace(send_result=lambda *_:None)
        for file, name in [('websocket_v11.py','ws_shopping_add'),('websocket_v20.py','ws_week_add_shopping')]:
            asyncio.run(production(file,name,namespace)(hass,connection,{'id':1,'ingredients':[ingredient],'ui_language':'el'}))
            row = sink.await_args.args[1][0]
            self.assertEqual(row['name'],'Καρότο (Karotten; Carottes)')
            self.assertEqual(row['quantity'],100)

    def test_translation_prompt_only_requests_title_and_steps(self):
        recipe = {'title':'New soup','ingredients':[{'name':'Must not be translated here'}], 'steps':[{'instruction':'Cook for 5 minutes.'}]}
        prompt = self.translation.translation_prompt(recipe,'el')
        payload = json.loads(prompt.split('Input: ',1)[1])
        self.assertEqual(payload,{'id':'0','title':'New soup','steps':['Cook for 5 minutes.']})
        self.assertNotIn('Must not be translated here', prompt)
        result = self.translation.apply_saved_translation(recipe,{'title':'Νέα σούπα','steps':['Μαγειρέψτε για 5 λεπτά.']},'el')
        self.assertEqual(result['ingredients'],recipe['ingredients'])
        self.assertEqual(result['title'],'Νέα σούπα')
        self.assertEqual(result['steps'][0]['instruction'],'Μαγειρέψτε για 5 λεπτά.')


if __name__ == '__main__':
    if '--capabilities' in sys.argv: print(json.dumps(capability_fixture()))
    else: unittest.main()
