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

FIXTURE = ROOT / "tests/fixtures/nutrition-batch45-formulated-spice-blend-triage-v60.json"
FIXTURE_SHA = "5e87f26757f859504a8d8098ac3125012741073621e61a5505786fde53840156"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"


class Batch45FormulatedSpiceBlendTriageTests(unittest.TestCase):
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
            identity_ambiguities=(
                ("C-generic-pepper-identity-ambiguous", classifier.GENERIC_PEPPER),
                ("C-formulated-spice-blend-ambiguous", classifier.FORMULATED_SPICE_BLEND),
            ),
        )

    def test_fixture_pins_batch44_baseline_and_exact_small_scope(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(self.fixture["baseRecordedReviewTargetCount"], 5080)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1239)
        self.assertEqual(self.fixture["manualBeforeCount"], 310)
        self.assertEqual(self.fixture["contextBeforeCount"], 929)
        self.assertEqual(len(self.selected), 5)
        self.assertEqual(len({row["reviewTargetId"] for row in self.selected}), 5)
        self.assertEqual(sum(row["usageCountSum"] for row in self.selected), 1419)

    def test_only_curry_and_garam_masala_forms_move_to_context(self):
        matched, manual, context = self.partition(self.selected)
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual(len(context), 5)
        self.assertTrue(
            all(row["classification"] == "C-formulated-spice-blend-ambiguous" for row in context)
        )
        self.assertEqual(sum(row["usageCountSum"] for row in context), 1419)
        self.assertEqual(
            {row["canonicalEnglishName"] for row in context},
            {"Curry", "Garam masala", "Garam masala, a little"},
        )

    def test_named_single_food_controls_remain_manual(self):
        expected = {
            "Broad bean",
            "Ground Sichuan pepper",
            "Juniper berries",
            "Parsley root",
            "Shiso leaves",
            "Vanilla pod",
        }
        self.assertEqual({row["canonicalEnglishName"] for row in self.controls}, expected)
        matched, manual, context = self.partition(self.controls)
        self.assertEqual(matched, [])
        self.assertEqual(context, [])
        self.assertEqual({row["canonicalEnglishName"] for row in manual}, expected)

    def test_exact_pattern_does_not_absorb_existing_composite_forms(self):
        self.assertTrue(classifier.FORMULATED_SPICE_BLEND.pattern.startswith("^"))
        self.assertTrue(classifier.FORMULATED_SPICE_BLEND.pattern.endswith("$"))
        for name in (
            "Curry paste",
            "Curry roux",
            "Green curry paste",
            "Thai green curry paste",
            "Tikka masala paste",
            "Garam masala (spice mix)",
            "Tsp Madras curry blend",
        ):
            self.assertIsNone(classifier.FORMULATED_SPICE_BLEND.match(name), name)

    def test_post_batch45_counts_are_small_and_lossless(self):
        self.assertEqual(self.fixture["expectedMovedToContextCount"], 5)
        self.assertEqual(self.fixture["expectedMovedUsageCount"], 1419)
        self.assertEqual(self.fixture["expectedManualCount"], 305)
        self.assertEqual(self.fixture["expectedContextCount"], 934)
        self.assertEqual(310 - 5, 305)
        self.assertEqual(929 + 5, 934)
        self.assertEqual(305 + 934, self.fixture["remainingReviewTargetCount"])
        self.assertEqual(self.fixture["bindingsCreatedByBatch45"], 0)

    def test_triage_only_does_not_change_recorded_bindings(self):
        checkpoint = cp.build_checkpoint(TOOLS)
        # Triage used the batch42 checkpoint; subsequent explicit reviews
        # must not be counted as bindings created by this historical batch.
        historical = [row for row in checkpoint["recordedBindings"]
                      if row["reviewFile"] <= "release_catalog_reviewed_nutrition_targets_045.v1.json"]
        self.assertEqual(len(historical), 5080)
        self.assertEqual(self.fixture["bindingsCreatedByBatch45"], 0)


if __name__ == "__main__":
    unittest.main()
