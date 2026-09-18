"""Real multilingual catalog matching and the review-only scanner endpoints."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import AsyncMock

import test_product_capture_v78 as capture
import test_runtime_audit_v74 as runtime


class ScannerMatchingTests(unittest.IsolatedAsyncioTestCase):
    setUp = runtime.AuditTests.setUp
    asyncTearDown = runtime.AuditTests.asyncTearDown
    api = capture.ProductCaptureTests.api

    def modules(self):
        return (importlib.import_module(runtime.PREFIX+'.barcode'),
                importlib.import_module(runtime.PREFIX+'.release_catalog'))

    def test_matches_foreign_aliases_without_changing_the_ui_label_or_identity(self):
        barcode, release = self.modules()
        catalog = release.ingredient_choices('el')
        for name in ['Kichererbsen', 'Pois chiche', 'Garbanzos', 'Ciecierzyca', 'ひよこ豆']:
            with self.subTest(name=name):
                rows = barcode.suggest_catalog_matches({'genericName':name}, catalog)
                self.assertEqual(rows[0]['ingredient']['key'], 'M_FOOD_385')
                self.assertEqual(rows[0]['ingredient']['name'], 'Ρεβίθια')
                self.assertEqual(rows[0]['score'], 1)
                self.assertIsNotNone(barcode.confident_match(rows))

    def test_ambiguous_and_weak_matches_remain_suggestions(self):
        barcode, _ = self.modules()
        catalog = [{'key':'one','name':'First','searchAliases':['Oat milk']},
                   {'key':'two','name':'Second','translations':{'de':'Oat milk'}}]
        self.assertIsNone(barcode.confident_match(barcode.suggest_catalog_matches({'genericName':'Oat milk'}, catalog)))
        weak = barcode.suggest_catalog_matches({'categories':['Oat milk']}, catalog[:1])
        self.assertIsNone(barcode.confident_match(weak))
        self.assertEqual(barcode.suggest_catalog_matches({'name':'Unknown ZX999'}, catalog), [])

    def test_keyless_foods_return_their_stable_catalog_id(self):
        barcode, release = self.modules()
        butter = next(row for row in release.ingredient_choices('el') if row['canonicalName']=='Butter')
        self.assertFalse(butter.get('key'))
        before = deepcopy(butter)
        rows = barcode.suggest_catalog_matches({'genericName':'Tereyağı'}, [butter])
        self.assertEqual(rows[0]['ingredient']['key'], butter['ingredientId'])
        self.assertEqual(butter, before)

    async def test_scanner_catalog_is_the_complete_offline_picker_with_all_aliases(self):
        _, release = self.modules()
        ns=self.api();ns['__package__']=runtime.PREFIX
        ns['v11']=runtime.NS(_ingredient_catalog=AsyncMock(side_effect=AssertionError('No online catalog')))
        runtime.functions('websocket_v33.py', {'_catalog'}, ns)
        rows=await ns['_catalog'](self.hass,self.bridge,{'language':'el'})
        picker=release.ingredient_choices('el')
        self.assertGreater(len(rows),2000)
        self.assertEqual(len(rows),len(picker))
        self.assertEqual([row['name'] for row in rows],[row['name'] for row in picker])
        self.assertTrue(all(row['key'] and row['searchAliases'] for row in rows))

    async def test_lookup_returns_an_automatic_multilingual_match_without_saving_stock(self):
        barcode, release = self.modules()
        ns=self.api();ns['_catalog']=AsyncMock(return_value=release.ingredient_choices('el'))
        ns['suggest_catalog_matches']=barcode.suggest_catalog_matches
        ns['confident_match']=barcode.confident_match
        ns['v23']._cached_product=AsyncMock(return_value={'found':True,'genericName':'Kichererbsen','productName':'Bio Kichererbsen'})
        await ns['ws_barcode_lookup'](self.hass,self.connection,{'id':1,'entry_id':'one','barcode':'12345678','language':'el'})
        self.assertEqual(self.errors,[])
        self.assertEqual(self.results[0]['match']['ingredient']['key'],'M_FOOD_385')
        self.assertEqual(self.results[0]['match']['ingredient']['name'],'Ρεβίθια')
        self.assertEqual(self.bridge.recipe_hub.profile['houseIngredients'],[])
        self.mapping.async_set.assert_not_awaited()

    async def test_saved_mapping_is_resolved_to_the_current_localized_catalog(self):
        ns=self.api()
        self.mapping.get=lambda code:{'ingredient':{'key':'rice','name':'Reis'},'productName':'Remembered rice'}
        ns['_catalog']=AsyncMock(return_value=[{'key':'rice','name':'Ρύζι'}])
        ns['v23']._cached_product=AsyncMock(side_effect=TimeoutError())
        await ns['ws_barcode_lookup'](self.hass,self.connection,{'id':1,'entry_id':'one','barcode':'12345678','language':'el'})
        self.assertEqual(self.errors,[])
        self.assertEqual(self.results[0]['mapping']['ingredient']['name'],'Ρύζι')
        self.assertEqual(self.results[0]['product'],{'found':False})

    async def test_full_picker_keyless_choice_can_be_saved_under_the_same_identity(self):
        _, release=self.modules()
        ns=self.api();ns['__package__']=runtime.PREFIX
        runtime.functions('websocket_v33.py', {'_catalog'}, ns)
        row=next(row for row in release.ingredient_choices('el') if row['canonicalName']=='Butter')
        await ns['ws_product_add'](self.hass,self.connection,{'id':1,'entry_id':'one','request_id':'v111-butter-0000000001',
            'ingredient':{'key':row['ingredientId'],'name':row['name']},'quantity':250,'unit':'g','language':'el',
            'lot_metadata':{'storageLocationId':'pantry','productName':'Butter'}})
        self.assertEqual(self.errors,[])
        self.assertEqual(self.results[0]['status'],'added')
        item=self.bridge.recipe_hub.profile['houseIngredients'][0]
        self.assertEqual(item['key'],row['ingredientId'])
        self.assertEqual(item['name'],row['name'])


if __name__=='__main__':
    unittest.main()
