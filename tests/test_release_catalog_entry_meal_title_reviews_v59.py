from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/apply_release_catalog_reviews_v2.py"
spec = importlib.util.spec_from_file_location("apply_release_catalog_reviews_entry_title_test", SCRIPT)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def base_prep(groups):
    return {
        "kind": "cook4me-release-assembly-prep",
        "summary": {},
        "providerFoods": [],
        "unkeyedIngredients": [],
        "recipeGroups": groups,
    }


def base_queue(task_id):
    return {
        "kind": "cook4me-local-translation-queue",
        "tasks": [
            {
                "taskId": task_id,
                "type": "recipe_title_english",
                "sourceLanguage": "fr",
                "sourceText": "Titre partagé",
            }
        ],
    }


class EntryMealTitleReviewTests(unittest.TestCase):
    def test_exact_reviewed_group_reuses_reviewed_english_title(self):
        task_id = "recipe_title_english:taxonomy-gap"
        prep = base_prep(
            [
                {
                    "groupingFunctionalId": "2774772",
                    "language": "fr",
                    "title": "Titre fournisseur",
                    "variantIds": ["VAR_1"],
                    "translationTaskId": task_id,
                }
            ]
        )
        result, queue = mod.apply_reviews(prep, base_queue(task_id))
        group = result["recipeGroups"][0]
        self.assertEqual("Beef skewers with teriyaki sauce", group["canonicalEnglishTitle"])
        self.assertEqual("reviewed:entry-meal-v1", group["canonicalEnglishSource"])
        self.assertEqual("2774772", group["groupingFunctionalId"])
        self.assertEqual(["VAR_1"], group["variantIds"])
        self.assertNotIn("translationTaskId", group)
        self.assertEqual([], queue["tasks"])
        self.assertEqual(1, result["summary"]["reviewedEntryMealEnglishApplied"])

    def test_shared_task_is_not_removed_while_another_group_still_needs_it(self):
        task_id = "recipe_title_english:shared"
        prep = base_prep(
            [
                {
                    "groupingFunctionalId": "2774772",
                    "language": "fr",
                    "title": "Titre partagé",
                    "variantIds": ["VAR_REVIEWED"],
                    "translationTaskId": task_id,
                },
                {
                    "groupingFunctionalId": "UNREVIEWED_GROUP",
                    "language": "fr",
                    "title": "Titre partagé",
                    "variantIds": ["VAR_PENDING"],
                    "translationTaskId": task_id,
                },
            ]
        )
        result, queue = mod.apply_reviews(prep, base_queue(task_id))
        reviewed, pending = result["recipeGroups"]
        self.assertNotIn("translationTaskId", reviewed)
        self.assertEqual(task_id, pending["translationTaskId"])
        self.assertEqual([task_id], [row["taskId"] for row in queue["tasks"]])


if __name__ == "__main__":
    unittest.main()
