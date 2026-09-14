from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_semantics_v60_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class SemanticIngredientCompilerTests(unittest.TestCase):
    def _payload(self, items):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-reviewed-keyless-ingredient-semantics",
            "items": items,
        }

    def test_high_confidence_food_labels_share_semantic_concept_not_provider_key(self):
        payload = self._payload(
            [
                {
                    "language": "de",
                    "source": "Tomate",
                    "english": "Tomato",
                    "classification": "food",
                    "confidence": "high",
                },
                {
                    "language": "el",
                    "source": "Ντομάτα",
                    "english": "Tomato",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        result = mod.compile_semantic_concepts([("batch.json", payload)])
        self.assertEqual(result["summary"]["reviewedSourceLabels"], 2)
        self.assertEqual(result["summary"]["semanticConcepts"], 1)
        concept = result["concepts"][0]
        self.assertEqual(concept["canonicalEnglish"], "Tomato")
        self.assertEqual(concept["classification"], "food")
        self.assertEqual(concept["aliases"]["de"], ["Tomate"])
        self.assertEqual(concept["aliases"]["el"], ["Ντομάτα"])
        self.assertFalse(concept["providerIdentityAssigned"])
        self.assertTrue(concept["nutritionEligible"])
        self.assertTrue(
            all(
                row["ingredientId"].startswith("local:")
                for row in concept["sourceIdentities"]
            )
        )
        self.assertNotIn("providerKey", concept)

    def test_medium_confidence_semantics_stay_source_local(self):
        payload = self._payload(
            [
                {
                    "language": "tr",
                    "source": "Kabak",
                    "english": "Zucchini",
                    "classification": "food",
                    "confidence": "medium",
                },
                {
                    "language": "de",
                    "source": "Zucchini",
                    "english": "Zucchini",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        result = mod.compile_semantic_concepts([("batch.json", payload)])
        self.assertEqual(result["summary"]["semanticConcepts"], 2)
        medium = next(
            row
            for row in result["concepts"]
            if row["sourceIdentities"][0]["language"] == "tr"
        )
        self.assertEqual(medium["mergePolicy"], "source-local-conservative")
        self.assertTrue(medium["needsSemanticConfirmation"])

    def test_ambiguous_review_is_preserved_but_never_nutrition_eligible(self):
        payload = self._payload(
            [
                {
                    "language": "uk",
                    "source": "очищених та тонко нарізаних",
                    "english": "Peeled and thinly sliced",
                    "classification": "ambiguous",
                    "confidence": "medium",
                }
            ]
        )
        result = mod.compile_semantic_concepts([("batch.json", payload)])
        concept = result["concepts"][0]
        self.assertEqual(concept["classification"], "ambiguous")
        self.assertFalse(concept["nutritionEligible"])
        self.assertFalse(concept["dietEligible"])
        self.assertFalse(concept["allergenEligible"])
        self.assertTrue(concept["needsSemanticConfirmation"])

    def test_source_local_identity_matches_v2_contract_and_is_stable(self):
        first = mod.source_local_ingredient_id("de", "Tomate")
        second = mod.source_local_ingredient_id("de", "Tomate")
        other = mod.source_local_ingredient_id("el", "Ντομάτα")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("local:de:"))

    def test_conflicting_duplicate_review_fails_closed(self):
        payload = self._payload(
            [
                {
                    "language": "de",
                    "source": "Sahne",
                    "english": "Cream",
                    "classification": "food",
                    "confidence": "high",
                },
                {
                    "language": "de",
                    "source": "Sahne",
                    "english": "Whipping cream",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        with self.assertRaises(RuntimeError):
            mod.compile_semantic_concepts([("batch.json", payload)])


if __name__ == "__main__":
    unittest.main()
