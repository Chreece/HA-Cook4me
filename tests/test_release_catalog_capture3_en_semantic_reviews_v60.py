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

REVIEW_PATH = TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_en_001.v1.json"

CAPTURE3_ENGLISH = {
    "local:en:34e83ee6bc7811a7bac0": "Chicken stock",
    "local:en:dfcd5908618553ad5d9b": "Cornflour",
    "local:en:690c49117e650454c8ef": "Tomato purée",
    "local:en:2c8b5c4b884d59b5a864": "Mixed herbs",
    "local:en:e402135452b94fa14598": "Baby corn",
    "local:en:898a07db0b4aa80fe3e6": "Fish sauce",
    "local:en:e91cbce0b1c212bb7afc": "Fish stock",
    "local:en:53223fdad9e61d7d6642": "Scallops",
    "local:en:df29c5777113c5918c5a": "Bone marrow",
    "local:en:c68d586a4e3363ad8d2b": "Brandy",
    "local:en:7a007e9b22a38dca976e": "Brown rice",
    "local:en:e5c4e6b27a55375793b6": "Chocolate spread",
    "local:en:becfb2cb2f37ed35d9d0": "Flaxseed",
    "local:en:3b76ee1a0835070d962b": "Garam masala",
    "local:en:a58e50b7351598e04303": "Lemongrass",
    "local:en:97ea64dd2fcf5a7605dc": "Noodles",
    "local:en:ba9377bfd839fb0e6612": "Parsley",
    "local:en:7bbcc6e622affdc2cc99": "Peas",
    "local:en:78d017c3859afce1720c": "Rosemary",
    "local:en:40a22ca67f4a9ffca47a": "Sweet corn",
    "local:en:b0dff35f93bc539e5067": "Wasabi",
    "local:en:1fc0680f47b6512aa7df": "Wine vinegar",
    "local:en:b624b21c2dce35ed78f3": "Yakitori sauce",
    "local:en:ace13dcaf6fead3c12b0": "Cream",
    "local:en:94cbd74d80f33ec3ddd9": "Garlic",
    "local:en:adbeb5d9fc61cdb0fb68": "Salt",
}


class Capture3EnglishSemanticReviewsV60Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        cls.items = cls.review["items"]

    def test_review_batch_is_exactly_the_26_captured_native_english_identities(self):
        self.assertEqual(len(self.items), 26)
        actual = {
            semantics.source_local_ingredient_id(row["language"], row["source"]): row["source"]
            for row in self.items
        }
        self.assertEqual(actual, CAPTURE3_ENGLISH)

    def test_native_english_semantics_are_not_translated_or_provider_inferred(self):
        self.assertEqual(self.review["kind"], "cook4me-reviewed-keyless-ingredient-semantics")
        policy = self.review["policy"]
        self.assertFalse(policy["providerIdentityAssigned"])
        self.assertTrue(policy["exactSourceLabelOnly"])
        self.assertTrue(policy["manualReview"])
        self.assertEqual(policy["catalogVersion"], "2026-09-11-v60-capture3")

        for row in self.items:
            self.assertEqual(row["language"], "en")
            self.assertEqual(row["english"], row["source"])
            self.assertEqual(row["classification"], "food")
            self.assertEqual(row["confidence"], "high")
            self.assertNotIn("foodKey", row)
            self.assertNotIn("providerIngredientId", row)
            self.assertNotIn("ingredientId", row)

    def test_compiler_preserves_exact_source_identity_and_food_intelligence(self):
        compiled = semantics.compile_semantic_concepts([(REVIEW_PATH.name, self.review)])
        self.assertEqual(compiled["summary"]["reviewedSourceLabels"], 26)
        self.assertEqual(set(compiled["sourceIdentityToConcept"]), set(CAPTURE3_ENGLISH))

        concepts = {row["conceptId"]: row for row in compiled["concepts"]}
        for ident, source in CAPTURE3_ENGLISH.items():
            concept = concepts[compiled["sourceIdentityToConcept"][ident]]
            self.assertEqual(concept["canonicalEnglish"], source)
            self.assertEqual(concept["classification"], "food")
            self.assertTrue(concept["nutritionEligible"])
            self.assertTrue(concept["dietEligible"])
            self.assertTrue(concept["allergenEligible"])
            self.assertFalse(concept["providerIdentityAssigned"])

    def test_reconciliation_now_proves_all_26_exact_capture3_english_rows_reviewed(self):
        queue_rows = [
            {
                "ingredientId": ident,
                "language": "en",
                "source": source,
                "usageCount": 1,
                "examples": [],
            }
            for ident, source in CAPTURE3_ENGLISH.items()
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
                "sourceLocalSemanticReviewCount": 26,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": {"en": 26},
            },
            "sourceLocalSemanticReview": queue_rows,
            "providerCanonicalEnglishReview": [],
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 26)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)
        self.assertEqual(value["summary"]["alreadyReviewedProviderCanonicalExactCount"], 0)
        self.assertEqual(value["summary"]["needsProviderCanonicalEnglishReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
