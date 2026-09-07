from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
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
        def __init__(self,*_a,**_k): self.saved=None
        def __class_getitem__(cls,_item): return cls
        async def async_load(self): return None
        async def async_save(self,data): self.saved=data
    ha_storage.Store = Store
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.storage"] = ha_storage
    pkg = types.ModuleType("cook4me_meal_history_test")
    pkg.__path__ = [str(PACKAGE)]
    sys.modules[pkg.__name__] = pkg
    const = types.ModuleType(f"{pkg.__name__}.const")
    const.DOMAIN = "cook4me"
    sys.modules[const.__name__] = const
    for name in ("inventory", "food_intelligence", "meal_history"):
        spec = importlib.util.spec_from_file_location(f"{pkg.__name__}.{name}", PACKAGE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return sys.modules[f"{pkg.__name__}.meal_history"]


class MealHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_record_allocates_confirmed_nutrition_per_person(self):
        store = self.module.Cook4MeMealHistoryStore(object(), "entry")
        row = asyncio.run(store.async_record(
            recipe={"recipeTitle":"Test meal","servings":4},
            nutrition={"totals":{"energyKcal":800,"protein":40},"coverage":1.0},
            allocations=[{"name":"Chris","servings":1.5},{"name":"Alex","servings":1}],
        ))
        self.assertEqual(row["allocations"][0]["nutrition"]["energyKcal"], 300)
        self.assertEqual(row["unassignedServings"], 1.5)

    def test_today_is_calendar_day_not_rolling_24_hours(self):
        store = self.module.Cook4MeMealHistoryStore(object(), "entry")
        reference = datetime(2026,9,7,10,0,tzinfo=timezone(timedelta(hours=2)))
        # 23 hours old but on the previous local calendar day: excluded from today.
        yesterday = reference - timedelta(hours=23)
        today = reference - timedelta(hours=1)
        store._data["meals"] = [
            {"timestamp": yesterday.isoformat(), "nutrition":{"totals":{"energyKcal":500}}, "allocations":[]},
            {"timestamp": today.isoformat(), "nutrition":{"totals":{"energyKcal":300}}, "allocations":[]},
        ]
        summary = store.summary(now=reference)
        self.assertEqual(summary["today"]["mealCount"], 1)
        self.assertEqual(summary["today"]["totals"]["energyKcal"], 300)
        self.assertEqual(summary["week"]["mealCount"], 2)


if __name__ == "__main__":
    unittest.main()
