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
    TOOLS / "release_catalog_reviewed_nutrition_targets_020.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_020b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_020c.v1.json",
]
EXPECTED_FILE_DIGESTS = [
    "9973fb2a3014d213028f138a8afb00802e7dbc1dd2e8e877e2da75c646dd1677",
    "8990e8b3b00f0df456ebe4d57d23fc90339ed73da9675c3c477e41c2334d5e32",
    "cb8a514012260ac57a7933e27512a31cb5893e86ca08b09742aefc55e02fe67a",
]
EXPECTED_COMBINED_DIGEST = "939bb44ca8881da3135a8b3dbee795a3bdfd035d64f5e666b4e596327f452cbc"
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
            str(row[key])
            for key in (
                "reviewTargetId",
                "reviewTargetKind",
                "canonicalEnglishName",
                "fdcId",
                "fdcDescription",
                "fdcDataType",
                "candidateEvidenceRank",
            )
        )
        digest.update(value.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _sequence(path: Path) -> int | None:
    match = FILE_RE.fullmatch(path.name)
    return int(match.group(1)) if match else None


class NutritionTargetReviewBatch14V60Tests(unittest.TestCase):
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

    def test_exact_sixty_batch14_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 60)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 60)
        self.assertEqual(
            [_digest(_load(path)["items"]) for path in REVIEW_FILES],
            EXPECTED_FILE_DIGESTS,
        )
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 1055)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 25)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 27)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 8)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 42)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 20:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 851)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_eighteen_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = {
            row["reviewTargetId"]: row
            for path in REVIEW_FILES
            for row in _load(path)["items"]
        }
        expected = {
            "concept:food:4417f9f4f541baedb0b9": (170416, 4, "Parsley, fresh"),
            "M_FOOD_170": (174223, 3, "Mollusks, squid, mixed species, raw"),
            "concept:food:f92660c91518b337ec11": (1104647, 5, "Garlic, raw"),
            "concept:food:80e5daa22a0f99ee6531": (2707934, 3, "Cookie, ladyfinger"),
            "concept:food:47feb8569c20a76ebb7b": (790577, 2, "Onions, red, raw"),
            "concept:food:77fefe2868847cb34376": (790577, 3, "Onions, red, raw"),
            "concept:food:bb64f4c301eae9224fc1": (2707152, 3, "Egg, whole, raw"),
            "concept:food:8154fa3cced1745b9aa3": (169997, 3, "Coriander (cilantro) leaves, raw"),
            "concept:food:4807a6ee31ad10257e28": (172233, 5, "Dill weed, fresh"),
            "concept:food:67109d8c97c24cafe412": (169414, 3, "Seeds, flaxseed"),
            "concept:food:26ca0f139719b4e2eba4": (168410, 2, "Edamame, frozen, unprepared"),
            "concept:food:db363065856b5100369e": (2708362, 3, "Buckwheat groats"),
            "concept:food:b7876805a831a97cfa4c": (171165, 4, "Soup, onion, dry, mix"),
            "concept:food:c6cae823c97c17af479f": (170000, 4, "Onions, raw"),
            "M_FOOD_502": (174223, 3, "Mollusks, squid, mixed species, raw"),
            "M_FOOD_224": (170922, 3, "Spices, coriander seed"),
            "concept:food:d4edd991faafc551302a": (170393, 5, "Carrots, raw"),
            "concept:food:a10c130ab3cbadac3c04": (170918, 3, "Spices, caraway seed"),
        }
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
                self.assertTrue(
                    "because" in notes
                    or "lexical" in notes
                    or "higher" in notes
                    or "ranks" in notes
                )

    def test_loader_consumes_all_sixty_bindings_without_identity_rewrite(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        loaded = resolver.load_reviews(TOOLS)
        # The exact creation boundary is locked above as 851 prior + 60 current.
        # Future immutable batches may add rows to the global loader.
        self.assertGreaterEqual(len(loaded), 911)
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
