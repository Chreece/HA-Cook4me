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
FIXTURE_SHA = "57ed367ab1ed7d2ccb45374ea2cbed2f212bb7f78367e8ce065361ef1cbb7029"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"
REFERENCE_MANIFEST_SHA = "e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d"


class Batch41ClassifierHardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
        cls.rows = cls.fixture["items"]
        _rules_doc, cls.compiled = classifier._load_rules()

    def partition(self, rows):
        return classifier._partition_remaining(
            rows,
            self.compiled,
            has_candidates=lambda row: row["candidateCount"] > 0,
        )

    def test_fixture_is_exact_compact_projection_of_batch40_manual_lane(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(self.fixture["referenceManifestSha256"], REFERENCE_MANIFEST_SHA)
        self.assertEqual(self.fixture["baseManualFamilyCandidateCount"], 416)
        self.assertEqual(self.fixture["baseContextHeavyCount"], 832)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1248)
        self.assertEqual(len(self.rows), 416)
        self.assertEqual(len({row["reviewTargetId"] for row in self.rows}), 416)
        self.assertTrue(all(row["candidateCount"] > 0 for row in self.rows))

    def test_hardening_moves_exactly_77_rows_from_manual_to_context(self):
        matched, manual, context = self.partition(self.rows)
        self.assertEqual(matched, [])
        self.assertEqual(len(manual), 339)
        self.assertEqual(len(context), 77)
        self.assertEqual(sum(row["usageCountSum"] for row in context), 675)
        self.assertEqual(self.fixture["expectedManualFamilyCandidateCount"], 339)
        self.assertEqual(self.fixture["expectedContextHeavyCount"], 909)
        self.assertEqual(self.fixture["baseContextHeavyCount"] + len(context), 909)
        self.assertEqual(len(manual) + self.fixture["expectedContextHeavyCount"], 1248)

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
        by_name = {row["canonicalEnglishName"]: row for row in self.rows}
        self.assertFalse(examples - set(by_name))
        matched, manual, context = self.partition([by_name[name] for name in examples])
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual({row["canonicalEnglishName"] for row in context}, examples)

    def test_simple_identity_controls_remain_manual(self):
        controls = {
            "Guinea fowl",
            "Nigella seeds",
            "Parsley root",
            "Fresh sage leaves",
            "Sage leaves, thinly sliced",
            "Vanilla pod",
            "Zucchini flowers",
        }
        by_name = {row["canonicalEnglishName"]: row for row in self.rows}
        self.assertFalse(controls - set(by_name))
        matched, manual, context = self.partition([by_name[name] for name in controls])
        self.assertEqual(matched, [])
        self.assertEqual(context, [])
        self.assertEqual({row["canonicalEnglishName"] for row in manual}, controls)

    def test_hardening_does_not_create_or_move_recorded_bindings(self):
        checkpoint = cp.build_checkpoint(TOOLS)
        self.assertEqual(checkpoint["summary"]["recordedReviewTargetCount"], 5071)
        self.assertEqual(self.fixture["expectedMovedToContextCount"], 77)
        self.assertEqual(self.fixture["bindingsCreatedByBatch41"], 0)
        self.assertEqual(self.fixture["remainingReviewTargetCount"], 1248)


if __name__ == "__main__":
    unittest.main()
