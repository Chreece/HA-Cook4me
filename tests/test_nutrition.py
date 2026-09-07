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

    package = types.ModuleType("cook4me_nutrition_test")
    package.__path__ = []
    const = types.ModuleType("cook4me_nutrition_test.const")
    const.DOMAIN = "cook4me"
    sys.modules["cook4me_nutrition_test"] = package
    sys.modules["cook4me_nutrition_test.const"] = const

    spec = importlib.util.spec_from_file_location(
        "cook4me_nutrition_test.nutrition",
        ROOT / "custom_components/cook4me/nutrition.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NutritionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def profile(self, kcal, protein, *, source="usda_fdc", basis_unit="g"):
        return {
            "basisQuantity": 100,
            "basisUnit": basis_unit,
            "values": {
                "energyKcal": kcal,
                "protein": protein,
                "carbohydrates": 10,
                "fat": 2,
            },
            "source": source,
        }

    def test_amount_scaling_and_unit_conversion(self):
        values = self.module.nutrition_for_amount(self.profile(100, 10), 0.25, "kg")
        self.assertAlmostEqual(values["energyKcal"], 250)
        self.assertAlmostEqual(values["protein"], 25)

    def test_exact_scanned_stock_wins_over_generic_reference(self):
        recipe = {
            "servings": 2,
            "ingredients": [
                {"foodKey": "M_FOOD_TOFU", "foodName": "Tofu", "quantity": 150, "unit": "g"}
            ],
        }
        inventory = [
            {"key": "M_FOOD_TOFU", "name": "Tofu", "quantity": 300, "unit": "g"}
        ]
        generic = {
            "k:M_FOOD_TOFU": {"nutrition": self.profile(80, 8)}
        }
        stock_lots = {
            "k:M_FOOD_TOFU": [
                {
                    "quantity": 300,
                    "unit": "g",
                    "bestBefore": "2026-09-10",
                    "nutrition": self.profile(120, 14, source="open_food_facts"),
                    "barcode": "12345678",
                }
            ]
        }
        result = self.module.calculate_recipe_nutrition(
            recipe, inventory, generic=generic, stock_lots=stock_lots
        )
        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual(result["totals"]["energyKcal"], 180.0)
        self.assertEqual(result["totals"]["protein"], 21.0)
        self.assertEqual(result["perServing"]["energyKcal"], 90.0)
        self.assertEqual(result["sourceKinds"], ["exact_product"])

    def test_generic_fills_only_uncovered_exact_stock(self):
        recipe = {
            "ingredients": [
                {"foodKey": "M_FOOD_RICE", "foodName": "Rice", "quantity": 200, "unit": "g"}
            ]
        }
        inventory = [
            {"key": "M_FOOD_RICE", "name": "Rice", "quantity": 100, "unit": "g"}
        ]
        stock_lots = {
            "k:M_FOOD_RICE": [
                {
                    "quantity": 100,
                    "unit": "g",
                    "nutrition": self.profile(100, 2, source="open_food_facts"),
                }
            ]
        }
        generic = {
            "k:M_FOOD_RICE": {"nutrition": self.profile(80, 3)}
        }
        result = self.module.calculate_recipe_nutrition(
            recipe, inventory, generic=generic, stock_lots=stock_lots
        )
        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual(result["totals"]["energyKcal"], 180.0)
        self.assertEqual(result["totals"]["protein"], 5.0)
        self.assertEqual(result["sourceKinds"], ["exact_product", "generic_reference"])
        self.assertTrue(result["estimated"])

    def test_incompatible_piece_quantity_is_reported_partial_not_guessed(self):
        recipe = {
            "ingredients": [
                {"foodKey": "M_FOOD_EGG", "foodName": "Egg", "quantity": 2, "unit": "pcs"}
            ]
        }
        generic = {
            "k:M_FOOD_EGG": {"nutrition": self.profile(140, 13)}
        }
        result = self.module.calculate_recipe_nutrition(recipe, [], generic=generic)
        self.assertEqual(result["coverage"], 0.0)
        self.assertEqual(result["totals"], {})
        self.assertEqual(
            result["ingredients"][0]["reason"],
            "nutrition_reference_missing_or_incompatible_unit",
        )

    def test_fdc_candidate_and_nutrients_are_normalized(self):
        foods = [
            {
                "fdcId": 1,
                "description": "Dates, medjool",
                "dataType": "Foundation",
                "foodNutrients": [
                    {"nutrientName": "Energy", "unitName": "KCAL", "value": 277},
                    {"nutrientName": "Protein", "unitName": "G", "value": 1.81},
                    {"nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 75},
                    {"nutrientName": "Total lipid (fat)", "unitName": "G", "value": 0.15},
                    {"nutrientName": "Fiber, total dietary", "unitName": "G", "value": 6.7},
                    {"nutrientName": "Sodium, Na", "unitName": "MG", "value": 1},
                ],
            },
            {
                "fdcId": 2,
                "description": "Date pudding",
                "dataType": "Survey (FNDDS)",
                "foodNutrients": [],
            },
        ]
        selected, score = self.module.select_fdc_candidate("Dates", foods)
        self.assertEqual(selected["fdcId"], 1)
        self.assertGreaterEqual(score, 0.86)
        profile = self.module.nutrition_from_fdc_food(selected, query="Dates")
        self.assertEqual(profile["basisUnit"], "g")
        self.assertEqual(profile["values"]["energyKcal"], 277)
        self.assertAlmostEqual(profile["values"]["sodium"], 0.001)
        self.assertAlmostEqual(profile["values"]["salt"], 0.0025)


if __name__ == "__main__":
    unittest.main()
