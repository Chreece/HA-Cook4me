from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "validate_release_catalog_v3.py"
spec = importlib.util.spec_from_file_location("validate_release_catalog_v3", SCRIPT)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def catalog():
    catalogs = [
        {
            "language": "de",
            "country": "DE",
            "market": "GS_DE",
            "state": "POPULATED",
            "searchRows": 1,
            "hydratedVariants": 1,
            "staleSearchOnlyVariants": 0,
            "unresolvedVariants": 0,
        }
    ] + [
        {
            "language": f"x{i}",
            "country": "ZZ",
            "market": "GS_ZZ",
            "state": "EMPTY",
            "searchRows": 0,
            "hydratedVariants": 0,
            "staleSearchOnlyVariants": 0,
            "unresolvedVariants": 0,
        }
        for i in range(27)
    ]
    nutrition = {
        "basis": "per100g",
        "values": {"energyKcal": 10.0},
        "source": "test",
    }
    return {
        "schemaVersion": 1,
        "catalogVersion": "test-v3",
        "complete": True,
        "source": {
            "auditedCatalogCount": 28,
            "catalogs": catalogs,
            "providerIngredientIdentityAuthoritative": True,
            "keylessFoodIdentityLocalOnly": True,
            "translationNeverMergesRecipeGroups": True,
            "secretsPersisted": False,
            "unresolvedProviderFoods": 0,
            "unresolvedKeylessSemantics": 0,
            "unresolvedRecipeGroups": 0,
            "providerTranslationConflicts": 0,
            "ingredientMappingFailures": 0,
            "missingGroupReviews": 0,
            "unresolvedProviderVariants": 0,
            "nutritionRequiredForComplete": True,
            "nutritionRequiredCount": 2,
            "nutritionResolvedCount": 2,
            "nutritionMissingCount": 0,
        },
        "ingredients": [
            {
                "id": "M_FOOD_TOMATO",
                "key": "M_FOOD_TOMATO",
                "canonicalName": "Tomato",
                "identityKind": "provider",
                "translations": {"de": "Tomate", "en": "Tomato"},
                "nutrition": deepcopy(nutrition),
            },
            {
                "id": "local:de:salt",
                "canonicalName": "Sea salt",
                "identityKind": "local-keyless",
                "classification": "food",
                "translations": {"de": "Meersalz", "en": "Sea salt"},
                "nutrition": deepcopy(nutrition),
            },
        ],
        "recipes": [
            {
                "groupingFunctionalId": "GROUP_1",
                "canonicalName": "Tomato soup",
                "variants": [
                    {
                        "variantId": "VAR_DE",
                        "groupingFunctionalId": "GROUP_1",
                        "originalTitle": "Tomatensuppe",
                        "originalLanguage": "de",
                        "ingredients": [
                            {"ingredientId": "M_FOOD_TOMATO", "key": "M_FOOD_TOMATO", "originalName": "Tomate"},
                            {"ingredientId": "local:de:salt", "originalName": "Meersalz"},
                            {"classification": "equipment", "originalName": "Alufolie"},
                        ],
                    }
                ],
            }
        ],
    }


class ValidateReleaseCatalogV3Tests(unittest.TestCase):
    def test_valid_complete_catalog_passes(self):
        result = validator.validate(catalog())
        self.assertTrue(result["valid"])
        self.assertEqual([], result["errors"])
        self.assertEqual(2, result["stats"]["ingredientCount"])
        self.assertEqual(1, result["stats"]["variantCount"])

    def test_local_keyless_identity_must_never_carry_provider_key(self):
        payload = catalog()
        payload["ingredients"][1]["key"] = "M_FOOD_SALT"
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("must not have provider key" in error for error in result["errors"]))

    def test_dangling_food_reference_fails(self):
        payload = catalog()
        payload["recipes"][0]["variants"][0]["ingredients"][1]["ingredientId"] = "local:de:missing"
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("dangling ingredient references" in error for error in result["errors"]))

    def test_equipment_must_not_reference_global_ingredient(self):
        payload = catalog()
        payload["recipes"][0]["variants"][0]["ingredients"][2]["ingredientId"] = "local:de:salt"
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("equipment/other lines reference" in error for error in result["errors"]))

    def test_duplicate_variant_identity_fails(self):
        payload = catalog()
        payload["recipes"].append(
            {
                "groupingFunctionalId": "GROUP_2",
                "canonicalName": "Other",
                "variants": [
                    {
                        "variantId": "VAR_DE",
                        "groupingFunctionalId": "GROUP_2",
                        "originalTitle": "Other",
                        "originalLanguage": "en",
                        "ingredients": [{"ingredientId": "M_FOOD_TOMATO", "key": "M_FOOD_TOMATO"}],
                    }
                ],
            }
        )
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("duplicate variantIds" in error for error in result["errors"]))

    def test_unresolved_source_counter_blocks_complete_catalog(self):
        payload = catalog()
        payload["source"]["unresolvedKeylessSemantics"] = 1
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertIn("source.unresolvedKeylessSemantics must be zero", result["errors"])

    def test_missing_required_nutrition_fails(self):
        payload = catalog()
        payload["ingredients"][1].pop("nutrition")
        payload["source"]["nutritionResolvedCount"] = 1
        payload["source"]["nutritionMissingCount"] = 1
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("required nutrition is incomplete" in error for error in result["errors"]))
        self.assertTrue(any("local:de:salt has no required per100g nutrition" in error for error in result["errors"]))

    def test_explicit_maintenance_nutrition_escape_hatch_is_visible_warning(self):
        payload = catalog()
        payload["source"]["nutritionRequiredForComplete"] = False
        payload["source"]["nutritionResolvedCount"] = 1
        payload["source"]["nutritionMissingCount"] = 1
        payload["ingredients"][1].pop("nutrition")
        result = validator.validate(payload)
        self.assertTrue(result["valid"])
        self.assertTrue(any("escape hatch" in warning for warning in result["warnings"]))

    def test_secret_like_keys_fail(self):
        payload = catalog()
        payload["source"]["api_key"] = "should-never-be-here"
        result = validator.validate(payload)
        self.assertFalse(result["valid"])
        self.assertTrue(any("secret-like keys present" in error for error in result["errors"]))

    def test_incomplete_catalog_can_be_structurally_checked_when_explicitly_allowed(self):
        payload = catalog()
        payload["complete"] = False
        self.assertFalse(validator.validate(payload)["valid"])
        self.assertTrue(validator.validate(payload, require_complete=False)["valid"])


if __name__ == "__main__":
    unittest.main()
