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

FILES = (
    TOOLS / "release_catalog_reviewed_nutrition_targets_015.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_015b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_015c.v1.json",
)
EXPECTED_FILE_DIGESTS = (
    "7da1dd3bdb0681330e34e633e10dd94aa7056e93c7b305b906c516af180e1514",
    "ec6bab113c57bf56d3937aa11e84e5d1fdd86a607a5a00316cfbcbb91a5c067c",
    "e3f61d6783d7671b454afa4d9d09c1bd2af5ba55d40775a3298e3242fd3ff077",
)
EXPECTED_COMBINED_DIGEST = "1b378dbd812983a5997665e4e92c11780398c0f2e77828c9946eeea777297e55"
EXPECTED_REFERENCE_MANIFEST_SHA256 = "e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d"
EXPECTED_POLICY = {
    "searchResultAutoAccepted": False,
    "exactFdcBindingRequired": True,
    "semanticConceptGroupingReviewed": True,
    "providerIdentityInference": False,
    "candidateSearchIsIdentityProof": False,
}
REVIEW_FILE_RE = re.compile(r"release_catalog_reviewed_nutrition_targets_(\d{3})[a-z]*\.v1\.json\Z")


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


class NutritionTargetReviewBatch11V60Tests(unittest.TestCase):
    def test_review_files_pin_the_three_dataset_fail_closed_contract(self):
        for path in FILES:
            with self.subTest(path=path.name):
                value = _load(path)
                self.assertEqual(value["kind"], "cook4me-reviewed-nutrition-target-source")
                self.assertEqual(value["catalogVersion"], "2026-09-11-v60-capture3")
                self.assertEqual(value["referenceManifestSha256"], EXPECTED_REFERENCE_MANIFEST_SHA256)
                self.assertEqual(value["evidenceKind"], "cook4me-fdc-review-target-candidate-evidence-offline-v60")
                self.assertEqual(value["policy"], EXPECTED_POLICY)
                self.assertEqual(value["selectionMethod"], "explicit-semantic-review")

    def test_exact_sixty_batch11_targets_are_locked_and_disjoint(self):
        combined: list[dict] = []
        for path, expected_digest in zip(FILES, EXPECTED_FILE_DIGESTS, strict=True):
            items = _load(path)["items"]
            self.assertEqual(len(items), 20)
            self.assertEqual(_digest(items), expected_digest)
            combined.extend(items)

        self.assertEqual(len(combined), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in combined}), 60)
        self.assertEqual(_digest(combined), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in combined), 11824)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in combined), 25)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in combined), 24)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in combined), 11)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            match = REVIEW_FILE_RE.fullmatch(path.name)
            if match and int(match.group(1)) < 15:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 647)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in combined})

        for row in combined:
            self.assertIn(row["reviewTargetKind"], {"provider-identity", "semantic-concept"})
            if row["reviewTargetKind"] == "semantic-concept":
                self.assertTrue(row["reviewTargetId"].startswith("concept:food:"))
            self.assertEqual(row["confidence"], "high")
            self.assertGreater(int(row["fdcId"]), 0)
            self.assertIn(row["fdcDataType"], {"Foundation", "SR Legacy", "Survey (FNDDS)"})
            self.assertGreaterEqual(int(row["candidateEvidenceRank"]), 1)
            self.assertLessEqual(int(row["candidateEvidenceRank"]), 8)
            self.assertTrue(str(row["fdcDescription"]).strip())
            self.assertGreater(int(row["usageCountAtReview"]), 0)

    def test_five_lower_rank_generic_choices_are_explicit(self):
        combined = [row for path in FILES for row in _load(path)["items"]]
        lower = {
            row["reviewTargetId"]: row
            for row in combined
            if int(row["candidateEvidenceRank"]) > 1
        }
        expected = {
            "concept:food:aa6aa107cbcd2106d2f3": (2707152, 5),
            "concept:food:207569710fc5bec5a962": (748967, 3),
            "concept:food:b6d1de63417801a5c201": (2709719, 3),
            "concept:food:70dc8e0994cce12ba7ba": (2710204, 2),
            "M_FOOD_88": (2709793, 7),
        }
        self.assertEqual(set(lower), set(expected))
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in combined), 55)
        for target_id, (fdc_id, rank) in expected.items():
            row = lower[target_id]
            self.assertEqual(int(row["fdcId"]), fdc_id)
            self.assertEqual(int(row["candidateEvidenceRank"]), rank)
            self.assertTrue(str(row.get("notes") or "").strip())

    def test_loader_consumes_all_sixty_bindings_without_identity_rewrite(self):
        combined = [row for path in FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        for row in combined:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
