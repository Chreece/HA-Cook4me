from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components/cook4me"


def load_modules():
    package_name = "cook4me_food_intelligence_test"
    if package_name in sys.modules:
        return sys.modules[f"{package_name}.food_intelligence"]
    import types
    pkg = types.ModuleType(package_name)
    pkg.__path__ = [str(PACKAGE)]
    sys.modules[package_name] = pkg
    for name in ("inventory", "food_intelligence"):
        spec = importlib.util.spec_from_file_location(f"{package_name}.{name}", PACKAGE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return sys.modules[f"{package_name}.food_intelligence"]


class FoodIntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_modules()

    def test_partial_stock_reports_only_real_shortage(self):
        recipe = {"ingredients": [{"foodKey": "M_FOOD_RICE", "foodName": "Rice", "quantity": 500, "unit": "g"}]}
        stock = [{"key": "M_FOOD_RICE", "name": "Rice", "quantity": 180, "unit": "g"}]
        result = self.module.recipe_quantity_feasibility(recipe, stock)
        self.assertAlmostEqual(result["quantityCoverage"], 0.36)
        self.assertFalse(result["fullyAvailable"])
        self.assertEqual(result["shortages"][0]["missingQuantity"], 320)
        shopping = self.module.shortage_shopping_items(result)
        self.assertEqual(shopping[0]["quantity"], 320)
        self.assertEqual(shopping[0]["unit"], "g")

    def test_quantity_feasibility_converts_units(self):
        recipe = {"ingredients": [{"foodKey": "M_FOOD_RICE", "foodName": "Rice", "quantity": 750, "unit": "g"}]}
        stock = [{"key": "M_FOOD_RICE", "name": "Rice", "quantity": 1, "unit": "kg"}]
        result = self.module.recipe_quantity_feasibility(recipe, stock)
        self.assertTrue(result["fullyAvailable"])
        self.assertEqual(result["quantityCoverage"], 1.0)
        self.assertEqual(result["items"][0]["missingQuantity"], 0)

    def test_unlimited_stock_is_enough(self):
        recipe = {"ingredients": [{"foodKey": "M_FOOD_WATER", "foodName": "Water", "quantity": 2, "unit": "l"}]}
        stock = [{"key": "M_FOOD_WATER", "name": "Water", "unlimited": True, "unit": "l"}]
        result = self.module.recipe_quantity_feasibility(recipe, stock)
        self.assertTrue(result["fullyAvailable"])
        self.assertTrue(result["items"][0]["unlimited"])

    def test_incompatible_units_are_unknown_not_fake_shortage(self):
        recipe = {"ingredients": [{"foodKey": "M_FOOD_MILK", "foodName": "Milk", "quantity": 500, "unit": "ml"}]}
        stock = [{"key": "M_FOOD_MILK", "name": "Milk", "quantity": 2, "unit": "pcs"}]
        result = self.module.recipe_quantity_feasibility(recipe, stock)
        self.assertEqual(result["items"][0]["status"], "incompatible_unit")
        self.assertEqual(result["shortages"], [])
        self.assertEqual(len(result["unknown"]), 1)
        self.assertEqual(self.module.shortage_shopping_items(result), [])

    def test_unknown_recipe_amount_is_explicitly_unknown(self):
        recipe = {"ingredients": [{"foodKey": "M_FOOD_ONION", "foodName": "Onion"}]}
        stock = [{"key": "M_FOOD_ONION", "name": "Onion", "quantity": 3, "unit": "pcs"}]
        result = self.module.recipe_quantity_feasibility(recipe, stock)
        self.assertEqual(result["items"][0]["status"], "unknown_requirement")
        self.assertEqual(result["confidence"], 0.0)

    def test_staples_do_not_degrade_quantity_coverage(self):
        recipe = {"ingredients": [{"foodKey": "M_FOOD_SALT", "foodName": "Salt", "quantity": 2, "unit": "g"}]}
        result = self.module.recipe_quantity_feasibility(
            recipe,
            [],
            availability=[{"key": "M_FOOD_SALT", "name": "Salt", "status": "staple"}],
        )
        self.assertEqual(result["items"][0]["status"], "staple")
        self.assertEqual(result["quantityCoverage"], 1.0)

    def test_nutrition_goal_bonus_is_coverage_gated_and_bounded(self):
        low = self.module.nutrition_goal_bonus(
            {"coverage": 0.2, "perServing": {"protein": 100}}, "high_protein"
        )
        self.assertEqual(low["bonus"], 0)
        high = self.module.nutrition_goal_bonus(
            {"coverage": 1.0, "perServing": {"protein": 100}}, "high_protein"
        )
        self.assertEqual(high["bonus"], 20)
        self.assertLessEqual(high["bonus"], 20)

    def test_meal_allocation_splits_nutrition_by_serving_share(self):
        result = self.module.allocate_meal_nutrition(
            {"energyKcal": 800, "protein": 40},
            4,
            [{"name": "Chris", "servings": 1.5}, {"name": "Alex", "servings": 1}],
        )
        self.assertEqual(result["assignedServings"], 2.5)
        self.assertEqual(result["unassignedServings"], 1.5)
        self.assertEqual(result["allocations"][0]["nutrition"]["energyKcal"], 300)
        self.assertEqual(result["allocations"][0]["nutrition"]["protein"], 15)


if __name__ == "__main__":
    unittest.main()
