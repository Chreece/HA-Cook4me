"""Food rules filter discovery and annotate cooking; delivery stays independent."""
from copy import deepcopy
import unittest
from test_recipe_logic import logic
import test_diet_send_v77 as send_tests


class IngredientGuidanceTests(unittest.TestCase):
    def test_every_identifiable_conflict_is_annotated_without_inventing_replacements(self):
        recipe = {'ingredients': [
            {'name': 'Патица', 'canonicalName': 'Duck', 'quantity': 200, 'unit': 'g'},
            {'name': 'Gelatin'}, {'name': 'Peanuts'}, {'name': 'Rice', 'ingredientId': 'rice-gr'},
            {'name': 'Pepper'}, {'name': 'Carrot'}], 'steps': ['Cook the original recipe']}
        before = deepcopy(recipe)
        match = logic.score_recipe(recipe, {'diet': 'vegetarian', 'allergies': ['peanut'],
            'avoid': ['pepper'], 'excludedIngredients': [{'ingredientId': 'rice', 'name': 'Rice', 'sourceIngredientIds': ['rice-gr']}]})
        rows = match['ingredientChanges']
        self.assertEqual([r['ingredientIndex'] for r in rows], [0, 1, 2, 3, 4])
        self.assertEqual(rows[0]['replacement']['key'], 'tofu')
        self.assertTrue(all(r['replacement'] is None for r in rows[1:]))
        self.assertEqual(rows[2]['reasons'], ['allergy:peanut'])
        self.assertEqual(rows[3]['reasons'], ['excluded:Rice'])
        self.assertEqual(rows[4]['reasons'], ['avoid:pepper'])
        self.assertFalse(match['safe']); self.assertFalse(match['eligibleWithSubstitutions'])
        self.assertEqual(recipe, before)

    def test_recipe_level_flags_never_strike_an_unrelated_ingredient(self):
        match = logic.score_recipe({'ingredients': ['Rice'], 'excludedFoods': ['GELATIN']}, {'diet': 'vegetarian'})
        self.assertFalse(match['safe']); self.assertEqual(match['ingredientChanges'], [])

    def test_explicit_ingredient_metadata_marks_unknown_name_without_guessing(self):
        match = logic.score_recipe({'ingredients': [{'name': 'Unknown', 'diets': {'vegan': 'incompatible'}}]}, {'diet': 'vegan'})
        self.assertEqual(match['ingredientChanges'][0]['reasons'], ['diet:vegan'])
        self.assertIsNone(match['ingredientChanges'][0]['replacement'])

    def test_compatible_rows_and_search_eligibility_are_preserved(self):
        compatible = logic.score_recipe({'ingredients': ['Goat cheese', 'Rice']}, {'diet': 'vegetarian'})
        self.assertTrue(compatible['safe']); self.assertEqual(compatible['ingredientChanges'], [])
        adapted = logic.score_recipe({'ingredients': ['Duck', 'Rice']}, {'diet': 'vegetarian'})
        self.assertFalse(adapted['safe']); self.assertTrue(adapted['eligibleWithSubstitutions'])


# Exercise the actual bridge and dashboard/queue functions as installer preflight.
class DeliveryGuidanceTests(send_tests.DietSendTests):
    pass


if __name__ == '__main__':
    unittest.main()
