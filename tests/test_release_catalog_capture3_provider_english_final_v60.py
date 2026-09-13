from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import release_catalog_canonical_reviews_v60 as reviews  # noqa: E402

BATCH = TOOLS / "release_catalog_reviewed_provider_food_english_capture3_005.v2.json"
EXPECTED_ID_DIGEST = "972fb52a4832b5eec3e256a0aab67476a27a054db2ffdb0ecc04e60eb401cfce"
EXPECTED_MEDIUM = {
    "M_FOOD_771",
    "M_FOOD_783",
    "M_FOOD_798",
}


class Capture3ProviderEnglishFinalV60Tests(unittest.TestCase):
    def test_exact_final_71_provider_identities_are_locked(self):
        payload = json.loads(BATCH.read_text(encoding="utf-8"))
        ids = sorted(payload["items"])
        digest = hashlib.sha256("\n".join(ids).encode()).hexdigest()
        self.assertEqual(len(ids), 71)
        self.assertEqual(digest, EXPECTED_ID_DIGEST)

    def test_final_confidence_boundary_is_explicit(self):
        payload = json.loads(BATCH.read_text(encoding="utf-8"))
        medium = {
            ident
            for ident, row in payload["items"].items()
            if row.get("confidence") == "medium"
        }
        self.assertEqual(medium, EXPECTED_MEDIUM)
        for ident, row in payload["items"].items():
            self.assertTrue(row.get("english"), ident)
            self.assertIn(row.get("confidence"), {"high", "medium"})

    def test_loader_attributes_every_final_review_to_batch5(self):
        loaded = reviews._provider_food_reviews(TOOLS)
        payload = json.loads(BATCH.read_text(encoding="utf-8"))
        for ident in payload["items"]:
            self.assertEqual(
                loaded[ident]["reviewFile"],
                "release_catalog_reviewed_provider_food_english_capture3_005.v2.json",
            )

    def test_full_provider_review_corpus_is_420_exact_identities(self):
        loaded = reviews._provider_food_reviews(TOOLS)
        self.assertEqual(len(loaded), 420)


if __name__ == "__main__":
    unittest.main()
