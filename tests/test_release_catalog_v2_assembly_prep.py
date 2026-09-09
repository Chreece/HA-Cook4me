from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "prepare_release_catalog_v2_assembly.py"
spec = importlib.util.spec_from_file_location("prepare_release_catalog_v2_assembly", SCRIPT)
assert spec and spec.loader
prep = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prep
spec.loader.exec_module(prep)


LANGUAGES = [
    ("ar", "AE"), ("bg", "BG"), ("cs", "CZ"), ("da", "DK"),
    ("de", "DE"), ("el", "GR"), ("en", "GB"), ("es", "ES"),
    ("fa", "AE"), ("fi", "FI"), ("fr", "FR"), ("hr", "HR"),
    ("hu", "HU"), ("it", "IT"), ("ja", "JP"), ("ko", "KR"),
    ("nl", "NL"), ("no", "NO"), ("pl", "PL"), ("pt", "PT"),
    ("ro", "RO"), ("ru", "RU"), ("sk", "SK"), ("sl", "SI"),
    ("sv", "SE"), ("tr", "TR"), ("uk", "UA"), ("zh", "TW"),
]


def marketing_capture():
    catalogs = []
    for language, country in LANGUAGES:
        items = [{"key": "M_FOOD_1", "name": "Water" if language == "en" else "Wasser" if language == "de" else f"Water-{language}"}]
        if language == "de":
            items.append({"key": "M_FOOD_2", "name": "Kartoffel"})
        catalogs.append(
            {
                "language": language,
                "country": country,
                "market": f"GS_{country}",
                "state": "POPULATED",
                "candidateRows": len(items),
                "reportedTotalElements": len(items),
                "truncated": False,
                "unparsedRows": 0,
                "missingNameRows": 0,
                "missingKeyRows": 0,
                "items": items,
            }
        )
    return {
        "schemaVersion": 3,
        "kind": "cook4me-marketing-food-capture-v3",
        "requestContract": "apk-th0.d-unfiltered",
        "requestSize": 100000,
        "isMixMainFilter": False,
        "errors": [],
        "catalogs": catalogs,
    }


def provider_capture():
    catalogs = []
    for index, (language, country) in enumerate(LANGUAGES):
        catalogs.append(
            {
                "language": language,
                "country": country,
                "market": f"GS_{country}",
                "state": "POPULATED" if index == 0 else "EMPTY",
                "searchRows": 3 if index == 0 else 0,
                "hydratedVariants": 3 if index == 0 else 0,
                "staleSearchOnlyVariants": 0,
                "unresolvedVariants": 0,
            }
        )
    return {
        "schemaVersion": 2,
        "kind": "cook4me-provider-capture",
        "source": {"catalogs": catalogs},
        "details": [
            {
                "variantId": "v1",
                "groupingFunctionalId": "g1",
                "language": "de",
                "market": "GS_DE",
                "title": "Kartoffelsuppe",
                "ingredients": [{"foodKey": "M_FOOD_2", "cleanName": "Kartoffel"}],
            },
            {
                "variantId": "v2",
                "groupingFunctionalId": "g2",
                "language": "de",
                "market": "GS_DE",
                "title": "Kartoffelsuppe",
                "ingredients": [
                    {
                        "applicationDescription": "250 Milliliter Wasser",
                        "cleanName": "250 Milliliter Wasser",
                        "quantity": 250.0,
                        "unit": {"name": "Milliliter", "abbreviation": "ml"},
                    }
                ],
            },
            {
                "variantId": "v3",
                "groupingFunctionalId": "g3",
                "language": "en",
                "market": "GS_GB",
                "title": "Test soup",
                "ingredients": [{"cleanName": "baking mold"}],
            },
        ],
        "staleSearchOnly": [],
    }


class ReleaseAssemblyPrepTests(unittest.TestCase):
    def test_structured_quantity_and_unit_are_removed_without_guessing(self):
        name, changed = prep.semantic_ingredient_name(
            {
                "applicationDescription": "250 Milliliter Wasser",
                "quantity": 250.0,
                "unit": {"name": "Milliliter", "abbreviation": "ml"},
            }
        )
        self.assertTrue(changed)
        self.assertEqual("Wasser", name)

    def test_prepare_keeps_provider_identity_and_translation_separate(self):
        result, queue = prep.prepare(provider_capture(), marketing_capture())
        summary = result["summary"]
        self.assertEqual(3, summary["providerDetails"])
        self.assertEqual(3, summary["providerRecipeGroups"])
        self.assertEqual(2, summary["providerFoodCatalogKeys"])
        self.assertEqual(2, summary["recipeUsedProviderFoodKeys"])
        self.assertEqual(1, summary["providerFoodsMissingSebEnglish"])
        self.assertEqual(1, summary["usedProviderFoodsMissingSebEnglish"])

        groups = {row["groupingFunctionalId"]: row for row in result["recipeGroups"]}
        self.assertEqual({"g1", "g2", "g3"}, set(groups))
        self.assertEqual(groups["g1"]["translationTaskId"], groups["g2"]["translationTaskId"])
        self.assertEqual("Test soup", groups["g3"]["canonicalEnglishTitle"])
        self.assertTrue(result["identityPolicy"]["translationNeverMergesRecipeGroups"])

        food2 = next(row for row in result["providerFoods"] if row["key"] == "M_FOOD_2")
        self.assertIn("translationTaskId", food2)
        self.assertNotIn("canonicalEnglishName", food2)

        water = next(row for row in result["unkeyedIngredients"] if row["sourceName"] == "Wasser")
        self.assertEqual("M_FOOD_1", water["exactProviderFoodKeyCandidate"])
        self.assertEqual("Water", water["canonicalEnglishName"])
        self.assertTrue(water["localSyntheticIngredientId"].startswith("local:de:"))
        self.assertNotEqual("M_FOOD_1", water["localSyntheticIngredientId"])

        mold = next(row for row in result["unkeyedIngredients"] if row["sourceName"] == "baking mold")
        task = next(row for row in queue["tasks"] if row["taskId"] == mold["translationTaskId"])
        self.assertFalse(task["needsTranslation"])
        self.assertEqual("unkeyed_ingredient", task["type"])

    def test_wrong_marketing_food_contract_is_rejected(self):
        marketing = marketing_capture()
        marketing["requestSize"] = 5000
        with self.assertRaisesRegex(RuntimeError, "proven APK"):
            prep.prepare(provider_capture(), marketing)


if __name__ == "__main__":
    unittest.main()
