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

PATHS = {
    "cs": TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_cs_001.v1.json",
    "sk": TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_sk_001.v1.json",
}
EXPECTED_IDS = {
    "cs": {
        "local:cs:b1b27e50c8304e58a848", "local:cs:fa0904aeaa5fa5d9b795",
        "local:cs:7725f2fb01ce05e09609", "local:cs:75423e10b715668dabdc",
        "local:cs:372297db29715c034c1a", "local:cs:752b5e2f0090da1f513d",
        "local:cs:bd07c9beb70c428e9754", "local:cs:8278cc0c0ca9e6edea63",
        "local:cs:8346635de5882c1cbea6", "local:cs:7348584b23d0e1134e54",
        "local:cs:a38e6543a5be70cc04b5", "local:cs:1cae803bd64bca8632ab",
        "local:cs:1aed78daee2f9204a23b", "local:cs:c574fd3ee85a343d06fd",
        "local:cs:8e28f4b194d4dd974977", "local:cs:26936cd4ed5bc9e50253",
        "local:cs:373ea7a8206512fad5f7", "local:cs:bd13d6f6fb1a4e2c92eb",
        "local:cs:377e0f1b4be4d19afd22", "local:cs:8379435bd16105e289b5",
        "local:cs:4b48fef92aa71ac74635", "local:cs:b8ce3af299540d9c7716",
        "local:cs:8faf4f43f751d43dd14e", "local:cs:0842890e7d594dc0b971",
        "local:cs:8242d99440f0188c8be8", "local:cs:0d7c9600a94b7d56266b",
        "local:cs:58b7f9f130d3b13e222f", "local:cs:c824d17e21aa40d26779",
        "local:cs:f75d7f60f35b8322382d", "local:cs:cecb8e097842592dff80",
        "local:cs:5a0ec327381216ce125f", "local:cs:26baf43f829eb1ed58e5",
    },
    "sk": {
        "local:sk:b75bbf547566df3ce84a", "local:sk:d1d5ca101184db8dacf6",
        "local:sk:5260872b31be013d6923", "local:sk:cd5cadda5fd1f53092a6",
        "local:sk:43cdaa5ef9503e77bf83", "local:sk:f7a8fabc063dc3f79977",
        "local:sk:2e2a3cf06817797295cc", "local:sk:0a68d5ef1e1e1111a726",
        "local:sk:1188e3245acf092e5479", "local:sk:ed075c360e55bfdde5da",
        "local:sk:48a8d6090dad98d82e7e", "local:sk:0c8dc2a3fa187b9a536b",
        "local:sk:2bf246d56f760103e5e2", "local:sk:ea1370b5d274629cdbea",
        "local:sk:6b7ccdc33b3fed699941", "local:sk:bb24b95efb257e302995",
        "local:sk:ec3ff40e1c3582be0832", "local:sk:19f221d3294a9f40dabc",
        "local:sk:aa1b91a33187b720cdc9", "local:sk:1b74d3ce08df4c2ccea7",
        "local:sk:6cb7b9b18e4a08f4b572", "local:sk:33279db2ee50921ec3d2",
        "local:sk:e69ea347cd4088124a24", "local:sk:7faff9df6693e202b665",
        "local:sk:b45164c38eb50b9e3237", "local:sk:718a329cd5754e2406f1",
        "local:sk:0103038b0b8fb371fb46", "local:sk:5f3effe7245e5ac22e5b",
        "local:sk:2d550a12e6d305265013",
    },
}


class Capture3CzechSlovakSemanticReviewsV60Tests(unittest.TestCase):
    def test_exact_capture3_identities_are_preserved(self):
        for language, path in PATHS.items():
            payload = json.loads(path.read_text(encoding="utf-8"))
            actual = {
                semantics.source_local_ingredient_id(row["language"], row["source"])
                for row in payload["items"]
            }
            self.assertEqual(actual, EXPECTED_IDS[language])

    def test_reviews_are_food_and_never_assign_provider_identity(self):
        for language, path in PATHS.items():
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertFalse(payload["policy"]["providerIdentityAssigned"])
            self.assertTrue(payload["policy"]["exactSourceLabelOnly"])
            self.assertTrue(payload["policy"]["manualReview"])
            self.assertEqual(payload["policy"]["catalogVersion"], "2026-09-11-v60-capture3")
            for row in payload["items"]:
                self.assertEqual(row["language"], language)
                self.assertTrue(row["english"])
                self.assertEqual(row["classification"], "food")
                self.assertEqual(row["confidence"], "high")
                self.assertNotIn("foodKey", row)
                self.assertNotIn("providerIngredientId", row)
                self.assertNotIn("ingredientId", row)

    def test_reconciliation_proves_all_61_exact_rows_reviewed(self):
        rows = []
        counts = {}
        for language, path in PATHS.items():
            payload = json.loads(path.read_text(encoding="utf-8"))
            counts[language] = len(payload["items"])
            rows.extend(
                {
                    "ingredientId": semantics.source_local_ingredient_id(language, row["source"]),
                    "language": language,
                    "source": row["source"],
                    "usageCount": 1,
                    "examples": [],
                }
                for row in payload["items"]
            )
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
                "sourceLocalSemanticReviewCount": 61,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": counts,
            },
            "sourceLocalSemanticReview": rows,
            "providerCanonicalEnglishReview": [],
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 61)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
