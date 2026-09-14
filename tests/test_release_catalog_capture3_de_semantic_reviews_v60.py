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

REVIEW_PATH = TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_de_001.v1.json"

CAPTURE3_GERMAN = {
    "local:de:34bfc404cdcfde1129d7": ("Maisstärke", "Cornstarch"),
    "local:de:0dcb6e0edd3eb9c8d2da": ("Hühnerbrühe", "Chicken stock"),
    "local:de:616f4419616f5ccf84d8": ("Tomatenmark", "Tomato paste"),
    "local:de:709b2e7b5b59e68f2334": ("Maismehl", "Corn flour"),
    "local:de:2fb7dd46cc262f102fc7": ("Orangenmarmelade", "Orange marmalade"),
    "local:de:6387efd680d9477bcc28": ("Semmelbrösel", "Breadcrumbs"),
    "local:de:b2bf1c3145ed8de217e4": ("Wasabi", "Wasabi"),
    "local:de:e53f4327506a1cc9c627": ("Edamame", "Edamame"),
    "local:de:10ea4388071c8ed0ae8e": ("Eisenkraut", "Verbena"),
    "local:de:64a4ca1464888b04523b": ("Erdnüsse", "Peanuts"),
    "local:de:c2695c399014b558fdf1": ("Lorbeer", "Bay leaf"),
    "local:de:2bcaec8f6846382e62fe": ("Rinderfilet", "Beef fillet"),
    "local:de:77d3681b8deddfb01904": ("Schokolade", "Chocolate"),
    "local:de:12dfe6179072ce679f67": ("Sesamsaat", "Sesame seeds"),
    "local:de:02f07d928317705ca949": ("Speisestärke", "Starch"),
    "local:de:acc4a68f2b8b8f9c6a7e": ("Vollkornmehl", "Wholemeal flour"),
    "local:de:a2e85077de653fcafd8f": ("Wurstbrät", "Sausage meat"),
    "local:de:6c52c9abdae7eafc9ca3": ("Gemüsebrühe", "Vegetable stock"),
    "local:de:36f12431ac4b5e440663": ("Salz", "Salt"),
}


class Capture3GermanSemanticReviewsV60Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        cls.items = cls.review["items"]

    def test_review_batch_is_exactly_the_19_captured_german_identities(self):
        self.assertEqual(len(self.items), 19)
        actual = {
            semantics.source_local_ingredient_id(row["language"], row["source"]): (
                row["source"],
                row["english"],
            )
            for row in self.items
        }
        self.assertEqual(actual, CAPTURE3_GERMAN)

    def test_reviews_are_food_only_and_never_assign_provider_identity(self):
        self.assertEqual(self.review["kind"], "cook4me-reviewed-keyless-ingredient-semantics")
        policy = self.review["policy"]
        self.assertFalse(policy["providerIdentityAssigned"])
        self.assertTrue(policy["exactSourceLabelOnly"])
        self.assertTrue(policy["manualReview"])
        self.assertEqual(policy["catalogVersion"], "2026-09-11-v60-capture3")

        for row in self.items:
            self.assertEqual(row["language"], "de")
            self.assertEqual(row["classification"], "food")
            self.assertEqual(row["confidence"], "high")
            self.assertNotIn("foodKey", row)
            self.assertNotIn("providerIngredientId", row)
            self.assertNotIn("ingredientId", row)

    def test_compiler_preserves_exact_german_source_identities(self):
        compiled = semantics.compile_semantic_concepts([(REVIEW_PATH.name, self.review)])
        self.assertEqual(compiled["summary"]["reviewedSourceLabels"], 19)
        self.assertEqual(set(compiled["sourceIdentityToConcept"]), set(CAPTURE3_GERMAN))
        concepts = {row["conceptId"]: row for row in compiled["concepts"]}
        for ident, (_, english) in CAPTURE3_GERMAN.items():
            concept = concepts[compiled["sourceIdentityToConcept"][ident]]
            self.assertEqual(concept["canonicalEnglish"], english)
            self.assertEqual(concept["classification"], "food")
            self.assertFalse(concept["providerIdentityAssigned"])

    def test_reconciliation_now_proves_all_19_exact_german_rows_reviewed(self):
        queue_rows = [
            {
                "ingredientId": ident,
                "language": "de",
                "source": source,
                "usageCount": 1,
                "examples": [],
            }
            for ident, (source, _) in CAPTURE3_GERMAN.items()
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
                "sourceLocalSemanticReviewCount": 19,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": {"de": 19},
            },
            "sourceLocalSemanticReview": queue_rows,
            "providerCanonicalEnglishReview": [],
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 19)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
