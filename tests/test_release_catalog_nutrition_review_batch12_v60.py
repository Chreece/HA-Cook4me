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
    TOOLS / "release_catalog_reviewed_nutrition_targets_017.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_017b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_017c.v1.json",
]
EXPECTED_FILE_DIGESTS = [
    "c9782a08942eb9eecd4780e78e14fd461fa2fc6712b5219e7f9a0f8651a056eb",
    "4862bbfb843a5ae4389d282095150d69d3eacf03f2e1ea7e972d6101d1520241",
    "7d8a4b66efe074787c7545b7158e88c9c425526c3e7b0ea6f1d8da3a944f759e",
]
EXPECTED_COMBINED_DIGEST = "a1ae55da422be0b9fb5bbbb7ed1f8aa72c945aa7e488d0bb36d9a67db3e36d55"
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


class NutritionTargetReviewBatch12V60Tests(unittest.TestCase):
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

    def test_exact_sixty_batch12_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 60)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 3747)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 29)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 22)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 9)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 53)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 17:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 726)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_seven_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = {row["reviewTargetId"]: row for path in REVIEW_FILES for row in _load(path)["items"]}
        expected = {
            "concept:food:1295f8b154a665b2d1df": (1104647, 2, "Garlic, raw"),
            "M_FOOD_614": (2705614, 3, "Sour cream, regular"),
            "concept:food:ec899f0c630595985e99": (2705614, 3, "Sour cream, regular"),
            "concept:food:ac6c9a87169e2d37eb24": (173800, 2, "Chickpeas (garbanzo beans, bengal gram), mature seeds, canned, drained solids"),
            "concept:food:8942d465c92c6668e156": (2705849, 7, "Beef, stew meat"),
            "concept:food:3bec4de5925d1e9320a1": (2705747, 6, "Cheese, cottage, NFS"),
            "concept:food:921afaed6fe1d01285b9": (2705398, 5, "Milk, evaporated, NS as to fat content"),
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
                self.assertTrue("higher-ranked" in notes or "rank 1" in notes)

    def test_loader_consumes_all_sixty_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
