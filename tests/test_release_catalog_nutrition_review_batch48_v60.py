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

FIXTURE = ROOT / "tests/fixtures/nutrition-batch48-generic-seafood-triage-v60.json"
FIXTURE_SHA = "2fd30820e024c8291ce1cc6152b59176c08ff2da72fb3d008903492b30b41b80"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"


class Batch48GenericSeafoodTriageTests(unittest.TestCase):
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
                *classifier.identity_ambiguities.RULES,
            ),
        )

    def test_fixture_pins_batch47_baseline_and_exact_two_rows(self):
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(self.fixture["baseRecordedReviewTargetCount"], 5080)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1239)
        self.assertEqual(self.fixture["manualBeforeCount"], 299)
        self.assertEqual(self.fixture["contextBeforeCount"], 940)
        self.assertEqual(len(self.selected), 2)
        self.assertEqual(sum(row["usageCountSum"] for row in self.selected), 31)
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)

    def test_only_bare_seafood_moves_to_context(self):
        matched, manual, context = self.partition(self.selected)
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual(len(context), 2)
        self.assertTrue(all(row["classification"] == "C-generic-seafood-identity-ambiguous" for row in context))
        self.assertEqual(sum(row["usageCountSum"] for row in context), 31)

    def test_named_single_food_controls_remain_manual(self):
        matched, manual, context = self.partition(self.controls)
        self.assertEqual(matched, [])
        self.assertEqual(context, [])
        self.assertEqual({row["canonicalEnglishName"] for row in manual}, {"Poultry fillet", "Broad bean", "Juniper berries"})

    def test_pattern_is_exact(self):
        self.assertTrue(classifier.identity_ambiguities.GENERIC_SEAFOOD.pattern.startswith("^"))
        self.assertTrue(classifier.identity_ambiguities.GENERIC_SEAFOOD.pattern.endswith("$"))
        for name in ("Frozen seafood", "Seafood mix", "Shrimp and seafood", "Seafood marinara mix"):
            self.assertIsNone(classifier.identity_ambiguities.GENERIC_SEAFOOD.match(name), name)

    def test_post_batch48_counts_are_lossless(self):
        self.assertEqual(self.fixture["expectedMovedToContextCount"], 2)
        self.assertEqual(self.fixture["expectedMovedUsageCount"], 31)
        self.assertEqual(self.fixture["expectedManualCount"], 297)
        self.assertEqual(self.fixture["expectedContextCount"], 942)
        self.assertEqual(297 + 942, 1239)
        self.assertEqual(self.fixture["bindingsCreatedByBatch48"], 0)

    def test_triage_only_does_not_change_recorded_bindings(self):
        checkpoint = cp.build_checkpoint(TOOLS)
        # Triage used the batch42 checkpoint; subsequent explicit reviews
        # must not be counted as bindings created by this historical batch.
        historical = [row for row in checkpoint["recordedBindings"]
                      if row["reviewFile"] <= "release_catalog_reviewed_nutrition_targets_045.v1.json"]
        self.assertEqual(len(historical), 5080)
        self.assertEqual(self.fixture["bindingsCreatedByBatch48"], 0)


if __name__ == "__main__":
    unittest.main()
