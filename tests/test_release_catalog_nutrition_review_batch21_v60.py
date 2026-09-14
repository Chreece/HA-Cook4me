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
    TOOLS / "release_catalog_reviewed_nutrition_targets_027.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027j.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027k.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027l.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027m.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027n.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_027o.v1.json",
]
EXPECTED_FILE_DIGESTS = ['850ef7707ea76f25948dd3a7b144e4cc9aae1ba8e2ff396ee9282a6066758b04', '894de22255e6b60da45a4495111ea5920cadf0f73a5a1b9c52ad2934463c3676', '3bc19324513cdc25005f5e0ca19d9f28fc49eb386d7cc7f6b1ef23373dec4e02', 'f767e796e26fe525959be18e5d59f373f57cba3e32dc20dd84b300f83fb9a767', '381698dd7fb651866428aecda4aee42b641e96c8cfaa0b7223d53bbe4303684e', '93f2ffacb4e96fd696aef8ff1d72a91c6ec077a8711ec2d34d6f5c0543afd5b9', '255cadb022ecad27c40627f94f74db706410e5595511ce8e1a55d1f5720750d8', 'fddf7ec7d50540a2b470ec2908ad277404e907172fa0e7edee15a6e85aad5c2e', 'f16a3914d464b4049972b5499b5eeb1ec1956174f397bc83372f6c48ead7b0e1', 'd4f750cce4fb1d1988a40f3cd9326245cf439e734239358d262f879cbdf45e6c', '122683185b3fb5504962a41f118239ae55418bda0a0eb64dba67e868eb446546', 'b6a97c9256355f6f309fe2c5bc09137b68167de04f2d174a46e7695534fd50bf', '3bb094f04fb5fc865b018d2824879b8bc8643bf98bed6f6b9456026533435b87', '7b3073b638a9c70bb5d60e6a8a8637bf81f7fedb5bd7a21d178b0dbf2d6fcc69', '8a8dae7bc36ea1858d77734939f66dc52d3725b4f057958e5aa6da45c05d3246']
EXPECTED_COMBINED_DIGEST = 'c0df6921f800264e099beb8fcc7dd560f753e77c70d4adb65a3af729776fd02c'
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


class NutritionTargetReviewBatch21V60Tests(unittest.TestCase):
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

    def test_exact_three_hundred_batch21_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 300)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 300)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 2292)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 161)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 92)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 47)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 176)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 27:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 1831)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_124_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 124)
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
        self.assertGreaterEqual(len(loaded), 2131)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
