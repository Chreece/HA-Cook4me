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
    TOOLS / "release_catalog_reviewed_nutrition_targets_029.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029j.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029k.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029l.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029m.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029n.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_029o.v1.json",
]
EXPECTED_FILE_DIGESTS = ['ad088361ac969ff176a8bf26bd9822cbfe769ed1a3bd4fc5d5126ebee5e57092', 'cf62182c8f73757b6a731614d2f4d89d218e8c690545bfcc61be521c6562c20a', '2758ffb2302c6a3b5bbfe3a5c8e24e11d69503acb724ec1e52db13cdeb6d7a08', '6343fd8bcf67518b6827922828acf6d16dd02f10b91ae74401e0e42036d8a28b', '020643cfe8517dd461dcdc609a91f4161ea007ec07d5b8262092cff6afe177b3', 'dd407fc464ec945f276bbcb0d0040ed198cdc5c46fcb7897c039d4c14ceb5fbb', '57dd9cba946f6d52889990efc8615d7c2513caaf3e73f9cef8c31504f5bbf849', '91b1bdd6d832240d577bf70b82e73a089014bb34e88d4c756e6e09f236383480', '853c28e5694837663c0d75368c9b8043c6d7cb828e6798c16872aab7d7889bfb', 'd71593bd61e580505a874957b3d99cc15bc641600b341c8fdb7d08ec22e0f03a', '7437ec6bb1e1c4547ea50a1b5ce86c101df81191ce0b724e9e12fc1eaca2271e', '68ef964aa96694a7e6af17969593f613809405fb9ea69a89ba9e9e51d9519e33', '1ee641011da611b35bf1c1b74f73ca5fc050851d9dcfbdba27f1053150d1fe4c', 'f81b31c352e69d656ecca99986d530ae70af60bfabed1f07d1062181b1d916b4', '9d422bd4675fa12e80a187250eb3d9cd81d2716109d710e0f49c23fe65d2a32f']
EXPECTED_COMBINED_DIGEST = "a041ffc9f311a3ade8ffcbfef5f7a11c274259c8891a737414548aae04583497"
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


class NutritionTargetReviewBatch23V60Tests(unittest.TestCase):
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

    def test_exact_three_hundred_batch23_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 300)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 300)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 5885)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 121)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 142)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 37)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 183)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 29:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 2431)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_117_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 117)
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
        self.assertGreaterEqual(len(loaded), 2731)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
