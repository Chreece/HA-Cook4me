from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


verifier = _load(
    "verify_post_activation_nutrition_review_decisions_v60_test",
    TOOLS / "verify_post_activation_nutrition_review_decisions_v60.py",
)


def _evidence(target: str, name: str, fdc_id: int, manifest_char: str):
    return {
        "schemaVersion": 1,
        "kind": verifier.direct.EVIDENCE_KIND,
        "catalogVersion": "v-test",
        "referenceManifestSha256": manifest_char * 64,
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
            "secretsPersisted": False,
        },
        "items": [
            {
                "reviewTargetId": target,
                "reviewTargetKind": "semantic-concept",
                "canonicalEnglishName": name,
                "usageCountSum": 1,
                "candidates": [
                    {
                        "fdcId": fdc_id,
                        "description": f"Reference {name}",
                        "dataType": "Foundation",
                        "localEvidenceRank": 1,
                    }
                ],
            }
        ],
    }


def _decision(evidence, evidence_sha: str):
    row = evidence["items"][0]
    candidate = row["candidates"][0]
    return {
        "schemaVersion": 1,
        "kind": verifier.direct.DECISIONS_KIND,
        "catalogVersion": evidence["catalogVersion"],
        "referenceManifestSha256": evidence["referenceManifestSha256"],
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
                "reviewTargetId": row["reviewTargetId"],
                "reviewTargetKind": row["reviewTargetKind"],
                "canonicalEnglishName": row["canonicalEnglishName"],
                "approved": True,
                "fdcId": candidate["fdcId"],
                "candidateEvidenceRank": 1,
                "fdcDescription": candidate["description"],
                "fdcDataType": candidate["dataType"],
                "confidence": "medium",
                "notes": "Explicit synthetic review for verifier regression coverage.",
            }
        ],
    }


def _write_batch(root: Path, batch: str, evidence: dict, evidence_sha: str):
    decision = _decision(evidence, evidence_sha)
    decision_raw = verifier.checkpoint._encoded(decision)
    decision_sha = hashlib.sha256(decision_raw).hexdigest()
    payload, _summary = verifier.direct.compile_review_source(
        evidence,
        decision,
        evidence_sha256=evidence_sha,
        decisions_sha256=decision_sha,
    )
    (root / f"release_catalog_nutrition_review_decisions_post_activation_{batch}.v1.json").write_bytes(decision_raw)
    (root / f"release_catalog_reviewed_nutrition_targets_{batch}.v1.json").write_bytes(
        verifier.checkpoint._encoded(payload)
    )


class MultiEvidenceReviewVerifierTests(unittest.TestCase):
    def test_each_decision_is_replayed_only_against_its_exact_evidence_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_a = _evidence("concept:food:test-a", "Test A", 1001, "a")
            evidence_b = _evidence("concept:food:test-b", "Test B", 1002, "b")
            path_a = root / "evidence-a.json"
            path_b = root / "evidence-b.json"
            path_a.write_bytes(verifier.checkpoint._encoded(evidence_a))
            path_b.write_bytes(verifier.checkpoint._encoded(evidence_b))
            sha_a = hashlib.sha256(path_a.read_bytes()).hexdigest()
            sha_b = hashlib.sha256(path_b.read_bytes()).hexdigest()
            _write_batch(root, "901", evidence_a, sha_a)
            _write_batch(root, "902", evidence_b, sha_b)

            summary = verifier.verify([path_a, path_b], root, root)
            self.assertEqual(summary["decisionBatchCount"], 2)
            self.assertEqual(summary["compiledBindingCount"], 2)
            self.assertEqual(summary["suppliedEvidenceSnapshotCount"], 2)
            self.assertEqual(summary["usedEvidenceSnapshotCount"], 2)
            self.assertEqual(summary["sourceEvidenceSha256s"], sorted([sha_a, sha_b]))
            self.assertEqual(summary["referenceManifestSha256s"], ["a" * 64, "b" * 64])
            self.assertEqual(
                {row["sourceEvidenceSha256"] for row in summary["batches"]},
                {sha_a, sha_b},
            )

    def test_missing_exact_evidence_generation_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_a = _evidence("concept:food:test-a", "Test A", 1001, "a")
            evidence_b = _evidence("concept:food:test-b", "Test B", 1002, "b")
            path_a = root / "evidence-a.json"
            path_b = root / "evidence-b.json"
            path_a.write_bytes(verifier.checkpoint._encoded(evidence_a))
            path_b.write_bytes(verifier.checkpoint._encoded(evidence_b))
            sha_a = hashlib.sha256(path_a.read_bytes()).hexdigest()
            sha_b = hashlib.sha256(path_b.read_bytes()).hexdigest()
            _write_batch(root, "901", evidence_a, sha_a)
            _write_batch(root, "902", evidence_b, sha_b)

            with self.assertRaisesRegex(ValueError, "no supplied evidence snapshot matches"):
                verifier.verify([path_a], root, root)

    def test_single_path_api_remains_backward_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = _evidence("concept:food:test-a", "Test A", 1001, "a")
            path = root / "evidence.json"
            path.write_bytes(verifier.checkpoint._encoded(evidence))
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            _write_batch(root, "901", evidence, sha)
            summary = verifier.verify(path, root, root)
            self.assertEqual(summary["sourceEvidenceSha256"], sha)
            self.assertEqual(summary["usedEvidenceSnapshotCount"], 1)


if __name__ == "__main__":
    unittest.main()
