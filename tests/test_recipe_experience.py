from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "cook4me_recipe_experience_test",
        ROOT / "custom_components/cook4me/recipe_experience.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RecipeExperienceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_recipe_storage_key_prefers_official_group_and_local_id(self):
        self.assertEqual(
            self.module.recipe_storage_key(
                {"groupingFunctionalId": "M_GROUP_42", "id": "local-1"}
            ),
            "g:M_GROUP_42",
        )
        self.assertEqual(
            self.module.recipe_storage_key({"id": "local-1", "source": "manual"}),
            "local:local-1",
        )

    def test_ingredient_identity_prefers_stable_food_key(self):
        left = {"foodKey": "M_FOOD_RICE", "foodName": "Rice"}
        right = {"key": "M_FOOD_RICE", "name": "Reis"}
        self.assertEqual(self.module.ingredient_identity(left), "k:M_FOOD_RICE")
        self.assertTrue(self.module.ingredient_matches(left, right))

    def test_ingredient_name_fallback_matching_is_unicode_safe(self):
        self.assertTrue(
            self.module.ingredient_matches(
                {"name": "Crème fraîche"}, {"name": "Creme fraiche"}
            )
        )

    def test_coverage_returns_exact_quantity_percentage(self):
        recipe = {
            "match": {
                "quantityAvailability": [
                    {
                        "key": "M_FOOD_RICE",
                        "name": "Rice",
                        "status": "shortage",
                        "coverage": 0.36,
                        "requiredQuantity": 500,
                        "requiredUnit": "g",
                        "availableQuantity": 180,
                        "availableUnit": "g",
                        "missingQuantity": 320,
                        "missingUnit": "g",
                    }
                ]
            }
        }
        result = self.module.ingredient_coverage(
            recipe, {"foodKey": "M_FOOD_RICE", "foodName": "Rice"}
        )
        self.assertEqual(result["percent"], 36)
        self.assertEqual(result["status"], "shortage")
        self.assertEqual(result["missingQuantity"], 320)

    def test_presence_fallback_supports_owned_missing_and_staple(self):
        for status, expected in (("at_home", 100), ("missing", 0), ("staple", 100)):
            with self.subTest(status=status):
                result = self.module.ingredient_coverage(
                    {
                        "match": {
                            "ingredientAvailability": [
                                {"key": "M_FOOD_1", "name": "Water", "status": status}
                            ]
                        }
                    },
                    {"foodKey": "M_FOOD_1", "foodName": "Water"},
                )
                self.assertEqual(result["percent"], expected)
                self.assertEqual(result["status"], status)

    def test_unknown_coverage_is_explicit(self):
        result = self.module.ingredient_coverage(
            {"match": {}}, {"name": "Mystery ingredient"}
        )
        self.assertIsNone(result["percent"])
        self.assertEqual(result["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
