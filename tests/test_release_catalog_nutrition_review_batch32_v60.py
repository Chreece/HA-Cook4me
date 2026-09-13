"""Batch 32's 32 explicit food/state decisions and immutable evidence receipts.

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
FIXTURE = ROOT / "tests/fixtures/nutrition-batch32-retained-reference-v60.json.gz"
FIXTURE_SHA = "10c3a1643a2faccf888bbff5fbcf4bf0b60ef63109f7488b0a5d41f10138088f"
FILES = sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets_038*.v1.json"))
FILE_HASHES = ['0f5a2acce3f68432c5350d21d7658621923ec72d4684ec9c799e9a6114e77b4b', '071c89e44e5b1602c3871d3593bdfc034a32416df116f0072743f0ce72531780']


class Batch32RetainedReferenceTests(unittest.TestCase):
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

    def test_32_full_ids_and_two_files_are_byte_locked(self):
        self.assertEqual(len(FILES), 2)
        self.assertEqual([len(d["items"]) for d in self.documents], [20, 12])
        self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES], FILE_HASHES)
        self.assertEqual(len(self.items), 32)
        self.assertEqual(len(self.ids), 32)

    def test_all_230_pre_batch_files_and_4543_bindings_are_unchanged(self):
        # Lexical 037 inclusive is the frozen baseline, not a guessed latest
        # batch number. Later 038+ files must not invalidate this old checkpoint.
        prefix = "release_catalog_reviewed_nutrition_targets"
        previous = [r for r in self.checkpoint["reviewFiles"]
                    if r["path"] == prefix + ".v1.json"
                    or r["path"].startswith(prefix + "_") and r["path"] < prefix + "_038"]
        self.assertEqual(len(previous), self.fixture["baseReviewFileCount"])
        self.assertEqual(cp._digest(cp._encoded(previous)), self.fixture["baseReviewFilesSha256"])
        names = {r["path"] for r in previous}
        bindings = [r for r in self.checkpoint["recordedBindings"] if r["reviewFile"] in names]
        self.assertEqual(len(bindings), 4543)
        self.assertEqual(cp._digest(cp._encoded(bindings)), self.fixture["baseRecordedBindingsSha256"])

    def test_new_ids_are_disjoint_from_every_other_source(self):
        names = {p.name for p in FILES}
        others = {r["reviewTargetId"] for r in self.checkpoint["recordedBindings"] if r["reviewFile"] not in names}
        self.assertFalse(self.ids & others)
        self.assertGreaterEqual(len(others), 4543)
        self.assertGreaterEqual(len(self.checkpoint["recordedBindings"]), 4575)

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
        self.assertEqual(len(self.targets), 32)
        self.assertEqual(len(self.sources), 20)

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

    def test_all_21_exact_fdc_receipts_match_retained_source_candidates(self):
        self.assertEqual(len({r["fdcId"] for r in self.records}), 21)
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

    def test_powdered_whole_and_unspecified_liquid_milk_are_separate(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        expected = {"Milk powder": 2705585, "Full-fat milk": 2705385,
                    "B- milk, brought to room temperature": 2705384,
                    "Hot milk": 2705384, "Warm fresh milk": 2705384}
        for name, fdc_id in expected.items():
            self.assertEqual(by_name[name]["fdcId"], fdc_id)
        powder = [r for r in self.items if r["fdcId"] == 2705585]
        self.assertEqual(len(powder), 2)  # provider and semantic IDs stay separate
        self.assertTrue(all("not reconstituted" in r["fdcDescription"] for r in powder))
        self.assertTrue(all("NFS" in r["fdcDescription"] for r in self.items
                            if r["fdcId"] == 2705384))

    def test_unspecified_cream_does_not_approve_numeric_fat_or_plant_alternatives(self):
        cream = [r for r in self.items if r["fdcId"] == 2705592]
        self.assertEqual(len(cream), 2)
        self.assertTrue(all(r["canonicalEnglishName"] == "Liquid cream" for r in cream))
        self.assertTrue(all("NS as to" in r["fdcDescription"] for r in cream))
        deferred = {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]}
        self.assertIn("Full-fat cream (30% fat)", deferred)
        self.assertIn("Milk (cow's milk or plant-based milk)", deferred)
        self.assertIn("Semi-skimmed milk", deferred)

    def test_newly_reviewed_dry_breadcrumbs_never_use_soft_white_bread(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        dried = by_name["Dried breadcrumbs"]
        self.assertEqual(dried["fdcId"], 174928)
        self.assertIn("dry, grated, plain", dried["fdcDescription"])
        soft = [r for r in self.items if r["fdcId"] == 174924]
        self.assertEqual(len(soft), 3)
        for row in soft:
            self.assertIn("White bread, crust", row["canonicalEnglishName"])
            self.assertIn("soft bread crumbs", row["fdcDescription"])
        self.assertEqual(by_name["French bread pieces"]["fdcId"], 172675)
        # The prior deferral was provisional, not an immutable rejection.
        old = json.loads(gzip.decompress((ROOT / "tests/fixtures/nutrition-batch31-retained-reference-v60.json.gz").read_bytes()))
        old_id = next(r["reviewTargetId"] for r in old["deferredExamples"]
                      if r["canonicalEnglishName"] == "Dried breadcrumbs")
        self.assertEqual(dried["reviewTargetId"], old_id)
        deferred = {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]}
        self.assertIn("White breadcrumbs", deferred)
        self.assertIn("B- breadcrumbs", deferred)
        self.assertIn("Panko breadcrumbs", deferred)

    def test_wholemeal_and_single_spices_do_not_promote_starch_or_mixtures(self):
        by_name = {r["canonicalEnglishName"]: r["fdcId"] for r in self.items}
        for name, fdc_id in (("Wholemeal flour", 168893), ("Red pepper flakes", 170932),
                             ("Ground anise", 171316), ("Hot ground paprika", 171329)):
            self.assertEqual(by_name[name], fdc_id)
        self.assertEqual(sum(r["fdcId"] == 168893 for r in self.items), 2)
        deferred = {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]}
        self.assertTrue({"Wholemeal flour T110", "Wholemeal flour T130", "Wheat starch",
                         "Ground fenugreek", "Paprika paste"} <= deferred)
        self.assertFalse(any("star anise" in r["canonicalEnglishName"].lower() for r in self.items))

    def test_raw_parts_frozen_state_and_cooked_eggplant_are_preserved(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        expected = {"Bitter melon, seeds and pith removed, cut 1 cm wide": (168393, "pods, raw"),
                    "Frozen edamame beans": (168410, "frozen, unprepared"),
                    "Peeled and steamed eggplant": (2709929, "cooked, no added fat"),
                    "Grapefruit segments, cut into two or three pieces": (173033, "pink and red and white"),
                    "Chopped salad onion": (2727585, "bulb and greens"),
                    "Salad onion(s), washed and thinly sliced": (2727585, "bulb and greens"),
                    "Veal liver, cut into pieces": (172534, "liver, raw")}
        for name, (fdc_id, words) in expected.items():
            self.assertEqual(by_name[name]["fdcId"], fdc_id)
            self.assertIn(words, by_name[name]["fdcDescription"])
        self.assertIn("Poultry liver", {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]})

    def test_confectionery_and_oil_use_do_not_imply_other_food_identities(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        for name in ("Sponge finger biscuits", "Ladyfinger biscuits", "Ladyfingers, cut into thirds"):
            self.assertEqual(by_name[name]["fdcId"], 2707934)
        self.assertEqual(by_name["Crushed shortbread biscuits"]["fdcId"], 2707964)
        for name in ("Gummy worm candies", "Strawberry fruit gummies"):
            self.assertEqual(by_name[name]["fdcId"], 2710359)
            self.assertIn("vegetarian status", by_name[name]["notes"])
        oil = by_name["Vegetable oil (for stir-frying noodles)"]
        self.assertEqual(oil["fdcId"], 2710180)
        self.assertIn("NFS", oil["fdcDescription"])
        self.assertIn("Ladyfinger biscuits or wafers", {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]})

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
