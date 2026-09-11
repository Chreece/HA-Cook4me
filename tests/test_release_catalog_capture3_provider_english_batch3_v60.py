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

BATCH = TOOLS / "release_catalog_reviewed_provider_food_english_capture3_003.v2.json"
EXPECTED_ID_DIGEST = "5f85eb2ec7139463629f0e68864bacb460bfe5d9569e54c55a69855f39b29584"
EXPECTED_MEDIUM = {
    "M_FOOD_8",
    "M_FOOD_37",
    "M_FOOD_218",
    "M_FOOD_281",
    "M_FOOD_288",
    "M_FOOD_563",
    "M_FOOD_616",
    "M_FOOD_632",
    "M_FOOD_756",
    "M_FOOD_765",
}


class Capture3ProviderEnglishBatch3V60Tests(unittest.TestCase):
    def test_exact_60_provider_identities_are_locked(self):
        payload = json.loads(BATCH.read_text(encoding="utf-8"))
        ids = sorted(payload["items"])
        digest = hashlib.sha256("\n".join(ids).encode()).hexdigest()
        self.assertEqual(len(ids), 60)
        self.assertEqual(digest, EXPECTED_ID_DIGEST)

    def test_confidence_boundary_is_explicit(self):
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

    def test_loader_attributes_every_batch3_review_to_batch3(self):
        loaded = reviews._provider_food_reviews(TOOLS)
        payload = json.loads(BATCH.read_text(encoding="utf-8"))
        for ident in payload["items"]:
            self.assertEqual(
                loaded[ident]["reviewFile"],
                "release_catalog_reviewed_provider_food_english_capture3_003.v2.json",
            )


if __name__ == "__main__":
    unittest.main()
