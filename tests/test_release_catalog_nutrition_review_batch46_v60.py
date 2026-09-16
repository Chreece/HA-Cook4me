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
import nutrition_review_history_v60 as history  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as cp  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/nutrition-batch46-formulated-herb-blend-triage-v60.json"
FIXTURE_SHA = "9323af51e2722fe42db89cb084dd4946c7c99db83f6a4e1e743634ca583aabc3"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"


class Batch46FormulatedHerbBlendTriageTests(unittest.TestCase):
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
                ("C-formulated-herb-blend-ambiguous", classifier.FORMULATED_HERB_BLEND),
            ),
        )

    def test_fixture_pins_batch45_baseline_and_exact_three_rows(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(self.fixture["baseRecordedReviewTargetCount"], 5080)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1239)
        self.assertEqual(self.fixture["manualBeforeCount"], 305)
        self.assertEqual(self.fixture["contextBeforeCount"], 934)
        self.assertEqual(len(self.selected), 3)
        self.assertEqual(sum(row["usageCountSum"] for row in self.selected), 92)

    def test_only_named_formulated_herb_blends_move(self):
        matched, manual, context = self.partition(self.selected)
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual(len(context), 3)
        self.assertTrue(all(
            row["classification"] == "C-formulated-herb-blend-ambiguous"
            for row in context
        ))
        self.assertEqual(
            {row["canonicalEnglishName"] for row in context},
            {"Herbes de Provence", "Italian herbs"},
        )

    def test_named_single_ingredient_controls_remain_manual(self):
        expected = {"Fresh sage leaves", "Shiso leaves", "Juniper berries", "Parsley root", "Vanilla pod"}
        self.assertEqual({row["canonicalEnglishName"] for row in self.controls}, expected)
        matched, manual, context = self.partition(self.controls)
        self.assertEqual(matched, [])
        self.assertEqual(context, [])
        self.assertEqual({row["canonicalEnglishName"] for row in manual}, expected)

    def test_pattern_is_exact_and_does_not_sweep_generic_herb_labels(self):
        self.assertTrue(classifier.FORMULATED_HERB_BLEND.pattern.startswith("^"))
        self.assertTrue(classifier.FORMULATED_HERB_BLEND.pattern.endswith("$"))
        for name in (
            "Herbs",
            "Fresh herbs",
            "Seven spring herbs",
            "Herb bundle",
            "Bunch of herbs",
            "Fresh herbs for serving (dill, sage, parsley)",
        ):
            self.assertIsNone(classifier.FORMULATED_HERB_BLEND.match(name), name)

    def test_post_batch46_counts_are_lossless(self):
        self.assertEqual(self.fixture["expectedMovedToContextCount"], 3)
        self.assertEqual(self.fixture["expectedMovedUsageCount"], 92)
        self.assertEqual(self.fixture["expectedManualCount"], 302)
        self.assertEqual(self.fixture["expectedContextCount"], 937)
        self.assertEqual(305 - 3, 302)
        self.assertEqual(934 + 3, 937)
        self.assertEqual(302 + 937, 1239)
        self.assertEqual(self.fixture["bindingsCreatedByBatch46"], 0)

    def test_triage_only_does_not_change_recorded_bindings(self):
        checkpoint = history.historical_checkpoint(cp.build_checkpoint(TOOLS))
        self.assertEqual(checkpoint["summary"]["recordedReviewTargetCount"], 5080)
        self.assertEqual(self.fixture["bindingsCreatedByBatch46"], 0)


if __name__ == "__main__":
    unittest.main()
