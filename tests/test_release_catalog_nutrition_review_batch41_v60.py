from __future__ import annotations

import gzip
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

FIXTURE = ROOT / "tests/fixtures/nutrition-batch41-manual-classifier-regression-v60.json.gz"
FIXTURE_SHA = "9f41226124c0cf14c076d2614cf036fa0ba6d6e824ca12b907c54240bca4b27a"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"
REFERENCE_MANIFEST_SHA = "e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d"


class Batch41ClassifierHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
        cls.moved = cls.fixture["movedRows"]
        cls.controls = cls.fixture["manualControls"]
        _rules_doc, cls.compiled = classifier._load_rules()

    def partition(self, rows):
        return classifier._partition_remaining(
            rows,
            self.compiled,
            has_candidates=lambda row: row["candidateCount"] > 0,
        )

    def test_fixture_pins_exact_evidence_and_batch40_baseline(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(self.fixture["referenceManifestSha256"], REFERENCE_MANIFEST_SHA)
        self.assertEqual(self.fixture["baseManualFamilyCandidateCount"], 416)
        self.assertEqual(self.fixture["baseContextHeavyCount"], 832)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1248)
        self.assertEqual(self.fixture["bindingsCreatedByBatch41"], 0)
        self.assertEqual(len(self.moved), 77)
        self.assertEqual(len({row["reviewTargetId"] for row in self.moved}), 77)
        self.assertEqual(len(self.controls), 8)
        self.assertEqual(len({row["canonicalEnglishName"] for row in self.controls}), 7)
        self.assertTrue(all(row["candidateCount"] > 0 for row in self.moved + self.controls))

    def test_all_77_retained_escape_rows_move_to_context(self):
        matched, manual, context = self.partition(self.moved)
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual(len(context), 77)
        self.assertEqual(sum(row["usageCountSum"] for row in context), 675)
        self.assertEqual(self.fixture["expectedMovedToContextCount"], 77)
        self.assertEqual(self.fixture["expectedManualFamilyCandidateCount"], 339)
        self.assertEqual(self.fixture["expectedContextHeavyCount"], 909)
        self.assertEqual(self.fixture["baseManualFamilyCandidateCount"] - len(context), 339)
        self.assertEqual(self.fixture["baseContextHeavyCount"] + len(context), 909)
        self.assertEqual(339 + 909, self.fixture["remainingReviewTargetCount"])

    def test_new_context_forms_are_explicitly_regressed(self):
        examples = {
            "Mixed herbs",
            "Oil, mixed with yogurt",
            "Pistachio flavoring",
            "Vanilla flavouring",
            "Earl Grey tea-flavoured water (1 tea bag for 2 people)",
            "Oil marinade from feta",
            "Starch slurry (starch:water 1:1)",
            "Purée",
            "Fruit compote",
            "Fruit coulis",
            "Fruit mousse",
            "Vinaigrette",
            "Dressing",
            "Sourdough starter",
            "Pike dumplings",
            "Beef meatballs",
            "Precooked ramen",
            "Knotted kombu, rehydrated in water",
            "Preserved lemon, diced",
            "Salted fermented shrimp",
            "Candied chestnuts for decorating",
            "Glazed chestnuts, crushed",
            "Green food coloring",
            "Beef consommé cube",
            "Herb bouquet",
            "Chestnut spread",
            "White pudding",
            "Matazeez dough",
            "Salt & pepper",
            "Herbs (thyme, rosemary, etc.)",
        }
        names = {row["canonicalEnglishName"] for row in self.moved}
        self.assertFalse(examples - names)

    def test_simple_identity_controls_remain_manual(self):
        expected = {
            "Guinea fowl",
            "Nigella seeds",
            "Parsley root",
            "Fresh sage leaves",
            "Sage leaves, thinly sliced",
            "Vanilla pod",
            "Zucchini flowers",
        }
        self.assertEqual({row["canonicalEnglishName"] for row in self.controls}, expected)
        matched, manual, context = self.partition(self.controls)
        self.assertEqual(matched, [])
        self.assertEqual(context, [])
        self.assertEqual({row["canonicalEnglishName"] for row in manual}, expected)

    def test_hardening_does_not_create_or_move_recorded_bindings(self):
        checkpoint = cp.build_checkpoint(TOOLS)
        # 5,071 is the immutable post-Batch-40 baseline. Later explicit review
        # batches are allowed to increase the global recorded count.
        self.assertGreaterEqual(checkpoint["summary"]["recordedReviewTargetCount"], 5071)
        self.assertEqual(self.fixture["bindingsCreatedByBatch41"], 0)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1248)


if __name__ == "__main__":
    unittest.main()
