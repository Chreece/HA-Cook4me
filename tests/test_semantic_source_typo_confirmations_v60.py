from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_semantic_source_typo_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class SourceTypoSemanticConfirmationTests(unittest.TestCase):
    def _payload(self, items):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-reviewed-keyless-ingredient-semantics",
            "items": items,
        }

    def test_source_typo_annotation_is_review_metadata_only(self):
        self.assertEqual(
            mod._safe_syntactic_english("Cheese tortellini (source typo)"),
            "Cheese tortellini",
        )

    def test_source_typo_qualifier_is_preserved(self):
        self.assertEqual(
            mod._safe_syntactic_english(
                "Octopus (pre-cook for 10 minutes in the bowl; source typo)"
            ),
            "Octopus (pre-cook for 10 minutes in the bowl)",
        )

    def test_explicit_source_typo_id_requires_exact_high_confidence_target(self):
        payload = self._payload(
            [
                {
                    "language": "uk",
                    "source": "тортеліні з сиромт",
                    "english": "Cheese tortellini (source typo)",
                    "classification": "food",
                    "confidence": "medium",
                },
                {
                    "language": "en",
                    "source": "Cheese tortellini",
                    "english": "Cheese tortellini",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        source_id = mod.source_local_ingredient_id("uk", "тортеліні з сиромт")
        expected = mod._semantic_concept_id("food", "Cheese tortellini")
        result = mod.compile_semantic_concepts(
            [("batch.json", payload)],
            syntax_confirmation_ids={source_id},
            syntax_confirmation_file="syntax.txt",
        )
        self.assertEqual(result["sourceIdentityToConcept"][source_id], expected)
        concept = next(
            row for row in result["concepts"] if row["conceptId"] == expected
        )
        identity = next(
            row
            for row in concept["sourceIdentities"]
            if row["ingredientId"] == source_id
        )
        self.assertEqual(
            identity["semanticConfirmationMethod"],
            "explicit-reviewed-syntactic-normalization",
        )


if __name__ == "__main__":
    unittest.main()
