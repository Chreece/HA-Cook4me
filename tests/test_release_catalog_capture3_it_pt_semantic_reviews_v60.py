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
    "it": TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_it_001.v1.json",
    "pt": TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_pt_001.v1.json",
}
EXPECTED = {
    "it": (79, "13ae01ff29420df8ff270bed4fdc753e7c938204a61027363e01c9c3a8ce2ec7"),
    "pt": (87, "4c80a60e3ed75a3b8e9a7709bff383a46bb1294922c69ca3e08b515237da49d1"),
}


class Capture3ItalianPortugueseSemanticReviewsV60Tests(unittest.TestCase):
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
                self.assertIn(row["confidence"], {"high", "medium"})
                self.assertNotIn("foodKey", row)
                self.assertNotIn("providerIngredientId", row)
                self.assertNotIn("ingredientId", row)

    def test_only_ambiguous_portuguese_fermento_is_medium(self):
        payload = json.loads(PATHS["pt"].read_text(encoding="utf-8"))
        medium = [row for row in payload["items"] if row["confidence"] == "medium"]
        self.assertEqual(
            medium,
            [{
                "language": "pt",
                "source": "Fermento",
                "english": "Leavening agent",
                "classification": "food",
                "confidence": "medium",
            }],
        )

    def test_reconciliation_proves_all_166_exact_rows_reviewed(self):
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
                "sourceLocalSemanticReviewCount": 166,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": counts,
            },
            "sourceLocalSemanticReview": rows,
            "providerCanonicalEnglishReview": [],
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 166)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)
        self.assertEqual(value["summary"]["needsProviderCanonicalEnglishReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
