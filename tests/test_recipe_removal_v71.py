"""Real saved-recipe stores and delete/book websocket handlers, isolated HA I/O."""
import ast
import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

ROOT=Path(__file__).resolve().parents[1]
PREFIX='cook4me_removal_v71'
package=types.ModuleType(PREFIX);package.__path__=[str(ROOT/'custom_components/cook4me')];sys.modules[PREFIX]=package

class RecipeRemovalTests(unittest.TestCase):
    def setUp(self):
        stubs=patch.dict(sys.modules,{'homeassistant.core':types.SimpleNamespace(HomeAssistant=object),
            'homeassistant.util':types.SimpleNamespace(dt=types.SimpleNamespace()),
            'homeassistant.helpers.storage':types.SimpleNamespace(Store=lambda *args:types.SimpleNamespace(async_save=AsyncMock()))})
        stubs.start();self.addCleanup(stubs.stop)
        self.module=importlib.import_module(f'{PREFIX}.recipe_book')
        self.hubmodule=importlib.import_module(f'{PREFIX}.recipe_hub')
        self.book=self.module.Cook4MeRecipeBookStore(None,'entry')
        self.hub=self.hubmodule.Cook4MeRecipeHub(None,'entry')
        self.bridge=types.SimpleNamespace(recipe_hub=self.hub,_recipe_book_store=self.book)
        self.local={'id':'mine','source':'manual','title':'Local soup','ingredients':[],'steps':['Stir']}
        self.official={'displayVariantId':'123','source':'release_offline','title':'Official soup'}

    def handler(self,path,name):
        node=next(row for row in ast.parse((ROOT/path).read_text()).body if isinstance(row,ast.AsyncFunctionDef) and row.name==name)
        node.decorator_list=[]
        ns={'__package__':PREFIX,'_bridge':lambda *args:self.bridge,
            '_send_error':lambda *args:(_ for _ in ()).throw(AssertionError(str(args))),
            'recipe_book_store_for_bridge':self.module.recipe_book_store_for_bridge}
        ns['legacy']=types.SimpleNamespace(_bridge=ns['_bridge'],_send_error=ns['_send_error'])
        module=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),node],type_ignores=[])
        exec(compile(ast.fix_missing_locations(module),str(path),'exec'),ns)
        return ns[name]

    def test_remove_official_favorite_uses_saved_key_after_detail_identity_changes(self):
        async def run():
            await self.book.async_toggle('favorites',self.official)
            saved=self.book.snapshot()['favorites'][0]
            saved.update(groupingFunctionalId='newly-hydrated-group',title='Translated title')
            result=await self.book.async_toggle('favorites',saved,remove=True)
            self.assertFalse(result['added']);self.assertEqual(result['favorites'],[])
            again=await self.book.async_toggle('favorites',saved,remove=True)
            self.assertFalse(again['added']);self.assertEqual(again['favorites'],[])
        asyncio.run(run())

    def test_remove_only_changes_selected_collection_and_preserves_local_original(self):
        async def run():
            self.hub._data['recipes']=[deepcopy(self.local)]
            for collection in ['favorites','recipeList']:await self.book.async_toggle(collection,self.local)
            recipe=self.book.snapshot()['favorites'][0]
            replies={};connection=types.SimpleNamespace(send_result=lambda id,result:replies.__setitem__(id,result))
            handler=self.handler('custom_components/cook4me/websocket_v18.py','ws_recipe_book_toggle')
            await handler(None,connection,{'id':1,'collection':'favorites','recipe':recipe,'remove':True})
            self.assertEqual(replies[1]['favorites'],[])
            self.assertEqual(len(replies[1]['recipeList']),1)
            self.assertEqual(self.hub.recipes,[self.local])
        asyncio.run(run())

    def test_deleting_favorited_local_recipe_clears_both_saved_copies_and_survives_reload(self):
        async def run():
            self.hub._data['recipes']=[deepcopy(self.local),{**self.local,'id':'keep'}]
            for collection in ['favorites','recipeList']:
                await self.book.async_toggle(collection,self.local)
                await self.book.async_toggle(collection,{**self.official,'id':'mine','groupingFunctionalId':'official-group'})
            replies={};connection=types.SimpleNamespace(send_result=lambda id,result:replies.__setitem__(id,result))
            handler=self.handler('custom_components/cook4me/websocket.py','ws_recipe_delete')
            await handler(None,connection,{'id':1,'recipe_id':'mine'})
            self.assertTrue(replies[1]['deleted']);self.assertEqual([row['id'] for row in self.hub.recipes],['keep'])
            for collection in ['favorites','recipeList']:
                self.assertEqual(len(replies[1]['book'][collection]),1)
                self.assertEqual(replies[1]['book'][collection][0]['displayVariantId'],'123')
            persisted=deepcopy(self.book._store.async_save.call_args.args[0])
            restored=self.module.Cook4MeRecipeBookStore(None,'entry');restored._store.async_load=AsyncMock(return_value=persisted)
            await restored.async_load();self.assertEqual(restored.snapshot(),replies[1]['book'])
        asyncio.run(run())

    def test_delete_retry_cleans_old_orphan_favorite_without_deleting_another_recipe(self):
        async def run():
            self.hub._data['recipes']=[{**self.local,'id':'keep'}]
            await self.book.async_toggle('favorites',self.local)
            handler=self.handler('custom_components/cook4me/websocket.py','ws_recipe_delete');replies={}
            await handler(None,types.SimpleNamespace(send_result=lambda id,result:replies.__setitem__(id,result)),{'id':1,'recipe_id':'mine'})
            self.assertTrue(replies[1]['deleted']);self.assertEqual(replies[1]['book']['favorites'],[])
            self.assertEqual(self.hub.recipes[0]['id'],'keep')
        asyncio.run(run())

    def test_legacy_toggle_can_remove_hydrated_snapshot_without_adding_duplicate(self):
        async def run():
            await self.book.async_toggle('favorites',self.official)
            snapshot=self.book.snapshot()['favorites'][0];snapshot['groupingFunctionalId']='new'
            result=await self.book.async_toggle('favorites',snapshot)
            self.assertFalse(result['added']);self.assertEqual(result['favorites'],[])
        asyncio.run(run())

if __name__=='__main__':unittest.main()
