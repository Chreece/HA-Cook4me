from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import release_catalog_canonical_reviews_v60 as reviews  # noqa: E402

BATCH = TOOLS / "release_catalog_reviewed_provider_food_english_capture3_001.v2.json"
EXPECTED_ID_DIGEST = "68e0043213d0e0d1c56d4a51a759e4296aee93f45c6dc7f0a6f18fbf4cd0f046"
EXPECTED_MEDIUM = {
    "M_FOOD_106",
    "M_FOOD_136",
    "M_FOOD_145",
    "M_FOOD_312",
    "M_FOOD_405",
    "M_FOOD_468",
    "M_FOOD_561",
    "M_FOOD_582",
    "M_FOOD_631",
}
BASE_PROVIDER_REVIEW_COUNT = 109


class Capture3ProviderEnglishBatch1V60Tests(unittest.TestCase):
    def test_exact_60_provider_identities_are_locked(self):
        payload = json.loads(BATCH.read_text(encoding="utf-8"))
        ids = sorted(payload["items"])
        digest = hashlib.sha256("\n".join(ids).encode()).hexdigest()
        self.assertEqual(len(ids), 60)
        self.assertEqual(digest, EXPECTED_ID_DIGEST)
        self.assertTrue(all(ident.startswith("M_FOOD_") for ident in ids))

    def test_review_policy_and_confidence_are_explicit(self):
        payload = json.loads(BATCH.read_text(encoding="utf-8"))
        self.assertEqual(payload["schemaVersion"], 2)
        self.assertEqual(payload["kind"], "cook4me-reviewed-provider-food-english")
        self.assertTrue(payload["policy"]["sourceIdentityUnchanged"])
        self.assertTrue(payload["policy"]["translationMayNotMergeProviderIds"])
        self.assertTrue(payload["policy"]["manualReview"])
        self.assertEqual(payload["policy"]["catalogVersion"], "2026-09-11-v60-capture3")
        medium = {
            ident
            for ident, row in payload["items"].items()
            if row.get("confidence") == "medium"
        }
        self.assertEqual(medium, EXPECTED_MEDIUM)
        for ident, row in payload["items"].items():
            self.assertTrue(row.get("english"), ident)
            self.assertIn(row.get("confidence"), {"high", "medium"})

    def test_loader_consumes_base_plus_all_capture3_batches(self):
        loaded = reviews._provider_food_reviews(TOOLS)
        batch_paths = sorted(
            TOOLS.glob("release_catalog_reviewed_provider_food_english_capture3_*.v2.json")
        )
        batch_count = sum(
            len(json.loads(path.read_text(encoding="utf-8")).get("items") or {})
            for path in batch_paths
        )
        self.assertEqual(len(loaded), BASE_PROVIDER_REVIEW_COUNT + batch_count)
        for ident in json.loads(BATCH.read_text(encoding="utf-8"))["items"]:
            self.assertEqual(
                loaded[ident]["reviewFile"],
                "release_catalog_reviewed_provider_food_english_capture3_001.v2.json",
            )

    def test_duplicate_provider_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = {
                "schemaVersion": 2,
                "kind": "cook4me-reviewed-provider-food-english",
                "items": {"M_FOOD_TEST": {"english": "One", "confidence": "high"}},
            }
            extra = {
                "schemaVersion": 2,
                "kind": "cook4me-reviewed-provider-food-english",
                "items": {"M_FOOD_TEST": {"english": "One", "confidence": "high"}},
            }
            (root / "release_catalog_reviewed_provider_food_english.v2.json").write_text(
                json.dumps(base), encoding="utf-8"
            )
            (root / "release_catalog_reviewed_provider_food_english_capture3_001.v2.json").write_text(
                json.dumps(extra), encoding="utf-8"
            )
            with self.assertRaisesRegex(RuntimeError, "duplicate provider-food English review identity"):
                reviews._provider_food_reviews(root)


if __name__ == "__main__":
    unittest.main()
