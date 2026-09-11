from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, COMPONENT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


safety = _load("cook4me_recipe_safety_index_v60_test", "recipe_safety_index_v60.py")
search = _load("cook4me_catalog_search_index_safety_test", "catalog_search_index.py")


class RecipeSafetyIndexV60Tests(unittest.TestCase):
    def _payload(self):
        return {
            "ingredients": [
                {
                    "id": "concept:food:tomato",
                    "conceptId": "concept:food:tomato",
                    "canonicalName": "Tomato",
                    "classification": "food",
                    "intelligence": {
                        "diets": {"vegetarian": True, "vegan": True},
                        "allergens": {"peanut": "absent", "milk": "absent"},
                    },
                },
                {
                    "id": "concept:food:rice",
                    "conceptId": "concept:food:rice",
                    "canonicalName": "Rice",
                    "classification": "food",
                    "intelligence": {
                        "diets": {"vegetarian": True, "vegan": True},
                        "allergens": {"peanut": "absent", "milk": "absent"},
                    },
                },
                {
                    "id": "concept:food:cream",
                    "conceptId": "concept:food:cream",
                    "canonicalName": "Cream",
                    "classification": "food",
                    "intelligence": {
                        "diets": {"vegetarian": True, "vegan": False},
                        "allergens": {"milk": "present", "peanut": "absent"},
                    },
                },
                {
                    "id": "concept:food:unknown-sauce",
                    "conceptId": "concept:food:unknown-sauce",
                    "canonicalName": "Unknown sauce",
                    "classification": "ambiguous",
                },
                {
                    "id": "local:en:paper",
                    "canonicalName": "Baking paper",
                    "classification": "equipment",
                },
            ],
            "recipes": [
                {
                    "canonicalName": "Vegan tomato rice",
                    "variants": [
                        {
                            "title": "Vegan tomato rice",
                            "language": "en",
                            "ingredients": [
                                {"conceptId": "concept:food:tomato"},
                                {"conceptId": "concept:food:rice"},
                                {"ingredientId": "local:en:paper", "classification": "equipment"},
                            ],
                        }
                    ],
                },
                {
                    "canonicalName": "Cream rice",
                    "variants": [
                        {
                            "title": "Cream rice",
                            "language": "en",
                            "ingredients": [
                                {"conceptId": "concept:food:rice"},
                                {"conceptId": "concept:food:cream"},
                            ],
                        }
                    ],
                },
                {
                    "canonicalName": "Mystery rice",
                    "variants": [
                        {
                            "title": "Mystery rice",
                            "language": "en",
                            "ingredients": [
                                {"conceptId": "concept:food:rice"},
                                {"conceptId": "concept:food:unknown-sauce"},
                            ],
                        }
                    ],
                },
            ],
        }

    def setUp(self):
        self.compiled = safety.compile_recipe_safety_index(self._payload())
        self.prepared = safety.prepare_recipe_safety_index(self.compiled)

    def test_explicit_vegan_and_peanut_absence_is_strictly_safe(self):
        result = safety.recipe_safety(
            self.prepared, 0, diet="vegan", allergies=["peanut"]
        )
        self.assertEqual(result["state"], "compatible")
        self.assertTrue(result["strictlyAllowed"])

    def test_known_milk_presence_and_nonvegan_ingredient_block_recipe(self):
        result = safety.recipe_safety(
            self.prepared, 1, diet="vegan", allergies=["milk"]
        )
        self.assertEqual(result["state"], "incompatible")
        self.assertEqual(result["dietState"], "incompatible")
        self.assertEqual(result["allergyState"], "incompatible")
        self.assertFalse(result["strictlyAllowed"])

    def test_unknown_ambiguous_food_evidence_is_not_treated_as_safe(self):
        result = safety.recipe_safety(
            self.prepared, 2, diet="vegan", allergies=["peanut"]
        )
        self.assertEqual(result["state"], "unknown")
        self.assertFalse(result["strictlyAllowed"])
        self.assertEqual(result["dietState"], "unknown")
        self.assertEqual(result["allergyState"], "unknown")

    def test_reviewed_equipment_does_not_poison_food_safety(self):
        # Recipe 0 contains baking paper with no diet/allergen facts. Because it
        # is reviewed equipment, it must not turn a proven-safe food recipe unknown.
        result = safety.recipe_safety(
            self.prepared, 0, diet="vegan", allergies=["milk", "peanut"]
        )
        self.assertTrue(result["strictlyAllowed"])

    def test_allowed_set_intersects_diet_and_allergy_before_search(self):
        allowed = safety.allowed_recipe_indices(
            self.prepared, diet="vegan", allergies=["peanut"]
        )
        self.assertEqual(allowed, frozenset({0}))

    def test_unknown_allergen_is_absent_from_strict_safe_set(self):
        allowed = safety.allowed_recipe_indices(
            self.prepared, allergies=["peanut"]
        )
        self.assertEqual(allowed, frozenset({0, 1}))
        self.assertNotIn(2, allowed)

    def test_search_filter_is_applied_before_pagination_and_total(self):
        payload = self._payload()
        compiled_search = search.compile_search_index(payload)
        prepared_search = search.prepare_search_index(compiled_search)
        result = search.search_index(
            prepared_search,
            "rice",
            allowed_indices=frozenset({0, 2}),
            page=0,
            size=1,
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["indices"]), 1)
        second = search.search_index(
            prepared_search,
            "rice",
            allowed_indices=frozenset({0, 2}),
            page=1,
            size=1,
        )
        self.assertEqual(second["total"], 2)
        self.assertEqual(len(second["indices"]), 1)
        self.assertNotEqual(result["indices"], second["indices"])

    def test_compiled_index_records_unknown_is_never_safe_policy(self):
        self.assertFalse(self.compiled["policy"]["unknownIsSafe"])
        self.assertTrue(self.compiled["policy"]["strictAllergyRequiresExplicitAbsence"])
        self.assertEqual(self.compiled["recipeCount"], 3)


if __name__ == "__main__":
    unittest.main()
