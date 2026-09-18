from __future__ import annotations

import gzip
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import classify_nutrition_review_queue_v60 as classifier  # noqa: E402
import nutrition_review_holds_v60 as holds  # noqa: E402
import prepare_nutrition_review_worklist_v60 as worklist  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as cp  # noqa: E402

BATCH35_FIXTURE = ROOT / "tests/fixtures/nutrition-batch35-evidence-requirements-v60.json.gz"
BATCH42_FIXTURE = ROOT / "tests/fixtures/nutrition-batch42-retained-reference-v60.json"
LEDGER = TOOLS / "release_catalog_nutrition_review_blockers.v1.json"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"

MOVED_IDS = {
    "concept:food:752e7ef0a5932d3a3c38",  # Pepper
    "concept:food:d475265f55cce204989d",  # Rice
    "concept:food:030f6d6ec1602b0758a1",  # Crème fraîche
    "M_FOOD_421",  # Rice
    "M_FOOD_150",  # Crème fraîche
    "concept:food:b36c631ec3d95bb496f7",  # Potato starch
    "M_FOOD_151",  # Thick crème fraîche
    "M_FOOD_189",  # Potato starch
    "concept:food:56ea6f33755e6cf32d8c",  # Chopped fresh tarragon
}

RECORDED_LATER_IDS = {
    "M_FOOD_192",  # Leaf gelatine
    "M_FOOD_305",  # Mascarpone
    "M_FOOD_308",  # Mint
    "concept:food:60adcbf73d9b372850eb",  # Gelatin sheets
    "concept:food:859fd9586f3f9edd14e3",  # Pomegranate seeds
    "concept:food:89315ece4b2889a4fbf6",  # Mascarpone cheese
    "concept:food:d8e84cd30d293efc721a",  # Mint
    "concept:food:e37ffa71487bdb06c7aa",  # Mascarpone
    "concept:food:fec88107bfd3514d5822",  # Grated coconut
}


class Batch43EvidenceRequirementTriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch35 = json.loads(gzip.decompress(BATCH35_FIXTURE.read_bytes()))
        cls.batch42 = json.loads(BATCH42_FIXTURE.read_text(encoding="utf-8"))
        cls.ledger, _ledger_sha = cp._read(LEDGER)
        cls.evidence_projection = {
            **cls.batch35["evidenceHeader"],
            "items": cls.batch35["targets"] + cls.batch35["additionalSourceRows"],
        }
        cls.requirements = worklist.validate_ledger(
            cls.ledger, cls.evidence_projection, EVIDENCE_SHA
        )
        cls.checkpoint = cp.build_checkpoint(TOOLS)
        cls.recorded_ids = {
            row["reviewTargetId"] for row in cls.checkpoint["recordedBindings"]
            if row["reviewFile"] <= "release_catalog_reviewed_nutrition_targets_045.v1.json"
        }
        cls.held_ids = set(holds.load_holds()["targets"])
        cls.active_ids = set(cls.requirements) - cls.recorded_ids - cls.held_ids
        cls.active_rows = [
            row for row in cls.batch35["targets"]
            if row["reviewTargetId"] in cls.active_ids
        ]
        _rules_doc, cls.compiled = classifier._load_rules()

    def test_original_28_requirement_ledger_is_still_exact_and_non_approving(self):
        self.assertEqual(self.batch35["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(len(self.requirements), 28)
        self.assertFalse(self.ledger["policy"]["bindingsApproved"])
        self.assertFalse(self.ledger["policy"]["deferredTargetsCountAsComplete"])
        self.assertFalse(self.ledger["policy"]["lexicalSearchIsIdentityProof"])
        self.assertFalse(self.ledger["policy"]["providerIdentityInference"])
        for row in self.requirements.values():
            self.assertEqual(row["disposition"], "deferred-no-binding")
            self.assertNotIn("fdcId", row)
            self.assertNotIn("candidateEvidenceRank", row)

    def test_nine_requirements_were_recorded_later_and_nineteen_remain_active(self):
        self.assertEqual(set(self.requirements) & self.recorded_ids, RECORDED_LATER_IDS)
        self.assertFalse(set(self.requirements) & self.held_ids)
        self.assertEqual(len(self.active_ids), 19)
        self.assertEqual(len(self.active_rows), 19)
        self.assertEqual(len(self.recorded_ids), 5080)

    def test_exactly_nine_active_requirements_were_in_the_manual_lane(self):
        matched, manual, context = classifier._partition_remaining(
            self.active_rows,
            self.compiled,
        )
        self.assertEqual(matched, [])
        self.assertEqual({row["reviewTargetId"] for row in manual}, MOVED_IDS)
        self.assertEqual(len(manual), 9)
        self.assertEqual(len(context), 10)
        self.assertEqual(sum(row["usageCountSum"] for row in manual), 6902)

    def test_explicit_requirement_forces_all_19_active_rows_to_context(self):
        active_requirements = {
            target_id: self.requirements[target_id] for target_id in self.active_ids
        }
        matched, manual, context = classifier._partition_remaining(
            self.active_rows,
            self.compiled,
            evidence_requirements=active_requirements,
        )
        self.assertEqual(matched, [])
        self.assertEqual(manual, [])
        self.assertEqual(len(context), 19)
        self.assertEqual(
            {row["reviewTargetId"] for row in context}, self.active_ids
        )
        self.assertTrue(all(
            row["classification"] == "C-explicit-evidence-requirement"
            for row in context
        ))
        for row in context:
            self.assertEqual(
                row["evidenceRequirementReasonCode"],
                self.requirements[row["reviewTargetId"]]["reasonCode"],
            )

    def test_post_batch43_counts_reconcile_without_creating_bindings(self):
        self.assertEqual(self.batch42["expectedRemainingCount"], 1239)
        self.assertEqual(self.batch42["expectedManualCount"], 330)
        self.assertEqual(self.batch42["expectedContextCount"], 909)
        self.assertEqual(self.batch42["bindingsApprovedByClassifier"], 0)
        self.assertEqual(self.batch42["expectedManualCount"] - len(MOVED_IDS), 321)
        self.assertEqual(self.batch42["expectedContextCount"] + len(MOVED_IDS), 918)
        self.assertEqual(321 + 918, self.batch42["expectedRemainingCount"])

    def test_high_impact_deferred_names_are_now_context_by_exact_target_id(self):
        moved_names = {
            row["canonicalEnglishName"]
            for row in self.active_rows
            if row["reviewTargetId"] in MOVED_IDS
        }
        self.assertEqual(
            moved_names,
            {
                "Pepper",
                "Rice",
                "Crème fraîche",
                "Thick crème fraîche",
                "Potato starch",
                "Chopped fresh tarragon",
            },
        )


if __name__ == "__main__":
    unittest.main()
