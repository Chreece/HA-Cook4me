from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_semantic_punctuation_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class SemanticPunctuationConfirmationTests(unittest.TestCase):
    def _payload(self, items):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-reviewed-keyless-ingredient-semantics",
            "items": items,
        }

    def test_explicit_punctuation_only_confirmation_uses_unique_high_target(self):
        payload = self._payload(
            [
                {
                    "language": "bg",
                    "source": "Пълнеж",
                    "english": "Filling",
                    "classification": "other",
                    "confidence": "medium",
                },
                {
                    "language": "en",
                    "source": "Filling:",
                    "english": "Filling:",
                    "classification": "other",
                    "confidence": "high",
                },
            ]
        )
        source_id = mod.source_local_ingredient_id("bg", "Пълнеж")
        expected_concept = mod._semantic_concept_id("other", "Filling:")
        result = mod.compile_semantic_concepts(
            [("batch.json", payload)],
            syntax_confirmation_ids={source_id},
            syntax_confirmation_file="syntax.txt",
        )
        self.assertEqual(result["summary"]["semanticConcepts"], 1)
        self.assertEqual(result["summary"]["syntacticConfirmedSourceLabels"], 1)
        self.assertEqual(result["sourceIdentityToConcept"][source_id], expected_concept)
        concept = result["concepts"][0]
        self.assertEqual(concept["canonicalEnglish"], "Filling:")
        self.assertFalse(concept["needsSemanticConfirmation"])
        identity = next(
            row
            for row in concept["sourceIdentities"]
            if row["ingredientId"] == source_id
        )
        self.assertEqual(
            identity["semanticConfirmationMethod"],
            "explicit-reviewed-syntactic-normalization",
        )

    def test_punctuation_only_confirmation_fails_when_target_is_not_unique(self):
        payload = self._payload(
            [
                {
                    "language": "bg",
                    "source": "Пълнеж",
                    "english": "Filling",
                    "classification": "other",
                    "confidence": "medium",
                },
                {
                    "language": "en",
                    "source": "Filling:",
                    "english": "Filling:",
                    "classification": "other",
                    "confidence": "high",
                },
                {
                    "language": "de",
                    "source": "Filling!",
                    "english": "Filling!",
                    "classification": "other",
                    "confidence": "high",
                },
            ]
        )
        source_id = mod.source_local_ingredient_id("bg", "Пълнеж")
        with self.assertRaisesRegex(RuntimeError, "unique punctuation-only"):
            mod.compile_semantic_concepts(
                [("batch.json", payload)],
                syntax_confirmation_ids={source_id},
            )

    def test_punctuation_key_preserves_diacritics(self):
        self.assertNotEqual(
            mod._structural_punctuation_key("Creme:"),
            mod._structural_punctuation_key("Crème"),
        )
        self.assertEqual(
            mod._structural_punctuation_key("STUFFING:"),
            mod._structural_punctuation_key("Stuffing"),
        )


if __name__ == "__main__":
    unittest.main()
