from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_semantic_standalone_equiv_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class StandaloneSemanticEquivalenceTests(unittest.TestCase):
    def _reviews(self):
        return [
            (
                "batch.json",
                {
                    "schemaVersion": 1,
                    "kind": "cook4me-reviewed-keyless-ingredient-semantics",
                    "items": [
                        {
                            "language": "cs",
                            "source": "hořčice plnotučná",
                            "english": "Full-fat mustard",
                            "classification": "food",
                            "confidence": "medium",
                        },
                        {
                            "language": "sk",
                            "source": "plnotučná horčica",
                            "english": "Full-fat mustard",
                            "classification": "food",
                            "confidence": "medium",
                        },
                    ],
                },
            )
        ]

    def _standalone(self, target_id: str):
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
                    "sourceReviewedEnglish": "Full-fat mustard",
                    "classification": "food",
                    "disposition": "reviewed-source-local-standalone",
                    "rationale": "Keep this reviewed source-local food concept conservative while allowing an exact reviewed duplicate to share it.",
                }
            ],
        }

    def _equivalence(self, source_id: str, target_id: str, *, source_english: str = "Full-fat mustard"):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-semantic-ingredient-standalone-equivalences",
            "policy": {
                "providerIdentityAssigned": False,
                "sourceLocalIdentityPreserved": True,
                "targetRemainsStandalone": True,
                "exactReviewedEnglishAndClassificationRequired": True,
                "manualReviewRequired": True,
                "safetyEligibilityGranted": False,
            },
            "summary": {"equivalenceCount": 1},
            "items": [
                {
                    "sourceIngredientId": source_id,
                    "targetSourceIngredientId": target_id,
                    "sourceReviewedEnglish": source_english,
                    "targetReviewedEnglish": "Full-fat mustard",
                    "classification": "food",
                    "rationale": "Both independently reviewed source-local rows have exactly the same English meaning and classification.",
                }
            ],
        }

    def test_exact_medium_source_rows_share_one_conservative_source_concept(self):
        reviews = self._reviews()
        target_id = mod.source_local_ingredient_id("cs", "hořčice plnotučná")
        source_id = mod.source_local_ingredient_id("sk", "plnotučná horčica")
        result = mod.compile_semantic_concepts(
            reviews,
            standalone_payload=self._standalone(target_id),
            standalone_equivalence_payload=self._equivalence(source_id, target_id),
            standalone_equivalence_file="equivalences.json",
        )
        self.assertEqual(
            result["sourceIdentityToConcept"][source_id],
            result["sourceIdentityToConcept"][target_id],
        )
        concept_id = result["sourceIdentityToConcept"][target_id]
        self.assertTrue(concept_id.startswith("concept:source:"))
        concept = next(row for row in result["concepts"] if row["conceptId"] == concept_id)
        self.assertFalse(concept["needsSemanticConfirmation"])
        self.assertFalse(concept["nutritionEligible"])
        self.assertFalse(concept["dietEligible"])
        self.assertFalse(concept["allergenEligible"])
        self.assertEqual(result["summary"]["standaloneEquivalentSourceLabels"], 1)
        source_identity = next(
            row for row in concept["sourceIdentities"]
            if row["ingredientId"] == source_id
        )
        self.assertEqual(
            source_identity["semanticStandaloneEquivalenceTargetSourceIngredientId"],
            target_id,
        )

    def test_equivalence_rejects_meaning_drift(self):
        reviews = self._reviews()
        target_id = mod.source_local_ingredient_id("cs", "hořčice plnotučná")
        source_id = mod.source_local_ingredient_id("sk", "plnotučná horčica")
        bad = self._equivalence(source_id, target_id, source_english="Mustard")
        with self.assertRaisesRegex(RuntimeError, "sourceReviewedEnglish"):
            mod.compile_semantic_concepts(
                reviews,
                standalone_payload=self._standalone(target_id),
                standalone_equivalence_payload=bad,
            )

    def test_equivalence_target_must_remain_standalone(self):
        reviews = self._reviews()
        target_id = mod.source_local_ingredient_id("cs", "hořčice plnotučná")
        source_id = mod.source_local_ingredient_id("sk", "plnotučná horčica")
        with self.assertRaisesRegex(RuntimeError, "target must remain standalone"):
            mod.compile_semantic_concepts(
                reviews,
                standalone_payload=None,
                standalone_equivalence_payload=self._equivalence(source_id, target_id),
            )

    def test_repository_equivalence_ledger_is_exact_and_fail_closed(self):
        tools = ROOT / "tools"
        ledger = json.loads(
            (tools / "release_catalog_semantic_standalone_equivalences.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(ledger["summary"]["equivalenceCount"], 7)
        self.assertEqual(len(ledger["items"]), 7)
        self.assertEqual(
            len({row["sourceIngredientId"] for row in ledger["items"]}), 7
        )
        result = mod.compile_from_paths(mod._review_paths(tools))
        self.assertEqual(result["summary"]["needsSemanticConfirmationSourceLabels"], 0)
        self.assertEqual(result["summary"]["standaloneEquivalentSourceLabels"], 7)
        concepts = {row["conceptId"]: row for row in result["concepts"]}
        for row in ledger["items"]:
            source_id = row["sourceIngredientId"]
            target_id = row["targetSourceIngredientId"]
            self.assertEqual(
                result["sourceIdentityToConcept"][source_id],
                result["sourceIdentityToConcept"][target_id],
            )
            concept = concepts[result["sourceIdentityToConcept"][source_id]]
            self.assertTrue(concept["conceptId"].startswith("concept:source:"))
            self.assertFalse(concept["nutritionEligible"])
            self.assertFalse(concept["dietEligible"])
            self.assertFalse(concept["allergenEligible"])


if __name__ == "__main__":
    unittest.main()
