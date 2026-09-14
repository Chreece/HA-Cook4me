from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("nutrition_checkpoint_v60", ROOT / "tools/snapshot_nutrition_review_checkpoint_v60.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def review(target="M_FOOD_1", fdc=123):
    return {"schemaVersion": 1, "kind": mod.REVIEW_KIND, "catalogVersion": "capture3",
            "referenceManifestSha256": "a" * 64, "policy": dict(mod.REQUIRED_POLICY),
            "items": [{"reviewTargetId": target, "reviewTargetKind": "provider-identity",
                       "canonicalEnglishName": "Test food", "fdcId": fdc,
                       "fdcDescription": "Test description", "fdcDataType": "SR Legacy",
                       "candidateEvidenceRank": 2}]}


def evidence(target="M_FOOD_1"):
    return {"schemaVersion": 1, "kind": mod.EVIDENCE_KIND, "catalogVersion": "capture3",
            "referenceManifestSha256": "a" * 64,
            "policy": {"candidateSearchIsIdentityProof": False, "selectionPerformed": False,
                       "searchResultAutoAccepted": False, "manualExactIdReviewRequired": True,
                       "providerIngredientIdentityInference": False, "networkRequestsPerformed": False},
            "items": [{"reviewTargetId": target, "reviewTargetKind": "provider-identity",
                       "canonicalEnglishName": "Test food", "candidates": [
                           {"fdcId": 999, "description": "Unselected first result", "dataType": "SR Legacy", "localEvidenceRank": 1},
                           {"fdcId": 123, "description": "Test description", "dataType": "SR Legacy", "localEvidenceRank": 2}]}]}


class NutritionReviewCheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.reviews = self.root / "tools"
        self.reviews.mkdir()
        self.path = self.reviews / "release_catalog_reviewed_nutrition_targets_001.v1.json"
        self.evidence_path = self.root / "evidence.json"
        self.write(self.path, review())
        self.write(self.evidence_path, evidence())

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def checkpoint(self):
        return mod.build_checkpoint(self.reviews)

    def test_deterministic_full_ids_and_provenance(self):
        first = self.checkpoint()
        self.assertEqual(first, self.checkpoint())
        self.assertEqual(first["summary"]["recordedReviewTargetCount"], 1)
        self.assertEqual(first["recordedBindings"][0]["reviewTargetId"], "M_FOOD_1")
        self.assertEqual(first["reviewFiles"][0]["sha256"], mod._digest(self.path.read_bytes()))
        self.assertFalse(first["policy"]["semanticApprovalPerformed"])

    def test_even_note_or_whitespace_changes_invalidate_source_fingerprint(self):
        before = self.checkpoint()
        self.path.write_text(self.path.read_text() + "\n", encoding="utf-8")
        self.assertNotEqual(before["reviewFilesSha256"], self.checkpoint()["reviewFilesSha256"])

    def test_duplicate_ids_rejected_even_same_fdc_id(self):
        other = self.reviews / "release_catalog_reviewed_nutrition_targets_002.v1.json"
        for fdc in (123, 456):
            with self.subTest(fdc=fdc):
                self.write(other, review(fdc=fdc))
                with self.assertRaisesRegex(ValueError, "duplicate reviewTargetId"):
                    self.checkpoint()

    def test_invalid_rows_are_not_silently_skipped(self):
        for bad in (None, {}, {"fdcId": 123}):
            value = review()
            value["items"] = [bad]
            self.write(self.path, value)
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.checkpoint()

    def test_fdc_ids_must_be_positive_integers_not_bool_float_or_string(self):
        for fdc in (True, 1.1, "123", 0, -1, None):
            self.write(self.path, review(fdc=fdc))
            with self.subTest(fdc=fdc), self.assertRaises(ValueError):
                self.checkpoint()

    def test_unsafe_policies_and_duplicate_json_keys_rejected(self):
        value = review()
        value["policy"]["searchResultAutoAccepted"] = 0
        self.write(self.path, value)
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.checkpoint()
        self.path.write_text('{"kind": "first", "kind": "second"}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            self.checkpoint()

    def test_missing_inputs_and_symlinks_rejected(self):
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "no nutrition review files"):
            self.checkpoint()
        self.path.symlink_to(self.evidence_path)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            self.checkpoint()

    def test_reference_and_identity_kind_checked(self):
        for field, bad in (("reviewTargetId", " concept:food:abc"), ("reviewTargetKind", "semantic-concept")):
            value = review()
            value["items"][0][field] = bad
            self.write(self.path, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.checkpoint()
        value = review()
        value["referenceManifestSha256"] = "not-a-hash"
        self.write(self.path, value)
        with self.assertRaises(ValueError):
            self.checkpoint()

    def test_exact_id_subtraction_not_name_or_rank_auto_acceptance(self):
        value = evidence()
        extra = deepcopy(value["items"][0])
        extra["reviewTargetId"] = "M_FOOD_2"
        value["items"].append(extra)
        self.write(self.evidence_path, value)
        result = mod.reconcile_evidence(self.checkpoint(), self.evidence_path)
        self.assertEqual([r["reviewTargetId"] for r in result["remaining"]], ["M_FOOD_2"])
        self.assertEqual(result["remaining"][0]["candidates"], extra["candidates"])
        self.assertEqual(result["summary"]["recordedTargetsInEvidence"], 1)
        self.assertTrue(result["readyForManualReview"])
        self.assertFalse(result["selectionPerformed"])

    def test_outside_evidence_is_counted_not_claimed_verified(self):
        self.write(self.evidence_path, evidence("M_FOOD_2"))
        result = mod.reconcile_evidence(self.checkpoint(), self.evidence_path)
        self.assertEqual(result["summary"]["recordedTargetsOutsideEvidence"], 1)
        self.assertEqual(result["summary"]["remainingEvidenceTargetCount"], 1)

    def test_manifest_drift_blocks_resume_and_does_not_requeue_recorded_id(self):
        value = evidence()
        value["referenceManifestSha256"] = "b" * 64
        self.write(self.evidence_path, value)
        result = mod.reconcile_evidence(self.checkpoint(), self.evidence_path)
        self.assertFalse(result["readyForManualReview"])
        self.assertEqual(result["remaining"], [])
        self.assertEqual(result["provenanceMismatches"][0]["reason"], "recorded_reference_manifest_differs")

    def test_name_kind_catalog_candidate_and_metadata_drift_block_resume(self):
        for mutation in ("name", "kind", "catalog", "candidate", "description", "rank"):
            value = evidence()
            row = value["items"][0]
            if mutation == "name": row["canonicalEnglishName"] = "Other food"
            elif mutation == "kind": row["reviewTargetKind"] = "invalid"
            elif mutation == "catalog": value["catalogVersion"] = "other"
            elif mutation == "candidate": row["candidates"].pop()
            elif mutation == "description": row["candidates"][1]["description"] = "Other description"
            else: row["candidates"][1]["localEvidenceRank"] = 1
            self.write(self.evidence_path, value)
            with self.subTest(mutation=mutation):
                if mutation == "kind":
                    with self.assertRaises(ValueError): mod.reconcile_evidence(self.checkpoint(), self.evidence_path)
                else:
                    result = mod.reconcile_evidence(self.checkpoint(), self.evidence_path)
                    self.assertFalse(result["readyForManualReview"])
                    self.assertEqual(result["summary"]["provenanceMismatchCount"], 1)

    def test_duplicate_evidence_targets_or_candidates_rejected(self):
        for duplicate in ("target", "candidate"):
            value = evidence()
            if duplicate == "target": value["items"].append(deepcopy(value["items"][0]))
            else: value["items"][0]["candidates"].append(deepcopy(value["items"][0]["candidates"][0]))
            self.write(self.evidence_path, value)
            with self.subTest(duplicate=duplicate), self.assertRaisesRegex(ValueError, "duplicate"):
                mod.reconcile_evidence(self.checkpoint(), self.evidence_path)

    def test_cli_preserves_inputs_and_refuses_overwriting_output(self):
        before = self.path.read_bytes(), self.evidence_path.read_bytes()
        output = self.root / "checkpoint"
        args = ["--review-root", str(self.reviews), "--evidence", str(self.evidence_path), "--output", str(output)]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(mod.main(args), 0)
            old = (output / "checkpoint.json").read_bytes()
            self.assertEqual(mod.main(args), 1)
        self.assertEqual(old, (output / "checkpoint.json").read_bytes())
        self.assertEqual(before, (self.path.read_bytes(), self.evidence_path.read_bytes()))

    def test_cli_provenance_mismatch_returns_two_with_report(self):
        value = evidence()
        value["referenceManifestSha256"] = "b" * 64
        self.write(self.evidence_path, value)
        output = self.root / "checkpoint"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(mod.main(["--review-root", str(self.reviews), "--evidence", str(self.evidence_path), "--output", str(output)]), 2)
        self.assertEqual(json.loads((output / "summary.json").read_text())["provenanceMismatchCount"], 1)


if __name__ == "__main__":
    unittest.main()
