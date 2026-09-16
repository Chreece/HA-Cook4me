from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location(
    "cook4me_semantic_manual_equivalence_test", MODULE
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

POLICY = {
    "providerIdentityAssigned": False,
    "sourceLocalIdentityPreserved": True,
    "targetRemainsStandalone": True,
    "reviewedEnglishAndClassificationPinned": True,
    "nonExactRequiresManualSemanticEquivalence": True,
    "targetMayHaveMultipleEquivalentSources": True,
    "manualReviewRequired": True,
    "safetyEligibilityGranted": False,
}


class ManualStandaloneSemanticEquivalenceTests(unittest.TestCase):
    def _reviews(self):
        return [
            (
                "batch.json",
                {
                    "schemaVersion": 1,
                    "kind": "cook4me-reviewed-keyless-ingredient-semantics",
                    "items": [
                        {
                            "language": "en",
                            "source": "Anise liqueur",
                            "english": "Anise liqueur",
                            "classification": "food",
                            "confidence": "medium",
                        },
                        {
                            "language": "uk",
                            "source": "tbsp anise liqueur",
                            "english": "tbsp anise liqueur",
                            "classification": "food",
                            "confidence": "medium",
                        },
                        {
                            "language": "pl",
                            "source": "From anise liqueur",
                            "english": "From anise liqueur",
                            "classification": "food",
                            "confidence": "medium",
                        },
                    ],
                },
            )
        ]

    def _ids(self):
        target = mod.source_local_ingredient_id("en", "Anise liqueur")
        first = mod.source_local_ingredient_id("uk", "tbsp anise liqueur")
        second = mod.source_local_ingredient_id("pl", "From anise liqueur")
        return target, first, second

    def _standalone(self, target_id):
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
                    "sourceIngredientId": target_id,
                    "sourceReviewedEnglish": "Anise liqueur",
                    "classification": "food",
                    "disposition": "reviewed-source-local-standalone",
                    "rationale": "Keep the reviewed target as a conservative standalone concept for manual source-local equivalence tests.",
                }
            ],
        }

    def _equivalence(self, items):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-semantic-ingredient-standalone-equivalences",
            "policy": POLICY,
            "summary": {"equivalenceCount": len(items)},
            "items": items,
        }

    def _row(self, source_id, source_english, target_id, *, manual=True):
        row = {
            "sourceIngredientId": source_id,
            "targetSourceIngredientId": target_id,
            "sourceReviewedEnglish": source_english,
            "targetReviewedEnglish": "Anise liqueur",
            "classification": "food",
            "rationale": "Manual review confirms that the extra wording is recipe metadata and the source-local ingredient meaning is unchanged.",
        }
        if manual is not None:
            row["manualSemanticEquivalence"] = manual
        return row

    def test_non_exact_equivalence_requires_explicit_manual_flag(self):
        target, first, _ = self._ids()
        with self.assertRaisesRegex(RuntimeError, "manualSemanticEquivalence=true"):
            mod.compile_semantic_concepts(
                self._reviews(),
                standalone_payload=self._standalone(target),
                standalone_equivalence_payload=self._equivalence(
                    [self._row(first, "tbsp anise liqueur", target, manual=None)]
                ),
            )

    def test_manual_non_exact_equivalence_stays_conservative(self):
        target, first, _ = self._ids()
        result = mod.compile_semantic_concepts(
            self._reviews(),
            standalone_payload=self._standalone(target),
            standalone_equivalence_payload=self._equivalence(
                [self._row(first, "tbsp anise liqueur", target)]
            ),
            standalone_equivalence_file="manual.json",
        )
        self.assertEqual(
            result["sourceIdentityToConcept"][first],
            result["sourceIdentityToConcept"][target],
        )
        concept = next(
            row for row in result["concepts"]
            if row["conceptId"] == result["sourceIdentityToConcept"][target]
        )
        self.assertTrue(concept["conceptId"].startswith("concept:source:"))
        self.assertFalse(concept["nutritionEligible"])
        self.assertFalse(concept["dietEligible"])
        self.assertFalse(concept["allergenEligible"])
        identity = next(
            row for row in concept["sourceIdentities"]
            if row["ingredientId"] == first
        )
        self.assertEqual(
            identity["semanticStandaloneEquivalenceMethod"],
            "explicit-manual-source-local-equivalence",
        )

    def test_multiple_sources_may_share_one_standalone_root(self):
        target, first, second = self._ids()
        result = mod.compile_semantic_concepts(
            self._reviews(),
            standalone_payload=self._standalone(target),
            standalone_equivalence_payload=self._equivalence(
                [
                    self._row(first, "tbsp anise liqueur", target),
                    self._row(second, "From anise liqueur", target),
                ]
            ),
        )
        concept_id = result["sourceIdentityToConcept"][target]
        self.assertEqual(result["sourceIdentityToConcept"][first], concept_id)
        self.assertEqual(result["sourceIdentityToConcept"][second], concept_id)
        self.assertEqual(result["summary"]["standaloneEquivalentSourceLabels"], 2)

    def test_equivalence_chain_is_rejected(self):
        target, first, second = self._ids()
        rows = [
            self._row(first, "tbsp anise liqueur", target),
            {
                **self._row(second, "From anise liqueur", first),
                "targetReviewedEnglish": "tbsp anise liqueur",
            },
        ]
        with self.assertRaisesRegex(RuntimeError, "chains/cycles"):
            mod.compile_semantic_concepts(
                self._reviews(),
                standalone_payload=self._standalone(target),
                standalone_equivalence_payload=self._equivalence(rows),
            )


if __name__ == "__main__":
    unittest.main()
