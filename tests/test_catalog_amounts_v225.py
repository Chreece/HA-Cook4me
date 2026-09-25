"""Catalog-only quantity cleanup, stable aliases, and recipe/purchase preservation."""
from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PKG = 'cook4me_amounts_v225'
package = ModuleType(PKG)
package.__path__ = [str(ROOT/'custom_components/cook4me')]
sys.modules[PKG] = package
amounts = importlib.import_module(PKG+'.catalog_amounts')
presentation = importlib.import_module(PKG+'.catalog_presentation')


class CatalogAmounts(unittest.TestCase):
    def test_numeric_and_unit_annotations(self):
        cases = {
            '250 g Rice': 'Rice', '200 milliliters of water': 'water', 'Rice, 300 milliliters': 'Rice',
            '1 1/2 tbsp olive oil': 'olive oil', '1½ cups Rice': 'Rice',
            '2 x 400 g canned tomatoes': 'canned tomatoes',
            '1,5 EL Olivenöl': 'Olivenöl', 'Lachsfilets à 200g': 'Lachsfilets',
            '1 κ.σ. ελαιόλαδο': 'ελαιόλαδο', 'Ελαιόλαδο (κ.σ.)': 'Ελαιόλαδο',
            'Ρύζι (φλιτζάνι)': 'Ρύζι', 'Νερό, 300 ml': 'Νερό',
            'Φιλέτα σολομού, 200 g το καθένα': 'Φιλέτα σολομού',
            'Κρέμα, περίπου 100 γρ.': 'Κρέμα',
            'Juice of 1.5 lemons and a little': 'Juice of lemons',
            'cardamom, 1 cinnamon stick, 2 bay leaves': 'cardamom, cinnamon stick, bay leaves',
            'Soup for 4 servings': 'Soup', 'Σούπα για 4 μερίδες': 'Σούπα',
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(amounts.catalog_name(source), expected)
                self.assertEqual(amounts.catalog_name(expected), expected)

    def test_food_specs_and_distinct_forms_survive(self):
        for name in ('15% fat cream', 'Cream, 30% fat', '100% pistachio cream',
                     'Chocolate, 50/55% cocoa', '3:1 preserving sugar', '00 Pasta flour',
                     'Weizenmehl Type 550', '5-spice powder', '7 grain bread',
                     'Canned tomatoes', 'Fresh tomatoes', 'Dried tomatoes',
                     'Garlic cloves', 'Cup noodles', 'Κελυφωτά φιστίκια (ανάλατα)'):
            with self.subTest(name=name):
                self.assertEqual(amounts.catalog_name(name), name)

    def test_dedup_retains_every_identity_and_old_search_alias(self):
        payload = {'ingredients': [
            {'id': 'oil', 'key': 'oil', 'canonicalName': 'Olive oil', 'translations': {'de': 'Olivenöl'}},
            {'id': 'spoon', 'canonicalName': 'Tablespoon olive oil', 'translations': {'de': '1 EL Olivenöl'}},
            {'id': 'weight', 'canonicalName': '250 g Olive oil'},
            {'id': 'extra', 'canonicalName': 'Extra-virgin olive oil'},
            {'id': 'tomato', 'canonicalName': 'Fresh tomatoes'},
            {'id': 'canned', 'canonicalName': '400 g Canned tomatoes'},
        ]}
        before = deepcopy(payload)
        for language in ('el', 'de', 'en'):
            rows = presentation.ingredient_choices(payload, language)
            oil = next(row for row in rows if row.get('key') == 'oil')
            self.assertEqual(set(oil['sourceIngredientIds']), {'oil', 'spoon', 'weight'})
            self.assertEqual(len(rows), 4)
            self.assertEqual(len(rows), len({presentation.name_key(r['name']) for r in rows}))
            self.assertEqual(presentation.ingredient_choices(payload, language, '250 g')[0]['key'], 'oil')
        self.assertEqual(payload, before)

    def test_recipe_and_shopping_amounts_and_original_labels_survive(self):
        recipes = importlib.import_module(PKG+'.recipe_presentation')
        shopping = importlib.import_module(PKG+'.shopping_presentation')
        raw = {'key': 'oil', 'canonicalName': 'Tablespoon olive oil',
               'name': '2 tbsp olive oil', 'quantity': 2, 'unit': 'tbsp'}
        recipe = {'title': 'Example', 'ingredients': [raw], 'servings': 3}
        before = deepcopy(recipe)
        with patch.object(recipes.release_catalog, 'ingredient_display_name', side_effect=presentation.display_name), \
             patch.object(recipes.release_catalog, 'ingredient_stock_identities', return_value=()):
            shown = recipes.present_recipe(recipe, 'el')
            bought = shopping.shopping_rows([raw], language='el', country='DE', supermarket_language='de')
        for item in (shown['ingredients'][0], bought[0]):
            self.assertEqual((item['quantity'], item['unit']), (2, 'tbsp'))
            self.assertEqual(item['originalName'], '2 tbsp olive oil')
        self.assertEqual(recipe, before)


class ShippedCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((ROOT/'custom_components/cook4me/catalog/merged_catalog.v1.json').read_bytes())
        cls.before = hashlib.sha256(json.dumps(cls.payload, ensure_ascii=False).encode()).hexdigest()
        cls.rows = {lang: presentation.ingredient_choices(cls.payload, lang) for lang in ('el', 'de', 'en')}

    def test_shipped_measurement_variants_are_single_choices(self):
        for lang, rows in self.rows.items():
            names = [presentation.name_key(row['name']) for row in rows]
            self.assertEqual(len(names), len(set(names)))
            for key in ('olive oil', 'water'):
                matches = [row for row in rows if presentation.name_key(row['canonicalName']) == key]
                self.assertEqual(len(matches), 1, (lang, key, [r['name'] for r in matches]))
                self.assertGreater(len(matches[0]['sourceIngredientIds']), 10)
            for row in rows:
                self.assertEqual(amounts.catalog_name(row['name']), row['name'], (lang, row['name']))
                self.assertNotRegex(row['name'], r'\((?:κ\.σ\.|κ\.γ\.|φλιτζάνι)\)')
            print(f'{lang}: {len(rows)} unique, amount-free catalog choices')

    def test_catalog_choices_never_mutate_recipe_or_source_records(self):
        after = hashlib.sha256(json.dumps(self.payload, ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(after, self.before)


if __name__ == '__main__':
    unittest.main()
