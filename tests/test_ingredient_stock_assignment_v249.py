"""Ingredient info can link a reviewed catalog ingredient to existing stock."""
import ast
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('assignment_v249')
pkg.__path__=[str(ROOT/'custom_components/cook4me')]
sys.modules[pkg.__name__]=pkg
from assignment_v249 import inventory

COMP=ROOT/'custom_components/cook4me'


def resolve_links(values, catalog, *, strict=False):
    """Execute the production resolver without importing HA nutrition modules."""
    path=COMP/'product_packages.py'
    tree=ast.parse(path.read_text(encoding='utf-8'))
    node=next(
        item for item in tree.body
        if isinstance(item,ast.FunctionDef) and item.name=='resolve_ingredient_links'
    )
    module=types.ModuleType('assignment_v249.product_link_resolver')
    module.__package__='assignment_v249'
    module.__file__=str(path)
    module.deepcopy=__import__('copy').deepcopy
    module.inventory_identity=inventory.inventory_identity
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec'),module.__dict__)
    return module.resolve_ingredient_links(values,catalog,strict=strict)


class IngredientStockAssignmentV249Tests(unittest.TestCase):
    def test_measured_stock_assigns_every_current_package_without_changing_stock(self):
        stock=[{
            'key':'stock-rice','name':'Rice product','unit':'g',
            'lots':[
                {'id':'a','quantity':300,'bestBefore':'2026-10-01','barcode':'11111111'},
                {'id':'b','quantity':200,'storage':'pantry','productName':'Second bag'},
            ],
        }]
        result=inventory.assign_inventory_ingredient(
            stock,'k:stock-rice',{'key':'catalog-rice','name':'Rice'}
        )
        row=result[0]
        self.assertEqual(row['quantity'],500)
        self.assertEqual([lot['id'] for lot in row['lots']],['a','b'])
        self.assertEqual(row['lots'][0]['bestBefore'],'2026-10-01')
        self.assertEqual(row['lots'][0]['barcode'],'11111111')
        self.assertEqual(row['lots'][1]['storage'],'pantry')
        for lot in row['lots']:
            self.assertEqual(lot['ingredientLinks'],[{'key':'catalog-rice','name':'Rice'}])
        linked=inventory.stock_for_ingredient(result,{'key':'catalog-rice','name':'Rice'})
        self.assertEqual(linked['quantity'],500)
        self.assertEqual(len(linked['lots']),2)

    def test_grouped_catalog_assignment_keeps_exact_recipe_source_identity(self):
        catalog=[{
            'id':'salt-display','key':'salt-display','ingredientId':'salt-display',
            'name':'Αλάτι','sourceIngredientIds':['salt-display','salt-recipe'],
            'displayGroupId':'ingredient:salt',
        }]
        resolved=resolve_links(
            [{'key':'salt-recipe','name':'Αλάτι'}],catalog,strict=True
        )
        self.assertEqual(resolved[0]['key'],'salt-recipe')
        self.assertEqual(
            resolved[0]['sourceIngredientIds'],
            ['salt-display','salt-recipe'],
        )
        self.assertEqual(resolved[0]['displayGroupId'],'ingredient:salt')

        stock=[{
            'key':'salt-cellar','name':'Salt cellar','unlimited':True,
        }]
        assigned=inventory.assign_inventory_ingredient(
            stock,'k:salt-cellar',resolved[0]
        )
        found=inventory.stock_for_ingredient(
            assigned,{'key':'salt-recipe','name':'Αλάτι'}
        )
        self.assertIsNotNone(found)
        self.assertTrue(found['unlimited'])

    def test_explicit_picker_source_ids_are_stable_inventory_identities(self):
        link=inventory.normalize_ingredient_links([{
            'key':'salt-display','name':'Αλάτι',
            'sourceIngredientIds':['salt-display','salt-recipe','salt-recipe'],
            'displayGroupId':'ingredient:salt',
        }])[0]
        self.assertEqual(
            link['sourceIngredientIds'],['salt-display','salt-recipe']
        )
        self.assertEqual(link['displayGroupId'],'ingredient:salt')
        self.assertEqual(
            inventory.ingredient_identities(link),
            {'k:salt-display','k:salt-recipe'},
        )

    def test_unlimited_stock_gets_row_link_and_existing_links_are_preserved(self):
        stock=[{
            'key':'seasoning','name':'Seasoning','unit':'pcs','unlimited':True,
            'ingredientLinks':[{'key':'salt','name':'Salt'}],
        }]
        result=inventory.assign_inventory_ingredient(
            stock,'k:seasoning',{'key':'pepper','name':'Pepper'}
        )
        self.assertTrue(result[0]['unlimited'])
        self.assertEqual(
            result[0]['ingredientLinks'],
            [{'key':'salt','name':'Salt'},{'key':'pepper','name':'Pepper'}],
        )
        again=inventory.assign_inventory_ingredient(
            result,'k:seasoning',{'key':'pepper','name':'Pepper'}
        )
        self.assertEqual(again[0]['ingredientLinks'],result[0]['ingredientLinks'])

    def test_primary_identity_is_already_assigned_and_missing_stock_is_rejected(self):
        stock=[{'key':'rice','name':'Rice','unit':'g','lots':[{'id':'a','quantity':100}]}]
        same=inventory.assign_inventory_ingredient(stock,'k:rice',{'key':'rice','name':'Rice'})
        self.assertNotIn('ingredientLinks',same[0]['lots'][0])
        with self.assertRaisesRegex(ValueError,'not found'):
            inventory.assign_inventory_ingredient(stock,'k:missing',{'key':'rice','name':'Rice'})

    def test_route_and_ingredient_info_expose_reviewed_identity(self):
        route=(COMP/'websocket_v14.py').read_text(encoding='utf-8')
        info=(COMP/'websocket_v18.py').read_text(encoding='utf-8')
        hub=(COMP/'recipe_hub.py').read_text(encoding='utf-8')
        self.assertIn('ws_inventory_assign_ingredient',route)
        self.assertIn('"cook4me/v14/inventory_assign_ingredient"',route)
        self.assertIn('resolve_ingredient_links([msg["ingredient"]], catalog, strict=True)',route)
        self.assertIn('async_inventory_assign_ingredient',hub)
        self.assertIn('ingredient.get("ingredientId")',info)


if __name__=='__main__':
    unittest.main()
