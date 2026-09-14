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
    TOOLS / "release_catalog_reviewed_nutrition_targets_026.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026j.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026k.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026l.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026m.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026n.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_026o.v1.json",
]
EXPECTED_FILE_DIGESTS = ['78b44b43bdeb035bb037cd2648d2d33e554c98eb36d6e1b2a0a241b83ff1f792', 'd55f806624be7fb154a1d6d6699782ee2bbecc87e5a962e3b2eedd8231b43cf5', '554f29820ed2f95ca8f91c683337c22869779c9bdbcd9631eb1a527d2116ae4f', '4dfe7dcc49481bad9c7aac24b4ac805f795e64c51bfbd724093db6d2c6139ac0', '8a7abe1fd84d5b17439ed506485d3b64548e48c6ee3cd1d18e59d9eb65385092', '8cd774951a8a6c2abc9a11c4f7b3608fe125f2d9e2e618f4fd227889b713a489', '437e26c2ec30648a4805b9ac3c2ea9485238ffe0906366bc8555f26651c1c05b', 'cc678f044393e73c7e7216684a78406b7960970df6a23103f26aede9491a2ad1', 'ec9a65ce65b508d35c01bcffefb3cb03cb3336ff65786bb466bf2cae936f19f2', 'cc68cf2e739be1ee3aff696c02c2bfea097f0bc4ddad26442a787683bba687a2', '195182e6af893b5df15e4fef5a515dcb80034e0df42f3454de3d9230ba83c9d3', '26ea4a0e58f637405023f0a956cc10737be5b8275b31b4988d6dc330abf74be9', '1d69ac6d70c2dbe55be8a719a544ba7f436991ea0c131ad62fe350b81b4badd1', 'e6c99ae665635501987bc81b153ec74f08c7d9e230eaeb4790844502cd498ea8', 'bc69ceed8a2a2ae6029c8779b4346608ce11feb367741dfa70b65af8b7346d66']
EXPECTED_COMBINED_DIGEST = '1dee8a5c89b96cca024d765d6a564e5b455b64a2a3cfd36979291b7d9fe9de46'
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


class NutritionTargetReviewBatch20V60Tests(unittest.TestCase):
    def test_review_files_pin_the_fail_closed_contract(self):
        expected_policy = {'searchResultAutoAccepted': False, 'exactFdcBindingRequired': True, 'semanticConceptGroupingReviewed': True, 'providerIdentityInference': False, 'candidateSearchIsIdentityProof': False}
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

    def test_exact_three_hundred_batch20_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 300)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 300)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 1776)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 142)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 86)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 72)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 140)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 26:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 1531)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_160_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 160)
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
        self.assertGreaterEqual(len(loaded), 1831)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
