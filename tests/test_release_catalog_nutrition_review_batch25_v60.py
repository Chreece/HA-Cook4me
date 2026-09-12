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
    TOOLS / "release_catalog_reviewed_nutrition_targets_031.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031j.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031k.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031l.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031m.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031n.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_031o.v1.json",
]
EXPECTED_FILE_DIGESTS = ['0e79f2707a1783fa7bddccb09c1f9997f401ee787cdbab3ad8daacf1db3ab864', '65fa0f16613d71723c5cc708c69fab7adb4fa3706f5696f109afdc04f3464d98', '7a69129624b36b7ac63639481f24917a8268470ff92fef7b48c5aae4086421cf', '3b114a287329db50df64bb5860820b331c518be6b68b03c391267be8bff57d54', '81cce7db6fefafd5e52b131bb402f4df98c2883a2c819f23933246e5e14bba2c', '6e1825990f011b4500af529098107e7cd7b3bf5ec7fa209308490053940ad04c', 'abd027ff344874320cb6301828b742f56e6e58dafbd3870badd09b510cf4724c', 'ee979b0fe874a3ae9bbf37b5138ef9fb980aebb0062b27347396573e898533cb', '574023c2783ba3fb8c7236c95df7651e94e18fe677a74833ac3153eb7cd5ed76', 'f45d2ce93b1c5bf60b1c688d549a5f9b37815acd1fc8d1d4012fb72fb25ae824', '5100287a2f504cbec4f5c86315dd6effb84b9355ebfff96564837f8f5e78d6c6', '47d7123ae751db3429a9942e5f291ee6f986e8bca8d12df21f26ef819323a7c1', 'd6fb78a52dd9f7521ee939fab0b22f273941806005a1ff939f8126deda9ee99d', '829f68a0183c9d4b324b10f875d0a4a799c62b12efbe16fa491d12511ad8c003', '82d0dcc20ab921752d5c23bc543b33d3dd7da0963f67ecc0687acdc2663809bf']
EXPECTED_COMBINED_DIGEST = "b1e68f764a2580c33780b5a730d4b8b63ddfc09b5d876bb316b59b78fda5938c"
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


class NutritionTargetReviewBatch25V60Tests(unittest.TestCase):
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

    def test_exact_three_hundred_batch25_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 300)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 300)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 15916)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 118)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 112)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 70)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 125)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 31:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 3031)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_175_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 175)
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
        self.assertGreaterEqual(len(loaded), 3331)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
