"""Batch 31's 62 explicit food/state decisions and immutable evidence receipts.

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
FIXTURE = ROOT / "tests/fixtures/nutrition-batch31-retained-reference-v60.json.gz"
FIXTURE_SHA = "28eeade0bc69d41a5cba4fad9305d1fe49fc32e3b52d8632a4f812eb7eddf03c"
FILES = sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets_037*.v1.json"))
FILE_HASHES = ['ada9b423929245ec6f112d44d5d1453a1acd2275ffd94a87ec750d0282c420d2', 'f080d67a00af235b3a906b130b62d9c69eac92d40d000e4ec0677383f6320841', '8d346c79edc61a5647a55fd3c3c67bfa4fd774fa912d0c1bb7f26b45cd0fcac4', '91265456e9e921c79177aea4c9546737db70c521230cb63fdfcb02d41c259682']


class Batch31RetainedReferenceTests(unittest.TestCase):
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

    def test_62_full_ids_and_four_files_are_byte_locked(self):
        self.assertEqual(len(FILES), 4)
        self.assertEqual([len(d["items"]) for d in self.documents], [20, 20, 20, 2])
        self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES], FILE_HASHES)
        self.assertEqual(len(self.items), 62)
        self.assertEqual(len(self.ids), 62)

    def test_all_226_pre_batch_files_and_4481_bindings_are_unchanged(self):
        # Lexical 036 inclusive is the frozen baseline, not a guessed latest
        # batch number. Later 037+ files must not invalidate this old checkpoint.
        prefix = "release_catalog_reviewed_nutrition_targets"
        previous = [r for r in self.checkpoint["reviewFiles"]
                    if r["path"] == prefix + ".v1.json"
                    or r["path"].startswith(prefix + "_") and r["path"] < prefix + "_037"]
        self.assertEqual(len(previous), self.fixture["baseReviewFileCount"])
        self.assertEqual(cp._digest(cp._encoded(previous)), self.fixture["baseReviewFilesSha256"])
        names = {r["path"] for r in previous}
        bindings = [r for r in self.checkpoint["recordedBindings"] if r["reviewFile"] in names]
        self.assertEqual(len(bindings), 4481)
        self.assertEqual(cp._digest(cp._encoded(bindings)), self.fixture["baseRecordedBindingsSha256"])

    def test_new_ids_are_disjoint_from_every_other_source(self):
        names = {p.name for p in FILES}
        others = {r["reviewTargetId"] for r in self.checkpoint["recordedBindings"] if r["reviewFile"] not in names}
        self.assertFalse(self.ids & others)
        self.assertGreaterEqual(len(others), 4481)
        self.assertGreaterEqual(len(self.checkpoint["recordedBindings"]), 4543)

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
        self.assertEqual(len(self.targets), 62)
        self.assertEqual(len(self.sources), 24)

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

    def test_all_26_exact_fdc_receipts_match_retained_source_candidates(self):
        self.assertEqual(len({r["fdcId"] for r in self.records}), 26)
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

    def test_18_deferred_examples_are_not_approved_by_this_batch(self):
        examples = self.fixture["deferredExamples"]
        self.assertEqual(len(examples), 18)
        self.assertFalse(self.ids & {r["reviewTargetId"] for r in examples})
        for row in examples:
            self.assertGreater(len(row["reason"]), 40)

    def test_dry_fresh_and_cooked_pasta_are_not_interchangeable(self):
        from collections import Counter
        chosen = Counter(r["fdcId"] for r in self.items)
        self.assertEqual(chosen[168927], 10)  # explicitly dry pasta
        self.assertEqual(chosen[169727], 4)   # fresh, unfilled, as purchased
        self.assertEqual(chosen[2708357], 3)  # explicitly cooked
        for row in self.items:
            if row["fdcId"] == 168927:
                self.assertIn("dry", row["fdcDescription"])
                self.assertTrue(any(w in row["canonicalEnglishName"].lower() for w in ("dry", "dried")))
            elif row["fdcId"] == 169727:
                self.assertIn("fresh", row["canonicalEnglishName"].lower())
                self.assertIn("as purchased", row["fdcDescription"])
            elif row["fdcId"] == 2708357:
                self.assertIn("cooked", row["canonicalEnglishName"].lower())
        by_name = {r["canonicalEnglishName"]: r["fdcId"] for r in self.items}
        self.assertEqual(by_name["Fresh tagliatelle"], 169727)
        self.assertEqual(by_name["Cooked orzo"], 2708357)
        self.assertEqual(by_name["Dry lasagna sheets"], 168927)

    def test_raw_and_cooked_shrimp_and_corn_packing_state_are_separate(self):
        by_name = {r["canonicalEnglishName"]: r["fdcId"] for r in self.items}
        expected = {
            "Raw prawns": 175179,
            "Raw peeled prawns, cut into 3 or 4 pieces": 175179,
            "Large fresh raw shrimp, peeled": 175179,
            "Frozen cooked prawns": 175180,
            "Frozen cooked shrimp": 175180,
            "Frozen sweetcorn": 168398,
            "Canned sweetcorn, drained": 169214,
            "Tinned sweetcorn, drained": 169214,
        }
        for name, fdc_id in expected.items():
            self.assertEqual(by_name[name], fdc_id)
        for row in self.items:
            if row["fdcId"] == 169214:
                self.assertIn("drained solids", row["fdcDescription"])
                self.assertNotIn("solids and liquids", row["fdcDescription"])
            elif row["fdcId"] == 168398:
                self.assertIn("unprepared", row["fdcDescription"])

    def test_unspecified_nut_salt_roast_and_pepper_color_are_not_invented(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        for name, fdc_id in (("Almond kernels", 2707485), ("Pistachio kernels", 2707527),
                             ("Bell pepper, washed and cut into pieces", 2709799)):
            self.assertEqual(by_name[name]["fdcId"], fdc_id)
            self.assertIn("NFS", by_name[name]["fdcDescription"])
        generic_peppers = [r for r in self.items if r["fdcId"] == 2709799]
        self.assertEqual(len(generic_peppers), 9)
        self.assertFalse(any(r["canonicalEnglishName"].lower() in ("pepper", "ground pepper")
                             for r in generic_peppers))

    def test_bread_toasting_dry_coffee_and_leek_part_are_explicit(self):
        by_name = {r["canonicalEnglishName"]: r["fdcId"] for r in self.items}
        expected = {
            "Baguette": 172675,
            "Baguette slices": 172675,
            "Large slices of rustic baguette, toasted": 174911,
            "Freeze-dried coffee": 2710480,
            "Dried onion": 170002,
            "Bicarbonate of soda": 175040,
            "Leek, white parts washed and finely chopped": 169246,
            "White part of leek, thinly sliced": 169246,
            "Fontina cheese, cut into pieces": 170843,
        }
        for name, fdc_id in expected.items():
            self.assertEqual(by_name[name], fdc_id)
        self.assertEqual(sum(r["fdcId"] == 169246 for r in self.items), 4)

    def test_no_nutrient_values_or_unproven_mass_conversions_are_added(self):
        forbidden = {"nutrition", "nutrients", "foodNutrients", "calories", "pieceWeightGrams",
                     "density", "densityGramsPerMl", "cookingYield", "edibleYield"}
        for row in self.items:
            self.assertFalse(forbidden & row.keys())
        for doc in self.documents:
            self.assertIn("No inferred density", doc["nutritionScope"])

    def test_missing_receipt_or_fabricated_destination_rank_is_rejected(self):
        for mutation in ("missing", "destination_rank"):
            doc = deepcopy(self.documents[0])
            if mutation == "missing":
                del doc["referenceReceipts"][str(doc["items"][0]["fdcId"])]
            else:
                doc["items"][0]["candidateEvidenceRank"] = 1
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "release_catalog_reviewed_nutrition_targets_001.v1.json").write_bytes(cp._encoded(doc))
                with self.assertRaises(ValueError):
                    cp.build_checkpoint(root)

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
