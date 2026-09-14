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
    TOOLS / "release_catalog_reviewed_nutrition_targets_021.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_021b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_021c.v1.json",
]
EXPECTED_FILE_DIGESTS = ['4155deba5fa9965a69aa45b2090b487a54b1d75ec01e135a3546f298cb02680e', '28ca6244dcb7f490598cced10fa71ac8392a7ff024da288579916ebd121fed20', '2bf795d0b46a6bdecb765cde15d54a1c141b7056c3a21ff69b047e67f7619d76']
EXPECTED_COMBINED_DIGEST = '0e135abf16adb27af37bc18ac05ea7a349f2989c65fdf05216f2423f398e32bf'
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


class NutritionTargetReviewBatch15V60Tests(unittest.TestCase):
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

    def test_exact_sixty_batch15_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 60)
        self.assertEqual(
            [_digest(_load(path)["items"]) for path in REVIEW_FILES],
            EXPECTED_FILE_DIGESTS,
        )
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 597)
        self.assertEqual(
            sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 23
        )
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 32)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 5)
        self.assertEqual(
            sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 32
        )

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 21:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 911)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_twenty_eight_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = {
            row["reviewTargetId"]: row
            for path in REVIEW_FILES
            for row in _load(path)["items"]
        }
        expected = {'M_FOOD_174': (173833, 2, 'Veal, shoulder, arm, separable lean and fat, raw'),
 'M_FOOD_182': (2706301, 2, 'Fish, swordfish'),
 'M_FOOD_251': (172648, 2, 'Veal, shank, separable lean and fat, raw'),
 'M_FOOD_3': (170090, 2, 'Seaweed, agar, dried'),
 'M_FOOD_375': (2727566, 3, 'Chicken, drumstick, meat and skin, raw'),
 'M_FOOD_407': (2709211, 2, 'Prune, dried'),
 'M_FOOD_499': (169103, 5, 'Orange peel, raw'),
 'M_FOOD_5': (2706098, 6, 'Chicken tenders or strips, NFS'),
 'M_FOOD_708': (169414, 3, 'Seeds, flaxseed'),
 'M_FOOD_709': (171330, 2, 'Spices, poppy seed'),
 'concept:food:089dede908cd50739447': (172237, 6, 'Vinegar, distilled'),
 'concept:food:2582db291142ff281017': (1104647, 2, 'Garlic, raw'),
 'concept:food:25a3bb94511209449991': (2709460, 4, 'Potato, french fries, from frozen, baked'),
 'concept:food:3c773f84dfefe63fa056': (2709962, 5, 'Green peas, NS as to form, cooked'),
 'concept:food:3df886ecadd054fcd7f7': (170090, 2, 'Seaweed, agar, dried'),
 'concept:food:428710881015f1cb3e7c': (2705716, 2, 'Cheese, goat'),
 'concept:food:5067cb61e75631af5eab': (172648, 2, 'Veal, shank, separable lean and fat, raw'),
 'concept:food:554641740a5d809867c1': (2705893, 2, 'Ribs, NFS'),
 'concept:food:582e7c116d983e899281': (170924, 2, 'Spices, curry powder'),
 'concept:food:7672658b56e8c90239dc': (2709203, 4, 'Date'),
 'concept:food:92a50ee68d2f0d019e27': (173833, 2, 'Veal, shoulder, arm, separable lean and fat, raw'),
 'concept:food:93c69a42fa83dd85fe46': (168156, 2, 'Lime juice, raw'),
 'concept:food:ab7ae9198dd0ea5d096a': (746768, 2, 'Figs, dried, uncooked'),
 'concept:food:cc75a1547cb8c360dd74': (170931, 6, 'Spices, pepper, black'),
 'concept:food:d2d7e520d8b8d804f72a': (168462, 4, 'Spinach, raw'),
 'concept:food:ef3e6e7c246aa03d69f5': (2710706, 3, 'Water, NFS'),
 'concept:food:f2d7a95d4119150bb69b': (169103, 5, 'Orange peel, raw'),
 'concept:food:f8c74464e8a8b448bbe7': (167749, 3, 'Lemon peel, raw')}
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
        self.assertGreaterEqual(len(loaded), 971)
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
