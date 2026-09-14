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

REVIEW_PATH = TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_zh_001.v1.json"
EXPECTED = {
    "local:zh:9dcf87720133a85e927a": ("水", "Water"),
    "local:zh:d71e3e7f4e06e3954894": ("醬油", "Soy sauce"),
    "local:zh:0c67589fc98c8865d02b": ("鹽", "Salt"),
    "local:zh:3135cbde3a7bd5bbf03e": ("橄欖油", "Olive oil"),
    "local:zh:3e2baebc18d0527aa4fd": ("酒", "Alcohol"),
    "local:zh:687d8f37d23fbb127e25": ("糖", "Sugar"),
    "local:zh:6e9b07030511c0e34126": ("高湯", "Stock"),
    "local:zh:35fd2a8377a0046a62ce": ("油", "Oil"),
    "local:zh:8981883cdb8a2e5602ee": ("蜂蜜", "Honey"),
    "local:zh:75aaaa3cf2719549a93d": ("麵粉", "Flour"),
    "local:zh:a65cc2310151254c51cb": ("太白粉", "Starch"),
    "local:zh:9fcf1d2a5e592d0c30b0": ("泡打粉", "Baking powder"),
    "local:zh:aece74ce7f6be4789865": ("牛奶", "Milk"),
    "local:zh:f68af058faf6dfe33f4d": ("薑", "Ginger"),
    "local:zh:cd36cebc59d18c2f16fe": ("魚露", "Fish sauce"),
    "local:zh:0d62f2e266ecd72c7da3": ("白米", "White rice"),
    "local:zh:54c602fe5629998c17b2": ("醋", "Vinegar"),
    "local:zh:e2d91464d28f52624fc6": ("乾芡實", "Dried fox nuts"),
    "local:zh:28180842b3406d36355d": ("伍斯特醬", "Worcestershire sauce"),
    "local:zh:d2277c9892818a6b4409": ("椰奶", "Coconut milk"),
    "local:zh:8d2545874bb1404721e6": ("番茄糊", "Tomato paste"),
    "local:zh:2374771921f3dabe0064": ("百香果", "Passion fruit"),
    "local:zh:1bea50e5f4fa12ce57c1": ("筆管麵", "Penne"),
    "local:zh:d33d5ac0e4c329926dc2": ("薏仁", "Job's tears"),
    "local:zh:983e1f2d4d74a429b21c": ("蛋", "Egg"),
    "local:zh:97eb7c6c6f8ff3a6c175": ("蛋黃", "Egg yolk"),
    "local:zh:e6bbf9ca65dabaf7d8c1": ("蝦", "Shrimp"),
    "local:zh:6cc8f1aa6862b549108d": ("蠔油", "Oyster sauce"),
    "local:zh:da6d8834187d35f83da1": ("豬小腸", "Pork small intestine"),
    "local:zh:8ff80194817e9f3bbfa1": ("豬肚", "Pork stomach"),
    "local:zh:ebdfb0b842f21e3c83a7": ("迷迭香", "Rosemary"),
    "local:zh:986f55331800a9c01003": ("松子", "Pine nuts"),
    "local:zh:53dafdf5fc99773f2c1f": ("枸杞", "Goji berries"),
    "local:zh:5afc40b6ce8e277e0787": ("紅棗", "Red dates"),
}


class Capture3ChineseSemanticReviewsV60Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        cls.items = cls.review["items"]

    def test_exact_capture3_identities_and_reviewed_semantics(self):
        actual = {
            semantics.source_local_ingredient_id(row["language"], row["source"]): (
                row["source"],
                row["english"],
            )
            for row in self.items
        }
        self.assertEqual(actual, EXPECTED)

    def test_reviews_are_food_and_never_assign_provider_identity(self):
        self.assertEqual(len(self.items), 34)
        policy = self.review["policy"]
        self.assertFalse(policy["providerIdentityAssigned"])
        self.assertTrue(policy["exactSourceLabelOnly"])
        self.assertTrue(policy["manualReview"])
        self.assertEqual(policy["catalogVersion"], "2026-09-11-v60-capture3")
        for row in self.items:
            self.assertEqual(row["language"], "zh")
            self.assertEqual(row["classification"], "food")
            self.assertEqual(row["confidence"], "high")
            self.assertTrue(row["english"])
            self.assertNotIn("foodKey", row)
            self.assertNotIn("providerIngredientId", row)
            self.assertNotIn("ingredientId", row)

    def test_reconciliation_proves_all_34_exact_rows_reviewed(self):
        rows = [
            {
                "ingredientId": ident,
                "language": "zh",
                "source": source,
                "usageCount": 1,
                "examples": [],
            }
            for ident, (source, _english) in EXPECTED.items()
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
                "sourceLocalSemanticReviewCount": 34,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": {"zh": 34},
            },
            "sourceLocalSemanticReview": rows,
            "providerCanonicalEnglishReview": [],
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 34)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)
        self.assertEqual(value["summary"]["needsProviderCanonicalEnglishReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
