from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import activate_post_activation_reviewed_nutrition_v60 as activation  # noqa: E402


class _Index:
    manifest_sha256 = "a" * 64


class PostActivationNutritionActivationTests(unittest.TestCase):
    def _catalog(self):
        return {
            "schemaVersion": 1,
            "catalogVersion": "test-v60",
            "complete": True,
            "recipes": [{"variants": [{}]}],
            "ingredients": [{}],
            "source": {
                "runtimeCatalogCompacted": True,
                "runtimeRecipeNutritionOnDemand": True,
                "semanticCoverageComplete": True,
                "reviewedNutritionRequiredCount": 10,
                "reviewedNutritionResolvedCount": 8,
                "failedDetailCount": 0,
                "detailNotFoundCount": 2,
                "reviewedNutritionReferenceManifestSha256": "b" * 64,
                "reviewedNutritionReferenceDatasets": [
                    {"dataType": "Foundation", "releaseDate": "old", "jsonSha256": "c" * 64}
                ],
            },
        }

    def _prepared(self):
        return (
            {"tasks": []},
            {"activatedPendingNutritionCount": 2},
            {"targets": []},
            {"activatedReviewTargetCount": 2},
        )

    def _pending(self):
        return {
            "summary": {
                "resolvedNowReviewTargets": 1,
                "resolvedNowIdentities": 1,
                "alreadyResolvedIdentities": 0,
                "pendingReviewTargetCount": 1,
                "pendingIdentityCount": 1,
                "networkRequestsPerformed": False,
                "referenceManifestSha256": "a" * 64,
            },
            "pending": [{}],
        }

    def _after(self):
        value = deepcopy(self._catalog())
        value["source"].update(
            {
                "reviewedNutritionResolvedCount": 9,
                "reviewedNutritionRequiredCount": 10,
                "reviewedNutritionRejectedEmbeddedCount": 0,
                "reviewedNutritionReferenceManifestSha256": "a" * 64,
                "reviewedNutritionReferenceDatasets": [
                    {"dataType": "SR Legacy", "releaseDate": "new", "jsonSha256": "d" * 64}
                ],
            }
        )
        return value

    def test_delta_activation_preserves_identity_counts_and_reference_receipts(self):
        with (
            patch.object(activation.adapter, "prepare", return_value=self._prepared()),
            patch.object(activation.target_resolver, "load_reviews", return_value={"target": {}}),
            patch.object(
                activation.offline,
                "resolve_offline",
                return_value=({"new-id": {"profile": True}}, self._pending()),
            ),
            patch.object(activation.builder, "apply_reviewed_nutrition", return_value=self._after()),
            patch.object(
                activation.compactor,
                "compact",
                return_value=(self._after(), {"networkRequestsPerformed": False}),
            ),
        ):
            result, summary, cache, pending = activation.activate_catalog(
                self._catalog(),
                review_root=TOOLS,
                index=_Index(),
                source_catalog_sha256="e" * 64,
            )
        self.assertEqual(summary["newlyResolvedIdentityCount"], 1)
        self.assertEqual(summary["reviewedNutritionResolvedCountAfter"], 9)
        self.assertEqual(summary["pendingIdentityCountAfter"], 1)
        self.assertEqual(len(cache), 1)
        self.assertEqual(pending["summary"]["pendingIdentityCount"], 1)
        source = result["source"]
        self.assertEqual(
            source["reviewedNutritionReferenceManifestSha256s"],
            ["a" * 64, "b" * 64],
        )
        self.assertEqual(len(source["reviewedNutritionReferenceDatasets"]), 2)
        self.assertTrue(source["postActivationNutritionOverlayApplied"])
        self.assertFalse(source["postActivationNutritionOverlayNetworkRequestsPerformed"])

    def test_resolved_count_must_equal_explicit_delta(self):
        bad_after = self._after()
        bad_after["source"]["reviewedNutritionResolvedCount"] = 8
        with (
            patch.object(activation.adapter, "prepare", return_value=self._prepared()),
            patch.object(activation.target_resolver, "load_reviews", return_value={"target": {}}),
            patch.object(
                activation.offline,
                "resolve_offline",
                return_value=({"new-id": {"profile": True}}, self._pending()),
            ),
            patch.object(activation.builder, "apply_reviewed_nutrition", return_value=bad_after),
        ):
            with self.assertRaisesRegex(RuntimeError, "resolved-count delta"):
                activation.activate_catalog(
                    self._catalog(), review_root=TOOLS, index=_Index()
                )

    def test_reference_receipt_merge_is_idempotent(self):
        before = self._catalog()["source"]
        after = {
            "reviewedNutritionReferenceManifestSha256s": ["b" * 64, "a" * 64],
            "reviewedNutritionReferenceDatasets": [
                {"dataType": "Foundation", "releaseDate": "old", "jsonSha256": "c" * 64},
            ],
        }
        activation.merge_reference_receipts(before, after)
        self.assertEqual(after["reviewedNutritionReferenceManifestSha256s"], ["a" * 64, "b" * 64])
        self.assertEqual(len(after["reviewedNutritionReferenceDatasets"]), 1)


if __name__ == "__main__":
    unittest.main()
