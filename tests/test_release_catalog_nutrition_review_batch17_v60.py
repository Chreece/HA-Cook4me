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
    TOOLS / "release_catalog_reviewed_nutrition_targets_023.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_023b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_023c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_023d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_023e.v1.json",
]
EXPECTED_FILE_DIGESTS = ['fcc01af2a60f1fa7f870942891a3230bf00806b1b3d5b154bcb9900d0aade794', '42cf1f05317e590537a0fe5c3a3623dbf8d37a8f7ab180c0a8938a6c136c195c', 'b19c606fbbdb22dfa106d78c07831082fb51d11266c384734bace07238230bad', '822e0c8aa1a886cabe29cdc72914588fee10e849c4bed9b98f906ff843ed3e62', '368167475575d19109bac19cbde6a3c19c5efff87e4b4935374bdda8d1393c9f']
EXPECTED_COMBINED_DIGEST = '702a423fc22f6389cbbed24ca7e2116d47d5a277a4f012642bb8e5de4b69a5d0'
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


class NutritionTargetReviewBatch17V60Tests(unittest.TestCase):
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

    def test_exact_hundred_batch17_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 100)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 100)
        self.assertEqual(
            [_digest(_load(path)["items"]) for path in REVIEW_FILES],
            EXPECTED_FILE_DIGESTS,
        )
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 278)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 35)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 33)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 32)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 55)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 23:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 1031)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_forty_five_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = {
            row["reviewTargetId"]: row
            for path in REVIEW_FILES
            for row in _load(path)["items"]
        }
        expected = {'concept:food:00581375f09e16aca2c3': (1104647, 8, 'Garlic, raw'),
 'concept:food:02144514ee01eb3d63a3': (2709719, 5, 'Tomatoes, raw'),
 'concept:food:1959f8d53a2254834835': (2685577, 8, 'Eggplant, raw'),
 'concept:food:216e64c4f08228c77025': (2709168, 2, 'Lemon, raw'),
 'concept:food:278d620f363bcb255faf': (2709769, 6, 'Green beans, raw'),
 'concept:food:3389920671271e18387d': (2346405, 7, 'Celery, raw'),
 'concept:food:36858a6cf57f85714319': (2709168, 4, 'Lemon, raw'),
 'concept:food:44b3cf582d5f3863b2c6': (1104647, 5, 'Garlic, raw'),
 'concept:food:4c3e5b2920977db24322': (168389, 7, 'Asparagus, raw'),
 'concept:food:5ee2505f3a4fb12c08cb': (170000, 4, 'Onions, raw'),
 'concept:food:6b8977dce73d12173320': (2346405, 7, 'Celery, raw'),
 'concept:food:70e68da02532c087167e': (1104647, 3, 'Garlic, raw'),
 'concept:food:80a54dc88cc15e4a0a9e': (1104647, 5, 'Garlic, raw'),
 'concept:food:882e925b5fc57c078a3f': (2709793, 2, 'Mushrooms, raw'),
 'concept:food:8db9efcbd0251984ade5': (2346405, 5, 'Celery, raw'),
 'concept:food:8ffb77364ac0485f2cb8': (2709769, 6, 'Green beans, raw'),
 'concept:food:92b801f555cfd43c0485': (1104647, 2, 'Garlic, raw'),
 'concept:food:97e22a43e5de46b3871b': (1104647, 2, 'Garlic, raw'),
 'concept:food:9c19dc520052ce045049': (170400, 3, 'Celeriac, raw'),
 'concept:food:9d135596e67f32e6a781': (2346410, 2, 'Raspberries, raw'),
 'concept:food:a4f62586e67e215f53cb': (1104647, 4, 'Garlic, raw'),
 'concept:food:a848c85687249f8046a4': (2709794, 2, 'Onions, green, raw'),
 'concept:food:ab82aacc18767565eb3f': (2709769, 2, 'Green beans, raw'),
 'concept:food:adfdf89432d1338638b4': (2685577, 4, 'Eggplant, raw'),
 'concept:food:b1b5c53d2f8795470415': (2685573, 6, 'Cauliflower, raw'),
 'concept:food:bb4521a0ea1a11307cfb': (1104647, 3, 'Garlic, raw'),
 'concept:food:c37c305cdb69a2c9b115': (1104647, 4, 'Garlic, raw'),
 'concept:food:c3e783edc10acaf7078f': (2685577, 4, 'Eggplant, raw'),
 'concept:food:c860fa0acb1f6984f301': (2709719, 4, 'Tomatoes, raw'),
 'concept:food:c928c1ab94b4aa698f01': (2709223, 2, 'Avocado, raw'),
 'concept:food:cbaebe5cbc1c17911b5a': (2346405, 2, 'Celery, raw'),
 'concept:food:cc93a7b83441d0ad40a5': (170416, 2, 'Parsley, fresh'),
 'concept:food:cc94cf3991312f16076d': (2346405, 8, 'Celery, raw'),
 'concept:food:cf19814044853f123e54': (1104647, 3, 'Garlic, raw'),
 'concept:food:cf3612c20f065bd5e716': (2346405, 4, 'Celery, raw'),
 'concept:food:d4f692cbc9635a3b9b5b': (2709769, 5, 'Green beans, raw'),
 'concept:food:d756a89a7001eb96bb70': (168448, 6, 'Pumpkin, raw'),
 'concept:food:d8b0b50e9ff3e9ffaecf': (170388, 2, 'Cabbage, savoy, raw'),
 'concept:food:e65dfee44f56202080e5': (2705878, 4, 'Ham'),
 'concept:food:e7dc928ae6811e0ce744': (2346398, 2, 'Pineapple, raw'),
 'concept:food:ee2df066c3e587490d93': (169975, 6, 'Cabbage, raw'),
 'concept:food:f5b1744204fed76a6248': (2346398, 2, 'Pineapple, raw'),
 'concept:food:fa505ec260fb085499fb': (2685573, 2, 'Cauliflower, raw'),
 'concept:food:fe68f0c4588232c2b178': (168462, 4, 'Spinach, raw'),
 'concept:food:ff666e7560c9700b4a12': (170393, 2, 'Carrots, raw')}
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
                self.assertIn("higher-ranked", notes)

    def test_loader_consumes_all_hundred_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        self.assertGreaterEqual(len(loaded), 1131)
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
