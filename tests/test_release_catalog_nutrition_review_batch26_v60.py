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
    TOOLS / "release_catalog_reviewed_nutrition_targets_032.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032b.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032c.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032d.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032e.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032f.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032g.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032h.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032i.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032j.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032k.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032l.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032m.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032n.v1.json",
    TOOLS / "release_catalog_reviewed_nutrition_targets_032o.v1.json",
]
EXPECTED_FILE_DIGESTS = ["420f42629ef55d09c4091d22f56bd20b9d60f4e39a7c417946c373fb0fc4b83b","79aea6d1887c72c98e8bb9dbbf2923dbf2e88a765264254d77d88fcfc63a7483","6f65b2da7d09f73b8b1977fe56d9b05805ff6b5a43f18d61bfe495827a163c30","7e6a2646c3b619780d7fde976c9d19f940539280f7bada15ab06e641c221cc49","d9017b72f83c7941d4a485265d199f95473d1ea3b05ad48f17077f0475bbe88b","6c986daa4cf41720d5c5974e315a2bee80abb659a2d2004ab0ebc3bcc21de178","894df2549a9e9958d08e3e15f2bdd2377ed7e9dec9e0bbb4eb21a376765aa4b8","8d34ab6d2db472e00a2c06b23424736587cd09d06c37771216e14def3970566c","377d31bc205f99487a782d9412212ad07d333153a89566d786258b11e3d028ca","6ca7576e210a580f052f9446a0ee345ff20f771311f6e6a47e8c2d1c8b2bc75f","89aed2c0efccb72efb887a408893556e7045b3234f02996722957a9ce4291930","00028c67265fd85ab6e0fec2ec9d0a276f439c7907579d35206cde8cb3f886a9","60d85a9fe53e905f727df66d46fb5a499f29f71d2faa59ab4d54e5989660f8e4","972401df94fae1ec943e745557cc34422f87b1749d78dc503ff65512ba2f1aa6","440916e94a111e27e1fe136c692b869dcc690d8ce4c08bd9a0e5cedfaa7db570"]
EXPECTED_COMBINED_DIGEST = "a393eeb3c96f0041856f37344e86db08b9bbdcc77c79ddc22c6f70a5cb27ba6b"
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


class NutritionTargetReviewBatch26V60Tests(unittest.TestCase):
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

    def test_exact_three_hundred_batch26_targets_are_locked_and_disjoint(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        self.assertEqual(len(current), 300)
        self.assertEqual(len({row["reviewTargetId"] for row in current}), 300)
        self.assertEqual([_digest(_load(path)["items"]) for path in REVIEW_FILES], EXPECTED_FILE_DIGESTS)
        self.assertEqual(_digest(current), EXPECTED_COMBINED_DIGEST)
        self.assertEqual(sum(int(row["usageCountAtReview"]) for row in current), 974)
        self.assertEqual(sum(row["fdcDataType"] == "Survey (FNDDS)" for row in current), 76)
        self.assertEqual(sum(row["fdcDataType"] == "SR Legacy" for row in current), 143)
        self.assertEqual(sum(row["fdcDataType"] == "Foundation" for row in current), 81)
        self.assertEqual(sum(int(row["candidateEvidenceRank"]) == 1 for row in current), 141)

        prior_paths = []
        for path in sorted(TOOLS.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
            seq = _sequence(path)
            if seq is not None and seq < 32:
                prior_paths.append(path)
        prior_rows = [row for path in prior_paths for row in _load(path)["items"]]
        self.assertEqual(len(prior_rows), 3331)
        prior_ids = {row["reviewTargetId"] for row in prior_rows}
        self.assertFalse(prior_ids & {row["reviewTargetId"] for row in current})

    def test_159_lower_rank_choices_are_explicit_semantic_decisions(self):
        current = [row for path in REVIEW_FILES for row in _load(path)["items"]]
        lower = [row for row in current if int(row["candidateEvidenceRank"]) != 1]
        self.assertEqual(len(lower), 159)
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
        self.assertGreaterEqual(len(loaded), 3631)
        for row in current:
            target_id = row["reviewTargetId"]
            self.assertIn(target_id, loaded)
            self.assertEqual(loaded[target_id]["reviewTargetId"], target_id)
            self.assertEqual(int(loaded[target_id]["fdcId"]), int(row["fdcId"]))
            self.assertEqual(loaded[target_id]["canonicalEnglishName"], row["canonicalEnglishName"])


if __name__ == "__main__":
    unittest.main()
