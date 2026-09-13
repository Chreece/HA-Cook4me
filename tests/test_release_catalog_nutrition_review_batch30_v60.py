"""Batch 30's 100 explicit food/state decisions and immutable evidence receipts.

These regression tests verify decisions/provenance, not laboratory accuracy.
The compressed fixture is a projection; the full-file audit is separate.
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
import nutrition_review_holds_v60 as holds  # noqa: E402
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402

EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"
FIXTURE = ROOT / "tests/fixtures/nutrition-batch30-retained-reference-v60.json.gz"
FIXTURE_SHA = "4efa1f5f77e0f543c281401ebbcd763529c63239bba139afe2d53ff4050d95d7"
FILES = sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets_036*.v1.json"))
FILE_HASHES = [
    "7fca80d26ce37d7b05220e430e773a431a860f199f7c166a7142944dbf71e238",
    "f68fb56a0d029853d6837c5e6424ffd08926d9dca3b6bdd36d9b1b3ebecdf0b5",
    "67fa1cb7bb4829fcce6f7dd09e8d71eeca6c39f14b2ff59e0502ed1ac012d238",
    "9102fe80cd81f5549d361038e2b0d22f7758dff81035c01e12fdd33b2adcb102",
    "234bddaa47f2922e9bba38b45b3d778a705ec3e2d8fce4828231e10db9308641",
]


class Batch30RetainedReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
        cls.documents = [json.loads(p.read_text(encoding="utf-8")) for p in FILES]
        cls.items = [r for d in cls.documents for r in d["items"]]
        cls.ids = {r["reviewTargetId"] for r in cls.items}
        cls.sources = {r["reviewTargetId"]: r for r in cls.fixture["sources"]}
        cls.targets = {r["reviewTargetId"]: r for r in cls.fixture["targets"]}
        cls.checkpoint = cp.build_checkpoint(TOOLS)
        names = {p.name for p in FILES}
        cls.records = [r for r in cls.checkpoint["recordedBindings"] if r["reviewFile"] in names]

    def test_100_full_ids_and_five_files_are_byte_locked(self):
        self.assertEqual(len(FILES), 5)
        self.assertEqual([len(d["items"]) for d in self.documents], [20] * 5)
        self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES], FILE_HASHES)
        self.assertEqual(len(self.items), 100)
        self.assertEqual(len(self.ids), 100)

    def test_all_221_pre_batch_files_and_4381_bindings_are_unchanged(self):
        # Lexical 035 inclusive is the frozen baseline, not a guessed latest
        # batch number. Later 036+ files must not invalidate this old checkpoint.
        prefix = "release_catalog_reviewed_nutrition_targets"
        previous = [r for r in self.checkpoint["reviewFiles"]
                    if r["path"] == prefix + ".v1.json"
                    or r["path"].startswith(prefix + "_") and r["path"] < prefix + "_036"]
        self.assertEqual(len(previous), self.fixture["baseReviewFileCount"])
        self.assertEqual(cp._digest(cp._encoded(previous)), self.fixture["baseReviewFilesSha256"])
        names = {r["path"] for r in previous}
        bindings = [r for r in self.checkpoint["recordedBindings"] if r["reviewFile"] in names]
        self.assertEqual(len(bindings), 4381)
        self.assertEqual(cp._digest(cp._encoded(bindings)), self.fixture["baseRecordedBindingsSha256"])

    def test_new_ids_are_disjoint_from_every_other_source(self):
        names = {p.name for p in FILES}
        others = {r["reviewTargetId"] for r in self.checkpoint["recordedBindings"] if r["reviewFile"] not in names}
        self.assertFalse(self.ids & others)
        self.assertGreaterEqual(len(others), 4381)
        self.assertGreaterEqual(len(self.checkpoint["recordedBindings"]), 4481)

    def test_all_12_holds_are_unchanged_and_not_used_as_destinations_or_locators(self):
        held = holds.load_holds()
        self.assertEqual(len(held["targets"]), 12)
        self.assertEqual(held["registrySha256"], self.fixture["holdRegistrySha256"])
        self.assertFalse(self.ids & set(held["targets"]))
        self.assertFalse(set(self.sources) & set(held["targets"]))
        for row in self.items:
            self.assertIsNone(holds.find_hold(row["reviewTargetId"]))

    def test_fixture_is_a_pinned_projection_not_a_claimed_full_snapshot(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertFalse(self.fixture["fullSnapshotIncluded"])
        self.assertFalse(self.fixture["sourceRowsAreExactOriginalRows"])
        self.assertTrue(self.fixture["sourceCandidatesAreExactOriginalRecords"])
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(len(self.targets), 100)
        self.assertEqual(len(self.sources), 32)

    def test_destination_ids_names_kinds_and_usage_are_preserved(self):
        for row in self.items:
            target = self.targets[row["reviewTargetId"]]
            for key in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName"):
                self.assertEqual(row[key], target[key])
            self.assertEqual(row["usageCountAtReview"], target["usageCountSum"])
            self.assertEqual(row["confidence"], "high")
            self.assertGreater(len(row["notes"]), 70)

    def test_manual_policy_and_source_rank_semantics_are_explicit(self):
        for doc in self.documents:
            self.assertEqual(doc["selectionMethod"], "explicit-semantic-review")
            self.assertEqual(doc["evidenceBindingScope"], cp.RETAINED_SCOPE)
            self.assertEqual(doc["sourceEvidenceSha256"], EVIDENCE_SHA)
            self.assertFalse(doc["policy"]["searchResultAutoAccepted"])
            self.assertFalse(doc["policy"]["candidateSearchIsIdentityProof"])
            for row in doc["items"]:
                self.assertNotIn("candidateEvidenceRank", row)

    def test_all_36_exact_fdc_receipts_match_retained_source_candidates(self):
        self.assertEqual(len({r["fdcId"] for r in self.records}), 36)
        for row in self.records:
            with self.subTest(target=row["reviewTargetId"]):
                self.assertEqual(cp.retained_reference_mismatch(row, self.sources, EVIDENCE_SHA), "")

    def test_resolver_loader_keeps_every_destination_and_source_receipt(self):
        loaded = resolver.load_reviews()
        for row in self.records:
            result = loaded[row["reviewTargetId"]]
            for key in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName", "fdcId",
                        "evidenceBindingScope", "sourceEvidenceSha256", "sourceEvidenceTargetId",
                        "sourceEvidenceCandidateRank", "sourceCandidateSha256"):
                self.assertEqual(result[key], row[key])

    def test_changed_snapshot_or_candidate_metadata_never_passes(self):
        original = self.records[0]
        self.assertEqual(cp.retained_reference_mismatch(original, self.sources, "b" * 64),
                         "retained_reference_source_file_differs")
        for key, bad in (("fdcDescription", "different"), ("fdcDataType", "different"),
                         ("sourceEvidenceCandidateRank", 999)):
            row = {**original, key: bad}
            self.assertEqual(cp.retained_reference_mismatch(row, self.sources, EVIDENCE_SHA),
                             "retained_reference_candidate_metadata_differs")
        sources = deepcopy(self.sources)
        candidate = next(c for c in sources[original["sourceEvidenceTargetId"]]["candidates"]
                         if c["fdcId"] == original["fdcId"])
        candidate["publicationDate"] = "changed"
        self.assertEqual(cp.retained_reference_mismatch(original, sources, EVIDENCE_SHA),
                         "retained_reference_candidate_bytes_differ")

    def test_17_deferred_examples_are_not_approved_by_this_batch(self):
        examples = self.fixture["deferredExamples"]
        self.assertEqual(len(examples), 17)
        self.assertFalse(self.ids & {r["reviewTargetId"] for r in examples})
        for row in examples:
            self.assertGreater(len(row["reason"]), 40)

    def test_reviewed_food_state_and_plant_part_distinctions_are_locked(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        expected = {
            "Ground cumin": 170923, "Ground coriander": 170922,
            "Dried oregano leaves": 171328, "Whole black peppercorns": 170931,
            "Lettuce leaves": 2709789, "A - Turnip leaves (finely sliced)": 170061,
            "Purple turnip, cut into pieces": 170465, "Very soft butter": 2710154,
            "Melted butter (for sauce)": 2710154, "Ice cubes": 2710706,
            "Burdock, skin scraped, washed and cut into 5 cm pieces": 169974,
            "Soy sprouts": 169284, "Sugar snap peas, strings removed": 170010,
        }
        for name, fdc_id in expected.items():
            self.assertEqual(by_name[name]["fdcId"], fdc_id)

    def test_no_nutrient_values_or_unproven_mass_conversions_are_added(self):
        forbidden = {"nutrition", "nutrients", "foodNutrients", "calories", "pieceWeightGrams",
                     "density", "densityGramsPerMl", "cookingYield", "edibleYield"}
        for row in self.items:
            self.assertFalse(forbidden & row.keys())
        for doc in self.documents:
            self.assertIn("No inferred density", doc["nutritionScope"])

    def test_duplicate_binding_even_with_same_fdc_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = cp._encoded(self.documents[0])
            (root / "release_catalog_reviewed_nutrition_targets_001.v1.json").write_bytes(raw)
            (root / "release_catalog_reviewed_nutrition_targets_002.v1.json").write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "duplicate reviewTargetId"):
                cp.build_checkpoint(root)


if __name__ == "__main__":
    unittest.main()
