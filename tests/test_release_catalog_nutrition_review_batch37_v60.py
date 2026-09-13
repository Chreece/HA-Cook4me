from __future__ import annotations

from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import classify_nutrition_review_queue_v60 as classifier  # noqa: E402
import nutrition_review_holds_v60 as holds  # noqa: E402
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as cp  # noqa: E402

EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"
SOURCES = tuple(TOOLS / name for name in (
    "release_catalog_reviewed_nutrition_targets_041.v1.json",
    "release_catalog_reviewed_nutrition_targets_041b.v1.json",
    "release_catalog_reviewed_nutrition_targets_041c.v1.json",
    "release_catalog_reviewed_nutrition_targets_041d.v1.json",
    "release_catalog_reviewed_nutrition_targets_041e.v1.json",
    "release_catalog_reviewed_nutrition_targets_041f.v1.json",
))
RULES = TOOLS / "release_catalog_nutrition_bulk_family_rules.v1.json"
FIXTURE = ROOT / "tests/fixtures/nutrition-batch37-retained-reference-v60.json.gz"
SOURCE_SHAS = {
    "release_catalog_reviewed_nutrition_targets_041.v1.json": "9947e5e8c53fef8e8f2a668a1b7d90b45aee9ef3a6ed3d3fd4f4c2f717d03bec",
    "release_catalog_reviewed_nutrition_targets_041b.v1.json": "8f24e871922bf35ce1edaf1ffea7d328ddbb1592066f67e50f5eef26c1a42b9b",
    "release_catalog_reviewed_nutrition_targets_041c.v1.json": "4584e3f0148cd18a38510c57610ccd5e3f4f73d7ec7f99e4ef38c81ae5e8911f",
    "release_catalog_reviewed_nutrition_targets_041d.v1.json": "19071c28e472fa712dd4e4b04234cfa185da1c85570d20e9b669ae0088b2b623",
    "release_catalog_reviewed_nutrition_targets_041e.v1.json": "1c44e168ba832504525d410bccde1ea073f6d63c50a91aa9522b491fce9a89c1",
    "release_catalog_reviewed_nutrition_targets_041f.v1.json": "576ae5c08122fddec51fbd803ae2e7c4002ca3b85a9c3e4323881dd37f679366",
}
RULES_SHA = "4f978c97cf12fc76ead871527c061f232a0e671bcf8b96442937a2c64a2a3000"
FIXTURE_SHA = "b593debf672511d9153849b9b3371e19181416881e6d7f98b4332c698c023111"
BASE_FILES_SHA = "9c9edddfad6f70a3783b5ab7c3cd2c35c04f53b888a0bb8521a17ac5ec7c66d8"
BASE_BINDINGS_SHA = "87b67adfc767731219ace6aa1d4909980c64f89e9b434873d3dff2565bc944d7"


class Batch37BulkFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = [json.loads(path.read_text(encoding="utf-8")) for path in SOURCES]
        cls.rules_doc = json.loads(RULES.read_text(encoding="utf-8"))
        cls.fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
        cls.items = [row for document in cls.documents for row in document["items"]]
        cls.ids = {r["reviewTargetId"] for r in cls.items}
        cls.rules = {r["ruleId"]: r for r in cls.rules_doc["rules"]}
        cls.sources = {r["reviewTargetId"]: r for r in cls.fixture["sources"]}
        cls.targets = {r["reviewTargetId"]: r for r in cls.fixture["targets"]}
        cls.checkpoint = cp.build_checkpoint(TOOLS)
        cls.source_names = {path.name for path in SOURCES}
        cls.records = [r for r in cls.checkpoint["recordedBindings"] if r["reviewFile"] in cls.source_names]

    def test_exact_file_bytes_and_counts(self):
        self.assertEqual({path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in SOURCES}, SOURCE_SHAS)
        self.assertEqual(hashlib.sha256(RULES.read_bytes()).hexdigest(), RULES_SHA)
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertEqual(len(self.items), 106)
        self.assertEqual(len(self.ids), 106)
        self.assertEqual(sum(r["bulkFamilyTier"] == "A" for r in self.items), 64)
        self.assertEqual(sum(r["bulkFamilyTier"] == "B" for r in self.items), 42)
        self.assertEqual(sum(r["usageCountAtReview"] for r in self.items), 1683)
        receipts = {}
        for document in self.documents:
            for key, value in document["referenceReceipts"].items():
                if key in receipts:
                    self.assertEqual(receipts[key], value)
                receipts[key] = value
        self.assertEqual(len(receipts), self.fixture["uniqueFdcCount"])

    def test_all_235_previous_review_files_and_4622_bindings_are_byte_pinned(self):
        def sequence(path):
            match = re.search(r"nutrition_targets_(\d+)", path)
            return int(match.group(1)) if match else 0
        previous = [r for r in self.checkpoint["reviewFiles"] if sequence(r["path"]) < 41]
        self.assertEqual(len(previous), 235)
        self.assertEqual(cp._digest(cp._encoded(previous)), BASE_FILES_SHA)
        names = {r["path"] for r in previous}
        bindings = [r for r in self.checkpoint["recordedBindings"] if r["reviewFile"] in names]
        self.assertEqual(len(bindings), 4622)
        self.assertEqual(cp._digest(cp._encoded(bindings)), BASE_BINDINGS_SHA)
        self.assertGreaterEqual(self.checkpoint["summary"]["recordedReviewTargetCount"], 4728)

    def test_destinations_are_disjoint_from_all_previous_and_future_review_rows(self):
        others = {r["reviewTargetId"] for r in self.checkpoint["recordedBindings"] if r["reviewFile"] not in self.source_names}
        self.assertFalse(self.ids & others)
        self.assertEqual(len(self.records), 106)

    def test_all_holds_remain_unchanged_and_are_not_bulk_destinations_or_locators(self):
        held = holds.load_holds()
        self.assertEqual(len(held["targets"]), 12)
        self.assertEqual(held["registrySha256"], self.fixture["holdRegistrySha256"])
        self.assertFalse(self.ids & set(held["targets"]))
        self.assertFalse(set(self.sources) & set(held["targets"]))

    def test_every_review_row_matches_exactly_one_committed_rule(self):
        for row in self.items:
            matches = [rule for rule in self.rules.values()
                       if re.match(rule["pattern"], row["canonicalEnglishName"], re.IGNORECASE)]
            self.assertEqual(len(matches), 1, row["reviewTargetId"])
            rule = matches[0]
            self.assertEqual(row["bulkFamilyRuleId"], rule["ruleId"])
            self.assertEqual(row["bulkFamilyTier"], rule["tier"])
            self.assertEqual(row["fdcId"], rule["fdcId"])
            self.assertEqual(row["fdcDescription"], rule["fdcDescription"])
            self.assertGreater(len(row["notes"]), 350)

    def test_rules_are_fully_anchored_unique_and_cannot_expand_automatically(self):
        self.assertEqual(len(self.rules), len(self.rules_doc["rules"]))
        self.assertTrue(self.rules_doc["policy"]["automaticRuleExpansionForbidden"])
        self.assertFalse(self.rules_doc["policy"]["candidateRankIsIdentityProof"])
        self.assertFalse(self.rules_doc["policy"]["providerIdentityInference"])
        for rule in self.rules.values():
            self.assertTrue(rule["pattern"].startswith("^"))
            self.assertTrue(rule["pattern"].endswith("$"))
            re.compile(rule["pattern"])

    def test_fixture_contains_exact_destination_rows_and_exact_source_candidates(self):
        self.assertFalse(self.fixture["fullSnapshotIncluded"])
        self.assertFalse(self.fixture["sourceRowsAreExactOriginalRows"])
        self.assertTrue(self.fixture["sourceCandidatesAreExactOriginalRecords"])
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(len(self.targets), 106)
        self.assertEqual(len(self.fixture["remainingAfterTargetIds"]), 1591)
        for row in self.items:
            target = self.targets[row["reviewTargetId"]]
            for key in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName"):
                self.assertEqual(row[key], target[key])
            self.assertEqual(row["usageCountAtReview"], target["usageCountSum"])

    def test_every_reference_receipt_matches_retained_candidate_bytes(self):
        for row in self.items:
            self.assertEqual(cp.retained_reference_mismatch(row, self.sources, EVIDENCE_SHA), "")

    def test_loader_preserves_bulk_rule_receipts_and_exact_ids(self):
        loaded = resolver.load_reviews(TOOLS)
        for row in self.items:
            got = loaded[row["reviewTargetId"]]
            for key in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName", "fdcId",
                        "bulkFamilyRuleId", "bulkFamilyTier", "sourceEvidenceTargetId",
                        "sourceEvidenceCandidateRank", "sourceCandidateSha256"):
                self.assertEqual(got[key], row[key])

    def test_classifier_partition_is_lossless_and_approves_nothing_itself(self):
        _, compiled = classifier._load_rules()
        rows = [
            {"reviewTargetId": "synthetic:rule", "canonicalEnglishName": "Bay leaf", "candidates": [{"fdcId": 1}]},
            {"reviewTargetId": "synthetic:manual", "canonicalEnglishName": "Plain novel ingredient", "candidates": [{"fdcId": 2}]},
            {"reviewTargetId": "synthetic:context", "canonicalEnglishName": "Vegetable stock", "candidates": [{"fdcId": 3}]},
            {"reviewTargetId": "synthetic:none", "canonicalEnglishName": "Novel ingredient", "candidates": []},
        ]
        before = deepcopy(rows)
        rule_matches, tier_b, tier_c = classifier._partition_remaining(rows, compiled)
        self.assertEqual(rows, before)
        self.assertEqual([r["reviewTargetId"] for r in rule_matches], ["synthetic:rule"])
        self.assertEqual([r["reviewTargetId"] for r in tier_b], ["synthetic:manual"])
        self.assertEqual([r["reviewTargetId"] for r in tier_c], ["synthetic:context", "synthetic:none"])
        self.assertEqual(len(rule_matches) + len(tier_b) + len(tier_c), len(rows))
        self.assertTrue(all("classification" in r for r in rule_matches + tier_b + tier_c))

    def test_remaining_queue_receipt_is_pinned_unique_and_disjoint_from_batch37(self):
        remaining = self.fixture["remainingAfterTargetIds"]
        self.assertEqual(len(remaining), 1591)
        self.assertEqual(len(set(remaining)), 1591)
        self.assertFalse(set(remaining) & self.ids)
        self.assertEqual(self.fixture["remainingBeforeCount"], 1697)
        self.assertEqual(self.fixture["selectedTargetCount"], 106)
        self.assertEqual(self.fixture["remainingAfterCount"], 1591)
        self.assertEqual(self.fixture["tierCounts"], {"A": 64, "B": 42})

    def test_tier_a_does_not_match_known_context_heavy_examples(self):
        names = ["Salt and pepper", "Vegetable stock", "Rice", "Mirin", "Curry paste",
                 "Rice, washed, soaked for 30 minutes and drained", "Chicken stock powder",
                 "Traditional mustard and cream", "Gochujang sauce", "Salted fermented shrimp"]
        _, compiled = classifier._load_rules()
        for name in names:
            self.assertEqual(classifier._matches(name, compiled), [], name)

    def test_tier_b_notes_are_explicitly_generic_not_exact_subtype_certificates(self):
        rows = [r for r in self.items if r["bulkFamilyTier"] == "B"]
        self.assertEqual(len(rows), 42)
        self.assertTrue(all(r["confidence"] == "medium" for r in rows))
        self.assertTrue(all("generic category fallback" in r["notes"] for r in rows))
        self.assertTrue(all("not a claim" in r["notes"] for r in rows))

    def test_tier_a_notes_do_not_claim_mass_or_brand_precision(self):
        rows = [r for r in self.items if r["bulkFamilyTier"] == "A"]
        self.assertEqual(len(rows), 64)
        self.assertTrue(all(r["confidence"] == "high" for r in rows))
        self.assertTrue(all("does not certify" in r["notes"] for r in rows))
        self.assertTrue(all("piece-weight" in r["notes"] for r in rows))

    def test_specific_state_families_remain_distinct(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        self.assertEqual(by_name["Dried mint"]["fdcId"], 172239)
        self.assertEqual(by_name["Fresh mint leaves"]["fdcId"], 173475)
        self.assertEqual(by_name["Canned sweetcorn"]["fdcId"], 169214)
        self.assertEqual(by_name["Toasted sandwich bread"]["fdcId"], 2707599)
        self.assertEqual(by_name["Wholewheat pasta"]["fdcId"], 168915)

    def test_generic_meat_and_fish_families_only_cover_cutting_or_unspecified_subtype(self):
        by_rule = {}
        for row in self.items:
            by_rule.setdefault(row["bulkFamilyRuleId"], []).append(row)
        self.assertTrue(all(r["fdcId"] == 2705822 for r in by_rule["beef-cheek-generic"] + by_rule["rump-steak-generic"]))
        self.assertTrue(all(r["fdcId"] == 2705862 for r in by_rule["pork-generic-cut"]))
        self.assertTrue(all(r["fdcId"] == 2706224 for r in by_rule["fish-fillet-nfs"] + by_rule["named-fish-generic"]))
        self.assertNotIn("Smoked herring or salmon, cut into pieces", {r["canonicalEnglishName"] for r in self.items})

    def test_generic_cheese_fallback_is_separate_from_specific_swiss_and_blue_families(self):
        by_name = {r["canonicalEnglishName"]: r for r in self.items}
        self.assertEqual(by_name["Emmental"]["fdcId"], 746767)
        self.assertEqual(by_name["Gorgonzola"]["fdcId"], 2705705)
        self.assertEqual(by_name["Mascarpone"]["fdcId"], 2705704)
        self.assertEqual(by_name["Burrata"]["fdcId"], 2705704)
        self.assertEqual(by_name["Mascarpone"]["bulkFamilyTier"], "B")

    def test_classifier_rule_match_without_review_row_is_never_auto_approval(self):
        doc, compiled = classifier._load_rules()
        sample = deepcopy(self.targets[next(iter(self.targets))])
        # Replace name with another rule-compatible value but an unseen ID.
        sample["reviewTargetId"] = "concept:food:synthetic-unreviewed"
        sample["canonicalEnglishName"] = "Bay leaf"
        matched = classifier._matches(sample["canonicalEnglishName"], compiled)
        self.assertEqual(len(matched), 1)
        self.assertTrue(doc["policy"]["ruleMatchIsApprovalOnlyWhenReviewRowExists"])
        self.assertNotIn(sample["reviewTargetId"], self.ids)

    def test_retained_reference_rank_or_candidate_drift_is_rejected(self):
        row = self.items[0]
        self.assertEqual(cp.retained_reference_mismatch({**row, "sourceEvidenceCandidateRank": 999}, self.sources, EVIDENCE_SHA),
                         "retained_reference_candidate_metadata_differs")
        sources = deepcopy(self.sources)
        source = sources[row["sourceEvidenceTargetId"]]
        candidate = next(c for c in source["candidates"] if c["fdcId"] == row["fdcId"])
        candidate["publicationDate"] = "changed"
        self.assertEqual(cp.retained_reference_mismatch(row, sources, EVIDENCE_SHA),
                         "retained_reference_candidate_bytes_differ")

    def test_cli_refuses_overwrite_and_returns_two_while_queue_remains(self):
        result = {
            "schemaVersion": 1,
            "kind": "cook4me-nutrition-review-tier-classification-v60",
            "summary": {"remainingReviewTargetCount": 1591},
            "tierBManual": [],
            "tierCContext": [],
        }
        with tempfile.TemporaryDirectory() as tmp, patch.object(classifier, "classify", return_value=result) as mocked:
            out = Path(tmp) / "classification"
            self.assertEqual(classifier.main(["--evidence", "not-read.json", "--output", str(out)]), 2)
            before = (out / "classification.json").read_bytes()
            self.assertEqual(classifier.main(["--evidence", "not-read.json", "--output", str(out)]), 1)
            self.assertEqual(before, (out / "classification.json").read_bytes())
            self.assertEqual(mocked.call_count, 1)


if __name__ == "__main__":
    unittest.main()
