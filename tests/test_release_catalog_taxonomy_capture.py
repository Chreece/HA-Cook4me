from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "capture_release_catalog_taxonomy_v2.py"
spec = importlib.util.spec_from_file_location("capture_release_catalog_taxonomy_v2", SCRIPT)
assert spec and spec.loader
taxonomy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = taxonomy
spec.loader.exec_module(taxonomy)


class ReleaseCatalogTaxonomyCaptureTests(unittest.TestCase):
    def test_taxonomy_export_keeps_only_classification_facts(self):
        root = {
            "fid": {"functionalId": "r1"},
            "groupingId": {"functionalId": "g1"},
            "lang": "en",
            "market": "GS_GB",
            "title": "Must not be persisted by taxonomy helper",
            "steps": [{"description": "secretly huge detail"}],
            "ingredients": [{"food": {"key": "M_FOOD_1"}}],
            "courses": [{"key": "MAIN_COURSE", "name": "Main course"}],
            "occasions": [{"key": "DINNER", "name": "Dinner"}],
            "excludedFoods": [{"key": "FISH", "name": "Fish"}],
            "detectedExcludedFoods": [{"key": "MEAT", "name": "Meat"}],
            "classifications": [{"key": "VEGETARIAN", "name": "Vegetarian"}],
            "domain": {"key": "FOOD", "name": "Food"},
        }
        row = taxonomy._taxonomy(root, "v1")
        self.assertEqual("v1", row["variantId"])
        self.assertEqual("g1", row["groupingFunctionalId"])
        self.assertEqual("MAIN_COURSE", row["courses"][0]["key"])
        self.assertEqual("DINNER", row["occasions"][0]["key"])
        self.assertEqual("FISH", row["excludedFoods"][0]["key"])
        self.assertEqual("MEAT", row["detectedExcludedFoods"][0]["key"])
        self.assertEqual("VEGETARIAN", row["classifications"][0]["key"])
        self.assertNotIn("title", row)
        self.assertNotIn("steps", row)
        self.assertNotIn("ingredients", row)

    def test_key_name_normalization_accepts_provider_string_or_object(self):
        self.assertEqual([{"key": "STARTER"}], taxonomy._key_name_list(["STARTER"]))
        self.assertEqual(
            [{"key": "MAIN_COURSE", "name": "Main course"}],
            taxonomy._key_name_list([{"key": "MAIN_COURSE", "name": "Main course"}]),
        )


if __name__ == "__main__":
    unittest.main()
