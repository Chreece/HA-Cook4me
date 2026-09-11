from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import reconcile_release_catalog_review_queues_v60 as reconcile  # noqa: E402
import release_catalog_canonical_reviews_v60 as canonical_reviews  # noqa: E402

PROOF_PATH = ROOT / "tests" / "test_release_catalog_capture3_final_reconciliation_v60.py"
spec = importlib.util.spec_from_file_location("capture3_final_reconciliation_proof", PROOF_PATH)
proof = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(proof)


class Capture3AllReviewsCompleteV60Tests(unittest.TestCase):
    def test_all_1524_original_capture3_review_rows_are_now_exactly_reviewed(self):
        semantic_rows, counts = proof._capture3_review_rows()
        provider_rows = [
            {"ingredientId": ident, "providerKey": ident}
            for ident in sorted(proof.PROVIDER_QUEUE_IDS)
        ]
        queue = {
            "schemaVersion": 1,
            "kind": "cook4me-v60-review-queues",
            "catalogVersion": proof.CATALOG_VERSION,
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
                "sourceLocalSemanticReviewCount": 1213,
                "providerCanonicalEnglishReviewCount": 311,
                "sourceLocalByLanguage": counts,
            },
            "sourceLocalSemanticReview": semantic_rows,
            "providerCanonicalEnglishReview": provider_rows,
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["queuedSourceLocalSemanticReviewCount"], 1213)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 1213)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)
        self.assertEqual(value["summary"]["queuedProviderCanonicalEnglishReviewCount"], 311)
        self.assertEqual(value["summary"]["alreadyReviewedProviderCanonicalExactCount"], 311)
        self.assertEqual(value["summary"]["needsProviderCanonicalEnglishReviewCount"], 0)
        self.assertEqual(value["summary"]["needsSourceLocalByLanguage"], {})

    def test_review_corpora_have_exact_final_counts(self):
        provider_reviews = canonical_reviews._provider_food_reviews(TOOLS)
        self.assertEqual(len(provider_reviews), 420)
        self.assertEqual(len(proof.PROVIDER_QUEUE_IDS & set(provider_reviews)), 311)
        self.assertEqual(len(set(provider_reviews) - proof.PROVIDER_QUEUE_IDS), 109)


if __name__ == "__main__":
    unittest.main()
