from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
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
    "compile_release_catalog_nutrition_hold_release_v60_test",
    TOOLS / "compile_release_catalog_nutrition_hold_release_v60.py",
)


class HoldReleaseCompilerTests(unittest.TestCase):
    def _hold_index(self):
        target = "concept:food:almond-puree"
        row = {
            "reviewTargetId": target,
            "reviewTargetKind": "semantic-concept",
            "canonicalEnglishName": "Almond purée",
            "fdcId": 2262074,
            "fdcDescription": "Almond butter, creamy",
            "fdcDataType": "Foundation",
            "candidateEvidenceRank": 5,
            "reviewFile": "release_catalog_reviewed_nutrition_targets_032.v1.json",
            "reviewFileSha256": "b" * 64,
            "status": "hold",
            "reasonCode": "target_evidence_missing",
            "reason": "Historical target evidence did not retain the selected row.",
            "observedCandidateRank": None,
            "memberIngredientIds": ["local:b", "local:a"],
            "sourceHoldFile": "release_catalog_nutrition_review_holds.v1.json",
        }
        return {
            "registrySha256": "c" * 64,
            "targets": {target: row},
            "identities": {"local:a": row, "local:b": row},
        }

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
                    "reviewTargetId": "concept:food:almond-cream-source",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Almond cream",
                    "memberIngredientIds": ["local:source"],
                    "memberCount": 1,
                    "usageCountSum": 1,
                    "usedByRecipe": True,
                    "candidateCount": 1,
                    "candidates": [
                        {
                            "fdcId": 2262074,
                            "description": "Almond butter, creamy",
                            "dataType": "Foundation",
                            "localEvidenceRank": 11,
                            "localEvidenceScore": 165.137255,
                        }
                    ],
                }
            ],
        }

    def _decisions(self, evidence_sha: str):
        return {
            "schemaVersion": 1,
            "kind": compiler.DECISIONS_KIND,
            "policy": dict(compiler.DECISION_POLICY),
            "items": [
                {
                    "reviewTargetId": "concept:food:almond-puree",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Almond purée",
                    "heldReasonCode": "target_evidence_missing",
                    "heldFdcId": 2262074,
                    "approved": True,
                    "fdcId": 2262074,
                    "fdcDescription": "Almond butter, creamy",
                    "fdcDataType": "Foundation",
                    "confidence": "medium",
                    "sourceEvidenceSha256": evidence_sha,
                    "referenceManifestSha256": "a" * 64,
                    "sourceEvidenceTargetId": "concept:food:almond-cream-source",
                    "sourceEvidenceCandidateRank": 11,
                    "notes": "Explicit rereview accepts the retained creamy almond-butter record as the bounded ground-almond reference while preserving the historical hold row unchanged.",
                }
            ],
        }

    def _compiled(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions(evidence_sha)
        decision_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(decisions))
        payload, summary = compiler.compile_hold_releases(
            {evidence_sha: evidence},
            decisions,
            self._hold_index(),
            decisions_sha256=decision_sha,
        )
        return evidence, evidence_sha, decisions, decision_sha, payload, summary

    def test_release_pins_hold_registry_members_and_exact_candidate(self):
        evidence, evidence_sha, _decisions, decision_sha, payload, summary = self._compiled()
        self.assertEqual(payload["holdRegistrySha256"], "c" * 64)
        self.assertEqual(payload["releaseDecisionSha256"], decision_sha)
        self.assertEqual(summary["releaseTargetCount"], 1)
        self.assertEqual(summary["releasedMemberIdentityCount"], 2)
        self.assertEqual(summary["automaticSelectionCount"], 0)
        item = payload["items"][0]
        self.assertEqual(item["memberIngredientIds"], ["local:a", "local:b"])
        self.assertEqual(item["heldReasonCode"], "target_evidence_missing")
        self.assertEqual(item["heldFdcId"], 2262074)
        self.assertEqual(item["sourceEvidenceSha256"], evidence_sha)
        selected = evidence["items"][0]["candidates"][0]
        expected_candidate_sha = compiler.checkpoint._digest(
            compiler.checkpoint._encoded(selected)
        )
        self.assertEqual(item["sourceCandidateSha256"], expected_candidate_sha)
        self.assertEqual(item["reviewFile"], compiler.RELEASE_FILENAME)

    def test_release_requires_exact_historical_hold_identity(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions(evidence_sha)
        decisions["items"][0]["canonicalEnglishName"] = "Almond spread"
        with self.assertRaisesRegex(ValueError, "identity differs"):
            compiler.compile_hold_releases(
                {evidence_sha: evidence}, decisions, self._hold_index()
            )

    def test_release_requires_exact_hold_reason_and_held_fdc(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        wrong_reason = self._decisions(evidence_sha)
        wrong_reason["items"][0]["heldReasonCode"] = "other"
        with self.assertRaisesRegex(ValueError, "reason code"):
            compiler.compile_hold_releases(
                {evidence_sha: evidence}, wrong_reason, self._hold_index()
            )
        wrong_fdc = self._decisions(evidence_sha)
        wrong_fdc["items"][0]["heldFdcId"] = 123
        with self.assertRaisesRegex(ValueError, "held FDC"):
            compiler.compile_hold_releases(
                {evidence_sha: evidence}, wrong_fdc, self._hold_index()
            )

    def test_release_fails_closed_on_wrong_or_missing_evidence(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions(evidence_sha)
        with self.assertRaisesRegex(ValueError, "exact source evidence"):
            compiler.compile_hold_releases({}, decisions, self._hold_index())

        changed = deepcopy(evidence)
        changed["items"][0]["candidates"][0]["description"] = "Almonds, raw"
        with self.assertRaisesRegex(ValueError, "description differs"):
            compiler.compile_hold_releases(
                {evidence_sha: changed}, decisions, self._hold_index()
            )

    def test_duplicate_release_target_is_rejected(self):
        evidence = self._evidence()
        evidence_sha = compiler.checkpoint._digest(compiler.checkpoint._encoded(evidence))
        decisions = self._decisions(evidence_sha)
        decisions["items"].append(deepcopy(decisions["items"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate hold-release"):
            compiler.compile_hold_releases(
                {evidence_sha: evidence}, decisions, self._hold_index()
            )


if __name__ == "__main__":
    unittest.main()
