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

BATCH = TOOLS / "release_catalog_reviewed_provider_food_english_capture3_002.v2.json"
EXPECTED_ID_DIGEST = "f7cce4f29c0055b35b48f208f53f19572e73f4dd4b0dd6d9672b0fa66070a187"
EXPECTED_MEDIUM = {
    "M_FOOD_17",
    "M_FOOD_128",
    "M_FOOD_142",
    "M_FOOD_212",
    "M_FOOD_236",
    "M_FOOD_524",
    "M_FOOD_557",
    "M_FOOD_558",
    "M_FOOD_569",
    "M_FOOD_761",
}


class Capture3ProviderEnglishBatch2V60Tests(unittest.TestCase):
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

    def test_loader_attributes_every_batch2_review_to_batch2(self):
        loaded = reviews._provider_food_reviews(TOOLS)
        payload = json.loads(BATCH.read_text(encoding="utf-8"))
        for ident in payload["items"]:
            self.assertEqual(
                loaded[ident]["reviewFile"],
                "release_catalog_reviewed_provider_food_english_capture3_002.v2.json",
            )


if __name__ == "__main__":
    unittest.main()
