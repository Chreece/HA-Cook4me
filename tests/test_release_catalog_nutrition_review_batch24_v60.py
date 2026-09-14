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
    TOOLS / "release_catalog_reviewed_nutrition_targets_030.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030j.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030k.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030l.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030m.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030n.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_030o.v1.json",
]
EXPECTED_FILE_DIGESTS = ['f70c69cf6d5033e9c41475ad90e31d380981622454b8aa8db382fb6148930444', 'eba3df7d24ac687043392464c426003994575953d63ecc97ed18ad796498efc9', 'ebe44ff5f99999716fcd1dd426c1632ab9ab58bcab66117685e2dd55f6f357ba', '4df9488d2077f1c0a35f12ef67186f5ab99290aafdb3b54baf2aba5e2a164871', 'f0ecf64c6ddabb80a776fc823c6716a9fc49ef6eaa44089bfffcb87f83522147', '0edd868e656a8d42d1cb82cf761d3cfa254c57f96306995007e88176cfbd9b71', '216d0e5236dfaf833f1e691684994be1948c5bba0070e1fcd63ebf3edf003bce', 'a00037855e96b302e6fd49060b99ba458a5de3eb69d497913c08bb9da030a14c', 'cfd530575a45f5c6cd4e0e6e21960bf3212c6a8b6c24931eb17a0f9f0e37baec', '2012e6111cb7070d6c5531345b593ce7fd575d15875e63fb3044c7a1d3a3b90d', '30c680daff821e69023d2c1e1a104daadaceccaf77454819d62761aa6c309596', '20cc7d71340eb9692d7efa07ff0e96819fa54f029961c79f311ac0a95c1b6305', '80f8ebe5e1243c0c07eb8d1dfff558ac88b34d4996264f396b73b63cdbcbdcaf', '28fa7395fba2e2c94791e3323a161e641a287e328f685613effea0cdf6567fb7', '2fed654775efc041528836c513c280378e465044edcbd1c06a5d0fc3287afde1']
EXPECTED_COMBINED_DIGEST = "09f453566df0347c5ddeb8cd0c523dcec6da28400a109923dcdac1b2a522cfc0"
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


class NutritionTargetReviewBatch24V60Tests(unittest.TestCase):
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

    def test_exact_three_hundred_batch24_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 300)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 300)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 9388)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 39)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 183)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 78)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 145)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 30:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 2731)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_155_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 155)
        for row in lower:
            with self.subTest(target_id=row["reviewTargetId"]):
                notes = str(row.get("notes") or "").lower()
                self.assertIn(f"rank-{int(row['candidateEvidenceRank'])}", notes)
                self.assertIn("explicit semantic review", notes)
                self.assertIn("pinned candidate evidence", notes)
                self.assertIn("not identity proof", notes)

    def test_loader_consumes_all_three_hundred_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        self.assertGreaterEqual(len(loaded), 3031)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
