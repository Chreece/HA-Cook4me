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
    TOOLS / "release_catalog_reviewed_nutrition_targets_024.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_024b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_024c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_024d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_024e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_024f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_024g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_024h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_024i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_024j.v1.json",
]
EXPECTED_FILE_DIGESTS = ['be0b2ab6a61cd5612a007c6d943a0cff97d0ca72ca07feb09993e19a3cd7eb08', 'cbe9779f147fff01b2b2693c2eb3e6396ca2f522d7410c0ab750146cd510ad6b', '4957f40e3b90fbcfba6a397639833c95af56c41d7706f2af6d2a1c26776884d0', '4da0649901a478d5a1387d3861147395b04be51de68ab4b431e6c455997f459c', '74b45ace012c09849cfd136e75224b445ce3efd29abc4967f31fe05d43e00e85', 'abffc68316b8552aae3dfb0e7ba2748397a63806c9a41730600e07fa0f7e26fb', '5d917b04f905059409fa02d728f5b90de92f8c631570fb645120c2769bfc2d25', '4a9ebf03cde87bffb8a834f853990943f3df348aa1662e4db9fd9d05022c5802', '696309107a125cbe8638565c2b723cc98afd512eabf37ccdaacc3260e835196f', '94eac41c515e808fd49f8b6a167a18f2866e27d23b94c95b4dea1894eda18400']
EXPECTED_COMBINED_DIGEST = '44f6e65aae2800eaf4ae733668da71c92772b18487c7359150ad1607a0d2bf0d'
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


class NutritionTargetReviewBatch18V60Tests(unittest.TestCase):
    def test_review_files_pin_the_three_dataset_fail_closed_contract(self):
        expected_policy = {
            "searchResultAutoAccepted": False,
            "exactFdcBindingRequired": True,
            "semanticConceptGroupingReviewed": True,
            "providerIdentityInference": False,
            "candidateSearchIsIdentityProof": False,
        }
        self.assertEqual(len(REVIEW_FILES), 10)
        for path in REVIEW_FILES:
            with self.subTest(path=path.name):
                value = _load(path)
                self.assertEqual(value["kind"], "cook4me-reviewed-nutrition-target-source")
                self.assertEqual(value["catalogVersion"], "2026-09-11-v60-capture3")
                self.assertEqual(value["referenceManifestSha256"], EXPECTED_REFERENCE_MANIFEST_SHA256)
                self.assertEqual(
                    value["evidenceKind"],
                    "cook4me-fdc-review-target-candidate-evidence-offline-v60",
                )
                self.assertEqual(value["selectionMethod"], "explicit-semantic-review")
                self.assertEqual(value["policy"], expected_policy)
                self.assertEqual(len(value["items"]), 20)
                self.assertTrue(all(row["confidence"] == "high" for row in value["items"]))

    def test_exact_two_hundred_batch18_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 200)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 200)
        self.assertEqual(
            [_digest(_load(path)["items"]) for path in REVIEW_FILES],
            EXPECTED_FILE_DIGESTS,
        )
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 2622)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 73)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 87)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 40)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 121)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 24:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 1131)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_seventy_nine_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 79)
        for row in lower:
            with self.subTest(target_id=row["reviewTargetId"]):
                notes = str(row.get("notes") or "").lower()
                self.assertIn(f"rank-{int(row['candidateEvidenceRank'])}", notes)
                self.assertIn("higher-ranked", notes)
                self.assertIn("explicit semantic review", notes)

    def test_loader_consumes_all_two_hundred_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        self.assertGreaterEqual(len(loaded), 1331)
        for row in current:
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
