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
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as cp  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/nutrition-batch42-guinea-fowl-evidence-v60.json"
REVIEW = TOOLS / "release_catalog_reviewed_nutrition_targets_045.v1.json"
FIXTURE_SHA = "d88cde9d3d040105c521be803abc6991007508ea324d7c825fa9c72d06b93ce2"
REVIEW_SHA = "ae0d371cec1f8f3f4ac81dd0805a8e949fbbda611227bc1312e9583772f4ce9c"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"
REFERENCE_MANIFEST_SHA = "e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d"


class Batch42GuineaFowlReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.review = json.loads(REVIEW.read_text(encoding="utf-8"))
        cls.target = cls.fixture["target"]
        cls.review_row = cls.review["items"][0]

    def test_retained_evidence_is_exact_and_non_selecting(self):
        self.assertEqual(hashlib.sha256(FIXTURE.read_bytes()).hexdigest(), FIXTURE_SHA)
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        self.assertEqual(self.fixture["referenceManifestSha256"], REFERENCE_MANIFEST_SHA)
        self.assertEqual(self.fixture["kind"], "cook4me-batch42-guinea-fowl-retained-evidence-v60")
        self.assertTrue(self.fixture["policy"]["retainedEvidenceOnly"])
        self.assertFalse(self.fixture["policy"]["candidateRankIsIdentityProof"])
        self.assertFalse(self.fixture["policy"]["selectionPerformedByFixture"])
        self.assertFalse(self.target["selectionPerformed"])
        self.assertTrue(self.target["needsManualExactIdReview"])

    def test_guinea_fowl_target_retains_both_exact_candidates(self):
        self.assertEqual(self.target["reviewTargetId"], "M_FOOD_379")
        self.assertEqual(self.target["reviewTargetKind"], "provider-identity")
        self.assertEqual(self.target["canonicalEnglishName"], "Guinea fowl")
        self.assertEqual(self.target["usageCountSum"], 2)
        candidates = self.target["candidates"]
        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            [(c["localEvidenceRank"], c["fdcId"], c["description"]) for c in candidates],
            [
                (1, 174471, "Guinea hen, meat only, raw"),
                (2, 172416, "Guinea hen, meat and skin, raw"),
            ],
        )
        self.assertEqual(candidates[1]["scientificName"], "Numida meleagris")
        self.assertEqual(candidates[1]["dataType"], "SR Legacy")

    def test_review_selects_whole_bird_candidate_not_search_rank(self):
        self.assertEqual(hashlib.sha256(REVIEW.read_bytes()).hexdigest(), REVIEW_SHA)
        self.assertEqual(self.review["referenceManifestSha256"], REFERENCE_MANIFEST_SHA)
        self.assertEqual(self.review["selectionMethod"], "explicit-semantic-review")
        self.assertFalse(self.review["policy"]["searchResultAutoAccepted"])
        self.assertFalse(self.review["policy"]["candidateSearchIsIdentityProof"])
        self.assertEqual(self.review_row["reviewTargetId"], "M_FOOD_379")
        self.assertEqual(self.review_row["canonicalEnglishName"], "Guinea fowl")
        self.assertEqual(self.review_row["fdcId"], 172416)
        self.assertEqual(self.review_row["fdcDescription"], "Guinea hen, meat and skin, raw")
        self.assertEqual(self.review_row["fdcDataType"], "SR Legacy")
        self.assertEqual(self.review_row["candidateEvidenceRank"], 2)
        self.assertEqual(self.review_row["usageCountAtReview"], 2)
        self.assertEqual(self.review_row["confidence"], "high")
        self.assertIn("Rank 1 is the narrower meat-only record", self.review_row["notes"])
        self.assertIn("Numida meleagris", self.review_row["notes"])
        self.assertIn("Candidate ranking is a locator, not identity proof", self.review_row["notes"])

    def test_existing_unqualified_quail_review_proves_whole_bird_convention(self):
        reviews = resolver.load_reviews(TOOLS)
        quail = reviews["M_FOOD_70"]
        guinea = reviews["M_FOOD_379"]
        self.assertEqual(quail["canonicalEnglishName"], "Quail")
        self.assertEqual(quail["fdcDescription"], "Quail, meat and skin, raw")
        self.assertEqual(guinea["fdcId"], 172416)
        self.assertEqual(guinea["fdcDescription"], "Guinea hen, meat and skin, raw")
        self.assertEqual(guinea["reviewFile"], REVIEW.name)

    def test_review_is_destination_specific_not_bulk_rule_expansion(self):
        _rules_doc, compiled = classifier._load_rules()
        self.assertEqual(classifier._matches("Guinea fowl", compiled), [])
        self.assertNotIn("bulkFamilyRuleId", self.review_row)
        self.assertNotIn("bulkFamilyTier", self.review_row)

    def test_checkpoint_advances_by_one_review_target(self):
        checkpoint = cp.build_checkpoint(TOOLS)
        self.assertEqual(checkpoint["summary"]["recordedReviewTargetCount"], 5072)
        self.assertEqual(checkpoint["summary"]["reviewFileCount"], 261)
        rows = [row for row in checkpoint["recordedBindings"] if row["reviewTargetId"] == "M_FOOD_379"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["fdcId"], 172416)
        self.assertEqual(rows[0]["reviewFile"], REVIEW.name)


if __name__ == "__main__":
    unittest.main()
