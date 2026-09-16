from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import classify_nutrition_review_queue_v60 as classifier  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as cp  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/nutrition-batch44-generic-pepper-triage-v60.json"
FIXTURE_SHA = "61922721e37afbb0f5920e04e767dba93b89ac26ea806a46a71a5073b28f2849"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"


class Batch44GenericPepperTriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.selected = cls.fixture["selectedRows"]
        cls.controls = cls.fixture["manualControls"]
        _rules_doc, cls.compiled = classifier._load_rules()

    def partition(self, rows):
        return classifier._partition_remaining(
            rows,
            self.compiled,
            has_candidates=lambda row: row["candidateCount"] > 0,
            identity_ambiguities=(("C-generic-pepper-identity-ambiguous", classifier.GENERIC_PEPPER),),
        )

    def test_fixture_pins_batch43_baseline_and_exact_small_scope(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(self.fixture["baseRecordedReviewTargetCount"], 5080)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1239)
        self.assertEqual(self.fixture["manualBeforeCount"], 321)
        self.assertEqual(self.fixture["contextBeforeCount"], 918)
        self.assertEqual(len(self.selected), 11)
        self.assertEqual(len({row["reviewTargetId"] for row in self.selected}), 11)
        self.assertEqual(sum(row["usageCountSum"] for row in self.selected), 2478)
        self.assertEqual(len(self.controls), 9)

    def test_only_generic_pepper_forms_move_to_context(self):
        matched, manual, context = self.partition(self.selected)
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual(len(context), 11)
        self.assertTrue(
            all(row["classification"] == "C-generic-pepper-identity-ambiguous" for row in context)
        )
        self.assertEqual(sum(row["usageCountSum"] for row in context), 2478)

    def test_named_pepper_controls_remain_manual(self):
        expected = {
            "Ground Sichuan pepper",
            "Pink peppercorn",
            "Pink peppercorns",
            "Pink peppercorns (for finishing)",
            "Creole pepper",
            "Sichuan pepper powder",
            "Sichuan peppercorns",
            "Sansho pepper (condiment), a little",
            "Çarliston pepper, cut into strips",
        }
        self.assertEqual({row["canonicalEnglishName"] for row in self.controls}, expected)
        matched, manual, context = self.partition(self.controls)
        self.assertEqual(matched, [])
        self.assertEqual(context, [])
        self.assertEqual({row["canonicalEnglishName"] for row in manual}, expected)

    def test_post_batch44_counts_are_small_and_lossless(self):
        self.assertEqual(self.fixture["expectedMovedToContextCount"], 11)
        self.assertEqual(self.fixture["expectedMovedUsageCount"], 2478)
        self.assertEqual(self.fixture["expectedManualCount"], 310)
        self.assertEqual(self.fixture["expectedContextCount"], 929)
        self.assertEqual(321 - 11, 310)
        self.assertEqual(918 + 11, 929)
        self.assertEqual(310 + 929, self.fixture["remainingReviewTargetCount"])
        self.assertEqual(self.fixture["bindingsCreatedByBatch44"], 0)

    def test_pattern_is_anchored_and_does_not_catch_named_peppers(self):
        self.assertEqual(classifier.GENERIC_PEPPER.pattern[0], "^")
        self.assertEqual(classifier.GENERIC_PEPPER.pattern[-1], "$")
        for name in (
            "Sichuan pepper",
            "Pink peppercorn",
            "Creole pepper",
            "Sansho pepper",
            "Çarliston pepper",
            "chili pepper",
        ):
            self.assertIsNone(classifier.GENERIC_PEPPER.match(name), name)

    def test_triage_only_does_not_change_recorded_bindings(self):
        checkpoint = cp.build_checkpoint(TOOLS)
        # Triage used the batch42 checkpoint; subsequent explicit reviews
        # must not be counted as bindings created by this historical batch.
        historical = [row for row in checkpoint["recordedBindings"]
                      if row["reviewFile"] <= "release_catalog_reviewed_nutrition_targets_045.v1.json"]
        self.assertEqual(len(historical), 5080)
        self.assertEqual(self.fixture["bindingsCreatedByBatch44"], 0)


if __name__ == "__main__":
    unittest.main()
