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

    def test_localized_name_unwraps_realm_list_transport_container(self):
        value = {
            "values": {
                "items": [
                    {"lang": "de", "market": "GS_DE", "value": "Kartoffel"},
                    {"lang": "en", "market": "GS_GB", "value": "Potato"},
                ]
            }
        }
        self.assertEqual("Potato", capture._localized_name(value, "en"))
        self.assertEqual("Kartoffel", capture._localized_name(value, "de"))

    def test_nested_transport_wrapper_is_unwrapped_by_apk_food_shape(self):
        raw = {
            "score": 1.0,
            "source": {
                "document": {
                    "key": "M_FOOD_305",
                    "name": {
                        "realmList": [
                            {"lang": "de", "market": "GS_DE", "value": "Mascarpone"},
                            {"lang": "en", "market": "GS_GB", "value": "Mascarpone"},
                        ]
                    },
                    "mixMedias": [],
                }
            },
        }
        food = capture._marketing_food_object(raw)
        self.assertIsNotNone(food)
        self.assertEqual("M_FOOD_305", food["key"])
        self.assertEqual("Mascarpone", capture._localized_name(food["name"], "en"))

    def test_normalization_keeps_provider_key_and_audits_conflicting_duplicates(self):
        payload = {
            "page": {"totalElements": 4},
            "content": [
                {"wrapper": {"key": "M_FOOD_1", "name": "Potato"}},
                {"wrapper": {"key": "M_FOOD_1", "name": "Potatoes"}},
                {"wrapper": {"key": "M_FOOD_2", "name": "Carrot"}},
                {"notFood": {"name": "No provider key"}},
            ],
        }
        rows, stats = capture.normalize_marketing_foods(payload, "en")
        self.assertEqual(["M_FOOD_1", "M_FOOD_2"], [row["key"] for row in rows])
        self.assertEqual("Potato", rows[0]["name"])
        self.assertEqual(["Potatoes"], rows[0]["aliases"])
        self.assertEqual(2, stats["uniqueKeys"])
        self.assertEqual(1, stats["unparsedRows"])
        self.assertEqual(0, stats["missingNameRows"])
        self.assertEqual(1, stats["duplicateRows"])
        self.assertEqual(1, stats["conflictingLabels"])
        self.assertEqual(4, stats["reportedTotalElements"])
        self.assertFalse(stats["truncated"])
        self.assertTrue(stats["unparsedShapeSamples"])

    def test_named_food_without_resolvable_apk_name_is_explicit_gap(self):
        payload = {
            "page": {"totalElements": 1},
            "content": [
                {
                    "wrapper": {
                        "key": "M_FOOD_1",
                        "name": {"realmList": [{"lang": "en", "market": "GS_GB"}]},
                    }
                }
            ],
        }
        rows, stats = capture.normalize_marketing_foods(payload, "en")
        self.assertEqual([], rows)
        self.assertEqual(1, stats["missingNameRows"])
        self.assertTrue(stats["missingNameShapeSamples"])

    def test_reported_total_detects_an_incomplete_size_limited_response(self):
        payload = {
            "page": {"totalElements": 6000},
            "content": [{"key": f"M_FOOD_{i}", "name": f"Food {i}"} for i in range(5000)],
        }
        rows, stats = capture.normalize_marketing_foods(payload, "en")
        self.assertEqual(5000, len(rows))
        self.assertEqual(6000, stats["reportedTotalElements"])
        self.assertTrue(stats["truncated"])

    def test_ambiguous_multiple_food_objects_are_not_guessed(self):
        raw = {
            "left": {"key": "M_FOOD_1", "name": "Potato"},
            "right": {"key": "M_FOOD_2", "name": "Carrot"},
        }
        self.assertIsNone(capture._marketing_food_object(raw))


if __name__ == "__main__":
    unittest.main()
