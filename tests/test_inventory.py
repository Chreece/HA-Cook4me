from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "cook4me_inventory_test",
        ROOT / "custom_components/cook4me/inventory.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_existing_stock_is_incremented_with_safe_unit_conversion(self):
        stock = [{"key": "M_FOOD_RICE", "name": "Rice", "quantity": 500, "unit": "g"}]
        updated = self.module.add_inventory_item(
            stock,
            {"key": "M_FOOD_RICE", "name": "Rice"},
            quantity=1,
            unit="kg",
        )
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["quantity"], 1500)
        self.assertEqual(updated[0]["unit"], "g")

    def test_unlimited_stock_never_gets_reduced(self):
        stock = [{"key": "M_FOOD_WATER", "name": "Water", "unlimited": True, "unit": "l"}]
        after, report = self.module.apply_consumption(
            stock,
            [{"identity": "k:M_FOOD_WATER", "quantity": 2, "unit": "l", "consume": True}],
        )
        self.assertEqual(after, stock)
        self.assertEqual(report["skipped"][0]["reason"], "unlimited")

    def test_recipe_consumption_matches_food_key_not_recipe_wording(self):
        stock = [{"key": "M_FOOD_SALMON", "name": "Lachsfilet", "quantity": 1, "unit": "kg"}]
        recipe = {
            "title": "Test",
            "ingredients": [
                {
                    "foodKey": "M_FOOD_SALMON",
                    "foodName": "Lachsfilet",
                    "name": "Lachsfilet (à 100 g)",
                    "quantity": 200,
                    "unit": "g",
                }
            ],
        }
        rows = self.module.recipe_consumption_items(recipe, stock)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["identity"], "k:M_FOOD_SALMON")
        self.assertEqual(rows[0]["quantity"], 200)
        self.assertEqual(rows[0]["unit"], "g")
        self.assertTrue(rows[0]["consume"])

    def test_confirmation_deducts_recipe_amount_from_stock_unit(self):
        stock = [{"key": "M_FOOD_RICE", "name": "Rice", "quantity": 1, "unit": "kg"}]
        after, report = self.module.apply_consumption(
            stock,
            [{"identity": "k:M_FOOD_RICE", "quantity": 200, "unit": "g", "consume": True}],
        )
        self.assertAlmostEqual(after[0]["quantity"], 0.8)
        self.assertEqual(after[0]["unit"], "kg")
        self.assertEqual(len(report["deducted"]), 1)

    def test_depleted_stock_is_removed(self):
        stock = [{"key": "M_FOOD_EGG", "name": "Egg", "quantity": 2, "unit": "pcs"}]
        after, report = self.module.apply_consumption(
            stock,
            [{"identity": "k:M_FOOD_EGG", "quantity": 2, "unit": "", "consume": True}],
        )
        self.assertEqual(after, [])
        self.assertEqual(report["depleted"][0]["identity"], "k:M_FOOD_EGG")


if __name__ == "__main__":
    unittest.main()
