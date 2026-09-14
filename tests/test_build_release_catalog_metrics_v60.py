from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/build_release_catalog_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_build_release_metrics_v60_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class ReleaseCatalogMetricAssemblyV60Tests(unittest.TestCase):
    def _semantics(self):
        source_id = mod.semantics.source_local_ingredient_id("de", "Tomate")
        concept_id = "concept:food:tomato-test"
        return {
            "sourceIdentityToConcept": {source_id: concept_id},
            "concepts": [
                {
                    "conceptId": concept_id,
                    "canonicalEnglish": "Tomato",
                    "classification": "food",
                    "mergePolicy": "reviewed-high-exact-english",
                    "nutritionEligible": True,
                    "dietEligible": True,
                    "allergenEligible": True,
                    "needsSemanticConfirmation": False,
                    "aliases": {"en": ["Tomato"], "de": ["Tomate"]},
                    "sourceIdentities": [
                        {
                            "ingredientId": source_id,
                            "language": "de",
                            "source": "Tomate",
                            "confidence": "high",
                            "reviewFile": "test-review.json",
                        }
                    ],
                }
            ],
        }

    def _payload(self):
        return {
            "schemaVersion": 1,
            "complete": True,
            "catalogVersion": "v60-metric-test",
            "source": {},
            "ingredients": [
                {
                    "id": "M_FOOD_RICE",
                    "key": "M_FOOD_RICE",
                    "canonicalName": "Rice",
                    "translations": {"en": "Rice", "de": "Reis"},
                    "nutrition": {
                        "basis": "per100g",
                        "values": {"energyKcal": 360, "protein": 7},
                    },
                }
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
                            "language": "de",
                            "market": "GS_DE",
                            "servings": 2,
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

    def test_release_build_precomputes_nutrition_vector_without_guessing_missing_food(self):
        result = mod.enrich_payload(self._payload(), self._semantics())
        vector = result["recipes"][0]["variants"][0]["calculatedNutritionV60"]
        self.assertEqual(vector["totals"]["energyKcal"], 720)
        self.assertEqual(vector["perServing"]["energyKcal"], 360)
        self.assertEqual(vector["coverage"], 0.5)
        self.assertFalse(vector["fullyCovered"])
        self.assertEqual(vector["calculation"], "identity-indexed-vector-sum-v1")

    def test_release_build_ships_reverse_dependency_index_for_targeted_invalidation(self):
        result = mod.enrich_payload(self._payload(), self._semantics())
        dependencies = result["recipeDependencyIndex"]
        self.assertEqual(dependencies["k:M_FOOD_RICE"], [0])
        self.assertEqual(dependencies["c:concept:food:tomato-test"], [0])
        self.assertEqual(dependencies["l:" + mod.semantics.source_local_ingredient_id("de", "Tomate")], [0])

    def test_release_source_contract_reports_vector_and_dependency_readiness(self):
        result = mod.enrich_payload(self._payload(), self._semantics())
        source = result["source"]
        self.assertTrue(source["compiledRecipeDependencyIndex"])
        self.assertTrue(source["precomputedRecipeNutritionVectors"])
        self.assertEqual(source["recipeMetricContract"], "identity-indexed-v60")
        self.assertEqual(source["recipeVariantNutritionVectorCount"], 1)
        self.assertEqual(source["recipeVariantNutritionFullyCoveredCount"], 0)
        self.assertGreater(source["recipeDependencyIdentityCount"], 0)


if __name__ == "__main__":
    unittest.main()
