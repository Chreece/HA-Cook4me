from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components/cook4me"


def load_module():
    ha = types.ModuleType("homeassistant")
    ha_core = types.ModuleType("homeassistant.core")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_storage = types.ModuleType("homeassistant.helpers.storage")
    ha_core.HomeAssistant = object
    class Store:
        def __class_getitem__(cls, _item): return cls
    ha_storage.Store = Store
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.storage"] = ha_storage

    pkg = types.ModuleType("cook4me_nutrition_fefo_test")
    pkg.__path__ = [str(PACKAGE)]
    sys.modules[pkg.__name__] = pkg
    const = types.ModuleType(f"{pkg.__name__}.const")
    const.DOMAIN = "cook4me"
    sys.modules[const.__name__] = const
    for name in ("inventory", "nutrition", "nutrition_fefo"):
        spec = importlib.util.spec_from_file_location(f"{pkg.__name__}.{name}", PACKAGE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return sys.modules[f"{pkg.__name__}.nutrition_fefo"]


class NutritionFefoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    @staticmethod
    def profile(kcal):
        return {"basisQuantity": 100, "basisUnit": "g", "values": {"energyKcal": kcal, "protein": 10}}

    def test_opened_package_effective_expiry_selects_exact_product_nutrition(self):
        recipe = {"servings": 1, "ingredients": [{"foodKey": "M_FOOD_TOFU", "foodName": "Tofu", "quantity": 100, "unit": "g"}]}
        inventory = [{"key": "M_FOOD_TOFU", "name": "Tofu", "unit": "g", "lots": [
            {"id": "opened", "quantity": 200, "bestBefore": "2026-09-20", "openedAt": "2026-09-07", "useWithinDays": 2, "barcode": "11111111"},
            {"id": "closed", "quantity": 200, "bestBefore": "2026-09-12", "barcode": "22222222"},
        ]}]
        stock_lots = {"k:M_FOOD_TOFU": [
            {"inventoryLotId": "opened", "quantity": 200, "unit": "g", "barcode": "11111111", "nutrition": self.profile(100)},
            {"inventoryLotId": "closed", "quantity": 200, "unit": "g", "barcode": "22222222", "nutrition": self.profile(300)},
        ]}
        result = self.module.calculate_recipe_nutrition_fefo(recipe, inventory, stock_lots=stock_lots)
        self.assertEqual(result["totals"]["energyKcal"], 100)
        source = result["ingredients"][0]["sources"][0]
        self.assertEqual(source["lotId"], "opened")
        self.assertEqual(source["barcode"], "11111111")
        self.assertEqual(source["effectiveBestBefore"], "2026-09-09")
        self.assertEqual(result["sourceKinds"], ["exact_product"])

    def test_generic_reference_fills_only_amount_not_covered_by_exact_stock(self):
        recipe = {"servings": 2, "ingredients": [{"foodKey": "M_FOOD_TOFU", "foodName": "Tofu", "quantity": 100, "unit": "g"}]}
        inventory = [{"key": "M_FOOD_TOFU", "name": "Tofu", "unit": "g", "lots": [
            {"id": "exact", "quantity": 50, "bestBefore": "2026-09-10", "barcode": "11111111"},
        ]}]
        stock_lots = {"k:M_FOOD_TOFU": [
            {"inventoryLotId": "exact", "quantity": 50, "unit": "g", "barcode": "11111111", "nutrition": self.profile(200)},
        ]}
        generic = {"k:M_FOOD_TOFU": {"nutrition": self.profile(100)}}
        result = self.module.calculate_recipe_nutrition_fefo(recipe, inventory, generic=generic, stock_lots=stock_lots)
        self.assertEqual(result["totals"]["energyKcal"], 150)
        self.assertEqual(result["perServing"]["energyKcal"], 75)
        self.assertEqual(result["coverage"], 1)
        self.assertEqual(set(result["sourceKinds"]), {"exact_product", "generic_reference"})

    def test_unknown_recipe_unit_reports_zero_coverage_without_guessing(self):
        recipe = {"ingredients": [{"foodKey": "M_FOOD_ONION", "foodName": "Onion", "quantity": 2, "unit": "pcs"}]}
        generic = {"k:M_FOOD_ONION": {"nutrition": self.profile(40)}}
        result = self.module.calculate_recipe_nutrition_fefo(recipe, [], generic=generic)
        self.assertEqual(result["coverage"], 0)
        self.assertFalse(result["fullyCovered"])


if __name__ == "__main__":
    unittest.main()
