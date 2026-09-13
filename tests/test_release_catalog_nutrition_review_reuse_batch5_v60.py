from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402

REUSE_FILE = TOOLS / "release_catalog_reviewed_nutrition_targets_016.v1.json"
EXPECTED_DIGEST = "f4c3f719b06b1baa91b9396184bcb8afb7e04842f454939197a54009d5897f27"
EXPECTED_REFERENCE_MANIFEST_SHA256 = "e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d"
FILE_RE = re.compile(r"release_catalog_reviewed_nutrition_targets_(\d+)[a-z]*\.v1\.json$")


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


def _sequence(path: Path) -> int | None:
    match = FILE_RE.fullmatch(path.name)
    return int(match.group(1)) if match else None


class NutritionReviewedDecisionReuseBatch5V60Tests(unittest.TestCase):
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
        self.assertEqual(len(items), 19)
        self.assertEqual(len({row["reviewTargetId"] for row in items}), 19)
        self.assertEqual(_digest(items), EXPECTED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in items), 3311)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in items), 9)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in items), 8)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in items), 2)

    def test_every_reuse_has_one_unambiguous_prior_exact_canonical_decision(self):
        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 16:
                prior_paths.append(path)

        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 707)
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

    def test_lower_rank_generic_reuse_choices_remain_explicit(self):
        current = {row["canonicalEnglishName"]: row for row in _load(REUSE_FILE)["items"]}
        expected = {
            "Egg": (2707152, 5, "Egg, whole, raw"),
            "Tomato": (2709719, 3, "Tomatoes, raw"),
            "Mayonnaise": (2710204, 2, "Mayonnaise, regular"),
        }
        for canonical, (fdc_id, rank, description) in expected.items():
            with self.subTest(canonical=canonical):
                row = current[canonical]
                self.assertEqual(int(row["fdcId"]), fdc_id)
                self.assertEqual(int(row["candidateEvidenceRank"]), rank)
                self.assertEqual(row["fdcDescription"], description)
                self.assertIn("rank", row["notes"].lower())
                self.assertIn("generic", row["notes"].lower())

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
