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
    "cook4me_validate_release_catalog_v60_test",
    TOOLS / "validate_release_catalog_v60.py",
)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def nutrition(kcal: float) -> dict:
    return {
        "basis": "per100g",
        "values": {"energyKcal": kcal, "protein": 1.0},
        "source": "reviewed-test",
    }


def base_catalog() -> dict:
    payload = {
        "schemaVersion": 1,
        "catalogVersion": "v60-validator-test",
        "complete": True,
        "generatedAt": "2026-09-11T00:00:00+00:00",
        "source": {
            "auditedCatalogCount": 28,
            "failedDetailCount": 0,
            "unresolvedCanonicalIngredientNames": 0,
            "unresolvedCanonicalRecipeNames": 0,
            "providerIngredientIdentityPreserved": True,
            "providerIngredientIdentityInferred": False,
            "keylessSourceLocalIdentity": True,
            "semanticConceptProviderIdentity": False,
            "semanticCoverageComplete": True,
            "unresolvedKeylessRecipeLineCount": 0,
            "compiledMultilingualSearchIndex": True,
            "compiledRecipeDependencyIndex": True,
            "compiledRecipeSafetyIndex": True,
            "strictDietAllergyUnknownIsSafe": False,
            "strictAllergyRequiresExplicitAbsence": True,
            "strictDietRequiresExplicitCompatibility": True,
            "foodIntelligenceIngredientCount": 2,
            "foodIntelligenceNutritionResolvedCount": 2,
            "foodIntelligenceNutritionComplete": True,
            "dietAllergyIntelligenceComplete": False,
            "ingredientIntelligenceComplete": False,
            "secretsPersisted": False,
        },
        "ingredients": [
            {
                "id": "M_FOOD_TOMATO",
                "key": "M_FOOD_TOMATO",
                "canonicalName": "Tomato",
                "translations": {"en": "Tomato", "de": "Tomate"},
                "nutrition": nutrition(18.0),
            },
            {
                "id": "local:de:sea-salt",
                "conceptId": "concept:food:sea-salt",
                "canonicalName": "Sea salt",
                "translations": {"en": "Sea salt", "de": "Meersalz"},
                "aliases": {"en": ["Sea salt"], "de": ["Meersalz"]},
                "classification": "food",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
                "nutritionEligible": True,
                "dietEligible": True,
                "allergenEligible": True,
                "needsSemanticConfirmation": False,
                "nutrition": nutrition(0.0),
            },
            {
                "id": "local:pt:palitos",
                "conceptId": "concept:ambiguous:palitos",
                "canonicalName": "Sticks / toothpicks",
                "translations": {"pt": "Palitos", "en": "Sticks / toothpicks"},
                "aliases": {"pt": ["Palitos"], "en": ["Sticks / toothpicks"]},
                "classification": "ambiguous",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
                "nutritionEligible": False,
                "dietEligible": False,
                "allergenEligible": False,
                "needsSemanticConfirmation": True,
            },
        ],
        "recipes": [
            {
                "groupingFunctionalId": "GROUP_1",
                "canonicalName": "Tomato test",
                "variants": [
                    {
                        "variantId": "VAR_DE",
                        "recipeFunctionalId": "REC_DE",
                        "groupingFunctionalId": "GROUP_1",
                        "title": "Tomatentest",
                        "originalTitle": "Tomatentest",
                        "language": "de",
                        "originalLanguage": "de",
                        "market": "GS_DE",
                        "ingredients": [
                            {
                                "ingredientId": "M_FOOD_TOMATO",
                                "key": "M_FOOD_TOMATO",
                                "originalName": "Tomate",
                                "originalLanguage": "de",
                            },
                            {
                                "ingredientId": "local:de:sea-salt",
                                "conceptId": "concept:food:sea-salt",
                                "classification": "food",
                                "sourceLocalIdentity": True,
                                "providerIdentityAssigned": False,
                                "originalName": "Meersalz",
                                "originalLanguage": "de",
                            },
                            {
                                "ingredientId": "local:pt:palitos",
                                "conceptId": "concept:ambiguous:palitos",
                                "classification": "ambiguous",
                                "sourceLocalIdentity": True,
                                "providerIdentityAssigned": False,
                                "originalName": "Palitos",
                                "originalLanguage": "pt",
                            },
                        ],
                    }
                ],
            }
        ],
    }
    dependencies = validator.recipe_metrics_v60.compile_recipe_dependency_index(
        payload["recipes"]
    )
    payload["recipeDependencyIndex"] = {
        ident: list(indices) for ident, indices in dependencies.items()
    }
    payload["source"]["recipeDependencyIdentityCount"] = len(dependencies)
    payload["searchIndex"] = validator.catalog_search_index.compile_search_index(payload)
    payload["recipeSafetyIndex"] = (
        validator.recipe_safety_index_v60.compile_recipe_safety_index(payload)
    )
    return payload


class ValidateReleaseCatalogV60Tests(unittest.TestCase):
    def test_capture_complete_catalog_allows_reviewed_ambiguous_concept_fail_closed(self):
        result = validator.validate(base_catalog())
        self.assertTrue(result["valid"], result["errors"])
        self.assertEqual(result["stats"]["ambiguousReviewedIngredientCount"], 1)
        self.assertTrue(result["stats"]["foodIntelligenceNutritionComplete"])
        self.assertFalse(result["stats"]["dietAllergyIntelligenceComplete"])
        self.assertFalse(result["stats"]["ingredientIntelligenceComplete"])
        self.assertTrue(result["warnings"])

    def test_require_intelligence_is_a_separate_stricter_gate(self):
        result = validator.validate(base_catalog(), require_intelligence=True)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("dietAllergyIntelligenceComplete" in error for error in result["errors"])
        )
        self.assertTrue(
            any("ingredientIntelligenceComplete" in error for error in result["errors"])
        )

    def test_ambiguous_concept_must_never_carry_nutrition(self):
        payload = base_catalog()
        ambiguous = next(
            row for row in payload["ingredients"] if row.get("classification") == "ambiguous"
        )
        ambiguous["nutrition"] = nutrition(20.0)
        payload["searchIndex"] = validator.catalog_search_index.compile_search_index(payload)
        payload["recipeSafetyIndex"] = (
            validator.recipe_safety_index_v60.compile_recipe_safety_index(payload)
        )
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("must not carry nutrition" in error for error in result["errors"]))

    def test_source_local_provider_identity_leak_is_rejected(self):
        payload = base_catalog()
        local = next(row for row in payload["ingredients"] if row["id"] == "local:de:sea-salt")
        local["key"] = "M_FOOD_SALT"
        payload["searchIndex"] = validator.catalog_search_index.compile_search_index(payload)
        payload["recipeSafetyIndex"] = (
            validator.recipe_safety_index_v60.compile_recipe_safety_index(payload)
        )
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("carries provider identity" in error for error in result["errors"]))

    def test_tampered_dependency_index_is_rejected(self):
        payload = base_catalog()
        payload["recipeDependencyIndex"]["k:M_FOOD_TOMATO"] = []
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("dependency index" in error for error in result["errors"]))

    def test_tampered_search_index_is_rejected(self):
        payload = base_catalog()
        payload["searchIndex"]["recipeCount"] = 99
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("search index" in error for error in result["errors"]))

    def test_tampered_safety_index_is_rejected(self):
        payload = base_catalog()
        payload["recipeSafetyIndex"]["policy"]["unknownIsSafe"] = True
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("safety index" in error for error in result["errors"]))

    def test_false_intelligence_claim_is_rejected_even_when_indexes_are_valid(self):
        payload = base_catalog()
        payload["source"]["dietAllergyIntelligenceComplete"] = True
        payload["source"]["ingredientIntelligenceComplete"] = True
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("dietAllergyIntelligenceComplete does not match" in error for error in result["errors"])
        )
        self.assertTrue(
            any("ingredientIntelligenceComplete does not match" in error for error in result["errors"])
        )

    def test_secret_like_key_is_rejected(self):
        payload = base_catalog()
        payload["source"]["access_token"] = "must-never-ship"
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("secret-like keys" in error for error in result["errors"]))

    def test_runtime_only_prepared_keys_must_not_be_persisted(self):
        payload = base_catalog()
        payload["_runtimeSearchIndex"] = {"_prepared": True}
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("runtime-only keys" in error for error in result["errors"]))

    def test_declared_nutrition_counts_must_match_ingredient_evidence(self):
        payload = base_catalog()
        payload["source"]["foodIntelligenceNutritionResolvedCount"] = 1
        payload["source"]["foodIntelligenceNutritionComplete"] = False
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("NutritionResolvedCount" in error for error in result["errors"])
        )
        self.assertTrue(
            any("NutritionComplete" in error for error in result["errors"])
        )


if __name__ == "__main__":
    unittest.main()
