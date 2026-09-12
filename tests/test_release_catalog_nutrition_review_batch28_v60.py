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
    TOOLS / "release_catalog_reviewed_nutrition_targets_034.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034j.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034k.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034l.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_034m.v1.json",
]
EXPECTED_FILE_DIGESTS = ["71b1881aee6852ce3c2aa5bf6a72cd1089c9d1b462104288b66a38b2999426b6","80fda2f08c02153d69e48acca62c68b8ee14929da0b5c956329c7b38fd59e953","4cdc2b905c2d4de1e4f964e21e68aa1ed78b060873b521bf0982253289b4d978","9312b385b71d2582fe98371669a7ee713031a4f3baee453b0715b992a574535d","b324cf5d8ebca6d9d55094bdf2efc6ba1a48fcd6b164a1c517cbbc99ef052de5","b8534d58af25e7f72aa33d462138c5c33d0a09d6f4778a5479303c6355f34153","580845008f542b71ff6b8dc9fcc7f783e385df9b8eeba46b5d5181778e1e9a74","1c11dbba4eacadf12a237a8d08271902b55e91a727ef88e907cab865f885f4f5","a58f6fc62fa656ddaaf2785ad6694f6d9f1c5920b4442111783dfea6a709f581","c78115454a0c7d710ff8a1856fc0fe1e7bcdb461f92f63df318737bf6e2e7172","99ebfdeb8cf9590d4376ec605f2c44a2d1da344859add9d259357a33e734ffdd","d449a2c7d62d739933988390edebb1374fce4ffb83e47469a5df4b1bd8d610ae","aa56aa84238545a924d636ee1335e6c6b1b9e19650f3c3921c5fd04e7d3db7fe"]
EXPECTED_COMBINED_DIGEST = "2b805e3c8a313b8e3d52d2757ad71502df0c27a3b5150a89cd1e5ff642b06251"
EXPECTED_REFERENCE_MANIFEST_SHA256 = "e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d"
FILE_RE = re.compile(r"release_catalog_reviewed_nutrition_targets_(\d+)[a-z]*\.v1\.json$")


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _digest(items: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in items:
        value = "\0".join((
            str(row["reviewTargetId"]), str(row["reviewTargetKind"]), str(row["canonicalEnglishName"]),
            str(row["fdcId"]), str(row["fdcDescription"]), str(row["fdcDataType"]), str(row["candidateEvidenceRank"]),
        ))
        digest.update(value.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _sequence(path: Path) -> int | None:
    match = FILE_RE.fullmatch(path.name)
    return int(match.group(1)) if match else None


class NutritionTargetReviewBatch28V60Tests(unittest.TestCase):
    def test_review_files_pin_the_fail_closed_contract(self):
        expected_policy = {
            "searchResultAutoAccepted": False,
            "exactFdcBindingRequired": True,
            "semanticConceptGroupingReviewed": True,
            "providerIdentityInference": False,
            "candidateSearchIsIdentityProof": False,
        }
        self.assertEqual(len(REVIEW_FILES), 13)
        expected_sizes = [20] * 12 + [10]
        for path, expected_size in zip(REVIEW_FILES, expected_sizes, strict=True):
            with self.subTest(path=path.name):
                value = _load(path)
                self.assertEqual(value["kind"], "cook4me-reviewed-nutrition-target-source")
                self.assertEqual(value["catalogVersion"], "2026-09-11-v60-capture3")
                self.assertEqual(value["referenceManifestSha256"], EXPECTED_REFERENCE_MANIFEST_SHA256)
                self.assertEqual(value["evidenceKind"], "cook4me-fdc-review-target-candidate-evidence-offline-v60")
                self.assertEqual(value["selectionMethod"], "explicit-semantic-review")
                self.assertEqual(value["policy"], expected_policy)
                self.assertEqual(len(value["items"]), expected_size)
                self.assertTrue(all(row["confidence"] == "high" for row in value["items"]))

    def test_exact_two_hundred_fifty_batch28_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 250)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 250)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 311)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 151)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 96)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 3)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 101)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 34:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 3881)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_149_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 149)
        for row in lower:
            with self.subTest(target_id=row["reviewTargetId"]):
                notes = str(row.get("notes") or "").lower()
                self.assertIn(f"rank-{int(row['candidateEvidenceRank'])}", notes)
                self.assertIn("explicit semantic review", notes)
                self.assertIn("pinned candidate evidence", notes)
                self.assertIn("not identity proof", notes)

    def test_loader_consumes_all_two_hundred_fifty_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        self.assertGreaterEqual(len(loaded), 4131)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
