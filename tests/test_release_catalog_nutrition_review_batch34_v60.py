"""Batch 34: explicit generic food references, not product/safety certification."""
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
FIXTURE = ROOT / "tests/fixtures/nutrition-batch34-retained-reference-v60.json.gz"
FIXTURE_SHA = "0ef118308aa73ae58d0388a2e3a49887cae06c67317829868ce1639fe3c61b20"
SOURCE = TOOLS / "release_catalog_reviewed_nutrition_targets_040.v1.json"
SOURCE_SHA = "8f123237bd4407e0682683cb1e25a7ac5a23119454c22cb18833816e0f501a2d"


class Batch34RetainedReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
        cls.document = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.items = cls.document["items"]
        cls.ids = {r["reviewTargetId"] for r in cls.items}
        cls.by_name = {r["canonicalEnglishName"]: r for r in cls.items}
        cls.sources = {r["reviewTargetId"]: r for r in cls.fixture["sources"]}
        cls.targets = {r["reviewTargetId"]: r for r in cls.fixture["targets"]}
        cls.checkpoint = cp.build_checkpoint(TOOLS)
        cls.records = [r for r in cls.checkpoint["recordedBindings"] if r["reviewFile"] == SOURCE.name]
        cls.deferred = {r["canonicalEnglishName"] for r in cls.fixture["deferredExamples"]}

    def test_18_explicit_full_ids_and_source_bytes(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), SOURCE_SHA)
        self.assertEqual(len(self.items), 18)
        self.assertEqual(len(self.ids), 18)
        self.assertEqual(len(self.document["referenceReceipts"]), 9)
        self.assertEqual(len({r["fdcId"] for r in self.items}), 9)

    def test_all_234_previous_files_and_4604_bindings_are_unchanged(self):
        prefix = "release_catalog_reviewed_nutrition_targets"
        previous = [r for r in self.checkpoint["reviewFiles"]
                    if r["path"] == prefix + ".v1.json"
                    or r["path"].startswith(prefix + "_") and r["path"] < prefix + "_040"]
        self.assertEqual(len(previous), 234)
        self.assertEqual(len(previous), self.fixture["baseReviewFileCount"])
        self.assertEqual(cp._digest(cp._encoded(previous)), self.fixture["baseReviewFilesSha256"])
        names = {r["path"] for r in previous}
        bindings = [r for r in self.checkpoint["recordedBindings"] if r["reviewFile"] in names]
        self.assertEqual(len(bindings), 4604)
        self.assertEqual(cp._digest(cp._encoded(bindings)), self.fixture["baseRecordedBindingsSha256"])

    def test_destinations_disjoint_from_all_other_files_including_future_batches(self):
        others = {r["reviewTargetId"] for r in self.checkpoint["recordedBindings"]
                  if r["reviewFile"] != SOURCE.name}
        self.assertFalse(self.ids & others)
        self.assertGreaterEqual(len(others), 4604)
        self.assertGreaterEqual(len(self.checkpoint["recordedBindings"]), 4622)

    def test_all_12_holds_unchanged_and_not_destinations_or_locators(self):
        held = holds.load_holds()
        self.assertEqual(len(held["targets"]), 12)
        self.assertEqual(held["registrySha256"], self.fixture["holdRegistrySha256"])
        self.assertFalse(self.ids & set(held["targets"]))
        self.assertFalse(set(self.sources) & set(held["targets"]))
        self.assertTrue(all(holds.find_hold(target) is None for target in self.ids))

    def test_fixture_is_a_byte_pinned_projection_not_a_full_snapshot(self):
        self.assertEqual(cp._digest(FIXTURE.read_bytes()), FIXTURE_SHA)
        self.assertFalse(self.fixture["fullSnapshotIncluded"])
        self.assertFalse(self.fixture["sourceRowsAreExactOriginalRows"])
        self.assertTrue(self.fixture["sourceCandidatesAreExactOriginalRecords"])
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(len(self.sources), 9)
        self.assertEqual(len(self.targets), 18)
        self.assertEqual(sum(len(r["candidates"]) for r in self.sources.values()), 9)

    def test_exact_destination_identity_usage_and_rationale_are_preserved(self):
        for row in self.items:
            target = self.targets[row["reviewTargetId"]]
            for key in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName"):
                self.assertEqual(row[key], target[key])
            self.assertEqual(row["usageCountAtReview"], target["usageCountSum"])
            self.assertEqual(row["confidence"], "high")
            self.assertGreater(len(row["notes"]), 200)

    def test_policy_never_invents_destination_rank_or_copies_source_approval(self):
        doc = self.document
        self.assertEqual(doc["selectionMethod"], "explicit-semantic-review")
        self.assertEqual(doc["evidenceBindingScope"], cp.RETAINED_SCOPE)
        self.assertEqual(doc["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertFalse(doc["policy"]["searchResultAutoAccepted"])
        self.assertFalse(doc["policy"]["candidateSearchIsIdentityProof"])
        self.assertFalse(doc["policy"]["providerIdentityInference"])
        self.assertTrue(all("candidateEvidenceRank" not in row for row in self.items))

    def test_all_nine_receipts_match_the_actual_retained_reference_records(self):
        for row in self.records:
            with self.subTest(target=row["reviewTargetId"]):
                self.assertEqual(cp.retained_reference_mismatch(row, self.sources, EVIDENCE_SHA), "")

    def test_loader_preserves_all_source_receipts_and_destination_ids(self):
        loaded = resolver.load_reviews()
        for row in self.records:
            for key in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName", "fdcId",
                        "evidenceBindingScope", "sourceEvidenceSha256", "sourceEvidenceTargetId",
                        "sourceEvidenceCandidateRank", "sourceCandidateSha256"):
                self.assertEqual(loaded[row["reviewTargetId"]][key], row[key])

    def test_file_rank_description_type_and_candidate_byte_drift_fail(self):
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
        self.assertEqual(len({r["reviewTargetId"] for r in examples}), 20)
        self.assertFalse(self.ids & {r["reviewTargetId"] for r in examples})
        self.assertTrue(all(len(r["reason"]) > 50 for r in examples))

    def test_five_raw_salmon_references_do_not_invent_species_or_processing(self):
        rows = [r for r in self.items if r["fdcId"] == 2706284]
        self.assertEqual(len(rows), 5)
        self.assertEqual({r["canonicalEnglishName"] for r in rows},
                         {"Salmon", "Salmon fillet, boned and skinned",
                          "Salmon steaks, 150 g each (skin removed)",
                          "Sashimi-grade salmon, cut into bite-size pieces"})
        self.assertTrue(all(r["fdcDescription"] == "Fish, salmon, raw" for r in rows))
        self.assertTrue(all("No species" in r["notes"] for r in rows))
        self.assertTrue({"Fresh salmon, cut into thirds and salted",
                         "Salmon fillets, 200 g each, salted and peppered",
                         "Salmon roe (for garnish), as needed", "Cod and salmon skewers"} <= self.deferred)

    def test_salmon_portion_size_and_sashimi_label_do_not_certify_edible_yield_or_safety(self):
        steak = self.by_name["Salmon steaks, 150 g each (skin removed)"]
        sashimi = self.by_name["Sashimi-grade salmon, cut into bite-size pieces"]
        self.assertIn("150 g steak size is not proof", steak["notes"])
        self.assertIn("no assurance", sashimi["notes"])
        self.assertNotIn("portionWeightGrams", steak)
        self.assertNotIn("safeToEatRaw", sashimi)

    def test_two_cooked_hams_are_distinct_from_two_prosciutto_references(self):
        cooked = [r for r in self.items if r["fdcId"] == 2705878]
        cured = [r for r in self.items if r["fdcId"] == 2705879]
        self.assertEqual(len(cooked), 2)
        self.assertEqual(len(cured), 2)
        self.assertTrue(all("cooked ham" in r["canonicalEnglishName"].lower() for r in cooked))
        self.assertTrue(all(r["fdcDescription"] == "Ham" for r in cooked))
        self.assertEqual({r["canonicalEnglishName"] for r in cured},
                         {"Pieces of Parma ham", "Slices of Italian prosciutto"})
        self.assertTrue(all(r["fdcDescription"] == "Ham, prosciutto" for r in cured))
        self.assertIn("Italian ham, cut into strips", self.deferred)
        self.assertIn("Cured ham, cut into strips", self.deferred)

    def test_four_brandy_inputs_are_not_liqueur_mixtures_or_alcohol_retention_values(self):
        rows = [r for r in self.items if r["fdcId"] == 2710699]
        self.assertEqual(len(rows), 4)
        self.assertEqual({r["canonicalEnglishName"] for r in rows}, {"Cognac", "Armagnac", "tbsp cognac"})
        self.assertTrue(all(r["fdcDescription"] == "Brandy" for r in rows))
        self.assertTrue(all("alcohol-retention" in r["notes"] for r in rows))
        self.assertTrue(all("exact alcohol strength" in r["notes"] for r in rows))
        self.assertIn("Cognac and orange liqueur", self.deferred)
        self.assertIn("Alcohol", self.deferred)
        self.assertNotIn("gramsPerTablespoon", self.by_name["tbsp cognac"])

    def test_dry_bulgur_is_not_a_meatball_or_a_soaked_grain(self):
        row = self.by_name["Fine bulgur for meatballs"]
        self.assertEqual((row["fdcId"], row["fdcDescription"]), (170688, "Bulgur, dry"))
        self.assertIn("not a finished meatball", row["notes"])
        self.assertIn("Soaked freekeh", self.deferred)

    def test_yellow_snap_beans_and_cooked_savoy_retain_color_part_and_state(self):
        wax = self.by_name["Wax beans"]
        cabbage = self.by_name["Boiled Savoy cabbage leaves"]
        self.assertEqual((wax["fdcId"], wax["fdcDescription"]), (169320, "Beans, snap, yellow, raw"))
        self.assertEqual((cabbage["fdcId"], cabbage["fdcDescription"]), (2709894, "Cabbage, savoy, cooked"))
        self.assertIn("mature dried bean seeds", wax["notes"])
        self.assertIn("Large Savoy cabbage leaves, blanched and refreshed", self.deferred)

    def test_sugar_coated_almonds_and_named_sauce_keep_their_own_composition(self):
        almond = self.by_name["Almond dragées (for finishing)"]
        sauce = self.by_name["Drops of Tabasco (optional)"]
        self.assertEqual((almond["fdcId"], almond["fdcDescription"]), (170656, "Candies, sugar-coated almonds"))
        self.assertEqual((sauce["fdcId"], sauce["fdcDescription"]),
                         (174528, "Sauce, ready-to-serve, pepper, TABASCO"))
        self.assertIn("not plain almonds", almond["notes"])
        self.assertIn("Optionality does not mean zero", sauce["notes"])
        self.assertNotIn("dropWeightGrams", sauce)

    def test_missing_receipt_and_fabricated_target_rank_are_rejected(self):
        doc = deepcopy(self.document)
        doc["referenceReceipts"].pop(str(doc["items"][0]["fdcId"]))
        with self.assertRaisesRegex(ValueError, "missing exact FDC reference receipt"):
            cp.retained_reference_receipt(doc, doc["items"][0], "test")
        doc = deepcopy(self.document)
        doc["items"][0]["candidateEvidenceRank"] = 1
        with self.assertRaisesRegex(ValueError, "source rank is not a target rank"):
            cp.retained_reference_receipt(doc, doc["items"][0], "test")

    def test_duplicate_full_target_ids_are_rejected_even_if_fdc_id_agrees(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for suffix in ("_a", "_b"):
                (root / f"release_catalog_reviewed_nutrition_targets{suffix}.v1.json").write_bytes(SOURCE.read_bytes())
            with self.assertRaisesRegex(ValueError, "duplicate reviewTargetId"):
                cp.build_checkpoint(root)


if __name__ == "__main__":
    unittest.main()
