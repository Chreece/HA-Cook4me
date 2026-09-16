from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


compiler = _load(
    "compile_release_catalog_fdc_review_decisions_v60_test",
    TOOLS / "compile_release_catalog_fdc_review_decisions_v60.py",
)


class ExplicitFdcReviewDecisionCompilerTests(unittest.TestCase):
    def _evidence(self):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-fdc-review-target-candidate-evidence-offline-v60",
            "catalogVersion": "v-test",
            "referenceManifestSha256": "a" * 64,
            "reviewTargetCount": 1,
            "policy": {
                "candidateSearchIsIdentityProof": False,
                "selectionPerformed": False,
                "searchResultAutoAccepted": False,
                "providerIngredientIdentityInference": False,
                "reviewedExactFdcBindingRequired": True,
                "literalExactDescriptionIsIdentityProof": False,
                "singletonCandidateIsIdentityProof": False,
                "aliasFallbackIsIdentityProof": False,
                "networkRequestsPerformed": False,
                "apiKeyRequired": False,
                "secretsPersisted": False,
            },
            "items": [
                {
                    "reviewTargetId": "concept:food:tomato-paste",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Tomato paste",
                    "memberIngredientIds": ["local:de:tomato-paste", "local:fr:tomato-paste"],
                    "memberCount": 2,
                    "usageCountSum": 17,
                    "usedByRecipe": True,
                    "candidateCount": 2,
                    "candidates": [
                        {
                            "fdcId": 111,
                            "description": "Tomato sauce, canned",
                            "dataType": "Survey (FNDDS)",
                            "localEvidenceRank": 1,
                            "localEvidenceScore": 900.0,
                        },
                        {
                            "fdcId": 222,
                            "description": "Tomato, paste, canned, without salt added",
                            "dataType": "Foundation",
                            "localEvidenceRank": 2,
                            "localEvidenceScore": 850.0,
                        },
                    ],
                }
            ],
        }

    def _decisions(self, evidence_sha: str):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-fdc-review-decisions-v60",
            "catalogVersion": "v-test",
            "referenceManifestSha256": "a" * 64,
            "sourceEvidenceSha256": evidence_sha,
            "policy": {
                "manualSemanticReviewPerformed": True,
                "candidateSearchIsIdentityProof": False,
                "searchResultAutoAccepted": False,
                "automaticSelectionPerformed": False,
                "exactFdcBindingRequired": True,
                "providerIdentityInference": False,
            },
            "items": [
                {
                    "reviewTargetId": "concept:food:tomato-paste",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Tomato paste",
                    "approved": True,
                    "fdcId": 222,
                    "candidateEvidenceRank": 2,
                    "fdcDescription": "Tomato, paste, canned, without salt added",
                    "fdcDataType": "Foundation",
                    "confidence": "high",
                    "notes": "Explicit review selected the plain tomato-paste reference; salt and recipe-role wording are not inferred.",
                }
            ],
        }

    def _compile(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions(evidence_sha)
        decisions_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(decisions))
        payload, summary = compiler.compile_review_source(
            evidence,
            decisions,
            evidence_sha256=evidence_sha,
            decisions_sha256=decisions_sha,
        )
        return evidence, evidence_sha, decisions, decisions_sha, payload, summary

    def test_explicit_binding_carries_exact_evidence_receipts(self):
        evidence, evidence_sha, _decisions, decisions_sha, payload, summary = self._compile()
        self.assertEqual(payload["kind"], "cook4me-reviewed-nutrition-target-source")
        self.assertEqual(payload["sourceEvidenceSha256"], evidence_sha)
        self.assertEqual(payload["reviewDecisionSha256"], decisions_sha)
        self.assertFalse(payload["policy"]["searchResultAutoAccepted"])
        self.assertFalse(payload["policy"]["candidateSearchIsIdentityProof"])
        self.assertEqual(len(payload["items"]), 1)

        item = payload["items"][0]
        selected = evidence["items"][0]["candidates"][1]
        self.assertEqual(item["reviewTargetId"], "concept:food:tomato-paste")
        self.assertEqual(item["fdcId"], 222)
        self.assertEqual(item["candidateEvidenceRank"], 2)
        self.assertEqual(item["usageCountAtReview"], 17)
        self.assertEqual(item["sourceEvidenceTargetId"], item["reviewTargetId"])
        self.assertEqual(item["sourceEvidenceCandidateRank"], 2)
        self.assertEqual(item["sourceEvidenceSha256"], evidence_sha)
        self.assertEqual(
            item["sourceCandidateSha256"],
            compiler.checkpoint._digest(compiler.checkpoint._encoded(selected)),
        )
        self.assertEqual(summary["compiledBindingCount"], 1)
        self.assertEqual(summary["automaticSelectionCount"], 0)
        self.assertFalse(summary["searchResultsAutoAccepted"])

    def test_compiled_source_is_accepted_by_existing_checkpoint_contract(self):
        _evidence, _evidence_sha, _decisions, _decisions_sha, payload, _summary = self._compile()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / "release_catalog_reviewed_nutrition_targets_post_activation_test.v1.json"
            path.write_bytes(compiler.checkpoint._encoded(payload))
            checkpoint = compiler.checkpoint.build_checkpoint(root)
        self.assertEqual(checkpoint["summary"]["recordedReviewTargetCount"], 1)
        binding = checkpoint["recordedBindings"][0]
        self.assertEqual(binding["reviewTargetId"], "concept:food:tomato-paste")
        self.assertEqual(binding["fdcId"], 222)
        self.assertEqual(binding["candidateEvidenceRank"], 2)

    def test_stale_or_different_evidence_bytes_are_rejected(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions("0" * 64)
        with self.assertRaisesRegex(ValueError, "exact evidence bytes"):
            compiler.compile_review_source(
                evidence,
                decisions,
                evidence_sha256=evidence_sha,
            )

    def test_approved_fdc_id_must_exist_in_that_exact_target_evidence(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions(evidence_sha)
        decisions["items"][0]["fdcId"] = 999
        with self.assertRaisesRegex(ValueError, "absent from target evidence"):
            compiler.compile_review_source(
                evidence,
                decisions,
                evidence_sha256=evidence_sha,
            )

    def test_candidate_metadata_must_match_the_reviewed_snapshot(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions(evidence_sha)
        decisions["items"][0]["candidateEvidenceRank"] = 1
        with self.assertRaisesRegex(ValueError, "candidate rank differs"):
            compiler.compile_review_source(
                evidence,
                decisions,
                evidence_sha256=evidence_sha,
            )

    def test_decision_identity_and_explicit_approval_are_fail_closed(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))

        wrong_name = self._decisions(evidence_sha)
        wrong_name["items"][0]["canonicalEnglishName"] = "Tomato puree"
        with self.assertRaisesRegex(ValueError, "decision identity differs"):
            compiler.compile_review_source(
                evidence,
                wrong_name,
                evidence_sha256=evidence_sha,
            )

        not_approved = self._decisions(evidence_sha)
        not_approved["items"][0]["approved"] = False
        with self.assertRaisesRegex(ValueError, "explicitly approved"):
            compiler.compile_review_source(
                evidence,
                not_approved,
                evidence_sha256=evidence_sha,
            )

    def test_legacy_manual_review_evidence_policy_remains_accepted(self):
        evidence = self._evidence()
        evidence["policy"] = {
            "candidateSearchIsIdentityProof": False,
            "selectionPerformed": False,
            "searchResultAutoAccepted": False,
            "manualExactIdReviewRequired": True,
            "providerIngredientIdentityInference": False,
            "networkRequestsPerformed": False,
            "secretsPersisted": False,
        }
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions(evidence_sha)
        payload, _summary = compiler.compile_review_source(
            evidence,
            decisions,
            evidence_sha256=evidence_sha,
        )
        self.assertEqual(payload["items"][0]["fdcId"], 222)

    def test_duplicate_decisions_are_rejected(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions(evidence_sha)
        decisions["items"].append(deepcopy(decisions["items"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate review decision"):
            compiler.compile_review_source(
                evidence,
                decisions,
                evidence_sha256=evidence_sha,
            )


if __name__ == "__main__":
    unittest.main()
