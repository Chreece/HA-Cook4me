from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "apply_release_catalog_reviews_v2.py"
spec = importlib.util.spec_from_file_location("apply_release_catalog_reviews_v2", SCRIPT)
assert spec and spec.loader
overlay = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = overlay
spec.loader.exec_module(overlay)


class ReleaseCatalogReviewOverlayTests(unittest.TestCase):
    def test_reviewed_provider_food_and_keyless_tasks_are_removed(self):
        prep = {
            "schemaVersion": 2,
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {
                    "key": "M_FOOD_589",
                    "usedByRecipe": True,
                    "translationTaskId": "food-task",
                }
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "ar",
                    "sourceName": "المياه",
                    "translationTaskId": "keyless-task",
                    "localSyntheticIngredientId": "local:ar:water",
                }
            ],
        }
        queue = {
            "schemaVersion": 2,
            "kind": "cook4me-local-translation-queue",
            "tasks": [
                {"taskId": "food-task", "type": "provider_food_english"},
                {"taskId": "keyless-task", "type": "unkeyed_ingredient"},
                {"taskId": "title-task", "type": "recipe_title_english"},
            ],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        food = reviewed["providerFoods"][0]
        self.assertEqual("Edamame", food["canonicalEnglishName"])
        self.assertNotIn("translationTaskId", food)
        keyless = reviewed["unkeyedIngredients"][0]
        self.assertEqual("Water", keyless["canonicalEnglishName"])
        self.assertEqual("food", keyless["classification"])
        self.assertEqual("local:ar:water", keyless["localSyntheticIngredientId"])
        self.assertNotIn("translationTaskId", keyless)
        self.assertEqual(["title-task"], [row["taskId"] for row in remaining["tasks"]])
        self.assertEqual(0, remaining["summary"]["providerFoodEnglish"])
        self.assertEqual(0, remaining["summary"]["unkeyedIngredient"])
        self.assertEqual(1, remaining["summary"]["recipeTitleEnglish"])

    def test_review_overlay_never_promotes_keyless_candidate_to_provider_identity(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [{"key": "M_FOOD_677", "canonicalEnglishName": "Water", "usedByRecipe": True}],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "de",
                    "sourceName": "Wasser",
                    "exactProviderFoodKeyCandidate": "M_FOOD_677",
                    "localSyntheticIngredientId": "local:de:water",
                }
            ],
        }
        queue = {"kind": "cook4me-local-translation-queue", "tasks": []}
        reviewed, _remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertEqual("local:de:water", row["localSyntheticIngredientId"])
        self.assertEqual("M_FOOD_677", row["exactProviderFoodKeyCandidate"])
        self.assertNotIn("providerFoodKey", row)


if __name__ == "__main__":
    unittest.main()
