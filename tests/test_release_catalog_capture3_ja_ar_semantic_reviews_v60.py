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

PATHS = {
    "ja": TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_ja_001.v1.json",
    "ar": TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_ar_001.v1.json",
}
EXPECTED = {
    "ja": (57, "5deb86a3a75f56aa6a1c9b28dcf283e0978fd9d774d7827935cdac24b6d8d9d2"),
    "ar": (74, "56285b3ca390a0fc81d5ab0ccb538685cfad66d616b8cef7ea0db31f67462a0d"),
}


class Capture3JapaneseArabicSemanticReviewsV60Tests(unittest.TestCase):
    def test_exact_capture3_identities_are_preserved(self):
        for language, path in PATHS.items():
            payload = json.loads(path.read_text(encoding="utf-8"))
            actual = sorted(
                semantics.source_local_ingredient_id(row["language"], row["source"])
                for row in payload["items"]
            )
            digest = hashlib.sha256("\n".join(actual).encode()).hexdigest()
            count, expected_digest = EXPECTED[language]
            self.assertEqual(len(actual), count)
            self.assertEqual(digest, expected_digest)

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

    def test_reconciliation_proves_all_131_exact_rows_reviewed(self):
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
                "exampleLimit": 3
            },
            "summary": {
                "sourceLocalSemanticReviewCount": 131,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": counts
            },
            "sourceLocalSemanticReview": rows,
            "providerCanonicalEnglishReview": []
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 131)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)
        self.assertEqual(value["summary"]["needsProviderCanonicalEnglishReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
