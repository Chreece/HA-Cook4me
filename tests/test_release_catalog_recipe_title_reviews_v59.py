from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/apply_release_catalog_reviews_v2.py"
spec = importlib.util.spec_from_file_location("apply_release_catalog_reviews_title_test", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class RecipeTitleReviewOverlayTests(unittest.TestCase):
    def test_reviewed_title_resolves_task_without_changing_provider_identity(self):
        prep = {
            "schemaVersion": 3,
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [],
            "unkeyedIngredients": [],
            "recipeGroups": [
                {
                    "groupingFunctionalId": "GROUP_SI_1",
                    "language": "sl",
                    "market": "GS_SI",
                    "title": "Rižota s kozicami",
                    "variantIds": ["VAR_SI_1"],
                    "originalTitles": [
                        {
                            "variantId": "VAR_SI_1",
                            "language": "sl",
                            "market": "GS_SI",
                            "name": "Rižota s kozicami",
                        }
                    ],
                    "translationTaskId": "recipe_title_english:test-shrimp-risotto",
                }
            ],
        }
        queue = {
            "schemaVersion": 3,
            "kind": "cook4me-local-translation-queue",
            "tasks": [
                {
                    "taskId": "recipe_title_english:test-shrimp-risotto",
                    "type": "recipe_title_english",
                    "sourceLanguage": "sl",
                    "sourceText": "Rižota s kozicami",
                },
                {
                    "taskId": "recipe_title_english:unrelated",
                    "type": "recipe_title_english",
                    "sourceLanguage": "de",
                    "sourceText": "Unrelated title",
                },
            ],
        }

        result, remaining = mod.apply_reviews(prep, queue)
        group = result["recipeGroups"][0]

        self.assertEqual("GROUP_SI_1", group["groupingFunctionalId"])
        self.assertEqual(["VAR_SI_1"], group["variantIds"])
        self.assertEqual("Rižota s kozicami", group["title"])
        self.assertEqual("Rižota s kozicami", group["originalTitles"][0]["name"])
        self.assertEqual("Shrimp risotto", group["canonicalEnglishTitle"])
        self.assertEqual("reviewed:recipe-title-v1", group["canonicalEnglishSource"])
        self.assertEqual("high", group["canonicalEnglishConfidence"])
        self.assertNotIn("translationTaskId", group)
        self.assertEqual(
            ["recipe_title_english:unrelated"],
            [row["taskId"] for row in remaining["tasks"]],
        )
        self.assertEqual(1, result["summary"]["reviewedRecipeTitleEnglishApplied"])
        self.assertEqual(1, result["summary"]["recipeGroupsCanonicalEnglishResolved"])
        self.assertEqual(1, remaining["summary"]["recipeTitleEnglish"])
        self.assertEqual(
            "release_catalog_reviewed_recipe_titles.v1.json",
            remaining["reviewOverlay"]["recipeTitleEnglish"],
        )

    def test_unknown_review_is_left_pending(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [],
            "unkeyedIngredients": [],
            "recipeGroups": [
                {
                    "groupingFunctionalId": "GROUP_UNKNOWN",
                    "language": "de",
                    "title": "Nicht überprüfter Titel",
                    "variantIds": ["VAR_UNKNOWN"],
                    "translationTaskId": "recipe_title_english:unknown",
                }
            ],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [
                {
                    "taskId": "recipe_title_english:unknown",
                    "type": "recipe_title_english",
                    "sourceLanguage": "de",
                    "sourceText": "Nicht überprüfter Titel",
                }
            ],
        }
        result, remaining = mod.apply_reviews(prep, queue)
        group = result["recipeGroups"][0]
        self.assertNotIn("canonicalEnglishTitle", group)
        self.assertEqual("recipe_title_english:unknown", group["translationTaskId"])
        self.assertEqual(1, len(remaining["tasks"]))


if __name__ == "__main__":
    unittest.main()
