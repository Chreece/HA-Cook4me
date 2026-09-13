from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/build_release_catalog_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_build_release_catalog_v60_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class ReleaseCatalogV60AssemblyTests(unittest.TestCase):
    def _semantic_payload(self):
        de_source = mod.semantics.source_local_ingredient_id("de", "Tomate")
        el_source = mod.semantics.source_local_ingredient_id("el", "Ντομάτα")
        concept_id = "concept:food:tomato-test"
        return {
            "schemaVersion": 1,
            "kind": "cook4me-semantic-ingredient-concepts",
            "sourceIdentityToConcept": {
                de_source: concept_id,
                el_source: concept_id,
            },
            "concepts": [
                {
                    "conceptId": concept_id,
                    "canonicalEnglish": "Tomato",
                    "classification": "food",
                    "mergePolicy": "reviewed-high-exact-english",
                    "providerIdentityAssigned": False,
                    "nutritionEligible": True,
                    "dietEligible": True,
                    "allergenEligible": True,
                    "needsSemanticConfirmation": False,
                    "aliases": {
                        "en": ["Tomato"],
                        "de": ["Tomate"],
                        "el": ["Ντομάτα"],
                    },
                    "sourceIdentities": [
                        {
                            "ingredientId": de_source,
                            "language": "de",
                            "source": "Tomate",
                            "confidence": "high",
                            "reviewFile": "de-review.json",
                            "providerIdentityAssigned": False,
                        },
                        {
                            "ingredientId": el_source,
                            "language": "el",
                            "source": "Ντομάτα",
                            "confidence": "high",
                            "reviewFile": "el-review.json",
                            "providerIdentityAssigned": False,
                        },
                    ],
                }
            ],
        }

    def _payload(self):
        return {
            "schemaVersion": 1,
            "catalogVersion": "v60-test",
            "complete": True,
            "source": {
                "format": "normalized-ingredient-references-v1",
                "providerIngredientIdentityOnly": True,
            },
            "ingredients": [
                {
                    "id": "M_FOOD_RICE",
                    "key": "M_FOOD_RICE",
                    "canonicalName": "Rice",
                    "translations": {"en": "Rice", "de": "Reis"},
                    "nutrition": {
                        "basis": "per100g",
                        "values": {"energyKcal": 360.0},
                    },
                }
            ],
            "recipes": [
                {
                    "groupingFunctionalId": "GROUP_RISOTTO",
                    "canonicalName": "Tomato risotto",
                    "variants": [
                        {
                            "variantId": "VAR_DE",
                            "recipeFunctionalId": "REC_DE",
                            "groupingFunctionalId": "GROUP_RISOTTO",
                            "title": "Tomatenrisotto",
                            "originalTitle": "Tomatenrisotto",
                            "language": "de",
                            "originalLanguage": "de",
                            "market": "GS_DE",
                            "ingredients": [
                                {
                                    "ingredientId": "M_FOOD_RICE",
                                    "key": "M_FOOD_RICE",
                                    "foodKey": "M_FOOD_RICE",
                                    "originalName": "Reis",
                                    "originalLanguage": "de",
                                    "quantity": 200,
                                    "unit": "g",
                                },
                                {
                                    "originalName": "Tomate",
                                    "originalLanguage": "de",
                                    "quantity": 100,
                                    "unit": "g",
                                },
                            ],
                        }
                    ],
                }
            ],
        }

    def test_keyless_line_gets_source_local_and_semantic_identity_without_provider_key(self):
        result = mod.enrich_payload(self._payload(), self._semantic_payload())
        ingredient = result["recipes"][0]["variants"][0]["ingredients"][1]
        self.assertTrue(ingredient["ingredientId"].startswith("local:de:"))
        self.assertEqual(ingredient["conceptId"], "concept:food:tomato-test")
        self.assertEqual(ingredient["canonicalName"], "Tomato")
        self.assertFalse(ingredient["providerIdentityAssigned"])
        self.assertNotIn("foodKey", ingredient)
        self.assertNotIn("key", ingredient)

    def test_global_source_local_row_keeps_multilingual_aliases_for_one_query(self):
        result = mod.enrich_payload(self._payload(), self._semantic_payload())
        local = next(row for row in result["ingredients"] if row.get("sourceLocalIdentity"))
        self.assertEqual(local["translations"]["de"], "Tomate")
        self.assertEqual(local["translations"]["el"], "Ντομάτα")
        self.assertEqual(local["classification"], "food")
        index = mod.search_index.prepare_search_index(result["searchIndex"])
        greek = mod.search_index.search_index(index, "Ντομάτα", size=10)
        self.assertEqual(greek["indices"], [0])

    def test_provider_identity_is_left_unchanged(self):
        result = mod.enrich_payload(self._payload(), self._semantic_payload())
        provider = next(row for row in result["ingredients"] if row.get("key") == "M_FOOD_RICE")
        self.assertEqual(provider["id"], "M_FOOD_RICE")
        rice = result["recipes"][0]["variants"][0]["ingredients"][0]
        self.assertEqual(rice["ingredientId"], "M_FOOD_RICE")
        self.assertEqual(rice["foodKey"], "M_FOOD_RICE")

    def test_unknown_keyless_label_stays_local_and_marks_semantic_gap(self):
        payload = self._payload()
        payload["recipes"][0]["variants"][0]["ingredients"][1]["originalName"] = "Unknown garnish fragment"
        result = mod.enrich_payload(payload, self._semantic_payload())
        ingredient = result["recipes"][0]["variants"][0]["ingredients"][1]
        self.assertTrue(ingredient["ingredientId"].startswith("local:de:"))
        self.assertEqual(ingredient["classification"], "ambiguous")
        self.assertEqual(ingredient["semanticIdentityState"], "unreviewed-source-local")
        self.assertFalse(result["source"]["semanticCoverageComplete"])
        local = next(
            row for row in result["ingredients"]
            if row.get("id") == ingredient["ingredientId"]
        )
        self.assertTrue(local["canonicalEnglishNeedsReview"])
        self.assertFalse(local["providerIdentityAssigned"])

    def test_capture_completeness_is_separate_from_food_intelligence_completeness(self):
        result = mod.enrich_payload(self._payload(), self._semantic_payload())
        self.assertTrue(result["complete"])
        self.assertTrue(result["source"]["semanticCoverageComplete"])
        self.assertFalse(result["source"]["foodIntelligenceNutritionComplete"])
        self.assertFalse(result["source"]["ingredientIntelligenceComplete"])
        self.assertTrue(result["source"]["compiledMultilingualSearchIndex"])


if __name__ == "__main__":
    unittest.main()
