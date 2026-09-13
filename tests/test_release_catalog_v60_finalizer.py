from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

spec = importlib.util.spec_from_file_location(
    "cook4me_release_catalog_v60_finalizer_test",
    TOOLS / "build_release_catalog_v60.py",
)
assert spec is not None and spec.loader is not None
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def legacy_profile(kcal: float) -> dict:
    return {
        "basis": "per100g",
        "values": {"energyKcal": kcal, "protein": 1.0},
        "source": "usda_fdc",
        "sourceId": 123,
    }


def reviewed_profile(ingredient_id: str, canonical: str, kcal: float, fdc_id: int) -> dict:
    return {
        "basis": "per100g",
        "values": {"energyKcal": kcal, "protein": 1.0},
        "source": "usda_fdc",
        "sourceId": fdc_id,
        "sourceDescription": canonical,
        "ingredientId": ingredient_id,
        "reviewedCanonicalEnglishName": canonical,
        "reviewConfidence": "high",
        "reviewFile": "release_catalog_reviewed_nutrition_sources_001.v1.json",
    }


def payload() -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "v60-finalizer-test",
        "complete": True,
        "source": {
            "semanticCoverageComplete": True,
            "ingredientIntelligenceComplete": False,
            "providerIngredientIdentityPreserved": True,
            "providerIngredientIdentityInferred": False,
            "keylessSourceLocalIdentity": True,
            "semanticConceptProviderIdentity": False,
            "secretsPersisted": False,
        },
        "ingredients": [
            {
                "id": "M_FOOD_RICE",
                "key": "M_FOOD_RICE",
                "canonicalName": "Rice",
                "translations": {"en": "Rice"},
                "nutrition": legacy_profile(360.0),
            },
            {
                "id": "local:de:tomato",
                "conceptId": "concept:food:tomato",
                "canonicalName": "Tomato",
                "translations": {"de": "Tomate", "en": "Tomato"},
                "aliases": {"de": ["Tomate"], "en": ["Tomato"]},
                "classification": "food",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
                "nutritionEligible": True,
                "dietEligible": True,
                "allergenEligible": True,
                "needsSemanticConfirmation": False,
                "nutrition": legacy_profile(18.0),
            },
            {
                "id": "local:pt:palitos",
                "conceptId": "concept:ambiguous:palitos",
                "canonicalName": "Sticks / toothpicks",
                "translations": {"pt": "Palitos"},
                "classification": "ambiguous",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
                "nutritionEligible": False,
                "dietEligible": False,
                "allergenEligible": False,
                "needsSemanticConfirmation": True,
                "nutrition": legacy_profile(99.0),
            },
        ],
        "recipes": [
            {
                "groupingFunctionalId": "GROUP_1",
                "canonicalName": "Tomato rice",
                "variants": [
                    {
                        "variantId": "VAR_1",
                        "recipeFunctionalId": "REC_1",
                        "groupingFunctionalId": "GROUP_1",
                        "title": "Tomatenreis",
                        "originalTitle": "Tomatenreis",
                        "language": "de",
                        "originalLanguage": "de",
                        "servings": 2,
                        "nutrition": {"legacy": True},
                        "ingredients": [
                            {
                                "ingredientId": "M_FOOD_RICE",
                                "key": "M_FOOD_RICE",
                                "foodKey": "M_FOOD_RICE",
                                "originalName": "Reis",
                                "quantity": 200,
                                "unit": "g",
                            },
                            {
                                "ingredientId": "local:de:tomato",
                                "conceptId": "concept:food:tomato",
                                "classification": "food",
                                "sourceLocalIdentity": True,
                                "providerIdentityAssigned": False,
                                "originalName": "Tomate",
                                "quantity": 100,
                                "unit": "g",
                            },
                        ],
                    }
                ],
            }
        ],
    }


class ReleaseCatalogV60FinalizerTests(unittest.TestCase):
    def test_finalizer_strips_legacy_nutrition_and_keeps_capture_complete(self):
        result = builder.apply_reviewed_nutrition(payload(), {})
        self.assertTrue(result["complete"])
        self.assertFalse(result["source"]["reviewedNutritionComplete"])
        self.assertEqual(result["source"]["reviewedNutritionRequiredCount"], 2)
        self.assertEqual(result["source"]["reviewedNutritionResolvedCount"], 0)
        self.assertEqual(result["source"]["reviewedNutritionRejectedEmbeddedCount"], 2)
        self.assertFalse(result["source"]["legacyFuzzyNutritionAccepted"])
        self.assertTrue(result["source"]["reviewedNutritionIdentityOnly"])
        for row in result["ingredients"]:
            self.assertNotIn("nutrition", row)
        variant = result["recipes"][0]["variants"][0]
        self.assertNotIn("nutrition", variant)
        self.assertFalse(variant["calculatedNutritionV60"]["fullyCovered"])

    def test_finalizer_attaches_only_reviewed_profiles_and_rebuilds_indexes(self):
        cache = {
            "M_FOOD_RICE": reviewed_profile("M_FOOD_RICE", "Rice", 360.0, 1001),
            "local:de:tomato": reviewed_profile(
                "local:de:tomato", "Tomato", 18.0, 1002
            ),
            # Even reviewed-looking nutrition for an ambiguous concept is ignored.
            "local:pt:palitos": reviewed_profile(
                "local:pt:palitos", "Sticks / toothpicks", 99.0, 1003
            ),
        }
        result = builder.apply_reviewed_nutrition(payload(), cache)
        source = result["source"]
        self.assertTrue(source["reviewedNutritionComplete"])
        self.assertEqual(source["reviewedNutritionRequiredCount"], 2)
        self.assertEqual(source["reviewedNutritionResolvedCount"], 2)
        self.assertTrue(source["foodIntelligenceNutritionComplete"])
        self.assertTrue(source["compiledRecipeDependencyIndex"])
        self.assertTrue(source["compiledMultilingualSearchIndex"])
        self.assertTrue(source["compiledRecipeSafetyIndex"])

        ingredients = {row["id"]: row for row in result["ingredients"]}
        self.assertEqual(
            ingredients["M_FOOD_RICE"]["nutrition"]["reviewFile"],
            "release_catalog_reviewed_nutrition_sources_001.v1.json",
        )
        self.assertIn("nutrition", ingredients["local:de:tomato"])
        self.assertNotIn("nutrition", ingredients["local:pt:palitos"])

        variant = result["recipes"][0]["variants"][0]
        self.assertTrue(variant["calculatedNutritionV60"]["fullyCovered"])
        self.assertGreater(variant["calculatedNutritionV60"]["totals"]["energyKcal"], 0)
        self.assertIn("k:M_FOOD_RICE", result["recipeDependencyIndex"])
        self.assertIn("c:concept:food:tomato", result["recipeDependencyIndex"])
        self.assertEqual(result["searchIndex"]["recipeCount"], 1)
        self.assertEqual(result["recipeSafetyIndex"]["recipeCount"], 1)

    def test_finalizer_rejects_review_profile_with_wrong_canonical_name(self):
        cache = {
            "M_FOOD_RICE": reviewed_profile(
                "M_FOOD_RICE", "Completely different food", 360.0, 1001
            )
        }
        result = builder.apply_reviewed_nutrition(payload(), cache)
        rice = next(row for row in result["ingredients"] if row["id"] == "M_FOOD_RICE")
        self.assertNotIn("nutrition", rice)
        self.assertEqual(result["source"]["reviewedNutritionResolvedCount"], 0)
        self.assertEqual(result["source"]["reviewedNutritionRejectedLegacyCacheCount"], 1)


if __name__ == "__main__":
    unittest.main()
