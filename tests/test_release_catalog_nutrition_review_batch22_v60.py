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
    TOOLS / "release_catalog_reviewed_nutrition_targets_028.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028j.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028k.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028l.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028m.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028n.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_028o.v1.json",
]
EXPECTED_FILE_DIGESTS = ['5a626a18b6459705674fad3f0f2a00c978b37207a5b5bf41f9bef49df60c0722', '0e877523ce160ec062921f1c5176e6dd8adc55a74018f4afcf0760306c3fd9e8', '9347c3eef07d39d1109b680f689fb2aabff9af9e30d11555d9471be63627cf4a', '4b237b457f3cdd9008051030e6b3528b99a23c3f3b41cc713ecc041334ca920b', '5963e76e17958821f7279b1fab11ea21cf0d0777b9177b77dc2b49c0178d230f', '918cc7e67397a3c4a26e9b57f6a1df77ce3a7d6b9af44e2ae5e724e6c4198512', 'b7d6b9bfd0cebd6b17599babf2cb4674b6eb72db6f3de77c734107e618a8176f', '63c949b73c438d04785a2aebc135c1d775e72b2085ffbf6c9e0d590eed062fef', '0ba24ee98919efa23a7b38a81011a570a7ab20ad9f1314278e4946231f33c235', 'c1073600ef791fc1e95165b76b91ddda8c0b110bccbcb242c3dc2e0466367d0f', '1c6a47ec197077b07abe18709d21a50c79e0d92f17de586080aa2f5fb1e07cb6', '9ce4a4fa784ed382a0ab759ecc679706a1cc9e84454577ac051071762e606380', '4418306fa92d52ca6dfaab079261a4c786a7b90fedbd77e891683b089a61ae86', '7babca0eaf35b4a45011bb5bdb39cdb4ec46b68376f2cfb24b464b09402022bd', '3631e64282a65b3d18482eec4f7c883f31890870dd4080b36bb7dfc6220d0752']
EXPECTED_COMBINED_DIGEST = "8874efcd813ee3a5d966ea80b133cd5f06abec7214f0db90abb6163dc6ad769f"
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


class NutritionTargetReviewBatch22V60Tests(unittest.TestCase):
    def test_review_files_pin_the_fail_closed_contract(self):
        expected_policy = {
            "searchResultAutoAccepted": False,
            "exactFdcBindingRequired": True,
            "semanticConceptGroupingReviewed": True,
            "providerIdentityInference": False,
            "candidateSearchIsIdentityProof": False,
        }
        self.assertEqual(len(REVIEW_FILES), 15)
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

    def test_exact_three_hundred_batch22_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 300)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 300)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 816)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 130)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 141)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 29)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 154)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 28:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 2131)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_146_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 146)
        for row in lower:
            with self.subTest(target_id=row["reviewTargetId"]):
                notes = str(row.get("notes") or "").lower()
                self.assertIn(f"rank-{int(row['candidateEvidenceRank'])}", notes)
                self.assertIn("higher-ranked", notes)
                self.assertIn("explicit semantic review", notes)
                self.assertIn("pinned candidate evidence", notes)

    def test_loader_consumes_all_three_hundred_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        self.assertGreaterEqual(len(loaded), 2431)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
