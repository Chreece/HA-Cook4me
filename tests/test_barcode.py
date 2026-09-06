from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    ha = types.ModuleType("homeassistant")
    ha_core = types.ModuleType("homeassistant.core")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_storage = types.ModuleType("homeassistant.helpers.storage")
    ha_core.HomeAssistant = object

    class Store:
        def __class_getitem__(cls, _item):
            return cls

    ha_storage.Store = Store
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.storage"] = ha_storage

    package = types.ModuleType("cook4me_barcode_test")
    package.__path__ = []
    const = types.ModuleType("cook4me_barcode_test.const")
    const.DOMAIN = "cook4me"
    sys.modules["cook4me_barcode_test"] = package
    sys.modules["cook4me_barcode_test.const"] = const

    spec = importlib.util.spec_from_file_location(
        "cook4me_barcode_test.barcode",
        ROOT / "custom_components/cook4me/barcode.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BarcodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_normalize_product_barcodes(self):
        self.assertEqual(self.module.normalize_barcode("4006 3813-3393 1"), "4006381333931")
        with self.assertRaises(ValueError):
            self.module.normalize_barcode("abc")

    def test_multi_pack_quantity_is_totalled(self):
        amount, unit = self.module.parse_package_quantity("2 x 125 g")
        self.assertEqual(amount, 250)
        self.assertEqual(unit, "g")

    def test_open_food_facts_structured_quantity_wins(self):
        product = self.module.normalize_openfoodfacts_payload(
            "4006381333931",
            {
                "product": {
                    "product_name": "Bio Butter",
                    "generic_name": "Butter",
                    "quantity": "250 g",
                    "product_quantity": 250,
                    "product_quantity_unit": "g",
                    "brands": "Example",
                }
            },
        )
        self.assertTrue(product["found"])
        self.assertEqual(product["name"], "Butter")
        self.assertEqual(product["quantity"], 250)
        self.assertEqual(product["unit"], "g")

    def test_generic_name_exact_match_is_confident(self):
        product = {"genericName": "Butter", "productName": "Example Bio Butter", "categories": []}
        catalog = [
            {"key": "M_FOOD_BUTTER", "name": "Butter"},
            {"key": "M_FOOD_OIL", "name": "Öl"},
        ]
        suggestions = self.module.suggest_catalog_matches(product, catalog)
        self.assertEqual(suggestions[0]["ingredient"]["key"], "M_FOOD_BUTTER")
        self.assertEqual(suggestions[0]["score"], 1.0)
        self.assertIsNotNone(self.module.confident_match(suggestions))

    def test_weak_category_similarity_does_not_auto_map(self):
        product = {"genericName": "", "productName": "Brand Mediterranean Mix", "categories": ["Olivenöl"]}
        catalog = [{"key": "M_FOOD_OIL", "name": "Olivenöl"}]
        suggestions = self.module.suggest_catalog_matches(product, catalog)
        self.assertEqual(suggestions[0]["score"], 0.94)
        self.assertIsNone(self.module.confident_match(suggestions))


if __name__ == "__main__":
    unittest.main()
