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

FIXTURE = ROOT / "tests/fixtures/nutrition-batch50-formulated-dashi-triage-v60.json"
FIXTURE_SHA = "477937ac5c93642995f2b3682b7ab9ad3718b4e2277673bedf543e4541d6f095"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"


class Batch50FormulatedDashiTriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.selected = cls.fixture["selectedRows"]
        cls.controls = cls.fixture["contextControls"]
        _rules_doc, cls.compiled = classifier._load_rules()

    def partition(self, rows):
        return classifier._partition_remaining(
            rows,
            self.compiled,
            has_candidates=lambda row: row["candidateCount"] > 0,
            identity_ambiguities=(
                ("C-generic-pepper-identity-ambiguous", classifier.GENERIC_PEPPER),
                ("C-formulated-spice-blend-ambiguous", classifier.FORMULATED_SPICE_BLEND),
                ("C-formulated-herb-blend-ambiguous", classifier.FORMULATED_HERB_BLEND),
                ("C-formulated-pepper-salt-ambiguous", classifier.FORMULATED_PEPPER_SALT),
                *classifier.identity_ambiguities.RULES,
            ),
        )

    def test_fixture_pins_batch49_baseline_and_exact_two_rows(self):
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(self.fixture["baseRecordedReviewTargetCount"], 5080)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1239)
        self.assertEqual(self.fixture["manualBeforeCount"], 295)
        self.assertEqual(self.fixture["contextBeforeCount"], 944)
        self.assertEqual(len(self.selected), 2)
        self.assertEqual(sum(row["usageCountSum"] for row in self.selected), 50)
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)

    def test_only_powder_and_granules_move_via_new_rule(self):
        matched, manual, context = self.partition(self.selected)
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual(len(context), 2)
        self.assertTrue(all(row["classification"] == "C-formulated-dashi-ambiguous" for row in context))
        self.assertEqual(sum(row["usageCountSum"] for row in context), 50)

    def test_existing_dashi_controls_remain_context_for_existing_reason(self):
        matched, manual, context = self.partition(self.controls)
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual(len(context), 4)
        self.assertTrue(all(row["classification"] == "C-context-or-composition-required" for row in context))

    def test_pattern_is_exact(self):
        pattern = classifier.identity_ambiguities.FORMULATED_DASHI
        self.assertTrue(pattern.pattern.startswith("^"))
        self.assertTrue(pattern.pattern.endswith("$"))
        for name in ("Dashi", "Shiro dashi", "B - Kombu dashi", "C - Kombu dashi", "Dashi stock"):
            self.assertIsNone(pattern.match(name), name)

    def test_post_batch50_counts_are_lossless(self):
        self.assertEqual(self.fixture["expectedMovedToContextCount"], 2)
        self.assertEqual(self.fixture["expectedMovedUsageCount"], 50)
        self.assertEqual(self.fixture["expectedManualCount"], 293)
        self.assertEqual(self.fixture["expectedContextCount"], 946)
        self.assertEqual(293 + 946, 1239)
        self.assertEqual(self.fixture["bindingsCreatedByBatch50"], 0)

    def test_triage_only_does_not_change_recorded_bindings(self):
        checkpoint = cp.build_checkpoint(TOOLS)
        self.assertEqual(checkpoint["summary"]["recordedReviewTargetCount"], 5080)
        self.assertEqual(self.fixture["bindingsCreatedByBatch50"], 0)


if __name__ == "__main__":
    unittest.main()
