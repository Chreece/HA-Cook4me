"""Batch 33: explicit generic food references, not product/laboratory certification."""
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
FIXTURE = ROOT / "tests/fixtures/nutrition-batch33-retained-reference-v60.json.gz"
FIXTURE_SHA = "99e42d4dbb4b9584321d4132db1f56a83f18d8a3887e5fdad78c30eaacb12dab"
FILES = sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets_039*.v1.json"))
FILE_HASHES = ["315c75cddb590218123f530d2e5a2ac3b28d2cb2b1af8c2783d6defc3e9ef624",
               "8abe27f81e1a9f3aca9127493298986c798d31d7da9e815fc72a8fcae276a8e1"]


class Batch33RetainedReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
        cls.documents = [json.loads(p.read_text(encoding="utf-8")) for p in FILES]
        cls.items = [row for doc in cls.documents for row in doc["items"]]
        cls.ids = {r["reviewTargetId"] for r in cls.items}
        cls.sources = {r["reviewTargetId"]: r for r in cls.fixture["sources"]}
        cls.targets = {r["reviewTargetId"]: r for r in cls.fixture["targets"]}
        cls.checkpoint = cp.build_checkpoint(TOOLS)
        names = {p.name for p in FILES}
        cls.records = [r for r in cls.checkpoint["recordedBindings"] if r["reviewFile"] in names]

    def test_29_full_ids_and_two_files_are_byte_locked(self):
        self.assertEqual([len(doc["items"]) for doc in self.documents], [20, 9])
        self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES], FILE_HASHES)
        self.assertEqual(len(self.items), 29)
        self.assertEqual(len(self.ids), 29)

    def test_all_232_prior_files_and_4575_bindings_are_unchanged(self):
        prefix = "release_catalog_reviewed_nutrition_targets"
        previous = [r for r in self.checkpoint["reviewFiles"]
                    if r["path"] == prefix + ".v1.json"
                    or r["path"].startswith(prefix + "_") and r["path"] < prefix + "_039"]
        self.assertEqual(len(previous), 232)
        self.assertEqual(len(previous), self.fixture["baseReviewFileCount"])
        self.assertEqual(cp._digest(cp._encoded(previous)), self.fixture["baseReviewFilesSha256"])
        names = {r["path"] for r in previous}
        bindings = [r for r in self.checkpoint["recordedBindings"] if r["reviewFile"] in names]
        self.assertEqual(len(bindings), 4575)
        self.assertEqual(cp._digest(cp._encoded(bindings)), self.fixture["baseRecordedBindingsSha256"])

    def test_ids_are_disjoint_from_every_other_source_including_future_batches(self):
        names = {p.name for p in FILES}
        others = {r["reviewTargetId"] for r in self.checkpoint["recordedBindings"] if r["reviewFile"] not in names}
        self.assertFalse(self.ids & others)
        self.assertGreaterEqual(len(others), 4575)
        self.assertGreaterEqual(len(self.checkpoint["recordedBindings"]), 4604)

    def test_all_12_holds_are_unchanged_and_not_destinations_or_locators(self):
        held = holds.load_holds()
        self.assertEqual(len(held["targets"]), 12)
        self.assertEqual(held["registrySha256"], self.fixture["holdRegistrySha256"])
        self.assertFalse(self.ids & set(held["targets"]))
        self.assertFalse(set(self.sources) & set(held["targets"]))
        self.assertTrue(all(holds.find_hold(target) is None for target in self.ids))

    def test_fixture_is_a_hashed_projection_not_a_full_snapshot(self):
        self.assertEqual(cp._digest(FIXTURE.read_bytes()), FIXTURE_SHA)
        self.assertFalse(self.fixture["fullSnapshotIncluded"])
        self.assertFalse(self.fixture["sourceRowsAreExactOriginalRows"])
        self.assertTrue(self.fixture["sourceCandidatesAreExactOriginalRecords"])
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(len(self.sources), 15)
        self.assertEqual(len(self.targets), 29)

    def test_destination_identity_usage_and_written_rationale_are_preserved(self):
        for row in self.items:
            target = self.targets[row["reviewTargetId"]]
            for key in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName"):
                self.assertEqual(row[key], target[key])
            self.assertEqual(row["usageCountAtReview"], target["usageCountSum"])
            self.assertEqual(row["confidence"], "high")
            self.assertGreater(len(row["notes"]), 100)

    def test_explicit_policy_never_fabricates_destination_candidate_ranks(self):
        for doc in self.documents:
            self.assertEqual(doc["selectionMethod"], "explicit-semantic-review")
            self.assertEqual(doc["evidenceBindingScope"], cp.RETAINED_SCOPE)
            self.assertEqual(doc["sourceEvidenceSha256"], EVIDENCE_SHA)
            self.assertFalse(doc["policy"]["searchResultAutoAccepted"])
            self.assertFalse(doc["policy"]["candidateSearchIsIdentityProof"])
            self.assertFalse(doc["policy"]["providerIdentityInference"])
            self.assertTrue(all("candidateEvidenceRank" not in row for row in doc["items"]))

    def test_all_15_exact_reference_receipts_match_the_retained_candidate_records(self):
        self.assertEqual(len({r["fdcId"] for r in self.records}), 15)
        for row in self.records:
            with self.subTest(target=row["reviewTargetId"]):
                self.assertEqual(cp.retained_reference_mismatch(row, self.sources, EVIDENCE_SHA), "")

    def test_resolver_loader_keeps_every_destination_and_source_receipt(self):
        loaded = resolver.load_reviews()
        for row in self.records:
            for key in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName", "fdcId",
                        "evidenceBindingScope", "sourceEvidenceSha256", "sourceEvidenceTargetId",
                        "sourceEvidenceCandidateRank", "sourceCandidateSha256"):
                self.assertEqual(loaded[row["reviewTargetId"]][key], row[key])

    def test_snapshot_rank_description_type_and_candidate_byte_drift_fail(self):
        original = self.records[0]
        self.assertEqual(cp.retained_reference_mismatch(original, self.sources, "b" * 64),
                         "retained_reference_source_file_differs")
        for key, bad in (("fdcDescription", "different"), ("fdcDataType", "different"),
                         ("sourceEvidenceCandidateRank", 999)):
            self.assertEqual(cp.retained_reference_mismatch({**original, key: bad}, self.sources, EVIDENCE_SHA),
                             "retained_reference_candidate_metadata_differs")
        sources = deepcopy(self.sources)
        candidate = next(c for c in sources[original["sourceEvidenceTargetId"]]["candidates"]
                         if c["fdcId"] == original["fdcId"])
        candidate["publicationDate"] = "changed"
        self.assertEqual(cp.retained_reference_mismatch(original, sources, EVIDENCE_SHA),
                         "retained_reference_candidate_bytes_differ")

    def test_20_deferred_examples_are_not_approved_by_this_batch(self):
        examples = self.fixture["deferredExamples"]
        self.assertEqual(len(examples), 20)
        self.assertFalse(self.ids & {r["reviewTargetId"] for r in examples})
        self.assertTrue(all(len(r["reason"]) > 50 for r in examples))

    def test_raw_minced_beef_and_pork_do_not_invent_species_or_fat_ratios(self):
        expected = {"Minced beef": 2705853, "Finely minced beef": 2705853,
                    "A- minced pork": 2514745, "Minced pork": 2514745}
        selected = {r["canonicalEnglishName"]: r for r in self.items if r["fdcId"] in set(expected.values())}
        self.assertEqual({name: r["fdcId"] for name, r in selected.items()}, expected)
        self.assertTrue(all("raw" in r["fdcDescription"] and "%" not in r["fdcDescription"]
                            for r in selected.values()))
        deferred = {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]}
        self.assertTrue({"Minced meat", "Minced meat (half lamb, half beef)", "Minced veal or beef",
                         "Beef meatballs", "Pork meatballs"} <= deferred)

    def test_nine_unbranded_vegetarian_sausages_never_use_pork_or_a_brand_profile(self):
        rows = [r for r in self.items if r["fdcId"] == 174269]
        self.assertEqual(len(rows), 9)
        self.assertTrue(all("vegetarian sausage" in r["canonicalEnglishName"].lower() for r in rows))
        self.assertTrue(all(r["fdcDescription"] == "Sausage, meatless" for r in rows))
        self.assertTrue(all("vegan status, allergens" in r["notes"] for r in rows))
        self.assertTrue(all("HERTA" not in r["canonicalEnglishName"] for r in rows))
        deferred = {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]}
        self.assertIn("HERTA vegetarian Knacki sausage", deferred)
        self.assertIn("HERTA Le Bon Végétal plain strips", deferred)

    def test_four_sake_bindings_are_separate_input_not_mirin_lees_or_a_marinade(self):
        rows = [r for r in self.items if r["fdcId"] == 167723]
        self.assertEqual({r["canonicalEnglishName"] for r in rows},
                         {"Sake (for sauce)", "Sake (for pre-seasoning)",
                          "Sake (for seasoning pork)", "Sake (to pour over salmon)"})
        self.assertTrue(all("separately measured input" in r["notes"] for r in rows))
        self.assertTrue(all("evaporation, retention" in r["notes"] for r in rows))
        deferred = {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]}
        self.assertTrue({"Sake lees", "Mirin"} <= deferred)

    def test_unspecified_almond_beverage_and_plain_dry_cereal_remain_distinct(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        almond = by_name["Almond drink"]
        self.assertEqual((almond["fdcId"], almond["fdcDescription"]), (2705410, "Almond milk, NFS"))
        flakes = by_name["Cornflakes, finely crushed"]
        self.assertEqual((flakes["fdcId"], flakes["fdcDescription"]), (2708453, "Cereal, corn flakes, plain"))
        self.assertIn("No milk is part", flakes["notes"])
        deferred = {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]}
        self.assertTrue({"Milk (cow's milk or plant-based milk)", "Plant-based drink"} <= deferred)

    def test_raw_seafood_is_not_smoked_ink_brined_or_a_whole_animal_mass_conversion(self):
        expected = {"Squid, washed and cut into rings": 174223,
                    "Cleaned flying squid, cut into strips": 174223,
                    "Baby cuttlefish": 174215,
                    "Skinless sea bass, cut into 3 cm pieces": 175142,
                    "Trout, gutted, scaled and cut into 4 fillets": 175153}
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        for name, fdc_id in expected.items():
            self.assertEqual(by_name[name]["fdcId"], fdc_id)
            self.assertIn("raw", by_name[name]["fdcDescription"])
            self.assertIn("mixed species", by_name[name]["fdcDescription"])
        deferred = {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]}
        self.assertTrue({"Cuttlefish ink", "Frozen squid, thawed in salt water and drained",
                         "Slices of smoked trout cut into strips"} <= deferred)

    def test_fresh_basil_and_chili_do_not_acquire_dried_or_color_assumptions(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        expected = {"Basil / purple basil, leaves picked": 172232, "*Fresh chili": 2709798,
                    "B- red chili, deseeded and thinly sliced into rounds": 170106}
        for name, fdc_id in expected.items():
            self.assertEqual(by_name[name]["fdcId"], fdc_id)
        self.assertEqual(by_name["*Fresh chili"]["fdcDescription"], "Peppers, hot, raw")
        self.assertNotIn(170932, {by_name[name]["fdcId"] for name in expected})

    def test_raw_backfat_and_shoulder_are_not_lard_lean_only_or_cured_pork(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        backfat = by_name["Pork fatback"]
        shoulder = by_name["Pork shoulder, cut into approximately 100 g pieces"]
        self.assertEqual((backfat["fdcId"], backfat["fdcDescription"]), (167811, "Pork, fresh, backfat, raw"))
        self.assertEqual(shoulder["fdcId"], 167843)
        self.assertIn("whole, separable lean and fat, raw", shoulder["fdcDescription"])
        self.assertNotIn("lean only", shoulder["fdcDescription"])
        deferred = {r["canonicalEnglishName"] for r in self.fixture["deferredExamples"]}
        self.assertTrue({"Pork collar", "Salted pork (100 g pieces)"} <= deferred)

    def test_missing_receipts_and_fabricated_destination_rank_are_rejected(self):
        doc = deepcopy(self.documents[0])
        row = doc["items"][0]
        doc["referenceReceipts"].pop(str(row["fdcId"]))
        with self.assertRaisesRegex(ValueError, "missing exact FDC reference receipt"):
            cp.retained_reference_receipt(doc, row, "test")
        doc = deepcopy(self.documents[0])
        doc["items"][0]["candidateEvidenceRank"] = 1
        with self.assertRaisesRegex(ValueError, "source rank is not a target rank"):
            cp.retained_reference_receipt(doc, doc["items"][0], "test")

    def test_duplicate_full_destination_ids_are_rejected_even_when_fdc_agrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for suffix in ("_a", "_b"):
                path = root / f"release_catalog_reviewed_nutrition_targets{suffix}.v1.json"
                path.write_bytes(FILES[0].read_bytes())
            with self.assertRaisesRegex(ValueError, "duplicate reviewTargetId"):
                cp.build_checkpoint(root)


if __name__ == "__main__":
    unittest.main()
