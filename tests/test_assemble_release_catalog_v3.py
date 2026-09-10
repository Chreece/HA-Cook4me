from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

ASSEMBLER_PATH = TOOLS / "assemble_release_catalog_v3.py"
spec = importlib.util.spec_from_file_location("assemble_release_catalog_v3", ASSEMBLER_PATH)
assert spec and spec.loader
assembler = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = assembler
spec.loader.exec_module(assembler)

RELEASE_PATH = ROOT / "custom_components" / "cook4me" / "release_catalog.py"
release_spec = importlib.util.spec_from_file_location("cook4me_release_catalog_v3_test", RELEASE_PATH)
assert release_spec and release_spec.loader
release = importlib.util.module_from_spec(release_spec)
release_spec.loader.exec_module(release)


def identity_policy() -> dict:
    return {
        "recipeProviderIdentityAuthoritative": True,
        "translationNeverMergesRecipeGroups": True,
        "providerNativeTitlesPreserved": True,
        "unkeyedCrossLanguageMergeFromTranslation": False,
        "exactProviderFoodNameMatchesRemainCandidates": True,
    }


def prep() -> dict:
    return {
        "schemaVersion": 2,
        "kind": "cook4me-release-assembly-prep",
        "generatedAt": "2026-09-10T00:00:00+00:00",
        "identityPolicy": identity_policy(),
        "providerFoods": [
            {
                "key": "M_FOOD_TOMATO",
                "canonicalEnglishName": "Tomato",
                "translations": [
                    {"language": "de", "market": "GS_DE", "name": "Tomate"},
                    {"language": "en", "market": "GS_GB", "name": "Tomato"},
                ],
                "usedByRecipe": True,
            }
        ],
        "unkeyedIngredients": [
            {
                "sourceLanguage": "de",
                "sourceName": "Meersalz",
                "canonicalEnglishName": "Sea salt",
                "classification": "food",
                "localSyntheticIngredientId": "local:de:sea-salt",
            },
            {
                "sourceLanguage": "de",
                "sourceName": "Alufolie",
                "canonicalEnglishName": "Aluminum foil",
                "classification": "equipment",
                "localSyntheticIngredientId": "local:de:foil",
            },
        ],
        "recipeGroups": [
            {
                "groupingFunctionalId": "GROUP_1",
                "canonicalEnglishTitle": "Tomato soup",
                "canonicalEnglishSource": "seb:en-sibling",
            }
        ],
    }


def provider() -> dict:
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
    ]
    for index in range(27):
        catalogs.append(
            {
                "language": f"x{index:02d}",
                "country": "ZZ",
                "market": "GS_ZZ",
                "state": "EMPTY",
                "searchRows": 0,
                "hydratedVariants": 0,
                "staleSearchOnlyVariants": 0,
                "unresolvedVariants": 0,
            }
        )
    return {
        "schemaVersion": 2,
        "kind": "cook4me-provider-capture",
        "generatedAt": "2026-09-10T00:00:00+00:00",
        "source": {
            "contract": "standalone-proven-cookeo-brand-v5",
            "applianceGroup": "APPLIANCE_GROUP_15",
            "recipeType": "BRAND",
            "auditedCatalogCount": 28,
            "catalogs": catalogs,
        },
        "details": [
            {
                "variantId": "VAR_DE",
                "recipeFunctionalId": "REC_DE",
                "groupingFunctionalId": "GROUP_1",
                "title": "Tomatensuppe",
                "language": "de",
                "market": "GS_DE",
                "servings": 2,
                "ingredients": [
                    {
                        "lineFunctionalId": "LINE_TOMATO_DE",
                        "foodKey": "M_FOOD_TOMATO",
                        "foodName": "Tomate",
                        "quantity": 100,
                        "unit": {"key": "M_UNIT_GRAM", "abbreviation": "g", "name": "Gramm"},
                    },
                    {
                        "lineFunctionalId": "LINE_SALT_DE",
                        "applicationDescription": "Meersalz",
                        "quantity": 5,
                        "unit": {"key": "M_UNIT_GRAM", "abbreviation": "g", "name": "Gramm"},
                    },
                    {
                        "lineFunctionalId": "LINE_FOIL_DE",
                        "applianceDescription": "Alufolie",
                    },
                ],
            },
            {
                "variantId": "VAR_EN",
                "recipeFunctionalId": "REC_EN",
                "groupingFunctionalId": "GROUP_1",
                "title": "Tomato soup",
                "language": "en",
                "market": "GS_GB",
                "servings": 2,
                "ingredients": [
                    {
                        "lineFunctionalId": "LINE_TOMATO_EN",
                        "foodKey": "M_FOOD_TOMATO",
                        "foodName": "Tomato",
                        "quantity": 100,
                        "unit": {"key": "M_UNIT_GRAM", "abbreviation": "g", "name": "gram"},
                    }
                ],
            },
        ],
        "staleSearchOnly": [],
    }


def nutrition() -> dict:
    return {
        "M_FOOD_TOMATO": {
            "basis": "per100g",
            "values": {"energyKcal": 18.0, "protein": 0.9},
            "source": "test",
        },
        "local:de:sea-salt": {
            "basis": "per100g",
            "values": {"energyKcal": 0.0, "salt": 100.0},
            "source": "test",
        },
    }


class AssembleReleaseCatalogV3Tests(unittest.TestCase):
    def test_complete_reviewed_catalog_preserves_provider_and_local_identity(self):
        payload = assembler.assemble(
            prep(), provider(), catalog_version="test-v3", nutrition=nutrition()
        )
        self.assertTrue(payload["complete"])
        self.assertEqual(28, payload["source"]["auditedCatalogCount"])
        self.assertEqual(0, payload["source"]["unresolvedProviderVariants"])
        self.assertEqual(0, payload["source"]["unresolvedKeylessSemantics"])
        ingredients = {row["id"]: row for row in payload["ingredients"]}
        self.assertIn("M_FOOD_TOMATO", ingredients)
        self.assertIn("local:de:sea-salt", ingredients)
        self.assertNotIn("local:de:foil", ingredients)
        self.assertEqual("Tomate", ingredients["M_FOOD_TOMATO"]["translations"]["de"])
        self.assertNotIn("key", ingredients["local:de:sea-salt"])

        group = payload["recipes"][0]
        self.assertEqual("Tomato soup", group["canonicalName"])
        variants = {row["language"]: row for row in group["variants"]}
        self.assertEqual("Tomatensuppe", variants["de"]["originalTitle"])
        de_lines = variants["de"]["ingredients"]
        self.assertEqual("M_FOOD_TOMATO", de_lines[0]["ingredientId"])
        self.assertEqual("M_FOOD_TOMATO", de_lines[0]["key"])
        self.assertEqual("local:de:sea-salt", de_lines[1]["ingredientId"])
        self.assertNotIn("key", de_lines[1])
        self.assertEqual("equipment", de_lines[2]["classification"])
        self.assertNotIn("ingredientId", de_lines[2])

    def test_generated_payload_is_usable_by_offline_runtime(self):
        payload = assembler.assemble(
            prep(), provider(), catalog_version="test-v3", nutrition=nutrition()
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "merged.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            old = release._CATALOG_PATH
            release._CATALOG_PATH = path
            release.load_release_catalog.cache_clear()
            try:
                self.assertTrue(release.release_catalog_ready())
                rows = release.ingredient_rows("de")
                names = {row["name"] for row in rows}
                self.assertIn("Tomate", names)
                self.assertIn("Meersalz", names)
                self.assertNotIn("Alufolie", names)
                result = release.search_release_recipes(
                    "tomate",
                    language="de",
                    configured_language="de",
                    country="DE",
                    strict_language=True,
                )
                self.assertEqual(1, len(result["items"]))
                item = result["items"][0]
                self.assertEqual("Tomatensuppe", item["title"])
                self.assertEqual("VAR_DE", item["sendVariantId"])
                self.assertTrue(item["sendable"])
                salt = next(row for row in item["ingredients"] if row.get("ingredientId") == "local:de:sea-salt")
                self.assertEqual("Meersalz", salt["name"])
            finally:
                release._CATALOG_PATH = old
                release.load_release_catalog.cache_clear()

    def test_unresolved_keyless_semantics_block_activation(self):
        reviewed = prep()
        reviewed["unkeyedIngredients"][0]["classification"] = "food_candidate"
        reviewed["unkeyedIngredients"][0]["translationTaskId"] = "pending"
        payload = assembler.assemble(
            reviewed, provider(), catalog_version="test-v3", nutrition=nutrition()
        )
        self.assertFalse(payload["complete"])
        self.assertEqual(1, payload["source"]["unresolvedKeylessSemantics"])

    def test_missing_nutrition_blocks_normal_activation_but_escape_hatch_is_explicit(self):
        profiles = nutrition()
        profiles.pop("local:de:sea-salt")
        payload = assembler.assemble(
            prep(), provider(), catalog_version="test-v3", nutrition=profiles
        )
        self.assertFalse(payload["complete"])
        self.assertEqual(1, payload["source"]["nutritionMissingCount"])
        maintenance = assembler.assemble(
            prep(),
            provider(),
            catalog_version="test-v3",
            nutrition=profiles,
            allow_missing_nutrition=True,
        )
        self.assertTrue(maintenance["complete"])
        self.assertFalse(maintenance["source"]["nutritionRequiredForComplete"])

    def test_unresolved_provider_variant_blocks_activation(self):
        captured = provider()
        captured["source"]["catalogs"][0]["unresolvedVariants"] = 1
        payload = assembler.assemble(
            prep(), captured, catalog_version="test-v3", nutrition=nutrition()
        )
        self.assertFalse(payload["complete"])
        self.assertEqual(1, payload["source"]["unresolvedProviderVariants"])

    def test_provider_translation_conflict_blocks_activation(self):
        reviewed = prep()
        reviewed["providerFoods"][0]["translations"].append(
            {"language": "de", "market": "GS_AT", "name": "Paradeiser"}
        )
        payload = assembler.assemble(
            reviewed, provider(), catalog_version="test-v3", nutrition=nutrition()
        )
        self.assertFalse(payload["complete"])
        self.assertEqual(1, payload["source"]["providerTranslationConflicts"])

    def test_identity_policy_is_mandatory(self):
        reviewed = prep()
        reviewed["identityPolicy"]["translationNeverMergesRecipeGroups"] = False
        with self.assertRaisesRegex(RuntimeError, "identity policy"):
            assembler.assemble(
                reviewed, provider(), catalog_version="test-v3", nutrition=nutrition()
            )


if __name__ == "__main__":
    unittest.main()
