from __future__ import annotations

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

REVIEW_PATH = TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_fr_001.v1.json"
CAPTURE3_FRENCH = {
    "local:fr:40a7d00fc677c1c336f6": ("Moelle", "Bone marrow"),
    "local:fr:540613a85e1ea0af1d11": ("Wasabi", "Wasabi"),
    "local:fr:1b169c33eea7cc7a3207": ("Fécule de maïs", "Cornstarch"),
    "local:fr:9cfaed3c418316d2e5f2": ("Riz", "Rice"),
    "local:fr:f6399a31254d9862eae2": ("Épices", "Spices"),
}


class Capture3FrenchSemanticReviewsV60Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        cls.items = cls.review["items"]

    def test_review_batch_is_exactly_the_five_captured_french_identities(self):
        actual = {
            semantics.source_local_ingredient_id(row["language"], row["source"]): (
                row["source"], row["english"]
            )
            for row in self.items
        }
        self.assertEqual(actual, CAPTURE3_FRENCH)

    def test_reviews_are_high_confidence_food_without_provider_identity(self):
        self.assertEqual(len(self.items), 5)
        self.assertFalse(self.review["policy"]["providerIdentityAssigned"])
        self.assertTrue(self.review["policy"]["exactSourceLabelOnly"])
        self.assertEqual(self.review["policy"]["catalogVersion"], "2026-09-11-v60-capture3")
        for row in self.items:
            self.assertEqual(row["language"], "fr")
            self.assertEqual(row["classification"], "food")
            self.assertEqual(row["confidence"], "high")
            self.assertNotIn("foodKey", row)
            self.assertNotIn("providerIngredientId", row)
            self.assertNotIn("ingredientId", row)

    def test_reconciliation_now_proves_all_five_exact_french_rows_reviewed(self):
        rows = [
            {"ingredientId": ident, "language": "fr", "source": source, "usageCount": 1, "examples": []}
            for ident, (source, _) in CAPTURE3_FRENCH.items()
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
                "exampleLimit": 3
            },
            "summary": {
                "sourceLocalSemanticReviewCount": 5,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": {"fr": 5}
            },
            "sourceLocalSemanticReview": rows,
            "providerCanonicalEnglishReview": []
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 5)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
