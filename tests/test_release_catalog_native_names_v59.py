from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


release = load_module(
    "cook4me_release_catalog_native_test",
    ROOT / "custom_components/cook4me/release_catalog.py",
)
prep = load_module(
    "prepare_release_catalog_native_test",
    ROOT / "tools/prepare_release_catalog_v2_assembly.py",
)

LANGUAGES = [
    ("ar", "AE"), ("bg", "BG"), ("cs", "CZ"), ("da", "DK"),
    ("de", "DE"), ("el", "GR"), ("en", "GB"), ("es", "ES"),
    ("fa", "AE"), ("fi", "FI"), ("fr", "FR"), ("hr", "HR"),
    ("hu", "HU"), ("it", "IT"), ("ja", "JP"), ("ko", "KR"),
    ("nl", "NL"), ("no", "NO"), ("pl", "PL"), ("pt", "PT"),
    ("ro", "RO"), ("ru", "RU"), ("sk", "SK"), ("sl", "SI"),
    ("sv", "SE"), ("tr", "TR"), ("uk", "UA"), ("zh", "TW"),
]


class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "merged.json"
        release._CATALOG_PATH = self.path
        release.load_release_catalog.cache_clear()
        self.path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "catalogVersion": "native-test",
                    "complete": True,
                    "ingredients": [
                        {
                            "id": "M_FOOD_TOMATO",
                            "key": "M_FOOD_TOMATO",
                            "canonicalName": "Tomato",
                            "translations": {"en": "Tomato", "de": "Tomate"},
                        }
                    ],
                    "recipes": [
                        {
                            "groupingFunctionalId": "GROUP_1",
                            "canonicalName": "Tomato soup",
                            "variants": [
                                {
                                    "variantId": "VAR_EN",
                                    "recipeFunctionalId": "REC_EN",
                                    "groupingFunctionalId": "GROUP_1",
                                    "title": "Tomato soup",
                                    "originalTitle": "Tomato soup",
                                    "language": "en",
                                    "originalLanguage": "en",
                                    "market": "GS_GB",
                                    "ingredients": [
                                        {
                                            "ingredientId": "M_FOOD_TOMATO",
                                            "key": "M_FOOD_TOMATO",
                                            "originalName": "Tomato",
                                            "originalLanguage": "en",
                                            "quantity": 400,
                                            "unit": "g",
                                        }
                                    ],
                                },
                                {
                                    "variantId": "VAR_DE",
                                    "recipeFunctionalId": "REC_DE",
                                    "groupingFunctionalId": "GROUP_1",
                                    "title": "Tomatensuppe",
                                    "originalTitle": "Tomatensuppe",
                                    "language": "de",
                                    "originalLanguage": "de",
                                    "market": "GS_DE",
                                    "ingredients": [
                                        {
                                            "ingredientId": "M_FOOD_TOMATO",
                                            "key": "M_FOOD_TOMATO",
                                            "originalName": "Frische Tomate",
                                            "originalLanguage": "de",
                                            "quantity": 400,
                                            "unit": "g",
                                        }
                                    ],
                                },
                            ],
                        }
                    ],
                    "source": {"auditedCatalogCount": 28, "sourceCatalogCount": 2},
                }
            ),
            encoding="utf-8",
        )
        release.load_release_catalog.cache_clear()

    def tearDown(self):
        release.load_release_catalog.cache_clear()
        self.tmp.cleanup()

    def test_native_variant_uses_exact_provider_recipe_and_ingredient_names(self):
        result = release.search_release_recipes(
            "frische tomate",
            language="de",
            configured_language="de",
            country="DE",
            strict_language=True,
        )
        self.assertEqual(1, len(result["items"]))
        item = result["items"][0]
        self.assertEqual("Tomatensuppe", item["title"])
        self.assertEqual("Tomatensuppe", item["originalTitle"])
        self.assertEqual("de", item["originalLanguage"])
        ingredient = item["ingredients"][0]
        self.assertEqual("Frische Tomate", ingredient["name"])
        self.assertEqual("Frische Tomate", ingredient["originalName"])
        self.assertEqual("de", ingredient["originalLanguage"])
        self.assertEqual("Tomato", ingredient["canonicalName"])

    def test_english_variant_keeps_same_identity_with_english_original(self):
        result = release.search_release_recipes(
            "tomato",
            language="en",
            configured_language="de",
            country="DE",
            strict_language=True,
        )
        item = result["items"][0]
        self.assertEqual("Tomato soup", item["originalTitle"])
        self.assertEqual("en", item["originalLanguage"])
        self.assertEqual("Tomato", item["ingredients"][0]["originalName"])
        self.assertEqual("M_FOOD_TOMATO", item["ingredients"][0]["ingredientId"])


class NativePrepTests(unittest.TestCase):
    @staticmethod
    def marketing_capture():
        catalogs = []
        for language, country in LANGUAGES:
            name = (
                "Potato" if language == "en"
                else "Kartoffel" if language == "de"
                else f"Potato-{language}"
            )
            catalogs.append(
                {
                    "language": language,
                    "country": country,
                    "market": f"GS_{country}",
                    "state": "POPULATED",
                    "candidateRows": 1,
                    "reportedTotalElements": 1,
                    "truncated": False,
                    "unparsedRows": 0,
                    "missingNameRows": 0,
                    "missingKeyRows": 0,
                    "items": [{"key": "M_FOOD_1", "name": name}],
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

    @staticmethod
    def provider_capture():
        catalogs = []
        for index, (language, country) in enumerate(LANGUAGES):
            catalogs.append(
                {
                    "language": language,
                    "country": country,
                    "market": f"GS_{country}",
                    "state": "POPULATED" if index == 0 else "EMPTY",
                    "searchRows": 2 if index == 0 else 0,
                    "hydratedVariants": 2 if index == 0 else 0,
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
                    "variantId": "VAR_DE",
                    "groupingFunctionalId": "GROUP_1",
                    "language": "de",
                    "market": "GS_DE",
                    "title": "Kartoffelsuppe",
                    "ingredients": [
                        {"foodKey": "M_FOOD_1", "cleanName": "Kartoffel"}
                    ],
                },
                {
                    "variantId": "VAR_EN",
                    "groupingFunctionalId": "GROUP_1",
                    "language": "en",
                    "market": "GS_GB",
                    "title": "Potato soup",
                    "ingredients": [
                        {"foodKey": "M_FOOD_1", "cleanName": "Potato"}
                    ],
                },
            ],
            "staleSearchOnly": [],
        }

    def test_later_english_sibling_is_canonical_and_all_originals_survive(self):
        result, queue = prep.prepare(self.provider_capture(), self.marketing_capture())
        group = result["recipeGroups"][0]
        self.assertEqual("Potato soup", group["canonicalEnglishTitle"])
        self.assertEqual("seb:en-sibling", group["canonicalEnglishSource"])
        self.assertEqual(
            {("de", "Kartoffelsuppe"), ("en", "Potato soup")},
            {(row["language"], row["name"]) for row in group["originalTitles"]},
        )
        self.assertTrue(result["identityPolicy"]["providerNativeTitlesPreserved"])
        self.assertFalse(
            any(task.get("type") == "recipe_title_english" for task in queue["tasks"])
        )


if __name__ == "__main__":
    unittest.main()
