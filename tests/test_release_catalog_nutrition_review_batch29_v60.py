"""Batch 29: explicit reviews of records retained in the immutable FDC snapshot.

The committed fixture is a projection, NOT a byte copy of the full snapshot.
Full-file SHA/provenance reconciliation is separately run on the retained file.
"""
from __future__ import annotations

from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import snapshot_nutrition_review_checkpoint_v60 as cp  # noqa: E402
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402
import nutrition_review_holds_v60 as holds  # noqa: E402

EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"
FIXTURE = ROOT / "tests/fixtures/nutrition-batch29-retained-reference-v60.json.gz"
FIXTURE_SHA = "6edd73b90c013d90550c447a2dd13f0ab3af816e357becb6ec4485594a7921c6"
FILES = sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets_035*.v1.json"))
FILE_HASHES = [
    "52d17c9fec3e4f58fe56534245834b91b589941a7fed97109a0119a138a5e60d",
    "0d694e39494047d82a4d99bd64400eda4bedeb972741673522cef727f188e79a",
    "2930bb1af865d3bfe347d8722dab599a33580439de9b4c66fc341c7f9ef1d4d9",
    "fdd41ea9239766e429b062f6cf93d126f2c403fae1db8e1ecf84af528c2a9a4e",
    "5ad066283ef0c585f4ad45374d63b9946d2e33a30aeb7357415b9adaea1332ca",
    "363a4e2254063f1a3fd5b00b1cfd3a84bd0b5c95e79e874aaf3cb03553da40c0",
    "444dc312581bd85d55c86f21e4856e016119b70b804321e8b0bb17d101454585",
    "ae17cab766c5ad2cf531456ed9f93feac5ba3bf5049e1e173bf776b8d24b4783",
    "2b88aea706e2e93015dd6e070917ac946400b421815357ce5efb6819d5428bd4",
    "af4af2c4df7617a973bf151e7ed7f715d668e4f792851fca67002c29bdf4f84b",
    "bb127708a90ef3c641e75f8bb3fba5ff935da2c46ac74efda670562fb0de4d26",
    "73530d1725e387a9d84aa62f261859ec021e619a050a60bff7e798df74623dfd",
    "cfc4a291557e3f39d88d98a30d767ce8690913707350b73a8ecc5d715f379955",
]


class Batch29RetainedReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
        cls.sources = {r["reviewTargetId"]: r for r in cls.fixture["sources"]}
        cls.fixture_targets = {r["reviewTargetId"]: r for r in cls.fixture["targets"]}
        cls.documents = [json.loads(p.read_text()) for p in FILES]
        cls.items = [r for d in cls.documents for r in d["items"]]
        cls.checkpoint = cp.build_checkpoint(TOOLS)
        names = {p.name for p in FILES}
        cls.records = [r for r in cls.checkpoint["recordedBindings"] if r["reviewFile"] in names]
        cls.held = holds.load_holds()

    def test_exact_250_full_ids_and_13_source_files_are_locked(self):
        self.assertEqual(len(FILES), 13)
        self.assertEqual([len(d["items"]) for d in self.documents], [20] * 12 + [10])
        self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES], FILE_HASHES)
        self.assertEqual(len(self.items), 250)
        self.assertEqual(len({r["reviewTargetId"] for r in self.items}), 250)

    def test_all_new_ids_are_disjoint_from_every_other_review_file(self):
        names = {p.name for p in FILES}
        others = {r["reviewTargetId"] for r in self.checkpoint["recordedBindings"] if r["reviewFile"] not in names}
        self.assertFalse(others & {r["reviewTargetId"] for r in self.items})
        self.assertGreaterEqual(len(others), 4131)
        self.assertGreaterEqual(len(self.checkpoint["recordedBindings"]), 4381)

    def test_original_hold_set_is_not_lifted_or_used_as_a_binding(self):
        self.assertEqual(len(self.held["targets"]), 12)
        for row in self.items:
            self.assertIsNone(holds.find_hold(row["reviewTargetId"]))
        self.assertFalse(set(self.sources) & set(self.held["targets"]))

    def test_fixture_is_a_locked_labeled_projection_not_a_full_snapshot(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertFalse(self.fixture["fullSnapshotIncluded"])
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(len(self.fixture_targets), 250)
        self.assertEqual(len(self.sources), 35)

    def test_destination_identity_kind_name_and_usage_are_preserved(self):
        for row in self.items:
            target = self.fixture_targets[row["reviewTargetId"]]
            for key in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName"):
                self.assertEqual(row[key], target[key])
            self.assertEqual(row["usageCountAtReview"], target["usageCountSum"])
            self.assertGreater(len(row["notes"]), 50)
            self.assertEqual(row["confidence"], "high")

    def test_no_destination_rank_is_invented_and_manual_policy_is_explicit(self):
        for doc in self.documents:
            self.assertEqual(doc["evidenceBindingScope"], cp.RETAINED_SCOPE)
            self.assertEqual(doc["selectionMethod"], "explicit-semantic-review")
            self.assertEqual(doc["sourceEvidenceSha256"], EVIDENCE_SHA)
            self.assertFalse(doc["policy"]["candidateSearchIsIdentityProof"])
            self.assertFalse(doc["policy"]["searchResultAutoAccepted"])
            for row in doc["items"]:
                self.assertNotIn("candidateEvidenceRank", row)

    def test_every_exact_fdc_receipt_matches_the_retained_source_projection(self):
        self.assertEqual(len({r["fdcId"] for r in self.records}), 38)
        for row in self.records:
            with self.subTest(target=row["reviewTargetId"]):
                self.assertEqual(cp.retained_reference_mismatch(row, self.sources, EVIDENCE_SHA), "")
                self.assertGreater(row["sourceEvidenceCandidateRank"], 0)

    def test_review_loader_preserves_reference_receipts_without_identity_rewrite(self):
        loaded = resolver.load_reviews()
        for row in self.records:
            result = loaded[row["reviewTargetId"]]
            for key in ("reviewTargetId", "canonicalEnglishName", "fdcId", "evidenceBindingScope",
                        "sourceEvidenceSha256", "sourceEvidenceTargetId", "sourceEvidenceCandidateRank",
                        "sourceCandidateSha256"):
                self.assertEqual(result[key], row[key])

    def test_unknown_scope_bad_hash_missing_receipt_and_automatic_selection_fail(self):
        original = self.documents[0]
        for mutation in ("scope", "hash", "receipt", "selection", "policy"):
            doc = deepcopy(original)
            if mutation == "scope": doc["evidenceBindingScope"] = "automatic"
            elif mutation == "hash": doc["sourceEvidenceSha256"] = "not-a-hash"
            elif mutation == "receipt": doc["referenceReceipts"] = {}
            elif mutation == "selection": doc["selectionMethod"] = "rank-1"
            else: doc["policy"]["candidateSearchIsIdentityProof"] = True
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                cp.retained_reference_receipt(doc, doc["items"][0], "test")

    def test_invalid_source_rank_candidate_hash_and_empty_notes_fail(self):
        for mutation in ("rank", "bool", "hash", "notes", "destination-rank"):
            doc = deepcopy(self.documents[0]); row = doc["items"][0]
            receipt = doc["referenceReceipts"][str(row["fdcId"])]
            if mutation == "rank": receipt["sourceEvidenceCandidateRank"] = 0
            elif mutation == "bool": receipt["sourceEvidenceCandidateRank"] = True
            elif mutation == "hash": receipt["sourceCandidateSha256"] = "bad"
            elif mutation == "notes": row["notes"] = ""
            else: row["candidateEvidenceRank"] = 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                cp.retained_reference_receipt(doc, row, "test")

    def test_another_file_with_same_reference_manifest_is_not_silently_accepted(self):
        reason = cp.retained_reference_mismatch(self.records[0], self.sources, "b" * 64)
        self.assertEqual(reason, "retained_reference_source_file_differs")

    def test_missing_source_target_or_fdc_record_blocks_provenance(self):
        row = deepcopy(self.records[0])
        row["sourceEvidenceTargetId"] = "missing"
        self.assertEqual(cp.retained_reference_mismatch(row, self.sources, EVIDENCE_SHA), "retained_reference_source_target_absent")
        row = deepcopy(self.records[0]); row["fdcId"] = 999999999
        self.assertEqual(cp.retained_reference_mismatch(row, self.sources, EVIDENCE_SHA), "retained_reference_fdc_id_absent")

    def test_description_data_type_and_source_rank_drift_are_blocked(self):
        for key, change in (("fdcDescription", "different"), ("fdcDataType", "different"), ("sourceEvidenceCandidateRank", 99)):
            row = {**self.records[0], key: change}
            with self.subTest(key=key):
                self.assertEqual(cp.retained_reference_mismatch(row, self.sources, EVIDENCE_SHA), "retained_reference_candidate_metadata_differs")

    def test_unlisted_candidate_metadata_change_is_detected_by_canonical_row_hash(self):
        row = deepcopy(self.records[0]); sources = deepcopy(self.sources)
        candidate = next(c for c in sources[row["sourceEvidenceTargetId"]]["candidates"] if c["fdcId"] == row["fdcId"])
        candidate["publicationDate"] = "changed"
        self.assertEqual(cp.retained_reference_mismatch(row, sources, EVIDENCE_SHA), "retained_reference_candidate_bytes_differ")

    def _synthetic_reconcile(self, *, wrong_name=False, reference_scope=True):
        # A projected synthetic evidence file, with its OWN hash substituted in
        # a copied checkpoint only. Never label this as the full retained file.
        row = deepcopy(self.records[0])
        target = deepcopy(self.fixture_targets[row["reviewTargetId"]])
        target["candidates"] = []
        if wrong_name: target["canonicalEnglishName"] += " changed"
        doc = self.documents[0]
        evidence = {"schemaVersion": 1, "kind": cp.EVIDENCE_KIND,
                    "catalogVersion": doc["catalogVersion"], "referenceManifestSha256": doc["referenceManifestSha256"],
                    "policy": {"candidateSearchIsIdentityProof": False, "selectionPerformed": False,
                               "searchResultAutoAccepted": False, "manualExactIdReviewRequired": True,
                               "providerIngredientIdentityInference": False, "networkRequestsPerformed": False},
                    "items": [target, deepcopy(self.sources[row["sourceEvidenceTargetId"]])]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "synthetic.json"; path.write_bytes(cp._encoded(evidence))
            row["sourceEvidenceSha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            if not reference_scope:
                row.pop("evidenceBindingScope")
                row["candidateEvidenceRank"] = row["sourceEvidenceCandidateRank"]
            checkpoint = {"recordedBindings": [row], "reviewFilesSha256": "a" * 64}
            return cp.reconcile_evidence(checkpoint, path)

    def test_explicit_reference_receipt_can_reconcile_an_absent_destination_candidate(self):
        result = self._synthetic_reconcile()
        self.assertEqual(result["summary"]["provenanceMismatchCount"], 0)
        self.assertFalse(result["selectionPerformed"])
        self.assertFalse(result["semanticApprovalPerformed"])

    def test_source_reference_never_overrides_destination_identity_drift(self):
        result = self._synthetic_reconcile(wrong_name=True)
        self.assertFalse(result["readyForManualReview"])
        self.assertEqual(result["provenanceMismatches"][0]["reason"], "recorded_target_identity_differs")

    def test_legacy_reviews_do_not_gain_implicit_cross_target_fallback(self):
        result = self._synthetic_reconcile(reference_scope=False)
        self.assertFalse(result["readyForManualReview"])
        self.assertEqual(result["provenanceMismatches"][0]["reason"], "recorded_fdc_id_absent_from_target_evidence")

    def test_resolved_profiles_keep_receipts_with_exact_destination_identity(self):
        review = resolver.load_reviews()[self.records[0]["reviewTargetId"]]
        target = self.fixture_targets[review["reviewTargetId"]]
        ident = review["reviewTargetId"] if target["reviewTargetKind"] == "provider-identity" else "local:test:batch29"
        queue = {"kind": "cook4me-release-catalog-nutrition-review-targets-v60", "policy": {
            "exactIngredientIdentityCompletenessPreserved": True, "providerIdentityInference": False,
            "providerIdentityReviewGrouped": False, "sourceLocalGroupingRequiresSemanticConcept": True,
            "sourceLocalGroupingRequiresHighConfidence": True, "sourceLocalGroupingRequiresExactCanonicalEnglish": True,
            "reviewedExactFdcProvenanceRequired": True, "searchResultAutoAccepted": False},
            "targets": [{**target, "memberIngredientIds": [ident], "semanticConceptId": review["reviewTargetId"]}]}
        def fetcher(fdc_id):
            self.assertEqual(fdc_id, review["fdcId"])
            return {"fdcId": fdc_id, "dataType": review["fdcDataType"], "description": review["fdcDescription"],
                    "foodNutrients": [{"nutrient": {"name": "Energy", "unitName": "kcal"}, "amount": 10.0}]}
        output, pending = resolver.resolve(queue, {}, {review["reviewTargetId"]: review}, fetcher=fetcher)
        self.assertEqual(pending["summary"]["resolvedNowReviewTargets"], 1)
        profile = output[ident]
        self.assertEqual(profile["nutritionReviewTargetId"], review["reviewTargetId"])
        self.assertEqual(profile["ingredientId"], ident)
        self.assertEqual(profile["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(profile["sourceCandidateSha256"], review["sourceCandidateSha256"])


if __name__ == "__main__":
    unittest.main()
