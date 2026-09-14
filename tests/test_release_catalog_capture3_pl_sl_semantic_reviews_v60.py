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

PL_REVIEW = TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_pl_001.v1.json"
SL_REVIEW = TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_sl_001.v1.json"

CAPTURE3 = {
    "pl": {
        "local:pl:2fb84711d1a2a66abdb7": ("Tahini", "Tahini"),
        "local:pl:da2c1a2e68f1feec767b": ("Pieprz", "Pepper"),
        "local:pl:f524a7ffb12b4b8b21c7": ("Przecier pomidorowy", "Tomato purée"),
        "local:pl:33e4e8afa5ae4e6d1102": ("Bagietka", "Baguette"),
        "local:pl:790f48b088d7eb32dea4": ("Makaron", "Pasta"),
        "local:pl:2a3f62d89d988a6bea96": ("Skrobia kukurydziana", "Cornstarch"),
        "local:pl:de413b4dd1504520b488": ("Kolendra", "Coriander"),
        "local:pl:de6c182a7bbd3274b760": ("Mieszanka nasion", "Seed mix"),
        "local:pl:dc17adc9a5021cf8111f": ("Papryka chili", "Chili pepper"),
        "local:pl:7435b79e0619c50b1a9e": ("Surimi", "Surimi"),
        "local:pl:9aaef9831975a624a107": ("Garam masala", "Garam masala"),
        "local:pl:b8606fe1a66bb9e3b975": ("Mieszanka ziół", "Mixed herbs"),
        "local:pl:ed3c64ec032cac8184aa": ("Makaron ryżowy", "Rice noodles"),
    },
    "sl": {
        "local:sl:d73cdea172b9a15daa43": ("Jušna osnova", "Stock"),
    },
}


class Capture3PolishSlovenianSemanticReviewsV60Tests(unittest.TestCase):
    def test_exact_captured_identities_and_reviewed_semantics(self):
        for language, path in (("pl", PL_REVIEW), ("sl", SL_REVIEW)):
            payload = json.loads(path.read_text(encoding="utf-8"))
            actual = {
                semantics.source_local_ingredient_id(row["language"], row["source"]): (
                    row["source"], row["english"]
                )
                for row in payload["items"]
            }
            self.assertEqual(actual, CAPTURE3[language])
            self.assertFalse(payload["policy"]["providerIdentityAssigned"])
            self.assertTrue(payload["policy"]["exactSourceLabelOnly"])
            self.assertEqual(payload["policy"]["catalogVersion"], "2026-09-11-v60-capture3")
            for row in payload["items"]:
                self.assertEqual(row["language"], language)
                self.assertEqual(row["classification"], "food")
                self.assertEqual(row["confidence"], "high")
                self.assertNotIn("foodKey", row)
                self.assertNotIn("providerIngredientId", row)
                self.assertNotIn("ingredientId", row)

    def test_reconciliation_proves_all_14_exact_rows_reviewed(self):
        rows = []
        counts = {}
        for language, values in CAPTURE3.items():
            counts[language] = len(values)
            rows.extend(
                {
                    "ingredientId": ident,
                    "language": language,
                    "source": source,
                    "usageCount": 1,
                    "examples": [],
                }
                for ident, (source, _) in values.items()
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
                "sourceLocalSemanticReviewCount": 14,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": counts,
            },
            "sourceLocalSemanticReview": rows,
            "providerCanonicalEnglishReview": [],
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 14)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
