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

FILES = (
    TOOLS / "release_catalog_reviewed_nutrition_targets_002.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_002b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_002c.v1.json",
)
EXPECTED_FILE_DIGESTS = (
    "5679783635ecd073add19014e3f190fe5479e957700680104c2128c8063f0f4f",
    "736500be9a6902e81f68af14acd6032b835eeeb463028d5b677e1db85f549333",
    "92e61a22f6505bc03bd161fb2641fc8b4b85d6f7c8187212487abad201360354",
)
EXPECTED_COMBINED_DIGEST = "0355a29f9f14880665f574a1544d384bd1687f75aac686bf20ccc10688263e6a"
EXPECTED_REFERENCE_MANIFEST_SHA256 = "6ec7b2207b149cce662136ea64b6c92ae73d6f7983efe12d18ecbc3b86388bd4"
EXPECTED_POLICY = {
    "searchResultAutoAccepted": False,
    "exactFdcBindingRequired": True,
    "semanticConceptGroupingReviewed": True,
    "providerIdentityInference": False,
    "candidateSearchIsIdentityProof": False,
}


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
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


class NutritionTargetReviewBatch2V60Tests(unittest.TestCase):
    def test_all_three_review_files_share_the_same_fail_closed_evidence_contract(self):
        for path in FILES:
            with self.subTest(path=path.name):
                value = _load(path)
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
                self.assertEqual(value["policy"], EXPECTED_POLICY)
                self.assertEqual(value["selectionMethod"], "explicit-semantic-review")

    def test_exact_sixty_batch2_targets_are_locked_without_duplicates(self):
        combined: list[dict] = []
        for path, expected_digest in zip(FILES, EXPECTED_FILE_DIGESTS, strict=True):
            items = _load(path)["items"]
            self.assertEqual(len(items), 20)
            self.assertEqual(_digest(items), expected_digest)
            combined.extend(items)

        self.assertEqual(len(combined), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in combined}), 60)
        self.assertEqual(_digest(combined), EXPECTED_COMBINED_DIGEST)

        batch1 = _load(TOOLS / "release_catalog_reviewed_nutrition_targets_001.v1.json")
        batch1_ids = {row["reviewTargetId"] for row in batch1["items"]}
        self.assertFalse(batch1_ids & {row["reviewTargetId"] for row in combined})

        for row in combined:
            self.assertIn(row["reviewTargetKind"], {"provider-identity", "semantic-concept"})
            if row["reviewTargetKind"] == "semantic-concept":
                self.assertTrue(row["reviewTargetId"].startswith("concept:food:"))
            self.assertEqual(row["confidence"], "high")
            self.assertGreater(int(row["fdcId"]), 0)
            self.assertIn(row["fdcDataType"], {"Foundation", "SR Legacy"})
            self.assertGreaterEqual(int(row["candidateEvidenceRank"]), 1)
            self.assertLessEqual(int(row["candidateEvidenceRank"]), 8)
            self.assertTrue(str(row["fdcDescription"]).strip())
            self.assertGreater(int(row["usageCountAtReview"]), 0)

    def test_loader_consumes_all_sixty_exact_bindings_without_identity_rewrite(self):
        combined = [row for path in FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        for row in combined:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(
                loaded[target_id]["canonicalEnglishName"],
                row["canonicalEnglishName"],
            )

    def test_non_top_rank_choices_are_explicit_semantic_decisions(self):
        combined = [row for path in FILES for row in _load(path)["items"]]
        by_target = {row["reviewTargetId"]: row for row in combined}
        expected = {
            "concept:food:fcf16d1009cab328b7e9": (173190, 2),
            "concept:food:91d5abdcf0f9915c955a": (175179, 2),
            "concept:food:8417b5c4895bce2768f2": (172883, 3),
            "M_FOOD_146": (2685570, 2),
            "M_FOOD_252": (172184, 3),
            "M_FOOD_42": (172183, 3),
            "M_FOOD_347": (169097, 8),
        }
        for target_id, (fdc_id, rank) in expected.items():
            with self.subTest(target_id=target_id):
                row = by_target[target_id]
                self.assertEqual(int(row["fdcId"]), fdc_id)
                self.assertEqual(int(row["candidateEvidenceRank"]), rank)
                self.assertTrue(str(row.get("notes") or "").strip())


if __name__ == "__main__":
    unittest.main()
