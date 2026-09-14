from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60 as builder  # noqa: E402


def reviewed_profile(ingredient_id: str, name: str, source_id: int) -> dict:
    return {
        "basis": "per100g",
        "values": {"energyKcal": 100.0, "protein": 2.0},
        "source": "usda_fdc",
        "sourceId": source_id,
        "ingredientId": ingredient_id,
        "reviewedCanonicalEnglishName": name,
        "reviewFile": "review.json",
        "nutritionReviewTargetId": ingredient_id,
        "nutritionReviewTargetKind": "provider-identity",
    }


def payload() -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "accounting-test",
        "complete": True,
        "source": {"semanticCoverageComplete": True},
        "ingredients": [
            {
                "id": "M_FOOD_1",
                "key": "M_FOOD_1",
                "canonicalName": "Rice",
            },
            {
                "id": "local:el:tomato",
                "conceptId": "concept:food:tomato",
                "canonicalName": "Tomato",
                "classification": "food",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
                "nutritionEligible": True,
                "needsSemanticConfirmation": False,
            },
            {
                "id": "local:el:context-food",
                "conceptId": "concept:food:context",
                "canonicalName": "Context food",
                "classification": "food",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
                "nutritionEligible": False,
                "needsSemanticConfirmation": False,
            },
            {
                "id": "local:el:equipment",
                "conceptId": "concept:equipment:test",
                "canonicalName": "Equipment",
                "classification": "equipment",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
                "nutritionEligible": False,
                "needsSemanticConfirmation": False,
            },
        ],
        "recipes": [],
    }


class ReviewedNutritionFoodAccountingTests(unittest.TestCase):
    def test_progressive_review_completeness_does_not_shrink_food_denominator(self):
        cache = {
            "M_FOOD_1": reviewed_profile("M_FOOD_1", "Rice", 1),
            "local:el:tomato": reviewed_profile(
                "local:el:tomato", "Tomato", 2
            ),
        }
        result = builder.apply_reviewed_nutrition(payload(), cache)
        source = result["source"]

        # All nutrition-eligible identities in this fixture are resolved.
        self.assertEqual(source["reviewedNutritionRequiredCount"], 2)
        self.assertEqual(source["reviewedNutritionResolvedCount"], 2)
        self.assertTrue(source["reviewedNutritionComplete"])

        # Food intelligence must still count the reviewed food identity that is
        # deliberately nutrition-ineligible, so progressive coverage stays honest.
        self.assertEqual(source["foodIntelligenceIngredientCount"], 3)
        self.assertEqual(source["foodIntelligenceNutritionResolvedCount"], 2)
        self.assertFalse(source["foodIntelligenceNutritionComplete"])
        self.assertFalse(source["ingredientIntelligenceComplete"])

    def test_equipment_is_not_part_of_food_intelligence_denominator(self):
        result = builder.apply_reviewed_nutrition(payload(), {})
        source = result["source"]
        self.assertEqual(source["reviewedNutritionRequiredCount"], 2)
        self.assertEqual(source["reviewedNutritionResolvedCount"], 0)
        self.assertEqual(source["foodIntelligenceIngredientCount"], 3)
        self.assertEqual(source["foodIntelligenceNutritionResolvedCount"], 0)


if __name__ == "__main__":
    unittest.main()
