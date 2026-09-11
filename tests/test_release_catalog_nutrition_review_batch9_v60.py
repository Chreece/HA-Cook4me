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
    TOOLS / "release_catalog_reviewed_nutrition_targets_011.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_011b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_011c.v1.json",
)
EXPECTED_FILE_DIGESTS = (
    "0c0222097052bc3b724a645f84bf79c35247c98120e76740e30c1ffd030dd500",
    "093e96909c22a5f589d1904d962ea4c0e3dedd5884ec830a2deaf996f7029045",
    "9fd9780bc0488ecfa954aba960cb2a4ab16817a39f207c775c99342dc54b94e1",
)
EXPECTED_COMBINED_DIGEST = "15338390a524bf8f773d0ec47cb3dfaa0b962665e5fbd2bb6bb0542b0c39713a"
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


class NutritionTargetReviewBatch9V60Tests(unittest.TestCase):
    def test_review_files_pin_the_three_dataset_fail_closed_contract(self):
        for path in FILES:
            with self.subTest(path=path.name):
                value = _load(path)
                self.assertEqual(value["kind"], "cook4me-reviewed-nutrition-target-source")
                self.assertEqual(value["catalogVersion"], "2026-09-11-v60-capture3")
                self.assertEqual(value["referenceManifestSha256"], EXPECTED_REFERENCE_MANIFEST_SHA256)
                self.assertEqual(value["evidenceKind"], "cook4me-fdc-review-target-candidate-evidence-offline-v60")
                self.assertEqual(value["policy"], EXPECTED_POLICY)
                self.assertEqual(value["selectionMethod"], "explicit-semantic-review")

    def test_exact_sixty_batch9_targets_are_locked_and_disjoint(self):
        combined: list[dict] = []
        for path, expected_digest in zip(FILES, EXPECTED_FILE_DIGESTS, strict=True):
            items = _load(path)["items"]
            self.assertEqual(len(items), 20)
            self.assertEqual(_digest(items), expected_digest)
            combined.extend(items)

        self.assertEqual(len(combined), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in combined}), 60)
        self.assertEqual(_digest(combined), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in combined), 1324)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in combined), 37)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in combined), 20)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in combined), 3)

        current_names = {path.name for path in FILES}
        prior_paths = [
            path
            for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json"))
            if path.name not in current_names
        ]
        prior_ids = {
            row["reviewTargetId"]
            for path in prior_paths
            for row in _load(path)["items"]
        }
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in combined})

        for row in combined:
            self.assertIn(row["reviewTargetKind"], {"provider-identity", "semantic-concept"})
            if row["reviewTargetKind"] == "semantic-concept":
                self.assertTrue(row["reviewTargetId"].startswith("concept:food:"))
            self.assertEqual(row["confidence"], "high")
            self.assertGreater(int(row["fdcId"]), 0)
            self.assertIn(row["fdcDataType"], {"Foundation", "SR Legacy", "Survey (FNDDS)"})
            self.assertGreaterEqual(int(row["candidateEvidenceRank"]), 1)
            self.assertLessEqual(int(row["candidateEvidenceRank"]), 8)
            self.assertTrue(str(row["fdcDescription"]).strip())
            self.assertGreater(int(row["usageCountAtReview"]), 0)

    def test_nfs_lower_rank_and_manual_normalizations_are_explicit(self):
        combined = [row for path in FILES for row in _load(path)["items"]]
        nfs_rows = [row for row in combined if "NFS" in str(row["fdcDescription"])]
        self.assertEqual(len(nfs_rows), 6)
        for row in nfs_rows:
            self.assertTrue(str(row.get("notes") or "").strip())

        lower = {row["reviewTargetId"]: row for row in combined if int(row["candidateEvidenceRank"]) > 1}
        self.assertEqual(
            set(lower),
            {
                "concept:food:100b989ced3212adc7aa",
                "M_FOOD_65",
            },
        )
        self.assertEqual(int(lower["concept:food:100b989ced3212adc7aa"]["fdcId"]), 2707822)
        self.assertEqual(int(lower["M_FOOD_65"]["fdcId"]), 2705716)
        for row in lower.values():
            self.assertTrue(str(row.get("notes") or "").strip())

        manual_note_ids = {
            "M_FOOD_535",
            "concept:food:31d37e344ebb446e5b91",
            "concept:food:43819d5e1bdce129407a",
            "concept:food:12260c8e523890d7c22b",
            "concept:food:ea4f4fb8d133e1b330d4",
            "concept:food:16793b3a381e06074cfd",
            "concept:food:73f67ea7027015d968a7",
            "concept:food:1c392f0a07a6bfe18070",
            "concept:food:51bf101d71e2ab511b7a",
            "concept:food:6e02c7b07ad5d5fedb2a",
            "concept:food:6ea84ffa46d47a5932e0",
            "concept:food:fa490e276f9d061d87fc",
            "concept:food:b315ee1a00cf5b0639a9",
            "concept:food:fe820d53bd1a9ed8fc33",
            "concept:food:a175b23fb10993a38185",
            "concept:food:ecba7b15456f2a527418",
            "concept:food:504fd7ee31c6e68ab0d3",
            "concept:food:ba9a75218faa203dce0f",
            "M_FOOD_65",
            "concept:food:c7bd045394ac89b46697",
        }
        by_id = {row["reviewTargetId"]: row for row in combined}
        self.assertTrue(manual_note_ids <= set(by_id))
        for target_id in manual_note_ids:
            self.assertTrue(str(by_id[target_id].get("notes") or "").strip())

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
