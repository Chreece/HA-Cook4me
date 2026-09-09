from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "capture_marketing_food_catalogs_v2.py"
spec = importlib.util.spec_from_file_location("capture_marketing_food_catalogs_v2", SCRIPT)
assert spec and spec.loader
capture = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = capture
spec.loader.exec_module(capture)


class MarketingFoodCaptureTests(unittest.TestCase):
    def test_all_28_catalog_mappings_are_reaudited(self):
        self.assertEqual(28, len(capture.AUDITED_CATALOGS))
        self.assertIn(("en", "GB"), capture.AUDITED_CATALOGS)
        self.assertIn(("el", "GR"), capture.AUDITED_CATALOGS)
        self.assertIn(("sv", "SE"), capture.AUDITED_CATALOGS)

    def test_localized_name_prefers_requested_language(self):
        value = [
            {"lang": "de", "value": "Kartoffel"},
            {"lang": "en", "value": "Potato"},
        ]
        self.assertEqual("Potato", capture._localized_name(value, "en"))
        self.assertEqual("Kartoffel", capture._localized_name(value, "de"))

    def test_normalization_keeps_provider_key_and_audits_conflicting_duplicates(self):
        payload = {
            "page": {"totalElements": 4},
            "content": [
                {"key": "M_FOOD_1", "name": "Potato"},
                {"key": "M_FOOD_1", "name": "Potatoes"},
                {"key": "M_FOOD_2", "name": "Carrot"},
                {"name": "No provider key"},
            ],
        }
        rows, stats = capture.normalize_marketing_foods(payload, "en")
        self.assertEqual(["M_FOOD_1", "M_FOOD_2"], [row["key"] for row in rows])
        self.assertEqual("Potato", rows[0]["name"])
        self.assertEqual(["Potatoes"], rows[0]["aliases"])
        self.assertEqual(2, stats["uniqueKeys"])
        self.assertEqual(1, stats["missingKeyRows"])
        self.assertEqual(1, stats["duplicateRows"])
        self.assertEqual(1, stats["conflictingLabels"])
        self.assertEqual(4, stats["reportedTotalElements"])
        self.assertFalse(stats["truncated"])

    def test_reported_total_detects_an_incomplete_size_limited_response(self):
        payload = {
            "page": {"totalElements": 6000},
            "content": [{"key": f"M_FOOD_{i}", "name": f"Food {i}"} for i in range(5000)],
        }
        rows, stats = capture.normalize_marketing_foods(payload, "en")
        self.assertEqual(5000, len(rows))
        self.assertEqual(6000, stats["reportedTotalElements"])
        self.assertTrue(stats["truncated"])


if __name__ == "__main__":
    unittest.main()
