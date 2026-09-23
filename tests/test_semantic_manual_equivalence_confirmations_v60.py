from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_semantic_equivalence_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class ManualSemanticEquivalenceConfirmationTests(unittest.TestCase):
    def _payload(self, items):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-reviewed-keyless-ingredient-semantics",
            "items": items,
        }

    def _confirmation(self, source_id, target_id, source_english, target_english, rationale):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-semantic-ingredient-confirmations",
            "policy": {
                "providerIdentityAssigned": False,
                "exactReviewedEnglishAndClassificationOnly": True,
                "sourceLocalIdentityPreserved": True,
                "manualConfirmationRequired": True,
                "manualSemanticEquivalenceAllowed": True,
            },
            "items": [
                {
                    "sourceIngredientId": source_id,
                    "confirmedConceptId": target_id,
                    "manualSemanticEquivalence": True,
                    "sourceReviewedEnglish": source_english,
                    "targetCanonicalEnglish": target_english,
                    "rationale": rationale,
                }
            ],
        }

    def test_manual_equivalence_merges_reviewed_wording_variant(self):
        payload = self._payload(
            [
                {
                    "language": "ja",
                    "source": "A-クリームチーズ(常温に戻す",
                    "english": "A - Cream cheese (bring to room temperature)",
                    "classification": "food",
                    "confidence": "medium",
                },
                {
                    "language": "en",
                    "source": "A- cream cheese, brought to room temperature",
                    "english": "A- cream cheese, brought to room temperature",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        source_id = mod.source_local_ingredient_id("ja", "A-クリームチーズ(常温に戻す")
        target_id = mod._semantic_concept_id("food", "A- cream cheese, brought to room temperature")
        confirmation = self._confirmation(
            source_id,
            target_id,
            "A - Cream cheese (bring to room temperature)",
            "A- cream cheese, brought to room temperature",
            "Same cream-cheese ingredient and same room-temperature preparation; wording differs only in grammatical aspect.",
        )
        result = mod.compile_semantic_concepts(
            [("batch.json", payload)],
            confirmation_payload=confirmation,
            confirmation_file="manual.json",
        )
        self.assertEqual(result["sourceIdentityToConcept"][source_id], target_id)
        self.assertEqual(result["summary"]["semanticEquivalentConfirmedSourceLabels"], 1)
        self.assertEqual(result["summary"]["exactConfirmedSourceLabels"], 0)
        identity = next(
            identity
            for concept in result["concepts"]
            for identity in concept["sourceIdentities"]
            if identity["ingredientId"] == source_id
        )
        self.assertEqual(
            identity["semanticConfirmationMethod"],
            "explicit-manual-semantic-equivalence",
        )

    def test_manual_equivalence_pins_source_and_target_text(self):
        payload = self._payload(
            [
                {
                    "language": "uk",
                    "source": "кристалізованих лимони",
                    "english": "Candied lemons",
                    "classification": "food",
                    "confidence": "medium",
                },
                {
                    "language": "en",
                    "source": "Candied lemon",
                    "english": "Candied lemon",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        source_id = mod.source_local_ingredient_id("uk", "кристалізованих лимони")
        target_id = mod._semantic_concept_id("food", "Candied lemon")
        confirmation = self._confirmation(
            source_id,
            target_id,
            "WRONG SOURCE TEXT",
            "Candied lemon",
            "Singular/plural wording only.",
        )
        with self.assertRaisesRegex(RuntimeError, "sourceReviewedEnglish"):
            mod.compile_semantic_concepts(
                [("batch.json", payload)],
                confirmation_payload=confirmation,
            )

    def test_manual_equivalence_requires_rationale_and_same_classification(self):
        payload = self._payload(
            [
                {
                    "language": "uk",
                    "source": "оцту",
                    "english": "Vinegar",
                    "classification": "food",
                    "confidence": "medium",
                },
                {
                    "language": "en",
                    "source": "Vinegar",
                    "english": "Vinegar",
                    "classification": "equipment",
                    "confidence": "high",
                },
            ]
        )
        source_id = mod.source_local_ingredient_id("uk", "оцту")
        target_id = mod._semantic_concept_id("equipment", "Vinegar")
        confirmation = self._confirmation(
            source_id,
            target_id,
            "Vinegar",
            "Vinegar",
            "",
        )
        with self.assertRaises(RuntimeError):
            mod.compile_semantic_concepts(
                [("batch.json", payload)],
                confirmation_payload=confirmation,
            )


if __name__ == "__main__":
    unittest.main()
