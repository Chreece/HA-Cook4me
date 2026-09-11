from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components/cook4me/ingredient_intelligence.py"
spec = importlib.util.spec_from_file_location("cook4me_ingredient_intelligence_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class IngredientIntelligenceV60Tests(unittest.TestCase):
    def test_unknown_allergy_evidence_is_never_strictly_safe(self):
        profile = {
            "conceptId": "concept:food:test",
            "diets": {"vegetarian": True},
            "allergens": {},
        }
        masks = mod.compile_recipe_masks([profile])
        result = mod.evaluate_recipe_masks(
            masks,
            diet="vegetarian",
            allergies=["milk"],
        )
        self.assertEqual(result["dietState"], mod.COMPATIBLE)
        self.assertEqual(result["allergyState"], mod.UNKNOWN)
        self.assertFalse(result["strictlyAllowed"])

    def test_explicit_allergen_presence_blocks_recipe(self):
        profile = {
            "conceptId": "concept:food:cream",
            "diets": {"vegetarian": True},
            "allergens": {"milk": "present"},
        }
        masks = mod.compile_recipe_masks([profile])
        result = mod.evaluate_recipe_masks(
            masks,
            diet="vegetarian",
            allergies=["milk"],
        )
        self.assertEqual(result["state"], mod.INCOMPATIBLE)
        self.assertGreater(result["allergenPresentConflictMask"], 0)

    def test_all_recipe_ingredients_must_prove_allergen_absence(self):
        safe = {
            "conceptId": "concept:food:rice",
            "allergens": {"peanut": "absent"},
        }
        unknown = {
            "conceptId": "concept:food:sauce",
            "allergens": {},
        }
        masks = mod.compile_recipe_masks([safe, unknown])
        result = mod.evaluate_recipe_masks(masks, allergies=["peanut"])
        self.assertEqual(result["allergyState"], mod.UNKNOWN)
        self.assertFalse(result["strictlyAllowed"])

    def test_explicit_absence_across_all_ingredients_is_safe(self):
        rows = [
            {
                "conceptId": "concept:food:rice",
                "allergens": {"peanut": "absent"},
            },
            {
                "conceptId": "concept:food:tomato",
                "allergens": {"peanut": "absent"},
            },
        ]
        masks = mod.compile_recipe_masks(rows)
        result = mod.evaluate_recipe_masks(masks, allergies=["peanut"])
        self.assertEqual(result["allergyState"], mod.COMPATIBLE)
        self.assertTrue(result["strictlyAllowed"])

    def test_diet_incompatibility_wins_over_other_unknowns(self):
        rows = [
            {
                "conceptId": "concept:food:beef",
                "diets": {"vegan": False},
                "allergens": {},
            }
        ]
        masks = mod.compile_recipe_masks(rows)
        result = mod.evaluate_recipe_masks(masks, diet="vegan")
        self.assertEqual(result["dietState"], mod.INCOMPATIBLE)
        self.assertEqual(result["state"], mod.INCOMPATIBLE)

    def test_masks_are_plain_integers_for_fast_storage_and_filtering(self):
        masks = mod.compile_recipe_masks(
            [
                {
                    "conceptId": "concept:food:tofu",
                    "diets": {"vegan": True, "vegetarian": True},
                    "allergens": {"soy": "present", "milk": "absent"},
                }
            ]
        )
        self.assertTrue(all(isinstance(value, int) for value in masks.values()))
        self.assertGreater(masks["allergenPresentMask"], 0)
        self.assertGreater(masks["dietCompatibleMask"], 0)

    def test_substitution_requires_explicit_edge_and_safe_target(self):
        profiles = {
            "concept:food:milk": {
                "conceptId": "concept:food:milk",
                "diets": {"vegan": False},
                "allergens": {"milk": "present"},
            },
            "concept:food:oat_milk": {
                "conceptId": "concept:food:oat_milk",
                "diets": {"vegan": True},
                "allergens": {"milk": "absent"},
            },
        }
        index = mod.build_substitution_index(
            [
                {
                    "fromConceptId": "concept:food:milk",
                    "toConceptId": "concept:food:oat_milk",
                    "contexts": ["sauce", "general"],
                    "ratio": {"from": 1, "to": 1},
                    "confidence": "high",
                    "evidence": "reviewed substitution test",
                }
            ]
        )
        result = mod.suggest_substitutions(
            "concept:food:milk",
            context="sauce",
            diet="vegan",
            allergies=["milk"],
            ingredient_profiles=profiles,
            substitution_index=index,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["toConceptId"], "concept:food:oat_milk")
        self.assertEqual(result[0]["ratio"], {"from": 1, "to": 1})
        self.assertTrue(result[0]["safety"]["strictlyAllowed"])

    def test_unknown_target_safety_is_not_offered_as_substitution(self):
        profiles = {
            "concept:food:unknown_alt": {
                "conceptId": "concept:food:unknown_alt",
                "diets": {},
                "allergens": {},
            }
        }
        index = mod.build_substitution_index(
            [
                {
                    "fromConceptId": "concept:food:milk",
                    "toConceptId": "concept:food:unknown_alt",
                    "contexts": ["general"],
                    "confidence": "medium",
                    "evidence": "reviewed edge but incomplete safety evidence",
                }
            ]
        )
        result = mod.suggest_substitutions(
            "concept:food:milk",
            diet="vegan",
            allergies=["milk"],
            ingredient_profiles=profiles,
            substitution_index=index,
        )
        self.assertEqual(result, [])

    def test_invalid_or_unevidenced_substitution_edges_are_ignored(self):
        index = mod.build_substitution_index(
            [
                {
                    "fromConceptId": "a",
                    "toConceptId": "b",
                    "evidence": "",
                },
                {
                    "fromConceptId": "a",
                    "toConceptId": "a",
                    "evidence": "bad self edge",
                },
            ]
        )
        self.assertEqual(index, {})


if __name__ == "__main__":
    unittest.main()
