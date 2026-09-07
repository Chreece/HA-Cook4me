from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components/cook4me"


def load_modules():
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
    pkg = types.ModuleType("cook4me_nutrition_inventory_test")
    pkg.__path__ = [str(PACKAGE)]
    sys.modules[pkg.__name__] = pkg
    const = types.ModuleType(f"{pkg.__name__}.const")
    const.DOMAIN = "cook4me"
    sys.modules[const.__name__] = const
    for name in ("inventory", "nutrition", "nutrition_inventory"):
        spec = importlib.util.spec_from_file_location(f"{pkg.__name__}.{name}", PACKAGE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return sys.modules[f"{pkg.__name__}.nutrition_inventory"]


class FakeStore:
    def __init__(self, data):
        self._data = data
        self.saves = 0
    async def _save(self):
        self.saves += 1


class NutritionInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_modules()

    @staticmethod
    def nutrition(kcal=100):
        return {"basisQuantity": 100, "basisUnit": "g", "values": {"energyKcal": kcal, "protein": 10}}

    def test_linked_nutrition_survives_best_before_edit(self):
        store = FakeStore({"generic": {}, "stockLots": {"k:M_FOOD_TOFU": [{
            "quantity": 200, "unit": "g", "bestBefore": "2026-09-10", "nutrition": self.nutrition(), "barcode": "11111111"
        }]}})
        asyncio.run(self.module.async_link_latest_stock_nutrition(
            store, {"key": "M_FOOD_TOFU", "name": "Tofu"}, inventory_lot_id="lot-1"
        ))
        inventory = [{"key": "M_FOOD_TOFU", "name": "Tofu", "unit": "g", "lots": [{
            "id": "lot-1", "quantity": 200, "bestBefore": "2026-09-20", "barcode": "11111111"
        }]}]
        asyncio.run(self.module.async_reconcile_nutrition_inventory(store, inventory))
        record = store._data["stockLots"]["k:M_FOOD_TOFU"][0]
        self.assertEqual(record["inventoryLotId"], "lot-1")
        self.assertEqual(record["bestBefore"], "2026-09-20")
        self.assertEqual(record["quantity"], 200)

    def test_confirmed_consumption_uses_exact_lot_id_before_generic_fallback(self):
        store = FakeStore({
            "generic": {"k:M_FOOD_TOFU": {"nutrition": self.nutrition(50)}},
            "stockLots": {"k:M_FOOD_TOFU": [
                {"inventoryLotId": "lot-a", "quantity": 100, "unit": "g", "nutrition": self.nutrition(100), "barcode": "11111111"},
                {"inventoryLotId": "lot-b", "quantity": 100, "unit": "g", "nutrition": self.nutrition(300), "barcode": "22222222"},
            ]},
        })
        result = asyncio.run(self.module.async_consume_nutrition_report(store, {"deductedLots": [{
            "identity": "k:M_FOOD_TOFU", "lotId": "lot-b", "quantity": 50, "unit": "g", "barcode": "22222222"
        }]}))
        self.assertEqual(result["totals"]["energyKcal"], 150)
        records = store._data["stockLots"]["k:M_FOOD_TOFU"]
        self.assertEqual(records[0]["quantity"], 100)
        self.assertEqual(records[1]["quantity"], 50)
        self.assertEqual(result["sourceKinds"], ["exact_product"])


if __name__ == "__main__":
    unittest.main()
