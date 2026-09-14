from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE = TOOLS / "prepare_post_activation_nutrition_review_targets_v60.py"
spec = importlib.util.spec_from_file_location("prepare_post_activation_nutrition_review_targets_v60_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def compacted_catalog(*, runtime_compacted: bool = True, include_review_file: bool = False):
    local = {
        "id": "local:hu:test",
        "canonicalName": "Paprika",
        "sourceLocalIdentity": True,
        "providerIdentityAssigned": False,
        "classification": "food",
        "nutritionEligible": True,
        "needsSemanticConfirmation": False,
        "conceptId": "concept:food:paprika",
        "reviewConfidence": "high",
        "sourceLanguage": "hu",
    }
    if include_review_file:
        local["semanticReviewFile"] = "release_catalog_semantic_review_example.v1.json"
    return {
        "schemaVersion": 1,
        "catalogVersion": "v-test",
        "complete": True,
        "source": {
            "semanticCoverageComplete": True,
            "runtimeCatalogCompacted": runtime_compacted,
        },
        "ingredients": [
            {
                "id": "M_FOOD_1",
                "key": "M_FOOD_1",
                "canonicalName": "Tomato",
            },
            local,
        ],
        "recipeDependencyIndex": {
            "M_FOOD_1": [0],
            "local:hu:test": [0, 1],
        },
        "recipes": [],
    }


class PostActivationNutritionReviewTargetTests(unittest.TestCase):
    def test_runtime_compacted_catalog_gets_explicit_semantic_review_receipt(self):
        queue, queue_summary, targets, target_summary = mod.prepare(compacted_catalog())
        self.assertEqual(queue_summary["pendingNutritionCount"], 2)
        self.assertEqual(target_summary["reviewTargetCount"], 2)
        self.assertEqual(target_summary["postActivationSemanticReviewReceiptCount"], 1)
        self.assertEqual(target_summary["postActivationSemanticReviewReceiptTargetCount"], 1)

        source_task = next(row for row in queue["tasks"] if row["identityKind"] == "source-local")
        self.assertIn("semanticReviewReceipt", source_task)
        self.assertTrue(source_task["semanticReviewReceipt"].startswith("runtime-catalog-semantic-review:v-test:"))

        concept = next(row for row in targets["targets"] if row["reviewTargetKind"] == "semantic-concept")
        self.assertEqual(concept["reviewTargetId"], "concept:food:paprika")
        self.assertEqual(len(concept["semanticReviewReceipts"]), 1)
        self.assertNotIn("semanticReviewFiles", concept)
        self.assertFalse(targets["policy"]["runtimeSemanticReviewReceiptIsFdcIdentityProof"])
        self.assertFalse(targets["policy"]["runtimeSemanticReviewReceiptIsNutritionBinding"])

    def test_original_review_file_is_preserved_when_present(self):
        _queue, _qs, targets, summary = mod.prepare(compacted_catalog(include_review_file=True))
        concept = next(row for row in targets["targets"] if row["reviewTargetKind"] == "semantic-concept")
        self.assertEqual(concept["semanticReviewFiles"], ["release_catalog_semantic_review_example.v1.json"])
        self.assertNotIn("semanticReviewReceipts", concept)
        self.assertEqual(summary["postActivationSemanticReviewReceiptCount"], 0)

    def test_non_compacted_catalog_cannot_use_post_activation_adapter(self):
        with self.assertRaisesRegex(RuntimeError, "runtimeCatalogCompacted=true"):
            mod.prepare(compacted_catalog(runtime_compacted=False))

    def test_missing_high_confidence_stays_fail_closed(self):
        catalog = compacted_catalog()
        catalog["ingredients"][1]["reviewConfidence"] = "medium"
        with self.assertRaisesRegex(RuntimeError, "high review confidence"):
            mod.prepare(catalog)


if __name__ == "__main__":
    unittest.main()
