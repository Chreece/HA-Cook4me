from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components/cook4me/release_catalog.py"
spec = importlib.util.spec_from_file_location("cook4me_release_catalog_v60_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class ReleaseCatalogCompiledSearchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "catalog.json"
        self.path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "catalogVersion": "v60-test",
                    "complete": True,
                    "ingredients": [
                        {
                            "id": "concept:food:tomato",
                            "canonicalName": "Tomato",
                            "aliases": {
                                "en": ["Tomato"],
                                "de": ["Tomate"],
                                "el": ["Ντομάτα"],
                            },
                        }
                    ],
                    "recipes": [
                        {
                            "groupingFunctionalId": "GROUP_PL",
                            "canonicalName": "Tomato risotto",
                            "variants": [
                                {
                                    "variantId": "VAR_PL",
                                    "recipeFunctionalId": "REC_PL",
                                    "groupingFunctionalId": "GROUP_PL",
                                    "title": "Risotto pomidorowe",
                                    "language": "pl",
                                    "market": "GS_PL",
                                    "ingredients": [
                                        {"ingredientId": "concept:food:tomato"}
                                    ],
                                }
                            ],
                        },
                        {
                            "groupingFunctionalId": "GROUP_FR",
                            "canonicalName": "Tomato soup",
                            "variants": [
                                {
                                    "variantId": "VAR_FR",
                                    "recipeFunctionalId": "REC_FR",
                                    "groupingFunctionalId": "GROUP_FR",
                                    "title": "Soupe de tomates",
                                    "language": "fr",
                                    "market": "GS_FR",
                                    "ingredients": [
                                        {"ingredientId": "concept:food:tomato"}
                                    ],
                                }
                            ],
                        },
                    ],
                    "source": {
                        "auditedCatalogCount": 28,
                        "sourceCatalogCount": 21,
                    },
                }
            ),
            encoding="utf-8",
        )
        mod._CATALOG_PATH = self.path
        mod.load_release_catalog.cache_clear()

    def tearDown(self):
        mod.load_release_catalog.cache_clear()
        self.tmp.cleanup()

    def test_runtime_search_uses_compiled_postings_not_legacy_recipe_scan(self):
        def fail_if_called(_recipe):
            raise AssertionError("legacy per-recipe search text scan was used")

        mod._legacy._recipe_search_text = fail_if_called
        result = mod.search_release_recipes(
            "Tomate",
            language="de",
            configured_language="de",
            country="DE",
            size=10,
        )
        self.assertEqual(result["page"]["totalElements"], 2)
        self.assertEqual(
            result["searchContract"],
            "repo-release-compiled-multilingual-index-v2",
        )

    def test_foreign_recipe_is_found_from_user_language_ingredient_alias(self):
        result = mod.search_release_recipes(
            "Ντομάτα",
            language="el",
            configured_language="de",
            country="DE",
            size=10,
        )
        self.assertEqual(
            {row["groupingFunctionalId"] for row in result["items"]},
            {"GROUP_PL", "GROUP_FR"},
        )

    def test_variant_lookup_is_direct_indexed(self):
        row = mod.recipe_by_variant(
            "VAR_FR",
            language="fr",
            configured_language="de",
            country="DE",
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["groupingFunctionalId"], "GROUP_FR")

    def test_summary_reports_runtime_fallback_as_not_prebuilt(self):
        summary = mod.release_catalog_summary()
        self.assertTrue(summary["compiledSearchReady"])
        self.assertFalse(summary["compiledSearchPrebuilt"])


if __name__ == "__main__":
    unittest.main()
