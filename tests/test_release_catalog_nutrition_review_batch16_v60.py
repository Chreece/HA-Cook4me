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
    TOOLS / "release_catalog_reviewed_nutrition_targets_022.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_022b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_022c.v1.json",
]
EXPECTED_FILE_DIGESTS = ['11f2b44e34433e0e6e3a96d67db8df9fc47599757a4ca0a1991eeb723bfe0d02', 'da8c58e3041a3f684d37b0387930aaef43d7d83dc06dcf3536b16ca9b9cf39a5', '18fb0669f22288db1b3f808e32dc1442b10ba2c3c6b204ec98c36e791e29d992']
EXPECTED_COMBINED_DIGEST = 'deab834627cf79ed881af36cdf57efe1644943dcd2ba26e3bc8fee010bebf078'
EXPECTED_REFERENCE_MANIFEST_SHA256 = 'e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d'
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


class NutritionTargetReviewBatch16V60Tests(unittest.TestCase):
    def test_review_files_pin_the_three_dataset_fail_closed_contract(self):
        expected_policy = {
            "searchResultAutoAccepted": False,
            "exactFdcBindingRequired": True,
            "semanticConceptGroupingReviewed": True,
            "providerIdentityInference": False,
            "candidateSearchIsIdentityProof": False,
        }
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

    def test_exact_sixty_batch16_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 60)
        self.assertEqual(
            [_digest(_load(path)["items"]) for path in REVIEW_FILES],
            EXPECTED_FILE_DIGESTS,
        )
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 440)
        self.assertEqual(
            sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 17
        )
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 28)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 15)
        self.assertEqual(
            sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 24
        )

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 22:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 971)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_thirty_six_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = {
            row["reviewTargetId"]: row
            for path in REVIEW_FILES
            for row in _load(path)["items"]
        }
        expected = {'concept:food:0854009abc61bdae7a87': (1104647, 3, 'Garlic, raw'),
 'concept:food:103635a7deeab4d244d7': (1104647, 2, 'Garlic, raw'),
 'concept:food:11866b38187c1b9d5717': (170393, 2, 'Carrots, raw'),
 'concept:food:19c782bf9a76c26be06a': (1104647, 7, 'Garlic, raw'),
 'concept:food:1a9e8d28e5db62cce8eb': (1104647, 3, 'Garlic, raw'),
 'concept:food:245757a3eb81cfde3277': (1104647, 3, 'Garlic, raw'),
 'concept:food:366d0b106b88da65325a': (2709780, 2, 'Basil, raw'),
 'concept:food:4098380ff93255aa227a': (2706190, 3, 'Sausage, NFS'),
 'concept:food:46cba883bcf87c27913a': (2709796, 8, 'Parsley, raw'),
 'concept:food:48a04d81fe94cc8be475': (1104647, 4, 'Garlic, raw'),
 'concept:food:4e922cdf4af90d0141f4': (1104647, 5, 'Garlic, raw'),
 'concept:food:5f04cb5c2e5093bf97bf': (169231, 7, 'Ginger root, raw'),
 'concept:food:6e27a056c3b5829bc212': (2258590, 6, 'Peppers, bell, red, raw'),
 'concept:food:7111b378d1e4a4a842a7': (170106, 3, 'Peppers, hot chili, red, raw'),
 'concept:food:7ce03d05f34b2140983b': (170416, 4, 'Parsley, fresh'),
 'concept:food:7f1d986959038de45728': (1104647, 3, 'Garlic, raw'),
 'concept:food:832e3d1a0cd896526fbe': (172231, 6, 'Spices, turmeric, ground'),
 'concept:food:8ad0999915091a6baaa5': (170416, 4, 'Parsley, fresh'),
 'concept:food:8ca2e7061561240be045': (169593, 2, 'Cocoa, dry powder, unsweetened'),
 'concept:food:8d7f257167ef300faad0': (169231, 7, 'Ginger root, raw'),
 'concept:food:977770caf59fc76df2cc': (170393, 4, 'Carrots, raw'),
 'concept:food:98335d5607cce7a1d7e8': (790577, 2, 'Onions, red, raw'),
 'concept:food:a33522d88db59d3b5878': (2706190, 2, 'Sausage, NFS'),
 'concept:food:a59ffda1b0b30ea0073d': (170931, 2, 'Spices, pepper, black'),
 'concept:food:a796d4db9fb5b8bdc1f8': (170931, 2, 'Spices, pepper, black'),
 'concept:food:ac33339e1dad8cc74ef2': (170499, 7, 'Shallots, raw'),
 'concept:food:b51f7bf50a086d2ad7da': (2709719, 2, 'Tomatoes, raw'),
 'concept:food:b9515e1875052da4f023': (170499, 4, 'Shallots, raw'),
 'concept:food:bb9399b50570d51ae54c': (1104647, 8, 'Garlic, raw'),
 'concept:food:c1b8a287a1c770962bd3': (170393, 2, 'Carrots, raw'),
 'concept:food:c9a4c87188cfe1945447': (1104647, 3, 'Garlic, raw'),
 'concept:food:d1321786ad62ed2a1fb4': (169727, 2, 'Pasta, fresh-refrigerated, plain, as purchased'),
 'concept:food:d485b3f193ea14968df5': (171326, 2, 'Spices, nutmeg, ground'),
 'concept:food:d592ac73a53338e2d43b': (790577, 2, 'Onions, red, raw'),
 'concept:food:ec95251905704ac20a8b': (2709719, 2, 'Tomatoes, raw'),
 'concept:food:fd839f08fed2ae63c575': (169231, 7, 'Ginger root, raw')}
        self.assertEqual(
            {
                target_id
                for target_id, row in current.items()
                if int(row["candidateEvidenceRank"]) != 1
            },
            set(expected),
        )
        for target_id, (fdc_id, rank, description) in expected.items():
            with self.subTest(target_id=target_id):
                row = current[target_id]
                self.assertEqual(int(row["fdcId"]), fdc_id)
                self.assertEqual(int(row["candidateEvidenceRank"]), rank)
                self.assertEqual(row["fdcDescription"], description)
                notes = str(row.get("notes") or "").lower()
                self.assertIn("rank", notes)

    def test_loader_consumes_all_sixty_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        self.assertGreaterEqual(len(loaded), 1031)
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
