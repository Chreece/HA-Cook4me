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

REVIEW_PATH = TOOLS / "release_catalog_reviewed_keyless_ingredients_capture3_es_001.v1.json"
CAPTURE3_SPANISH = {
    "local:es:0d7fafe3f7a7c8be2fe0": ("Agua", "Water"),
    "local:es:497f1a1f17959ac3e898": ("aceite de oliva", "Olive oil"),
    "local:es:9e4ebfb08e65e97be5d6": ("Arroz", "Rice"),
    "local:es:30eee1b699602293610e": ("leche de coco", "Coconut milk"),
    "local:es:3d78f672d7e2cde2f039": ("Mantequilla", "Butter"),
    "local:es:d8f40e4a46945e477f9a": ("Vino blanco", "White wine"),
    "local:es:fab441ba365c0ca03ca8": ("Cebolla", "Onion"),
    "local:es:87b42dcbb88aafdf61b2": ("cúrcuma", "Turmeric"),
    "local:es:f3f20386d1ecad22581d": ("Huevo", "Egg"),
    "local:es:4915c0775f121e58c481": ("Leche", "Milk"),
    "local:es:39075f19629c75b001e5": ("Zanahoria", "Carrot"),
    "local:es:24165352ffd24b17cced": ("aceite de coco", "Coconut oil"),
    "local:es:b070c75c7d8b0a68a6cd": ("Ajo", "Garlic"),
    "local:es:fecc5f1c77f33bab1de9": ("Apio", "Celery"),
    "local:es:bfdb9aa41159e8632024": ("caldo de verduras", "Vegetable stock"),
    "local:es:78684f468f52b8460091": ("Cerveza", "Beer"),
    "local:es:dbec1c1ba70a25f79894": ("garbanzos", "Chickpeas"),
    "local:es:040fea02fcc1bb5c75f0": ("Harina", "Flour"),
    "local:es:581d2e51e97ea0008bbe": ("Leche entera", "Whole milk"),
    "local:es:5473e1ef5e3ed1114d78": ("Lentejas", "Lentils"),
    "local:es:8fa46058b2586536b8c0": ("Lentejas verdes", "Green lentils"),
    "local:es:c7c8dc164058106f5650": ("maracuyá", "Passion fruit"),
    "local:es:7aa362ccad3a55fc1117": ("Perejil", "Parsley"),
    "local:es:2571da9fcb761695bad5": ("Puerro", "Leek"),
    "local:es:e051668ed49629db13c7": ("sal", "Salt"),
    "local:es:c6ee8517c94c494d542e": ("Ternera", "Veal"),
    "local:es:72faa38fdd08bdb61b63": ("Tomillo", "Thyme"),
    "local:es:9ae8c83d93e684e8bf6f": ("vinagre de sidra", "Cider vinegar"),
    "local:es:a89d033255a3ade41bb2": ("Carne picada", "Minced meat"),
    "local:es:62bb0a41923c04c267a8": ("Hierbas provenzales", "Herbes de Provence"),
    "local:es:54efa0d3f84ce97566fc": ("Manzana", "Apple"),
    "local:es:e7ab4f067df621968bdb": ("Membrillo", "Quince"),
    "local:es:f62d091c5eb3a3a26baf": ("Azúcar", "Sugar"),
    "local:es:565c284b92a37c3ba67e": ("Carne", "Meat"),
    "local:es:f0e9d34a172600729cd1": ("Chalota", "Shallot"),
}


class Capture3SpanishSemanticReviewsV60Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
        cls.items = cls.review["items"]

    def test_review_batch_is_exactly_the_35_captured_spanish_identities(self):
        actual = {
            semantics.source_local_ingredient_id(row["language"], row["source"]): (
                row["source"], row["english"]
            )
            for row in self.items
        }
        self.assertEqual(actual, CAPTURE3_SPANISH)

    def test_reviews_are_high_confidence_food_without_provider_identity(self):
        self.assertEqual(len(self.items), 35)
        policy = self.review["policy"]
        self.assertFalse(policy["providerIdentityAssigned"])
        self.assertTrue(policy["exactSourceLabelOnly"])
        self.assertTrue(policy["manualReview"])
        self.assertEqual(policy["catalogVersion"], "2026-09-11-v60-capture3")
        for row in self.items:
            self.assertEqual(row["language"], "es")
            self.assertEqual(row["classification"], "food")
            self.assertEqual(row["confidence"], "high")
            self.assertNotIn("foodKey", row)
            self.assertNotIn("providerIngredientId", row)
            self.assertNotIn("ingredientId", row)

    def test_reconciliation_now_proves_all_35_exact_spanish_rows_reviewed(self):
        rows = [
            {"ingredientId": ident, "language": "es", "source": source, "usageCount": 1, "examples": []}
            for ident, (source, _) in CAPTURE3_SPANISH.items()
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
                "sourceLocalSemanticReviewCount": 35,
                "providerCanonicalEnglishReviewCount": 0,
                "sourceLocalByLanguage": {"es": 35}
            },
            "sourceLocalSemanticReview": rows,
            "providerCanonicalEnglishReview": []
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 35)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)


if __name__ == "__main__":
    unittest.main()
