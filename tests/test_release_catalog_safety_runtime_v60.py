from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, COMPONENT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


search_module = _load("cook4me_search_build_safety_runtime_test", "catalog_search_index.py")
safety_module = _load("cook4me_safety_build_runtime_test", "recipe_safety_index_v60.py")
release = _load("cook4me_release_catalog_safety_runtime_test", "release_catalog.py")


class ReleaseCatalogSafetyRuntimeV60Tests(unittest.TestCase):
    def _payload(self):
        ingredients = [
            {
                "id": "concept:food:tomato",
                "conceptId": "concept:food:tomato",
                "canonicalName": "Tomato",
                "translations": {"en": "Tomato", "de": "Tomate", "el": "Ντομάτα"},
                "aliases": {"en": ["Tomato"], "de": ["Tomate"], "el": ["Ντομάτα"]},
                "classification": "food",
                "intelligence": {
                    "diets": {"vegetarian": True, "vegan": True},
                    "allergens": {"peanut": "absent", "milk": "absent"},
                },
            },
            {
                "id": "concept:food:rice",
                "conceptId": "concept:food:rice",
                "canonicalName": "Rice",
                "translations": {"en": "Rice", "de": "Reis", "el": "Ρύζι"},
                "classification": "food",
                "intelligence": {
                    "diets": {"vegetarian": True, "vegan": True},
                    "allergens": {"peanut": "absent", "milk": "absent"},
                },
            },
            {
                "id": "concept:food:cream",
                "conceptId": "concept:food:cream",
                "canonicalName": "Cream",
                "translations": {"en": "Cream", "de": "Sahne"},
                "classification": "food",
                "intelligence": {
                    "diets": {"vegetarian": True, "vegan": False},
                    "allergens": {"peanut": "absent", "milk": "present"},
                },
            },
            {
                "id": "concept:food:mystery",
                "conceptId": "concept:food:mystery",
                "canonicalName": "Mystery sauce",
                "translations": {"en": "Mystery sauce"},
                "classification": "ambiguous",
            },
        ]
        recipes = [
            {
                "groupingFunctionalId": "GROUP_SAFE",
                "canonicalName": "Tomato rice",
                "variants": [
                    {
                        "variantId": "VAR_SAFE",
                        "recipeFunctionalId": "REC_SAFE",
                        "groupingFunctionalId": "GROUP_SAFE",
                        "title": "Tomatenreis",
                        "language": "de",
                        "market": "GS_DE",
                        "ingredients": [
                            {"conceptId": "concept:food:tomato", "name": "Tomate"},
                            {"conceptId": "concept:food:rice", "name": "Reis"},
                        ],
                    }
                ],
            },
            {
                "groupingFunctionalId": "GROUP_CREAM",
                "canonicalName": "Cream rice",
                "variants": [
                    {
                        "variantId": "VAR_CREAM",
                        "recipeFunctionalId": "REC_CREAM",
                        "groupingFunctionalId": "GROUP_CREAM",
                        "title": "Riz à la crème",
                        "language": "fr",
                        "market": "GS_FR",
                        "ingredients": [
                            {"conceptId": "concept:food:rice", "name": "Riz"},
                            {"conceptId": "concept:food:cream", "name": "Crème"},
                        ],
                    }
                ],
            },
            {
                "groupingFunctionalId": "GROUP_UNKNOWN",
                "canonicalName": "Mystery rice",
                "variants": [
                    {
                        "variantId": "VAR_UNKNOWN",
                        "recipeFunctionalId": "REC_UNKNOWN",
                        "groupingFunctionalId": "GROUP_UNKNOWN",
                        "title": "Mystery rice",
                        "language": "en",
                        "market": "GS_GB",
                        "ingredients": [
                            {"conceptId": "concept:food:rice", "name": "Rice"},
                            {"conceptId": "concept:food:mystery", "name": "Mystery sauce"},
                        ],
                    }
                ],
            },
        ]
        payload = {
            "schemaVersion": 1,
            "catalogVersion": "v60-safety-runtime-test",
            "complete": True,
            "source": {
                "sourceCatalogCount": 21,
                "auditedCatalogCount": 28,
                "compiledRecipeSafetyIndex": True,
                "dietAllergyIntelligenceComplete": False,
            },
            "ingredients": ingredients,
            "recipes": recipes,
        }
        payload["searchIndex"] = search_module.compile_search_index(payload)
        payload["recipeSafetyIndex"] = safety_module.compile_recipe_safety_index(payload)
        return payload

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "catalog.json"
        self.path.write_text(json.dumps(self._payload()), encoding="utf-8")
        release._CATALOG_PATH = self.path
        release.load_release_catalog.cache_clear()

    def tearDown(self):
        release.load_release_catalog.cache_clear()
        self.tmp.cleanup()

    def test_no_filter_keeps_all_matching_recipes_and_old_search_contract(self):
        result = release.search_release_recipes(
            "rice",
            language="en",
            configured_language="de",
            country="DE",
            size=10,
        )
        self.assertEqual(result["page"]["totalElements"], 3)
        self.assertFalse(result["safetyFiltered"])
        self.assertEqual(
            result["searchContract"],
            "repo-release-compiled-multilingual-index-v2",
        )
        self.assertTrue(result["safetyIndexPrebuilt"])
        self.assertTrue(all("safety" not in row for row in result["items"]))

    def test_vegan_and_peanut_filter_returns_only_explicitly_safe_recipe(self):
        result = release.search_release_recipes(
            "rice",
            language="en",
            configured_language="de",
            country="DE",
            diet="vegan",
            allergies=["peanut"],
            size=10,
        )
        self.assertEqual(result["page"]["totalElements"], 1)
        self.assertEqual(result["page"]["totalPages"], 1)
        self.assertEqual(result["items"][0]["groupingFunctionalId"], "GROUP_SAFE")
        self.assertTrue(result["items"][0]["safety"]["strictlyAllowed"])
        self.assertTrue(result["safetyFiltered"])

    def test_known_allergen_presence_is_excluded(self):
        result = release.search_release_recipes(
            "rice",
            language="en",
            configured_language="de",
            country="DE",
            allergies=["milk"],
            size=10,
        )
        self.assertEqual(result["page"]["totalElements"], 1)
        self.assertEqual(result["items"][0]["groupingFunctionalId"], "GROUP_SAFE")

    def test_unknown_allergen_evidence_is_excluded_not_treated_as_safe(self):
        result = release.search_release_recipes(
            "rice",
            language="en",
            configured_language="de",
            country="DE",
            allergies=["peanut"],
            size=10,
        )
        groups = {row["groupingFunctionalId"] for row in result["items"]}
        self.assertEqual(groups, {"GROUP_SAFE", "GROUP_CREAM"})
        self.assertNotIn("GROUP_UNKNOWN", groups)

    def test_multilingual_query_and_safety_filter_are_intersected(self):
        result = release.search_release_recipes(
            "Ντομάτα",
            language="el",
            configured_language="de",
            country="DE",
            diet="vegan",
            allergies=["milk"],
            size=10,
        )
        self.assertEqual(result["page"]["totalElements"], 1)
        self.assertEqual(result["items"][0]["groupingFunctionalId"], "GROUP_SAFE")

    def test_summary_reports_prebuilt_safety_readiness_separately_from_data_completion(self):
        summary = release.release_catalog_summary()
        self.assertTrue(summary["compiledSafetyReady"])
        self.assertTrue(summary["compiledSafetyPrebuilt"])
        self.assertEqual(summary["compiledSafetyRecipeCount"], 3)
        self.assertFalse(summary["strictDietAllergyUnknownIsSafe"])
        self.assertFalse(summary["dietAllergyIntelligenceComplete"])

    def test_strict_language_and_safety_filter_intersect_before_pagination(self):
        result = release.search_release_recipes(
            "rice",
            language="fr",
            configured_language="de",
            country="DE",
            strict_language=True,
            allergies=["milk"],
            size=10,
        )
        # The only French recipe contains milk; it must be removed before totals.
        self.assertEqual(result["page"]["totalElements"], 0)
        self.assertEqual(result["items"], [])


if __name__ == "__main__":
    unittest.main()
