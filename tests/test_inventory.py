from __future__ import annotations

from datetime import date
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
        self.assertEqual([lot["quantity"] for lot in updated[0]["lots"]], [500, 1000])

    def test_legacy_single_date_stock_migrates_to_one_batch(self):
        stock = self.module.normalize_inventory(
            [
                {
                    "key": "M_FOOD_BUTTER",
                    "name": "Butter",
                    "quantity": 250,
                    "unit": "g",
                    "bestBefore": "2026-09-10",
                }
            ]
        )
        self.assertEqual(
            stock[0]["lots"],
            [{"quantity": 250, "bestBefore": "2026-09-10"}],
        )
        self.assertEqual(stock[0]["quantity"], 250)
        self.assertEqual(stock[0]["bestBefore"], "2026-09-10")

    def test_unlimited_stock_never_gets_reduced(self):
        stock = [{"key": "M_FOOD_WATER", "name": "Water", "unlimited": True, "unit": "l"}]
        after, report = self.module.apply_consumption(
            stock,
            [{"identity": "k:M_FOOD_WATER", "quantity": 2, "unit": "l", "consume": True}],
        )
        self.assertEqual(after, stock)
        self.assertEqual(report["skipped"][0]["reason"], "unlimited")

    def test_best_before_is_stored_for_finite_and_unlimited_stock(self):
        finite = self.module.add_inventory_item(
            [],
            {"key": "M_FOOD_YOGURT", "name": "Yogurt"},
            quantity=500,
            unit="g",
            best_before="2026-09-20",
        )
        unlimited = self.module.add_inventory_item(
            [],
            {"key": "M_FOOD_WATER", "name": "Water"},
            unlimited=True,
            best_before="2027-01-01",
        )
        self.assertEqual(finite[0]["bestBefore"], "2026-09-20")
        self.assertEqual(
            finite[0]["lots"],
            [{"quantity": 500, "bestBefore": "2026-09-20"}],
        )
        self.assertEqual(unlimited[0]["bestBefore"], "2027-01-01")
        self.assertNotIn("lots", unlimited[0])

    def test_finite_expiry_requires_amount(self):
        with self.assertRaisesRegex(ValueError, "attached to an amount"):
            self.module.add_inventory_item(
                [],
                {"key": "M_FOOD_YOGURT", "name": "Yogurt"},
                best_before="2026-09-20",
            )

    def test_restock_preserves_amount_per_expiry_batch(self):
        stock = [
            {
                "key": "M_FOOD_BUTTER",
                "name": "Butter",
                "quantity": 250,
                "unit": "g",
                "bestBefore": "2026-10-15",
            }
        ]
        updated = self.module.add_inventory_item(
            stock,
            {"key": "M_FOOD_BUTTER", "name": "Butter"},
            quantity=250,
            unit="g",
            best_before="2026-09-30",
        )
        self.assertEqual(updated[0]["quantity"], 500)
        self.assertEqual(updated[0]["bestBefore"], "2026-09-30")
        self.assertEqual(
            updated[0]["lots"],
            [
                {"quantity": 250, "bestBefore": "2026-09-30"},
                {"quantity": 250, "bestBefore": "2026-10-15"},
            ],
        )

    def test_best_before_can_be_edited_and_cleared(self):
        stock = [
            {
                "key": "M_FOOD_MILK",
                "name": "Milk",
                "quantity": 1,
                "unit": "l",
                "bestBefore": "2026-09-10",
            }
        ]
        updated = self.module.update_inventory_item(
            stock,
            "k:M_FOOD_MILK",
            quantity=1,
            unit="l",
            best_before="2026-09-12",
        )
        self.assertEqual(updated[0]["bestBefore"], "2026-09-12")
        self.assertEqual(updated[0]["lots"][0]["bestBefore"], "2026-09-12")
        cleared = self.module.update_inventory_item(
            updated,
            "k:M_FOOD_MILK",
            quantity=1,
            unit="l",
            best_before="",
        )
        self.assertNotIn("bestBefore", cleared[0])
        self.assertNotIn("bestBefore", cleared[0]["lots"][0])

    def test_batch_list_can_be_edited_without_collapsing_dates(self):
        stock = [
            {
                "key": "M_FOOD_MILK",
                "name": "Milk",
                "unit": "l",
                "lots": [
                    {"quantity": 1, "bestBefore": "2026-09-10"},
                    {"quantity": 2, "bestBefore": "2026-09-20"},
                ],
            }
        ]
        updated = self.module.update_inventory_item(
            stock,
            "k:M_FOOD_MILK",
            unit="l",
            lots=[
                {"quantity": 0.5, "bestBefore": "2026-09-10"},
                {"quantity": 2, "bestBefore": "2026-09-20"},
            ],
        )
        self.assertEqual(updated[0]["quantity"], 2.5)
        self.assertEqual(len(updated[0]["lots"]), 2)
        self.assertEqual(updated[0]["bestBefore"], "2026-09-10")

    def test_invalid_best_before_is_rejected_on_user_write(self):
        with self.assertRaises(ValueError):
            self.module.add_inventory_item(
                [],
                {"key": "M_FOOD_EGG", "name": "Egg"},
                quantity=6,
                unit="pcs",
                best_before="31-12-2026",
            )

    def test_expiry_window_reports_only_the_expiring_batch_amount(self):
        stock = [
            {"key": "M_FOOD_PAST", "name": "Past", "unlimited": True, "bestBefore": "2026-09-06"},
            {
                "key": "M_FOOD_TODAY",
                "name": "Today",
                "unit": "g",
                "lots": [
                    {"quantity": 100, "bestBefore": "2026-09-07"},
                    {"quantity": 900, "bestBefore": "2026-10-07"},
                ],
            },
            {"key": "M_FOOD_SOON", "name": "Soon", "quantity": 1, "unit": "pcs", "bestBefore": "2026-09-10"},
            {"key": "M_FOOD_LATER", "name": "Later", "quantity": 1, "unit": "pcs", "bestBefore": "2026-09-11"},
        ]
        rows = self.module.expiring_inventory_items(
            stock,
            today=date(2026, 9, 7),
            within_days=3,
            include_past=True,
        )
        self.assertEqual([row["name"] for row in rows], ["Past", "Today", "Soon"])
        self.assertEqual([row["daysRemaining"] for row in rows], [-1, 0, 3])
        self.assertEqual(rows[1]["quantity"], 100)
        self.assertTrue(rows[0]["pastBestBefore"])

    def test_recipe_expiry_priority_uses_next_valid_batch_and_skips_past_batch(self):
        stock = [
            {
                "key": "M_FOOD_DATES",
                "name": "Dattel",
                "unit": "g",
                "lots": [
                    {"quantity": 50, "bestBefore": "2026-09-06"},
                    {"quantity": 150, "bestBefore": "2026-09-08"},
                ],
            },
        ]
        recipe = {
            "ingredients": [
                {"foodKey": "M_FOOD_DATES", "foodName": "Datteln"},
            ]
        }
        priority = self.module.recipe_expiry_priority(
            recipe,
            stock,
            today=date(2026, 9, 7),
            within_days=3,
        )
        self.assertEqual(len(priority["ingredients"]), 1)
        self.assertEqual(priority["ingredients"][0]["identity"], "k:M_FOOD_DATES")
        self.assertEqual(priority["ingredients"][0]["daysRemaining"], 1)
        self.assertEqual(priority["ingredients"][0]["quantity"], 150)
        self.assertGreater(priority["priority"], 0)

    def test_recipe_consumption_matches_food_key_not_recipe_wording(self):
        stock = [
            {
                "key": "M_FOOD_SALMON",
                "name": "Lachsfilet",
                "quantity": 1,
                "unit": "kg",
                "bestBefore": "2026-09-09",
            }
        ]
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
        self.assertEqual(rows[0]["stockBestBefore"], "2026-09-09")
        self.assertEqual(rows[0]["stockLots"][0]["bestBefore"], "2026-09-09")
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

    def test_consumption_uses_earliest_expiry_first_then_advances_date(self):
        stock = [
            {
                "key": "M_FOOD_BUTTER",
                "name": "Butter",
                "unit": "g",
                "lots": [
                    {"quantity": 250, "bestBefore": "2026-09-10"},
                    {"quantity": 500, "bestBefore": "2026-10-01"},
                ],
            }
        ]
        after, report = self.module.apply_consumption(
            stock,
            [{"identity": "k:M_FOOD_BUTTER", "quantity": 250, "unit": "g", "consume": True}],
        )
        self.assertEqual(after[0]["quantity"], 500)
        self.assertEqual(after[0]["bestBefore"], "2026-10-01")
        self.assertEqual(
            after[0]["lots"],
            [{"quantity": 500, "bestBefore": "2026-10-01"}],
        )
        self.assertEqual(report["deductedLots"][0]["bestBefore"], "2026-09-10")

    def test_partial_old_batch_keeps_old_expiry_until_that_batch_is_empty(self):
        stock = [
            {
                "key": "M_FOOD_BUTTER",
                "name": "Butter",
                "unit": "g",
                "lots": [
                    {"quantity": 250, "bestBefore": "2026-09-10"},
                    {"quantity": 500, "bestBefore": "2026-10-01"},
                ],
            }
        ]
        after, _report = self.module.apply_consumption(
            stock,
            [{"identity": "k:M_FOOD_BUTTER", "quantity": 100, "unit": "g", "consume": True}],
        )
        self.assertEqual(after[0]["quantity"], 650)
        self.assertEqual(after[0]["bestBefore"], "2026-09-10")
        self.assertEqual(after[0]["lots"][0]["quantity"], 150)

    def test_cross_batch_consumption_continues_into_next_expiry(self):
        stock = [
            {
                "key": "M_FOOD_BUTTER",
                "name": "Butter",
                "unit": "g",
                "lots": [
                    {"quantity": 250, "bestBefore": "2026-09-10"},
                    {"quantity": 500, "bestBefore": "2026-10-01"},
                ],
            }
        ]
        after, report = self.module.apply_consumption(
            stock,
            [{"identity": "k:M_FOOD_BUTTER", "quantity": 300, "unit": "g", "consume": True}],
        )
        self.assertEqual(after[0]["quantity"], 450)
        self.assertEqual(after[0]["bestBefore"], "2026-10-01")
        self.assertEqual(after[0]["lots"][0]["quantity"], 450)
        self.assertEqual(len(report["deductedLots"]), 2)

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
