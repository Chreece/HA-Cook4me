from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "refine_release_catalog_classification_v3.py"
spec = importlib.util.spec_from_file_location("refine_release_catalog_classification_v3", SCRIPT)
assert spec and spec.loader
refine = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = refine
spec.loader.exec_module(refine)


def classification(rows):
    return {
        "schemaVersion": 1,
        "kind": "cook4me-release-recipe-classification-v2",
        "summary": {"dietResolved": len(rows), "dietReviewRequired": 0},
        "recipes": rows,
    }


def provider(details):
    return {
        "kind": "cook4me-provider-capture",
        "source": {"taxonomyAugmented": True},
        "details": details,
    }


class ReleaseCatalogClassificationV3Tests(unittest.TestCase):
    def test_provider_course_is_primary_and_brunch_is_secondary(self):
        c = classification([
            {
                "groupingFunctionalId": "g1",
                "language": "en",
                "title": "Eggs",
                "primaryDiet": "vegetarian",
                "dietTags": ["vegetarian", "pescatarian"],
                "dietClassification": {"status": "resolved"},
            }
        ])
        p = provider([
            {
                "groupingFunctionalId": "g1",
                "courses": [{"key": "STARTER"}],
                "occasions": [{"key": "BRUNCH"}, {"key": "OCCASION_STARTER"}],
                "classifications": [],
            }
        ])
        result, review = refine.refine(c, p)
        row = result["recipes"][0]
        self.assertEqual("recipe", row["entryType"])
        self.assertEqual("starter", row["primaryMealType"])
        self.assertEqual({"starter", "breakfast"}, set(row["mealTypes"]))
        self.assertEqual("resolved", row["mealTypeClassification"]["status"])
        self.assertEqual(0, review["summary"]["mealItems"])

    def test_food_cooking_is_not_forced_into_a_meal_type(self):
        c = classification([
            {
                "groupingFunctionalId": "g2",
                "language": "en",
                "title": "Artichoke",
                "primaryDiet": "vegan",
                "dietTags": ["vegan", "vegetarian", "pescatarian"],
                "dietClassification": {"status": "resolved"},
            }
        ])
        p = provider([
            {
                "groupingFunctionalId": "g2",
                "courses": [],
                "occasions": [],
                "classifications": [{"key": "IS_FOOD_COOKING"}],
            }
        ])
        result, _review = refine.refine(c, p)
        row = result["recipes"][0]
        self.assertEqual("ingredient_preparation", row["entryType"])
        self.assertEqual([], row["mealTypes"])
        self.assertIsNone(row["primaryMealType"])
        self.assertEqual("not_applicable", row["mealTypeClassification"]["status"])

    def test_provider_vegetarian_hint_cannot_override_omnivore(self):
        c = classification([
            {
                "groupingFunctionalId": "g3",
                "language": "en",
                "title": "Veggie burger",
                "primaryDiet": "omnivore",
                "dietTags": ["omnivore"],
                "dietClassification": {"status": "resolved"},
            }
        ])
        p = provider([
            {
                "groupingFunctionalId": "g3",
                "courses": [{"key": "MAIN_COURSE"}],
                "occasions": [{"key": "VEGETARIAN"}],
                "classifications": [],
            }
        ])
        result, _review = refine.refine(c, p)
        row = result["recipes"][0]
        self.assertEqual("omnivore", row["primaryDiet"])
        self.assertTrue(row["dietClassification"]["providerDietHintConflict"])

    def test_reviewed_non_food_override_makes_diet_not_applicable(self):
        grouping = "1081008"
        c = classification([
            {
                "groupingFunctionalId": grouping,
                "language": "de",
                "title": "Selbstgemachtes Efeu-Spülmittel",
                "primaryDiet": None,
                "dietTags": [],
                "dietClassification": {"status": "review_required"},
            }
        ])
        p = provider([
            {
                "groupingFunctionalId": grouping,
                "courses": [],
                "occasions": [],
                "classifications": [],
            }
        ])
        result, review = refine.refine(c, p)
        row = result["recipes"][0]
        self.assertEqual("non_food", row["entryType"])
        self.assertEqual("not_applicable", row["dietClassification"]["status"])
        self.assertEqual(0, review["summary"]["dietItems"])


if __name__ == "__main__":
    unittest.main()
