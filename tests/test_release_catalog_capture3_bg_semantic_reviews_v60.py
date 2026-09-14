from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import compile_release_catalog_semantics_v60 as semantics  # noqa: E402
import reconcile_release_catalog_review_queues_v60 as reconcile  # noqa: E402

REVIEW_PATH = TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_bg_001.v1.json"
EXPECTED_ID_DIGEST = "a756ea8a588b51ab47307eda2b3a27d4c3e4ddc8cb85c1e01a7c99a678dfffbf"
EXPECTED_MEDIUM = {
    "Телешки бульон",
    "Телешка кайма",
    "Сметана",
    "Телешко",
    "Телешко филе",
}


class Capture3BulgarianSemanticReviewsV60Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        cls.items = cls.review["items"]

    def test_exact_capture3_identities_are_preserved(self):
        actual = sorted(
            semantics.source_local_ingredient_id(row["language"], row["source"])
            for row in self.items
        )
        digest = hashlib.sha256("\n".join(actual).encode()).hexdigest()
        self.assertEqual(len(actual), 144)
        self.assertEqual(digest, EXPECTED_ID_DIGEST)

    def test_reviews_are_food_and_never_assign_provider_identity(self):
        policy = self.review["policy"]
        self.assertFalse(policy["providerIdentityAssigned"])
        self.assertTrue(policy["exactSourceLabelOnly"])
        self.assertTrue(policy["manualReview"])
        self.assertEqual(policy["catalogVersion"], "2026-09-11-v60-capture3")
        for row in self.items:
            self.assertEqual(row["language"], "bg")
            self.assertTrue(row["english"])
            self.assertEqual(row["classification"], "food")
            self.assertIn(row["confidence"], {"high", "medium"})
            self.assertNotIn("foodKey", row)
            self.assertNotIn("providerIngredientId", row)
            self.assertNotIn("ingredientId", row)

    def test_ambiguous_bulgarian_terms_remain_conservative(self):
        medium = {row["source"] for row in self.items if row["confidence"] == "medium"}
        self.assertEqual(medium, EXPECTED_MEDIUM)

    def test_reconciliation_proves_all_144_exact_rows_reviewed(self):
        rows = [
            {
                "ingredientId": semantics.source_local_ingredient_id("bg", row["source"]),
                "language": "bg",
                "source": row["source"],
                "usageCount": 1,
                "examples": [],
            }
            for row in self.items
        ]
        queue = {
            "schemaVersion": 1,
            "kind": "cook4me-v60-review-queues",
            "catalogVersion": "2026-09-11-v60-capture3",
            "policy": {
                "offlineOnly": True,
                "capturedCatalogMutated": False,
                "providerIdentityInferred": False,
                "sourceLocalIdentityRecomputed": True,
                "exactSourceLabelOnly": True,
                "translationsGenerated": False,
                "classificationsGenerated": False,
                "reviewDecisionsGenerated": False,
                "exampleLimit": 3,
            },
            "summary": {
                "sourceLocalSemanticReviewCount": 144,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": {"bg": 144},
            },
            "sourceLocalSemanticReview": rows,
            "providerCanonicalEnglishReview": [],
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 144)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)
        self.assertEqual(value["summary"]["needsProviderCanonicalEnglishReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
