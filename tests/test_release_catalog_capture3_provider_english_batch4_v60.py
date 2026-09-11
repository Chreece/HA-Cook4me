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

BATCH = TOOLS / "release_catalog_reviewed_provider_food_english_capture3_004.v2.json"
EXPECTED_ID_DIGEST = "1b3fac23d17bfa05ce55459a145b238ba6579b6309b70f919402279b77d71c8c"
EXPECTED_MEDIUM = {
    "M_FOOD_47",
    "M_FOOD_97",
    "M_FOOD_184",
    "M_FOOD_234",
    "M_FOOD_381",
    "M_FOOD_509",
    "M_FOOD_515",
    "M_FOOD_520",
    "M_FOOD_554",
    "M_FOOD_606",
    "M_FOOD_633",
    "M_FOOD_675",
    "M_FOOD_793",
}


class Capture3ProviderEnglishBatch4V60Tests(unittest.TestCase):
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

    def test_loader_attributes_every_batch4_review_to_batch4(self):
        loaded = reviews._provider_food_reviews(TOOLS)
        payload = json.loads(BATCH.read_text(encoding="utf-8"))
        for ident in payload["items"]:
            self.assertEqual(
                loaded[ident]["reviewFile"],
                "release_catalog_reviewed_provider_food_english_capture3_004.v2.json",
            )


if __name__ == "__main__":
    unittest.main()
