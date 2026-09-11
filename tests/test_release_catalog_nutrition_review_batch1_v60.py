from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402

REVIEW = TOOLS / "release_catalog_reviewed_nutrition_targets_001.v1.json"
EXPECTED_COUNT = 60
EXPECTED_DIGEST = "212e36298efb0a0455405f81b21e01fa002c153dbfa692bc2126b5daa4feb10c"
EXPECTED_REFERENCE_MANIFEST_SHA256 = "6ec7b2207b149cce662136ea64b6c92ae73d6f7983efe12d18ecbc3b86388bd4"


def _load() -> dict:
    value = json.loads(REVIEW.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _digest(items: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in items:
        value = "\0".join(
            (
                str(row["reviewTargetId"]),
                str(row["reviewTargetKind"]),
                str(row["canonicalEnglishName"]),
                str(row["fdcId"]),
                str(row["fdcDescription"]),
                str(row["fdcDataType"]),
                str(row["candidateEvidenceRank"]),
            )
        )
        digest.update(value.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


class NutritionTargetReviewBatch1V60Tests(unittest.TestCase):
    def test_batch_policy_and_offline_evidence_are_locked(self):
        value = _load()
        self.assertEqual(value["kind"], "cook4me-reviewed-nutrition-target-source")
        self.assertEqual(value["catalogVersion"], "2026-09-11-v60-capture3")
        self.assertEqual(
            value["referenceManifestSha256"],
            EXPECTED_REFERENCE_MANIFEST_SHA256,
        )
        self.assertEqual(
            value["evidenceKind"],
            "cook4me-fdc-review-target-candidate-evidence-offline-v60",
        )
        self.assertEqual(value["selectionMethod"], "explicit-semantic-review")
        self.assertEqual(
            value["policy"],
            {
                "searchResultAutoAccepted": False,
                "exactFdcBindingRequired": True,
                "semanticConceptGroupingReviewed": True,
                "providerIdentityInference": False,
                "candidateSearchIsIdentityProof": False,
            },
        )

    def test_exact_sixty_reviewed_targets_are_locked(self):
        items = _load()["items"]
        self.assertEqual(len(items), EXPECTED_COUNT)
        self.assertEqual(len({row["reviewTargetId"] for row in items}), EXPECTED_COUNT)
        self.assertEqual(_digest(items), EXPECTED_DIGEST)

        for row in items:
            self.assertIn(
                row["reviewTargetKind"],
                {"provider-identity", "semantic-concept"},
            )
            if row["reviewTargetKind"] == "semantic-concept":
                self.assertTrue(row["reviewTargetId"].startswith("concept:food:"))
            self.assertGreater(int(row["fdcId"]), 0)
            self.assertEqual(row["confidence"], "high")
            self.assertIn(row["fdcDataType"], {"Foundation", "SR Legacy"})
            self.assertGreaterEqual(int(row["candidateEvidenceRank"]), 1)
            self.assertLessEqual(int(row["candidateEvidenceRank"]), 8)
            self.assertTrue(str(row["fdcDescription"]).strip())
            self.assertGreater(int(row["usageCountAtReview"]), 0)

    def test_loader_consumes_every_batch1_binding_without_rewriting_identity(self):
        items = _load()["items"]
        loaded = resolver.load_reviews(TOOLS)
        for row in items:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(
                loaded[target_id]["canonicalEnglishName"],
                row["canonicalEnglishName"],
            )
            self.assertEqual(
                loaded[target_id]["reviewFile"],
                REVIEW.name,
            )

    def test_selected_generic_records_are_explicit_not_search_rank_autoselection(self):
        by_name = {
            (row["reviewTargetKind"], row["canonicalEnglishName"]): row
            for row in _load()["items"]
        }
        self.assertEqual(
            by_name[("semantic-concept", "Extra virgin olive oil")]["fdcId"],
            748608,
        )
        self.assertEqual(
            by_name[("semantic-concept", "Tahini")]["fdcId"],
            168604,
        )
        self.assertEqual(
            by_name[("semantic-concept", "Orange")]["fdcId"],
            169097,
        )
        self.assertEqual(
            by_name[("semantic-concept", "Egg yolk")]["fdcId"],
            172184,
        )


if __name__ == "__main__":
    unittest.main()
