from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unicodedata
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402

REUSE_FILE = TOOLS / "release_catalog_reviewed_nutrition_targets_010.v1.json"
EXPECTED_DIGEST = "5ec41dac05f9c9cd1e779953445622e6ae698b2b022f9d1ea7c666643bbdb499"
EXPECTED_REFERENCE_MANIFEST_SHA256 = "e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d"
PRIOR_FILES = (
    TOOLS / "release_catalog_reviewed_nutrition_targets_001.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_002.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_002b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_002c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_003.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_003b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_003c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_004.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_004b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_004c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_005.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_005b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_005c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_006.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_006b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_006c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_007.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_007b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_007c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_008.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_009.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_009b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_009c.v1.json",
)


def _load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _norm(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


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


class NutritionReviewedDecisionReuseBatch2V60Tests(unittest.TestCase):
    def test_reuse_artifact_is_locked(self):
        value = _load(REUSE_FILE)
        self.assertEqual(value["kind"], "cook4me-reviewed-nutrition-target-source")
        self.assertEqual(value["catalogVersion"], "2026-09-11-v60-capture3")
        self.assertEqual(value["referenceManifestSha256"], EXPECTED_REFERENCE_MANIFEST_SHA256)
        self.assertEqual(value["evidenceKind"], "cook4me-fdc-review-target-candidate-evidence-offline-v60")
        self.assertEqual(value["selectionMethod"], "exact-canonical-reviewed-decision-reuse")
        self.assertEqual(
            value["policy"],
            {
                "searchResultAutoAccepted": False,
                "exactFdcBindingRequired": True,
                "semanticConceptGroupingReviewed": True,
                "providerIdentityInference": False,
                "candidateSearchIsIdentityProof": False,
            },
        )
        items = value["items"]
        self.assertEqual(len(items), 14)
        self.assertEqual(len({row["reviewTargetId"] for row in items}), 14)
        self.assertEqual(_digest(items), EXPECTED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in items), 990)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in items), 12)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in items), 1)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in items), 1)

    def test_every_reuse_has_one_unambiguous_prior_exact_canonical_decision(self):
        prior_rows = [row for path in PRIOR_FILES for row in _load(path)["items"]]
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        current = _load(REUSE_FILE)["items"]
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

        for row in current:
            with self.subTest(target_id=row["reviewTargetId"], canonical=row["canonicalEnglishName"]):
                canonical = _norm(row["canonicalEnglishName"])
                matching = [old for old in prior_rows if _norm(old["canonicalEnglishName"]) == canonical]
                self.assertTrue(matching, "reuse must have a prior exact-canonical review")
                prior_fdc_ids = {int(old["fdcId"]) for old in matching}
                self.assertEqual(
                    prior_fdc_ids,
                    {int(row["fdcId"])},
                    "canonical review history must be unambiguous",
                )
                self.assertTrue(str(row.get("notes") or "").strip())
                self.assertGreaterEqual(int(row["candidateEvidenceRank"]), 1)
                self.assertLessEqual(int(row["candidateEvidenceRank"]), 8)

    def test_loader_consumes_reuse_rows_without_identity_rewrite(self):
        current = _load(REUSE_FILE)["items"]
        loaded = resolver.load_reviews(TOOLS)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
