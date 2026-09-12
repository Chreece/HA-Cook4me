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

REVIEW_FILES = [
    TOOLS / "release_catalog_reviewed_nutrition_targets_019.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_019b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_019c.v1.json",
]
EXPECTED_FILE_DIGESTS = [
    "5df6234e49bdeacaa8bb5a6303275359305e41d0a3906e2786192c5d688f654e",
    "1239fe48e47021d7d64740c17f84a2823699540e1834f7a1799d2464b570b931",
    "d04dbdbac6268bf9ceb4f05d8ca349c8364e5f6c0add0eb2b76e2a4cf115ba98",
]
EXPECTED_COMBINED_DIGEST = "99fc720dfc217a29081086eb9975f20f5fd4e5ad7f89e9fac88cf7bbc20b7aed"
EXPECTED_REFERENCE_MANIFEST_SHA256 = "e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d"
FILE_RE = re.compile(r"release_catalog_reviewed_nutrition_targets_(\d+)[a-z]*\.v1\.json$")


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


def _sequence(path: Path) -> int | None:
    match = FILE_RE.fullmatch(path.name)
    return int(match.group(1)) if match else None


class NutritionTargetReviewBatch13V60Tests(unittest.TestCase):
    def test_review_files_pin_the_three_dataset_fail_closed_contract(self):
        expected_policy = {
            "searchResultAutoAccepted": False,
            "exactFdcBindingRequired": True,
            "semanticConceptGroupingReviewed": True,
            "providerIdentityInference": False,
            "candidateSearchIsIdentityProof": False,
        }
        for path in REVIEW_FILES:
            with self.subTest(path=path.name):
                value = _load(path)
                self.assertEqual(value["kind"], "cook4me-reviewed-nutrition-target-source")
                self.assertEqual(value["catalogVersion"], "2026-09-11-v60-capture3")
                self.assertEqual(value["referenceManifestSha256"], EXPECTED_REFERENCE_MANIFEST_SHA256)
                self.assertEqual(value["evidenceKind"], "cook4me-fdc-review-target-candidate-evidence-offline-v60")
                self.assertEqual(value["selectionMethod"], "explicit-semantic-review")
                self.assertEqual(value["policy"], expected_policy)
                self.assertEqual(len(value["items"]), 20)
                self.assertTrue(all(row["confidence"] == "high" for row in value["items"]))

    def test_exact_sixty_batch13_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 60)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 472)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 15)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 27)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 18)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 52)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 19:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 791)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_eight_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = {row["reviewTargetId"]: row for path in REVIEW_FILES for row in _load(path)["items"]}
        expected = {
            "concept:food:2712c791eb747a8312d5": (2709780, 2, "Basil, raw"),
            "concept:food:f74d13fc8b349d968f07": (170499, 2, "Shallots, raw"),
            "concept:food:798ba8e929256df1effe": (1104647, 2, "Garlic, raw"),
            "concept:food:da57a201b929e21d6f8e": (2709796, 2, "Parsley, raw"),
            "concept:food:22cbb7e8b153eaf011c2": (1104647, 2, "Garlic, raw"),
            "concept:food:142d2ff52239a431a27a": (1104647, 2, "Garlic, raw"),
            "concept:food:1de61bfb6e1a58b37b82": (170151, 2, "Seeds, sesame seeds, whole, roasted and toasted"),
            "concept:food:10ec8d8cf3d5aef71d6c": (167843, 2, "Pork, fresh, shoulder, whole, separable lean and fat, raw"),
        }
        self.assertEqual(
            {target_id for target_id, row in current.items() if int(row["candidateEvidenceRank"]) != 1},
            set(expected),
        )
        for target_id, (fdc_id, rank, description) in expected.items():
            with self.subTest(target_id=target_id):
                row = current[target_id]
                self.assertEqual(int(row["fdcId"]), fdc_id)
                self.assertEqual(int(row["candidateEvidenceRank"]), rank)
                self.assertEqual(row["fdcDescription"], description)
                notes = str(row.get("notes") or "").lower()
                self.assertIn("rank", notes)
                self.assertIn("rank 1", notes)

    def test_loader_consumes_all_sixty_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        self.assertEqual(len(loaded), 851)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
