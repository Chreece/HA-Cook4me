from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_semantic_standalone_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class StandaloneSemanticDispositionTests(unittest.TestCase):
    def _payload(self, items):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-reviewed-keyless-ingredient-semantics",
            "items": items,
        }

    def _standalone(self, source_id, english, classification, disposition):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-semantic-ingredient-standalone-dispositions",
            "policy": {
                "providerIdentityAssigned": False,
                "sourceLocalIdentityPreserved": True,
                "crossIdentityMergeAllowed": False,
                "reviewDispositionOnly": True,
                "exactReviewedEnglishAndClassificationRequired": True,
                "safetyEligibilityGranted": False,
            },
            "items": [
                {
                    "sourceIngredientId": source_id,
                    "sourceReviewedEnglish": english,
                    "classification": classification,
                    "disposition": disposition,
                    "rationale": "Pinned conservative review disposition with no cross-identity merge and no safety eligibility granted.",
                }
            ],
        }

    def test_food_standalone_closes_review_without_merge_or_safety_eligibility(self):
        payload = self._payload(
            [
                {
                    "language": "ar",
                    "source": "حمّص مجروش",
                    "english": "Crushed chickpeas",
                    "classification": "food",
                    "confidence": "medium",
                }
            ]
        )
        source_id = mod.source_local_ingredient_id("ar", "حمّص مجروش")
        source_concept = mod._source_concept_id("ar", "حمّص مجروش")
        result = mod.compile_semantic_concepts(
            [("batch.json", payload)],
            standalone_payload=self._standalone(
                source_id,
                "Crushed chickpeas",
                "food",
                "reviewed-source-local-standalone",
            ),
            standalone_file="standalone.json",
        )
        self.assertEqual(result["sourceIdentityToConcept"][source_id], source_concept)
        concept = result["concepts"][0]
        self.assertEqual(concept["conceptId"], source_concept)
        self.assertEqual(concept["mergePolicy"], "reviewed-source-local-standalone")
        self.assertFalse(concept["needsSemanticConfirmation"])
        self.assertFalse(concept["nutritionEligible"])
        self.assertFalse(concept["dietEligible"])
        self.assertFalse(concept["allergenEligible"])
        self.assertEqual(result["summary"]["standaloneConfirmedSourceLabels"], 1)

    def test_ambiguous_fragment_can_be_final_reviewed_ambiguous(self):
        payload = self._payload(
            [
                {
                    "language": "uk",
                    "source": "дрібно нарізати",
                    "english": "Finely chop",
                    "classification": "ambiguous",
                    "confidence": "medium",
                }
            ]
        )
        source_id = mod.source_local_ingredient_id("uk", "дрібно нарізати")
        result = mod.compile_semantic_concepts(
            [("batch.json", payload)],
            standalone_payload=self._standalone(
                source_id,
                "Finely chop",
                "ambiguous",
                "reviewed-ambiguous-source-fragment",
            ),
        )
        concept = result["concepts"][0]
        self.assertEqual(concept["classification"], "ambiguous")
        self.assertEqual(concept["mergePolicy"], "reviewed-ambiguous-source-fragment")
        self.assertFalse(concept["needsSemanticConfirmation"])
        self.assertFalse(concept["nutritionEligible"])
        self.assertEqual(result["summary"]["reviewedAmbiguousSourceLabels"], 1)

    def test_standalone_disposition_is_pinned_to_reviewed_text_and_classification(self):
        payload = self._payload(
            [
                {
                    "language": "ar",
                    "source": "حمّص مجروش",
                    "english": "Crushed chickpeas",
                    "classification": "food",
                    "confidence": "medium",
                }
            ]
        )
        source_id = mod.source_local_ingredient_id("ar", "حمّص مجروش")
        bad = self._standalone(
            source_id,
            "Chickpeas",
            "food",
            "reviewed-source-local-standalone",
        )
        with self.assertRaisesRegex(RuntimeError, "sourceReviewedEnglish"):
            mod.compile_semantic_concepts(
                [("batch.json", payload)], standalone_payload=bad
            )

    def test_repository_standalone_ledger_closes_exact_remaining_audit(self):
        tools = ROOT / "tools"
        ledger = json.loads(
            (tools / "release_catalog_semantic_standalone_dispositions.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(ledger["summary"]["standaloneDispositionCount"], 293)
        self.assertEqual(ledger["summary"]["reviewedAmbiguousCount"], 28)
        self.assertEqual(ledger["summary"]["reviewedSourceLocalStandaloneCount"], 265)
        ledger_ids = [row["sourceIngredientId"] for row in ledger["items"]]
        self.assertEqual(len(ledger_ids), len(set(ledger_ids)))

        result = mod.compile_from_paths(mod._review_paths(tools))
        self.assertEqual(result["summary"]["needsSemanticConfirmationSourceLabels"], 0)
        self.assertEqual(result["summary"]["standaloneConfirmedSourceLabels"], 293)
        self.assertEqual(result["summary"]["reviewedAmbiguousSourceLabels"], 28)

        standalone_ids = {row["sourceIngredientId"] for row in ledger["items"]}
        concepts = {row["conceptId"]: row for row in result["concepts"]}
        for source_id in standalone_ids:
            concept = concepts[result["sourceIdentityToConcept"][source_id]]
            self.assertFalse(concept["needsSemanticConfirmation"])
            self.assertFalse(concept["nutritionEligible"])
            self.assertFalse(concept["dietEligible"])
            self.assertFalse(concept["allergenEligible"])


if __name__ == "__main__":
    unittest.main()
