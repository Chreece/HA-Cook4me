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
    TOOLS / "release_catalog_reviewed_nutrition_targets_009.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_009b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_009c.v1.json",
)
EXPECTED_FILE_DIGESTS = ('08e82297113223d0f0eb796963b8157f47c3b163bc328079eb6909f182cc378d', '15454b1a1dd9df28e6f9919072023bcb5ccfb7318e66cd18c9ab51ea7d5f9667', 'b3c7832e68d555c0c20ea49d3620674c62f6b2f35ff939ae49c5d843ad52d410')
EXPECTED_COMBINED_DIGEST = 'dd513a7e42248916216d96b39d4e9afc11abfbd902cbffaa1d17a7f5ca98084d'
EXPECTED_REFERENCE_MANIFEST_SHA256 = 'e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d'
EXPECTED_POLICY = {
    "searchResultAutoAccepted": False,
    "exactFdcBindingRequired": True,
    "semanticConceptGroupingReviewed": True,
    "providerIdentityInference": False,
    "candidateSearchIsIdentityProof": False,
}
ALIAS_REVIEW_IDS = {'M_FOOD_23', 'concept:food:af5e6dc934a9fba93f31', 'M_FOOD_496', 'concept:food:c0c50f06834b235eb83a', 'concept:food:9fca90ea523509ef3fe0', 'M_FOOD_32', 'M_FOOD_80', 'M_FOOD_433', 'M_FOOD_497', 'M_FOOD_693', 'concept:food:ce7c1685f099dac25872', 'concept:food:a83851acf9af0da1a423', 'concept:food:60b22c4255ce8686d254', 'M_FOOD_154', 'M_FOOD_427'}
LOWER_RANK_IDS = {'concept:food:64f9ed409087c53cefd2', 'concept:food:d5f06a9e29984ffa2802', 'M_FOOD_321', 'concept:food:4f24c8ef99028921f066', 'M_FOOD_522', 'M_FOOD_325', 'M_FOOD_521', 'concept:food:251e4b7a2558d1767dd3'}


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


class NutritionTargetReviewBatch8V60Tests(unittest.TestCase):
    def test_review_files_pin_the_three_dataset_fail_closed_contract(self):
        for path in FILES:
            with self.subTest(path=path.name):
                value = _load(path)
                self.assertEqual(value["kind"], "cook4me-reviewed-nutrition-target-source")
                self.assertEqual(value["catalogVersion"], "2026-09-11-v60-capture3")
                self.assertEqual(value["referenceManifestSha256"], EXPECTED_REFERENCE_MANIFEST_SHA256)
                self.assertEqual(
                    value["evidenceKind"],
                    "cook4me-fdc-review-target-candidate-evidence-offline-v60",
                )
                self.assertEqual(value["policy"], EXPECTED_POLICY)
                self.assertEqual(value["selectionMethod"], "explicit-semantic-review")

    def test_exact_sixty_batch8_targets_are_locked_and_disjoint(self):
        combined: list[dict] = []
        for path, expected_digest in zip(FILES, EXPECTED_FILE_DIGESTS, strict=True):
            items = _load(path)["items"]
            self.assertEqual(len(items), 20)
            self.assertEqual(_digest(items), expected_digest)
            combined.extend(items)

        self.assertEqual(len(combined), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in combined}), 60)
        self.assertEqual(_digest(combined), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in combined), 32022)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in combined), 45)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in combined), 12)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in combined), 3)

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
            TOOLS / "release_catalog_reviewed_nutrition_targets_005.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_005b.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_005c.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_006.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_006b.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_006c.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_007.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_007b.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_007c.v1.json",
            TOOLS / "release_catalog_reviewed_nutrition_targets_008.v1.json",
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
            self.assertIn(
                row["fdcDataType"],
                {"Foundation", "SR Legacy", "Survey (FNDDS)"},
            )
            self.assertGreaterEqual(int(row["candidateEvidenceRank"]), 1)
            self.assertLessEqual(int(row["candidateEvidenceRank"]), 8)
            self.assertTrue(str(row["fdcDescription"]).strip())
            self.assertGreater(int(row["usageCountAtReview"]), 0)

    def test_nfs_alias_and_lower_rank_decisions_are_explicit(self):
        combined = [row for path in FILES for row in _load(path)["items"]]
        nfs_rows = [
            row
            for row in combined
            if "NFS" in str(row["fdcDescription"])
            or "NS as to" in str(row["fdcDescription"])
        ]
        self.assertEqual(len(nfs_rows), 25)
        for row in nfs_rows:
            self.assertTrue(str(row.get("notes") or "").strip())

        by_id = {row["reviewTargetId"]: row for row in combined}
        self.assertEqual(
            {target_id for target_id, row in by_id.items() if "synonym" in str(row.get("notes") or "")},
            ALIAS_REVIEW_IDS,
        )
        for target_id in ALIAS_REVIEW_IDS:
            self.assertTrue(str(by_id[target_id].get("notes") or "").strip())

        lower = {
            row["reviewTargetId"]: row
            for row in combined
            if int(row["candidateEvidenceRank"]) > 1
        }
        self.assertEqual(set(lower), LOWER_RANK_IDS)
        for row in lower.values():
            self.assertTrue(str(row.get("notes") or "").strip())

    def test_loader_consumes_all_sixty_bindings_without_identity_rewrite(self):
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


if __name__ == "__main__":
    unittest.main()
