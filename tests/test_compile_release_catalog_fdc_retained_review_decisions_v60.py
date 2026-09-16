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
    "compile_release_catalog_fdc_retained_review_decisions_v60_test",
    TOOLS / "compile_release_catalog_fdc_retained_review_decisions_v60.py",
)


class RetainedReferenceFdcReviewCompilerTests(unittest.TestCase):
    def _evidence(self):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-fdc-review-target-candidate-evidence-offline-v60",
            "catalogVersion": "v-test",
            "referenceManifestSha256": "a" * 64,
            "reviewTargetCount": 2,
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
                    "reviewTargetId": "concept:food:vegetable-stock",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Vegetable stock",
                    "memberIngredientIds": ["local:de:vegetable-stock"],
                    "memberCount": 1,
                    "usageCountSum": 88,
                    "usedByRecipe": True,
                    "candidateCount": 0,
                    "candidates": [],
                },
                {
                    "reviewTargetId": "concept:food:source-herbs",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Herb bouquet, to taste",
                    "memberIngredientIds": ["local:fr:herb-bouquet"],
                    "memberCount": 1,
                    "usageCountSum": 1,
                    "usedByRecipe": True,
                    "candidateCount": 1,
                    "candidates": [
                        {
                            "fdcId": 171583,
                            "description": "Soup, vegetable broth, ready to serve",
                            "dataType": "SR Legacy",
                            "localEvidenceRank": 7,
                            "localEvidenceScore": 123.0,
                        }
                    ],
                },
            ],
        }

    def _decisions(self, evidence_sha: str):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-fdc-retained-reference-review-decisions-v60",
            "catalogVersion": "v-test",
            "referenceManifestSha256": "a" * 64,
            "sourceEvidenceSha256": evidence_sha,
            "evidenceBindingScope": "retained-reference-record",
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
                    "reviewTargetId": "concept:food:vegetable-stock",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Vegetable stock",
                    "approved": True,
                    "fdcId": 171583,
                    "sourceEvidenceTargetId": "concept:food:source-herbs",
                    "sourceEvidenceCandidateRank": 7,
                    "fdcDescription": "Soup, vegetable broth, ready to serve",
                    "fdcDataType": "SR Legacy",
                    "confidence": "medium",
                    "notes": "Explicit destination review accepts ready-to-serve vegetable broth as the generic liquid vegetable-stock reference; concentration and recipe-specific seasoning are not certified.",
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

    def test_zero_candidate_destination_can_use_explicit_retained_record(self):
        evidence, evidence_sha, _decisions, decisions_sha, payload, summary = self._compile()
        self.assertEqual(payload["evidenceBindingScope"], "retained-reference-record")
        self.assertEqual(payload["sourceEvidenceSha256"], evidence_sha)
        self.assertEqual(payload["reviewDecisionSha256"], decisions_sha)
        self.assertEqual(summary["compiledBindingCount"], 1)
        self.assertEqual(summary["retainedReferenceFdcCount"], 1)
        self.assertEqual(summary["automaticSelectionCount"], 0)

        item = payload["items"][0]
        selected = evidence["items"][1]["candidates"][0]
        digest = compiler.checkpoint._digest(compiler.checkpoint._encoded(selected))
        self.assertEqual(item["fdcId"], 171583)
        self.assertEqual(item["sourceEvidenceTargetId"], "concept:food:source-herbs")
        self.assertEqual(item["sourceEvidenceCandidateRank"], 7)
        self.assertEqual(item["sourceCandidateSha256"], digest)
        self.assertNotIn("candidateEvidenceRank", item)
        self.assertEqual(
            payload["referenceReceipts"]["171583"],
            {
                "sourceEvidenceTargetId": "concept:food:source-herbs",
                "sourceEvidenceCandidateRank": 7,
                "sourceCandidateSha256": digest,
            },
        )

    def test_compiled_retained_source_is_accepted_and_receipt_matches_evidence(self):
        evidence, evidence_sha, _decisions, _decisions_sha, payload, _summary = self._compile()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review_path = root / "release_catalog_reviewed_nutrition_targets_retained_test.v1.json"
            review_path.write_bytes(compiler.checkpoint._encoded(payload))
            built = compiler.checkpoint.build_checkpoint(root)
        binding = built["recordedBindings"][0]
        evidence_by_id = {row["reviewTargetId"]: row for row in evidence["items"]}
        self.assertEqual(binding["evidenceBindingScope"], "retained-reference-record")
        self.assertEqual(
            compiler.checkpoint.retained_reference_mismatch(
                binding,
                evidence_by_id,
                evidence_sha,
            ),
            "",
        )

    def test_stale_evidence_and_unknown_source_fail_closed(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        stale = self._decisions("0" * 64)
        with self.assertRaisesRegex(ValueError, "exact evidence bytes"):
            compiler.compile_review_source(evidence, stale, evidence_sha256=evidence_sha)

        missing_source = self._decisions(evidence_sha)
        missing_source["items"][0]["sourceEvidenceTargetId"] = "concept:food:missing"
        with self.assertRaisesRegex(ValueError, "source evidence target.*absent"):
            compiler.compile_review_source(
                evidence,
                missing_source,
                evidence_sha256=evidence_sha,
            )

    def test_source_candidate_identity_and_metadata_must_match(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))

        absent_fdc = self._decisions(evidence_sha)
        absent_fdc["items"][0]["fdcId"] = 999
        with self.assertRaisesRegex(ValueError, "absent from source target"):
            compiler.compile_review_source(evidence, absent_fdc, evidence_sha256=evidence_sha)

        bad_rank = self._decisions(evidence_sha)
        bad_rank["items"][0]["sourceEvidenceCandidateRank"] = 6
        with self.assertRaisesRegex(ValueError, "source candidate rank differs"):
            compiler.compile_review_source(evidence, bad_rank, evidence_sha256=evidence_sha)

        bad_description = self._decisions(evidence_sha)
        bad_description["items"][0]["fdcDescription"] = "Vegetable stock"
        with self.assertRaisesRegex(ValueError, "description differs"):
            compiler.compile_review_source(evidence, bad_description, evidence_sha256=evidence_sha)

    def test_destination_approval_and_identity_are_required(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))

        not_approved = self._decisions(evidence_sha)
        not_approved["items"][0]["approved"] = False
        with self.assertRaisesRegex(ValueError, "explicitly approved"):
            compiler.compile_review_source(evidence, not_approved, evidence_sha256=evidence_sha)

        wrong_name = self._decisions(evidence_sha)
        wrong_name["items"][0]["canonicalEnglishName"] = "Vegetable broth powder"
        with self.assertRaisesRegex(ValueError, "destination decision identity differs"):
            compiler.compile_review_source(evidence, wrong_name, evidence_sha256=evidence_sha)

    def test_conflicting_receipts_for_same_fdc_id_are_rejected(self):
        evidence = self._evidence()
        evidence["reviewTargetCount"] = 4
        duplicate_source = deepcopy(evidence["items"][1])
        duplicate_source["reviewTargetId"] = "concept:food:source-herbs-2"
        duplicate_source["canonicalEnglishName"] = "Other herb source"
        duplicate_source["candidates"][0]["localEvidenceRank"] = 3
        second_destination = deepcopy(evidence["items"][0])
        second_destination["reviewTargetId"] = "concept:food:vegetable-stock-2"
        second_destination["canonicalEnglishName"] = "Vegetable stock, plain"
        evidence["items"].extend([duplicate_source, second_destination])
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))

        decisions = self._decisions(evidence_sha)
        second = deepcopy(decisions["items"][0])
        second["reviewTargetId"] = "concept:food:vegetable-stock-2"
        second["canonicalEnglishName"] = "Vegetable stock, plain"
        second["sourceEvidenceTargetId"] = "concept:food:source-herbs-2"
        second["sourceEvidenceCandidateRank"] = 3
        decisions["items"].append(second)
        with self.assertRaisesRegex(ValueError, "conflicting retained evidence receipts"):
            compiler.compile_review_source(evidence, decisions, evidence_sha256=evidence_sha)


if __name__ == "__main__":
    unittest.main()
