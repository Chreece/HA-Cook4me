"""Actual catalog identities keep whole peppers separate from seasoning spices."""
from copy import deepcopy
import importlib
import unittest

from test_catalog_amounts_v225 import PKG, presentation

catalog = importlib.import_module(PKG+'.release_catalog')
recipes = importlib.import_module(PKG+'.recipe_presentation')
shopping = importlib.import_module(PKG+'.shopping_presentation')


class GreekPeppers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = catalog.load_release_catalog()
        cls.sources = {r['id']: r for r in cls.payload['ingredients']}
        cls.choices = {lang: catalog.ingredient_choices(lang) for lang in ('el', 'de', 'en')}

    def choice(self, ident, lang='el'):
        return next(row for row in self.choices[lang] if ident in row['sourceIngredientIds'])

    def test_provider_pepper_homonyms_remain_separate(self):
        expected = {
            'M_FOOD_389': ('Πιπεριά', 'Paprika', 'Bell pepper'),
            'M_FOOD_388': ('Πιπέρι', 'Pfeffer', 'Pepper'),
            'M_FOOD_377': ('Πιπεριά τσίλι', 'Chilischote', 'Chili pepper'),
            'M_FOOD_358': ('Πάπρικα', 'Paprikapulver', 'Paprika'),
        }
        for index, language in enumerate(('el', 'de', 'en')):
            groups = []
            for ident, names in expected.items():
                with self.subTest(ingredient=ident, language=language):
                    row = self.choice(ident, language)
                    self.assertEqual(row['name'], names[index])
                    self.assertEqual(catalog.ingredient_display_name({'ingredientId': ident}, language), names[index])
                    groups.append(set(row['sourceIngredientIds']))
            for i, ids in enumerate(groups):
                for other in groups[i+1:]:
                    self.assertFalse(ids & other)

    def test_prepared_whole_peppers_join_vegetable_choice(self):
        targets = [key for key in presentation.presentation_overrides() if key.startswith('local:')]
        self.assertEqual(len(targets), 6)
        for ident in targets:
            with self.subTest(ingredient=ident):
                self.assertEqual(catalog.ingredient_display_name({'ingredientId': ident}, 'el'), 'Πιπεριά')
                self.assertIs(self.choice(ident), self.choice('M_FOOD_389'))
                self.assertIsNot(self.choice(ident), self.choice('M_FOOD_388'))

    def test_spices_and_colored_peppers_keep_their_meaning(self):
        for source, greek in {
            'Black pepper': 'Μαύρο πιπέρι', 'White pepper': 'Λευκό πιπέρι',
            'Ground pepper': 'Αλεσμένο πιπέρι', 'Salt and pepper': 'Αλάτι και πιπέρι',
            'Paprika powder': 'Πάπρικα σε σκόνη', 'Smoked paprika': 'Καπνιστή πάπρικα',
            'Red pepper': 'Κόκκινη πιπεριά', 'Green pepper': 'Πράσινη πιπεριά',
            'Yellow pepper': 'Κίτρινη πιπεριά',
        }.items():
            self.assertEqual(presentation.display_name({'canonicalName': source}, 'el'), greek)

    def test_recipes_and_purchases_use_correct_name_without_changing_amount(self):
        ingredient = {'ingredientId': 'M_FOOD_389', 'name': 'Paprika', 'quantity': 2, 'unit': 'piece'}
        recipe = {'title': 'Example', 'ingredients': [ingredient], 'servings': 2}
        before = deepcopy(recipe)
        shown = recipes.present_recipe(recipe, 'el')['ingredients'][0]
        bought = shopping.shopping_rows([ingredient], 'el', 'DE', supermarket_language='de')[0]
        self.assertEqual(shown['displayName'], 'Πιπεριά')
        self.assertEqual(bought['uiName'], 'Πιπεριά')
        self.assertEqual(bought['supermarketName'], 'Paprika')
        for row in (shown, bought):
            self.assertEqual((row['quantity'], row['unit'], row['originalName']), (2, 'piece', 'Paprika'))
        self.assertEqual(recipe, before)

    def test_overrides_are_exact_id_display_views_and_preserve_provider_data(self):
        for ident in presentation.presentation_overrides():
            source = self.sources[ident]
            before = deepcopy(source)
            view = presentation.presentation_ingredient(source)
            self.assertEqual(presentation.presentation_ingredient(view), view)
            self.assertEqual(view['id'], source['id'])
            self.assertIn(source['canonicalName'], view['aliases']['en'])
            self.assertEqual(source, before)
        unknown = {'id': 'unknown', 'canonicalName': 'Pepper', 'translations': {'de': 'Paprika'}}
        self.assertIs(presentation.presentation_ingredient(unknown), unknown)


if __name__ == '__main__':
    unittest.main()
