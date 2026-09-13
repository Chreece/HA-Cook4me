from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402

FILES = (
    TOOLS / "release_catalog_reviewed_nutrition_targets_013.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_013b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_013c.v1.json",
)
EXPECTED_FILE_DIGESTS = (
    "a21554bfcfa0d031f8c91a1897443aaf4a65ce1c0f38b9c9d7afd13e28415e72",
    "49df4ce82f02bb6b9c434ff2e95800875b14115b7a1993eb7b1cabdf1344dbca",
    "fc0495ee50c195f233b8f2dfa57a12a1bed9daec33850968ac7e76b861e56a83",
)
EXPECTED_COMBINED_DIGEST = "5f2f4610f72409f665e9bba7263d9bf1961d25d0372f876c8f49e8ca7c218f08"
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


def _review_file_sequence(path: Path) -> int | None:
    match = re.fullmatch(
        r"release_catalog_reviewed_nutrition_targets_(\d{3})[a-z]*\.v1\.json",
        path.name,
    )
    return int(match.group(1)) if match else None


class NutritionTargetReviewBatch10V60Tests(unittest.TestCase):
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

    def test_exact_sixty_batch10_targets_are_locked_and_disjoint(self):
        combined: list[dict] = []
        for path, expected_digest in zip(FILES, EXPECTED_FILE_DIGESTS, strict=True):
            items = _load(path)["items"]
            self.assertEqual(len(items), 20)
            self.assertEqual(_digest(items), expected_digest)
            combined.extend(items)

        self.assertEqual(len(combined), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in combined}), 60)
        self.assertEqual(_digest(combined), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in combined), 663)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in combined), 24)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in combined), 27)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in combined), 9)

        # Batch 10 was reviewed against the corpus through sequence 012 only.
        # Later review artifacts must not retroactively become its "prior" corpus.
        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            sequence = _review_file_sequence(path)
            if sequence is not None and sequence < 13:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 583)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
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
        self.assertEqual(len(nfs_rows), 3)
        for row in nfs_rows:
            self.assertTrue(str(row.get("notes") or "").strip())

        lower = {row["reviewTargetId"]: row for row in combined if int(row["candidateEvidenceRank"]) > 1}
        self.assertEqual(set(lower), {"M_FOOD_584", "concept:food:5e65990fa69b5be1bab9"})
        self.assertEqual(int(lower["M_FOOD_584"]["fdcId"]), 2706339)
        self.assertEqual(int(lower["concept:food:5e65990fa69b5be1bab9"]["fdcId"]), 2709203)
        for row in lower.values():
            self.assertTrue(str(row.get("notes") or "").strip())

        manual_note_ids = {
            "M_FOOD_584",
            "concept:food:0718fe8c3c4310828143",
            "concept:food:1f0306077d54ff979553",
            "concept:food:25590c6499abf15b2fe7",
            "concept:food:288c09c53fa91f12284c",
            "concept:food:35a5a3ad2a59226507aa",
            "concept:food:37cab1bdb4ee4d4c6273",
            "concept:food:484303784e770a99d615",
            "concept:food:4bf2763877456eaadcae",
            "concept:food:50264490701501cd769f",
            "concept:food:57b41bc377365ad40e20",
            "concept:food:5e65990fa69b5be1bab9",
            "concept:food:6aec3c22870911fcc356",
            "concept:food:716e61c0aed17286b8df",
            "concept:food:7282b0d898672817aacb",
            "concept:food:840b91ee3da50c9e0de2",
            "concept:food:8ccc1fe5992a7c6f44aa",
            "concept:food:a2cc68e99cf59b9a6488",
            "concept:food:abc0a0360b3cda5d8e69",
            "concept:food:c272194047b874ab9deb",
            "concept:food:c85f56ce00b385b5a32b",
            "concept:food:ee2419023ccbc713075a",
            "concept:food:f356acfb55ee333c9e95",
            "concept:food:f90af95de1320f588457",
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
