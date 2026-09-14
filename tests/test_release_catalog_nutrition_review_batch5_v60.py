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
    TOOLS / "release_catalog_reviewed_nutrition_targets_005.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_005b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_005c.v1.json",
)
EXPECTED_FILE_DIGESTS = (
    "a59ceb4424b92e50017565d588a1fde214fda858f38363d99a7be9e169326971",
    "0446506034deb4eecb75b3c5cf95ef6f00aed28406650b45d3d35d81c9946bd4",
    "d9ded52aea624aea509a6d31e9a9bf6d1883ce92af28deb2cec8c64950bb9e9a",
)
EXPECTED_COMBINED_DIGEST = "30dfd8b88002cbebe3c9355feae4e0c8d16603ccea3bac6702de0c8ed79bc789"
EXPECTED_REFERENCE_MANIFEST_SHA256 = "e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d"
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


class NutritionTargetReviewBatch5V60Tests(unittest.TestCase):
    def test_all_three_files_pin_the_fndds_extended_fail_closed_contract(self):
        for path in FILES:
            with self.subTest(path=path.name):
                value = _load(path)
                self.assertEqual(value["kind"], "cook4me-reviewed-nutrition-target-source")
                self.assertEqual(value["catalogVersion"], "2026-09-11-v60-capture3")
                self.assertEqual(value["referenceManifestSha256"], EXPECTED_REFERENCE_MANIFEST_SHA256)
                self.assertEqual(value["evidenceKind"], "cook4me-fdc-review-target-candidate-evidence-offline-v60")
                self.assertEqual(value["policy"], EXPECTED_POLICY)
                self.assertEqual(value["selectionMethod"], "explicit-semantic-review")

    def test_exact_sixty_batch5_targets_are_locked_and_disjoint(self):
        combined: list[dict] = []
        for path, expected_digest in zip(FILES, EXPECTED_FILE_DIGESTS, strict=True):
            items = _load(path)["items"]
            self.assertEqual(len(items), 20)
            self.assertEqual(_digest(items), expected_digest)
            combined.extend(items)

        self.assertEqual(len(combined), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in combined}), 60)
        self.assertEqual(_digest(combined), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in combined), 260527)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in combined), 44)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in combined), 11)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in combined), 5)

        earlier_paths = [
            TOOLS / "release_catalog_reviewed_nutrition_targets_001.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_002.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_002b.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_002c.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_003.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_003b.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_003c.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_004.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_004b.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_004c.v1.json",
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
            self.assertIn(row["fdcDataType"], {"Foundation", "SR Legacy", "Survey (FNDDS)"})
            self.assertEqual(int(row["candidateEvidenceRank"]), 1)
            self.assertTrue(str(row["fdcDescription"]).strip())
            self.assertGreater(int(row["usageCountAtReview"]), 0)

    def test_nfs_bindings_are_explicit_same_specificity_review_decisions(self):
        combined = [row for path in FILES for row in _load(path)["items"]]
        nfs_rows = [row for row in combined if str(row["fdcDescription"]).endswith(", NFS")]
        self.assertGreaterEqual(len(nfs_rows), 1)
        for row in nfs_rows:
            with self.subTest(target_id=row["reviewTargetId"]):
                self.assertEqual(row["fdcDataType"], "Survey (FNDDS)")
                self.assertTrue(str(row.get("notes") or "").strip())

    def test_loader_consumes_all_sixty_bindings_without_identity_rewrite(self):
        combined = [row for path in FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        for row in combined:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
