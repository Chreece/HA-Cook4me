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

FIXTURE = ROOT / "tests/fixtures/nutrition-batch47-pepper-salt-triage-v60.json"
FIXTURE_SHA = "4aff9516ddb49aa9576459c3680f7fbae52da7f04067995fdb92852f9388538d"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"


class Batch47PepperSaltTriageTests(unittest.TestCase):
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
                ("C-formulated-pepper-salt-ambiguous", classifier.FORMULATED_PEPPER_SALT),
            ),
        )

    def test_fixture_pins_batch46_baseline_and_exact_three_rows(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(self.fixture["baseRecordedReviewTargetCount"], 5080)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1239)
        self.assertEqual(self.fixture["manualBeforeCount"], 302)
        self.assertEqual(self.fixture["contextBeforeCount"], 937)
        self.assertEqual(len(self.selected), 3)
        self.assertEqual(sum(row["usageCountSum"] for row in self.selected), 64)

    def test_only_pepper_salt_forms_move_to_context(self):
        matched, manual, context = self.partition(self.selected)
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual(len(context), 3)
        self.assertTrue(all(
            row["classification"] == "C-formulated-pepper-salt-ambiguous"
            for row in context
        ))
        self.assertEqual(sum(row["usageCountSum"] for row in context), 64)
        self.assertEqual(
            {row["canonicalEnglishName"] for row in context},
            {"Pepper salt (a little)", "A- pepper salt", "C- pepper salt, a little"},
        )

    def test_other_salt_and_named_pepper_controls_remain_manual(self):
        expected = {
            "Ground Sichuan pepper",
            "Pink peppercorn",
            "Salted water",
            "Fleur de sel, freshly ground pepper",
            "Salt, pepper",
            "Salt, black pepper",
        }
        self.assertEqual({row["canonicalEnglishName"] for row in self.controls}, expected)
        matched, manual, context = self.partition(self.controls)
        self.assertEqual(matched, [])
        self.assertEqual(context, [])
        self.assertEqual({row["canonicalEnglishName"] for row in manual}, expected)

    def test_pattern_is_exact_and_does_not_absorb_general_salt_pepper_labels(self):
        self.assertTrue(classifier.FORMULATED_PEPPER_SALT.pattern.startswith("^"))
        self.assertTrue(classifier.FORMULATED_PEPPER_SALT.pattern.endswith("$"))
        for name in (
            "Salt, pepper",
            "Salt, black pepper",
            "Fleur de sel, freshly ground pepper",
            "Ground Sichuan pepper",
            "Pink peppercorn",
            "Salted water",
        ):
            self.assertIsNone(classifier.FORMULATED_PEPPER_SALT.match(name), name)

    def test_post_batch47_counts_are_lossless(self):
        self.assertEqual(self.fixture["expectedMovedToContextCount"], 3)
        self.assertEqual(self.fixture["expectedMovedUsageCount"], 64)
        self.assertEqual(self.fixture["expectedManualCount"], 299)
        self.assertEqual(self.fixture["expectedContextCount"], 940)
        self.assertEqual(302 - 3, 299)
        self.assertEqual(937 + 3, 940)
        self.assertEqual(299 + 940, 1239)
        self.assertEqual(self.fixture["bindingsCreatedByBatch47"], 0)

    def test_triage_only_does_not_change_recorded_bindings(self):
        checkpoint = cp.build_checkpoint(TOOLS)
        # Triage used the batch42 checkpoint; subsequent explicit reviews
        # must not be counted as bindings created by this historical batch.
        historical = [row for row in checkpoint["recordedBindings"]
                      if row["reviewFile"] <= "release_catalog_reviewed_nutrition_targets_045.v1.json"]
        self.assertEqual(len(historical), 5080)
        self.assertEqual(self.fixture["bindingsCreatedByBatch47"], 0)


if __name__ == "__main__":
    unittest.main()
