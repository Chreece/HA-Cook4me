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
    TOOLS / "release_catalog_reviewed_nutrition_targets_003.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_003b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_003c.v1.json",
)
EXPECTED_FILE_DIGESTS = (
    "a2c902c9896fbebd5726c184bfc90f3cadffdc50e8cc245e45505bb8a9c3fb14",
    "f9117f38c5650eddd58e3642d20077d3e4a4e476ea1033eaf06d3d8f84d513f2",
    "574e568982f33a0dffdb6ad80e40b4d2cf69ea9831a0bd2a0e82ba56162a26a6",
)
EXPECTED_COMBINED_DIGEST = "f064ffd27c014cd1199033191a72b25e989ac97f50759444d58045c6ed924816"
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


class NutritionTargetReviewBatch3V60Tests(unittest.TestCase):
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

    def test_exact_sixty_batch3_targets_are_locked_and_disjoint(self):
        combined: list[dict] = []
        for path, expected_digest in zip(FILES, EXPECTED_FILE_DIGESTS, strict=True):
            items = _load(path)["items"]
            self.assertEqual(len(items), 20)
            self.assertEqual(_digest(items), expected_digest)
            combined.extend(items)

        self.assertEqual(len(combined), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in combined}), 60)
        self.assertEqual(_digest(combined), EXPECTED_COMBINED_DIGEST)

        earlier_paths = [
            TOOLS / "release_catalog_reviewed_nutrition_targets_001.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_002.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_002b.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_002c.v1.json",
        ]
        earlier_ids = {
            row["reviewTargetId"]
            for path in earlier_paths
            for row in _load(path)["items"]
        }
        self.assertFalse(earlier_ids & {row["reviewTargetId"] for row in combined})

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

    def test_lower_rank_choices_are_explicit_semantic_decisions(self):
        combined = [row for path in FILES for row in _load(path)["items"]]
        by_target = {row["reviewTargetId"]: row for row in combined}
        expected = {
            "M_FOOD_24": (171705, 4),
            "concept:food:22f990455046e2b6be61": (169599, 2),
            "M_FOOD_54": (172883, 3),
            "concept:food:d5ecd53d8c116ad40c9d": (170170, 3),
            "concept:food:0bb4e97eb071484bbe59": (2346405, 2),
            "concept:food:87b7f649cb027da90858": (172184, 6),
            "concept:food:4882b4354d294569cf65": (170000, 3),
            "M_FOOD_460": (169242, 2),
            "concept:food:36145f0730310c876de2": (170393, 2),
            "concept:food:f02290b8d03b8bb46064": (169231, 2),
        }
        for target_id, (fdc_id, rank) in expected.items():
            with self.subTest(target_id=target_id):
                row = by_target[target_id]
                self.assertEqual(int(row["fdcId"]), fdc_id)
                self.assertEqual(int(row["candidateEvidenceRank"]), rank)
                self.assertTrue(str(row.get("notes") or "").strip())


if __name__ == "__main__":
    unittest.main()
