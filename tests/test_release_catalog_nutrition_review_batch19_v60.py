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
    TOOLS / "release_catalog_reviewed_nutrition_targets_025.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_025b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_025c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_025d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_025e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_025f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_025g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_025h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_025i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_025j.v1.json",
]
EXPECTED_FILE_DIGESTS = ['36cf673f2e8946d73b873cf3027f5b748ad5a44523f4d5284e8c0c4367da4e63', '8f12cc8abbc15b19be546b2356ce89f4d82e68e721c1082a5b82e3ea6d0035ed', '7f31317a66661127120f79b560177f2791417f8259971455b8a973e9d2d542d9', 'ca98949e18c5534b62a0af24bfbd12cddb57a5e6d04cd44bd6f823b4b613518f', 'eec3feb33e644d8f687e869dbe6eff52cc61221af9c283e70542bfd143d815ba', '623e4a69a8fd3b61bf825704d48aa27dd3b4642700966091fd49f50efa0a040a', 'ef065e6ef523642deead9200b08beb787c33c290a40af15094097eb911fd8ff2', 'a99b1246ccb28b07218f46a58518bffea0deb8174105de93a4022137172db506', '107652a99ad965a3bf1542834d63c1b84e50f62d1f7ca32a2987d5d4a580f1bb', '34203bf9764ce79ce4c06762a5200498defed8dfd1529ce9a39933ec156b9bc8']
EXPECTED_COMBINED_DIGEST = '35468075d9110cddabd0ea5b830a7cbfabfe8c6e418f6171926021c0f00ce49c'
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


class NutritionTargetReviewBatch19V60Tests(unittest.TestCase):
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

    def test_exact_two_hundred_batch19_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 200)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 200)
        self.assertEqual(
            [_digest(_load(path)["items"]) for path in REVIEW_FILES],
            EXPECTED_FILE_DIGESTS,
        )
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 372)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 75)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 78)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 47)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 96)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 25:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 1331)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_one_hundred_four_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 104)
        for row in lower:
            with self.subTest(target_id=row["reviewTargetId"]):
                notes = str(row.get("notes") or "").lower()
                self.assertIn(f"rank-{int(row['candidateEvidenceRank'])}", notes)
                self.assertIn("higher-ranked", notes)
                self.assertIn("explicit semantic review", notes)
                self.assertIn("pinned candidate evidence", notes)

    def test_loader_consumes_all_two_hundred_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        self.assertGreaterEqual(len(loaded), 1531)
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
