from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_modules():
    ha = types.ModuleType("homeassistant")
    ha_core = types.ModuleType("homeassistant.core")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_storage = types.ModuleType("homeassistant.helpers.storage")
    ha_core.HomeAssistant = object

    class Store:
        def __init__(self, *args, **kwargs):
            self.saved = None

        def __class_getitem__(cls, _item):
            return cls

        async def async_load(self):
            return None

        async def async_save(self, data):
            self.saved = data

    ha_storage.Store = Store
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.storage"] = ha_storage

    package_name = "cook4me_lifecycle_test"
    package = types.ModuleType(package_name)
    package.__path__ = []
    const = types.ModuleType(f"{package_name}.const")
    const.DOMAIN = "cook4me"
    sys.modules[package_name] = package
    sys.modules[f"{package_name}.const"] = const

    def load(name: str, filename: str):
        spec = importlib.util.spec_from_file_location(
            f"{package_name}.{name}",
            ROOT / "custom_components/cook4me" / filename,
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    inventory = load("inventory", "inventory.py")
    today = load("today_logic", "today_logic.py")
    costs = load("costs", "costs.py")
    costing = load("costing", "costing.py")
    lifecycle = load("meal_lifecycle", "meal_lifecycle.py")
    return inventory, costs, costing, lifecycle


class MealLifecycleV20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory, cls.costs, cls.costing, cls.lifecycle = load_modules()

    def recipe(self, amount, unit="g", *, key="M_FOOD_TOMATO", name="Tomato"):
        return {
            "title": "Recipe",
            "servings": 2,
            "ingredients": [
                {"foodKey": key, "foodName": name, "quantity": amount, "unit": unit}
            ],
        }

    def slot(self, slot_id, amount, unit="g"):
        return {
            "id": slot_id,
            "date": "2026-09-08",
            "mealType": "dinner",
            "recipe": self.recipe(amount, unit),
        }

    def test_two_meals_share_one_stock_reservation(self):
        inventory = [{
            "key": "M_FOOD_TOMATO", "name": "Tomato", "quantity": 500,
            "unit": "g", "lots": [{"id": "lot-1", "quantity": 500}],
        }]
        status = self.lifecycle.reservation_status(
            [self.slot("a", 300), self.slot("b", 300)], inventory
        )
        self.assertEqual(len(status["items"]), 1)
        self.assertAlmostEqual(status["items"][0]["quantity"], 600)
        self.assertAlmostEqual(status["items"][0]["available"], 500)
        self.assertAlmostEqual(status["items"][0]["shortage"], 100)
        self.assertFalse(status["fullyCovered"])

    def test_plan_aggregates_only_proven_convertible_units(self):
        requirements = self.lifecycle.planned_requirements([
            self.slot("a", 0.5, "kg"),
            self.slot("b", 250, "g"),
        ])
        self.assertEqual(len(requirements), 1)
        self.assertAlmostEqual(requirements[0]["quantity"], 0.75)
        self.assertEqual(requirements[0]["unit"], "kg")

        incompatible = self.lifecycle.planned_requirements([
            self.slot("c", 1, "pcs"),
            self.slot("d", 100, "g"),
        ])
        self.assertEqual(len(incompatible), 2)

    def test_leftovers_do_not_reserve_raw_stock_again(self):
        requirements = self.lifecycle.planned_requirements([
            {
                "id": "leftover",
                "date": "2026-09-08",
                "mealType": "lunch",
                "leftoverId": "left-1",
            }
        ])
        self.assertEqual(requirements, [])

    def cost_store(self):
        store = self.costs.Cook4MeCostStore(object(), "entry")
        store._loaded = True
        store._data = {
            "settings": {"currency": "", "country": "", "autoGlobalPrices": True},
            "references": {},
        }
        return store

    def add_reference(self, store, key, *, amount, currency, basis_quantity, basis_unit, source="purchase", confidence="exact_purchase"):
        store._data["references"][key] = {
            "identity": key.split("|")[0],
            "amount": amount,
            "currency": currency,
            "basisQuantity": basis_quantity,
            "basisUnit": basis_unit,
            "source": source,
            "confidence": confidence,
            "country": "",
            "date": "2026-09-08",
        }

    def test_exact_lot_purchase_cost_scales_to_recipe_amount(self):
        store = self.cost_store()
        self.add_reference(
            store, "lot:lot-1|EUR||purchase",
            amount=2.50, currency="EUR", basis_quantity=500, basis_unit="g",
        )
        inventory = [{
            "key": "M_FOOD_TOMATO", "name": "Tomato", "quantity": 500,
            "unit": "g", "lots": [{"id": "lot-1", "quantity": 500}],
        }]
        result = self.costing.calculate_recipe_cost(
            self.recipe(200), inventory, store
        )
        self.assertEqual(result["totalsByCurrency"], {"EUR": 1.0})
        self.assertEqual(result["perServingByCurrency"], {"EUR": 0.5})
        self.assertEqual(result["exactPurchaseCoverage"], 1.0)
        self.assertFalse(result["currencyConversionApplied"])

    def test_mixed_currencies_remain_separate(self):
        store = self.cost_store()
        self.add_reference(
            store, "lot:euro|EUR||purchase",
            amount=2, currency="EUR", basis_quantity=100, basis_unit="g",
        )
        self.add_reference(
            store, "lot:pound|GBP||purchase",
            amount=3, currency="GBP", basis_quantity=100, basis_unit="g",
        )
        inventory = [
            {"key": "A", "name": "A", "quantity": 100, "unit": "g", "lots": [{"id": "euro", "quantity": 100}]},
            {"key": "B", "name": "B", "quantity": 100, "unit": "g", "lots": [{"id": "pound", "quantity": 100}]},
        ]
        recipe = {
            "servings": 1,
            "ingredients": [
                {"foodKey": "A", "foodName": "A", "quantity": 100, "unit": "g"},
                {"foodKey": "B", "foodName": "B", "quantity": 100, "unit": "g"},
            ],
        }
        result = self.costing.calculate_recipe_cost(recipe, inventory, store)
        self.assertEqual(result["totalsByCurrency"], {"EUR": 2.0, "GBP": 3.0})
        self.assertFalse(result["currencyConversionApplied"])

    def test_incompatible_price_basis_is_not_guessed(self):
        store = self.cost_store()
        self.add_reference(
            store, "lot:lot-1|EUR||purchase",
            amount=2, currency="EUR", basis_quantity=100, basis_unit="ml",
        )
        inventory = [{
            "key": "M_FOOD_TOMATO", "name": "Tomato", "quantity": 100,
            "unit": "g", "lots": [{"id": "lot-1", "quantity": 100}],
        }]
        result = self.costing.calculate_recipe_cost(self.recipe(100), inventory, store)
        self.assertEqual(result["totalsByCurrency"], {})
        self.assertEqual(result["coverage"], 0.0)

    def test_global_observation_needs_explicit_package_basis(self):
        original = self.costing.lookup_open_prices
        try:
            self.costing.lookup_open_prices = lambda *args, **kwargs: {
                "ok": True,
                "items": [
                    {"barcode": "1", "pricePer": "KG", "basisQuantity": 1, "basisUnit": "kg", "usable": True},
                    {"barcode": "1", "pricePer": "UNIT", "basisQuantity": 500, "basisUnit": "g", "usable": True},
                ],
            }
            result = self.costing.lookup_open_prices_safe("1")
        finally:
            self.costing.lookup_open_prices = original
        self.assertFalse(result["items"][0]["usable"])
        self.assertEqual(result["items"][0]["costExclusionReason"], "no_explicit_package_basis")
        self.assertTrue(result["items"][1]["usable"])
        self.assertEqual(result["usableCount"], 1)

    def test_feedback_and_leftover_scaling(self):
        store = self.lifecycle.Cook4MeMealLifecycleStore(object(), "entry")
        store._loaded = True
        recipe = {"id": "r1", "title": "Good"}

        async def run():
            await store.async_set_feedback(recipe, rating=5, would_cook_again=True)
            leftover = await store.async_add_leftover_from_meal(
                {
                    "id": "m1", "title": "Good", "servings": 4,
                    "remainingServings": 2,
                    "cookedNutrition": {"totals": {"energyKcal": 800, "protein": 40}},
                },
                cost={"totalsByCurrency": {"EUR": 8}},
            )
            return leftover

        leftover = asyncio.run(run())
        self.assertGreater(store.feedback_bonus(recipe), 0)
        self.assertEqual(leftover["nutrition"]["totals"]["energyKcal"], 400)
        self.assertEqual(leftover["costByCurrency"], {"EUR": 4.0})


if __name__ == "__main__":
    unittest.main()
