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
    TOOLS / "release_catalog_reviewed_nutrition_targets_033.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033j.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033k.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033l.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_033m.v1.json",
]
EXPECTED_FILE_DIGESTS = ["07be3e118da30be4d8036845f5d77366b2ae44bfaf4e35267d550f4007d28527","a1b1a94e729f2f5680c016c4d6d3792e48bf823d52ad0f94d583b52da5583e4e","d536c5ebb2176721320620bd1cdd5bfc3b1e343357140ae82ec9a91de11e7de7","085130103ccb5e8f6b9b73c527aa0a426326750d7f926a914e3b387609155de5","543167b5bf965662b099798e4b03903679dd5e55e024c9cbb4c094aedacb8f45","9a96377ef7da4bd16ef44e4f1a60d52f058e4ffcaf13cd15fd1a7007a78392b4","656550fd41c3c9a78e88c0ca093e1f9fb4f365867e3a6b4d11848e9d0cc43feb","62c40289ee6b4e459db4a3a6b4835a9ef8ac918288aef441cb5392924672bba2","191c6199d1d4240806a3a5232da3bb20e0b18964a01f22d45d4ec4c543767736","ed2b04eb530aad52c6694940cad3f0004336728330d35e5548366f6c04a16b8f","e579365d0048e55b614a852c551011fe580b3adbc3798de558a3aa38b3a9092f","5ed55ba0bc24111cda16732af6d6204f669a40a53473dc8cf66ed10be3af6c38","62627713c2edcc2f36302de8cc79bdd01f1409a86cc1dfaeb6c9ebd2fcdeaff3"]
EXPECTED_COMBINED_DIGEST = "e48d396035266c14e5af7bd9fb4edd507e96cbee4543838114caf0988b1a0792"
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


class NutritionTargetReviewBatch27V60Tests(unittest.TestCase):
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

    def test_exact_two_hundred_fifty_batch27_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 250)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 250)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 1352)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 106)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 139)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 5)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 69)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 33:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 3631)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_181_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 181)
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
        self.assertGreaterEqual(len(loaded), 3881)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
