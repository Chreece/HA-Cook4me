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
    "ro": TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_ro_001.v1.json",
    "hu": TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_hu_001.v1.json",
}
EXPECTED_IDS = {
    "ro": set("""
local:ro:bb9e9c0d0f711388783f local:ro:39cbb70688726f48500b local:ro:07558615c1d31da6aa4b
local:ro:4def39e2c7f664d21b8b local:ro:1569685b9d56c8dbd631 local:ro:55fff4424dc12c7c6bde
local:ro:b2e494525aeac7b76c0c local:ro:9be8bf42e4a267259a69 local:ro:a6039eb6d1b59603d1c8
local:ro:4a3ad58f0d2df1ee971c local:ro:4a3b54d8a51e7594a176 local:ro:6278715642d598440d37
local:ro:36ba5c149cccfd931a26 local:ro:4481926b9c5de0ae8ba6 local:ro:cfb9a6223810be727f83
local:ro:7c823a5f054ff3f5372d local:ro:711803464e1ac342429b local:ro:d81b3929cf4874c5a274
local:ro:03759ff1c0ef417266a4 local:ro:60d0b352fb61fa4fb1fa local:ro:b3a04e792dbcfdf834eb
local:ro:e8d1fdf483ef634de2a1 local:ro:d048eff8a10d91da4e35 local:ro:fbf6f0892bf7018fc5fc
local:ro:46fb631a24c7397b7cae local:ro:00cc73a24816113d0647 local:ro:aa9f001b8ccbcb2ee756
local:ro:0feb6505f225742aa433 local:ro:d4b0a783239cf9aca648 local:ro:566802cb04bb052c6669
local:ro:0075e02c1b72c01c3f46 local:ro:21863c020cfbf70b464f local:ro:0b5696ad9081757a8007
local:ro:2f0b47a9fb6ba2f91464
""".split()),
    "hu": set("""
local:hu:f34409631574ecc7daaa local:hu:14945bf0cf20ed1ab55f local:hu:bd3ce2de9849709ee6f0
local:hu:a1987a0c40c7c36a1700 local:hu:e6ada440eb6a298cbef1 local:hu:72e8b0cc72bb7dd79a8d
local:hu:55ff0abb6516030d42f5 local:hu:f63b318d02fb5a775eeb local:hu:af50f410e85675337bb1
local:hu:9439e2a9afffa6103810 local:hu:cc0c6ae43c65ad30d1cc local:hu:262bc68a14c6f29c433d
local:hu:28f5b0cee03d0765872f local:hu:35f2964bd0a233571251 local:hu:ce2b830a8b8e8208f7d7
local:hu:7ad83d8e4da50f70bfa3 local:hu:390eed93917473c733d9 local:hu:4ba54ad668ed6cf2bc57
local:hu:f4dd73aa61ca40454efd local:hu:6a95875117deaca96011 local:hu:cb411bff8c8d36016fa2
local:hu:beda4680c8507c495388 local:hu:457beb95f3e1921ac6ce local:hu:a3d040fce05b96746de5
local:hu:728c2e4538ecbbf66272 local:hu:4220d05bc2f5fda5dfe2 local:hu:a46de12f10887537c0e1
local:hu:7ee53fc3e6db568ab299 local:hu:ce92942db9bb107dbcc2 local:hu:732a6d21190c4cee4b05
local:hu:1f3533d76d5e1719d0c1 local:hu:4e9d936a79c24345656d local:hu:3a91dfb649c140111336
local:hu:20d5487f243af17b6282 local:hu:81b3c1a0eccc53231a9d local:hu:d5311662ffeb31be7557
""".split()),
}


class Capture3RomanianHungarianSemanticReviewsV60Tests(unittest.TestCase):
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

    def test_reconciliation_proves_all_70_exact_rows_reviewed(self):
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
                "sourceLocalSemanticReviewCount": 70,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": counts,
            },
            "sourceLocalSemanticReview": rows,
            "providerCanonicalEnglishReview": [],
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 70)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
