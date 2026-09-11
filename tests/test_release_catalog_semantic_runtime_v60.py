from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components/cook4me/release_catalog.py"
spec = importlib.util.spec_from_file_location("cook4me_release_semantic_runtime_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class ReleaseCatalogSemanticRuntimeV60Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "catalog.json"
        self.path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "catalogVersion": "v60-semantic-test",
                    "complete": True,
                    "source": {
                        "sourceCatalogCount": 21,
                        "auditedCatalogCount": 28,
                        "semanticIngredientConcepts": True,
                        "semanticCoverageComplete": False,
                        "sourceLocalIngredientCount": 3,
                        "ingredientIntelligenceComplete": False,
                    },
                    "ingredients": [
                        {
                            "id": "local:de:tomato",
                            "conceptId": "concept:food:tomato",
                            "canonicalName": "Tomato",
                            "translations": {
                                "de": "Tomate",
                                "el": "Ντομάτα",
                                "en": "Tomato",
                            },
                            "aliases": {
                                "de": ["Tomate"],
                                "el": ["Ντομάτα"],
                                "en": ["Tomato"],
                            },
                            "classification": "food",
                            "sourceLocalIdentity": True,
                            "providerIdentityAssigned": False,
                            "nutritionEligible": True,
                            "dietEligible": True,
                            "allergenEligible": True,
                        },
                        {
                            "id": "local:de:paper",
                            "canonicalName": "Baking paper",
                            "translations": {"de": "Backpapier"},
                            "classification": "equipment",
                            "sourceLocalIdentity": True,
                            "providerIdentityAssigned": False,
                        },
                        {
                            "id": "local:de:fragment",
                            "canonicalName": "Peeled and sliced",
                            "translations": {"de": "geschält und geschnitten"},
                            "classification": "ambiguous",
                            "sourceLocalIdentity": True,
                            "providerIdentityAssigned": False,
                        },
                    ],
                    "recipes": [
                        {
                            "groupingFunctionalId": "GROUP_DE",
                            "canonicalName": "Tomato risotto",
                            "variants": [
                                {
                                    "variantId": "VAR_DE",
                                    "recipeFunctionalId": "REC_DE",
                                    "groupingFunctionalId": "GROUP_DE",
                                    "title": "Tomatenrisotto",
                                    "originalTitle": "Tomatenrisotto",
                                    "language": "de",
                                    "originalLanguage": "de",
                                    "market": "GS_DE",
                                    "ingredients": [
                                        {
                                            "ingredientId": "local:de:tomato",
                                            "originalName": "Tomate",
                                            "originalLanguage": "de",
                                            "quantity": 200,
                                            "unit": "g",
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        mod._CATALOG_PATH = self.path
        mod.load_release_catalog.cache_clear()

    def tearDown(self):
        mod.load_release_catalog.cache_clear()
        self.tmp.cleanup()

    def test_cross_language_search_returns_semantic_identity_on_display_ingredient(self):
        result = mod.search_release_recipes(
            "Ντομάτα",
            language="el",
            configured_language="de",
            country="DE",
            size=10,
        )
        self.assertEqual(result["page"]["totalElements"], 1)
        ingredient = result["items"][0]["ingredients"][0]
        self.assertEqual(ingredient["ingredientId"], "local:de:tomato")
        self.assertEqual(ingredient["conceptId"], "concept:food:tomato")
        self.assertEqual(ingredient["classification"], "food")
        self.assertEqual(ingredient["name"], "Ντομάτα")
        self.assertTrue(ingredient["sourceLocalIdentity"])
        self.assertFalse(ingredient["providerIdentityAssigned"])
        self.assertNotIn("nutrition", ingredient)

    def test_food_picker_exposes_concept_and_hides_non_food_by_default(self):
        rows = mod.ingredient_rows("de")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Tomate")
        self.assertEqual(rows[0]["conceptId"], "concept:food:tomato")
        self.assertEqual(rows[0]["ingredientId"], "local:de:tomato")

    def test_non_food_rows_remain_queryable_when_explicitly_requested(self):
        rows = mod.ingredient_rows("de", food_only=False)
        self.assertEqual(
            {row["classification"] for row in rows},
            {"food", "equipment", "ambiguous"},
        )
        equipment = mod.ingredient_rows("de", "Backpapier", food_only=False)
        self.assertEqual(len(equipment), 1)
        self.assertEqual(equipment[0]["classification"], "equipment")

    def test_summary_exposes_intelligence_readiness_separately(self):
        summary = mod.release_catalog_summary()
        self.assertTrue(summary["semanticIngredientConcepts"])
        self.assertFalse(summary["semanticCoverageComplete"])
        self.assertFalse(summary["ingredientIntelligenceComplete"])
        self.assertEqual(summary["sourceLocalIngredientCount"], 3)

    def test_concept_lookup_is_built_once_at_catalog_warmup(self):
        payload = mod.load_release_catalog()
        self.assertIn("concept:food:tomato", payload["_runtimeIngredientsByConcept"])
        rows = payload["_runtimeIngredientsByConcept"]["concept:food:tomato"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "local:de:tomato")


if __name__ == "__main__":
    unittest.main()
