from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components/cook4me/vendor/cook4me_official_nutrition.py"
spec = importlib.util.spec_from_file_location("cook4me_official_nutrition_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class OfficialNutritionTests(unittest.TestCase):
    def test_unit_only_nutrients_do_not_fabricate_zero_values(self):
        result = mod.extract_official_nutrition(
            {
                "nutrition": {
                    "nutrients": {
                        "PROTEIN": {"unit": {"key": "UNIT_27"}},
                        "FAT": {"unit": {"key": "UNIT_27"}},
                    },
                    "areHPnnsPortionsManuallyModified": False,
                }
            }
        )
        self.assertIsNotNone(result)
        self.assertFalse(result["hasNumericValues"])
        self.assertFalse(result["hasPer100gValues"])
        self.assertNotIn("quantity", result["nutrients"][0])
        self.assertEqual(result["nutrients"][0]["unit"]["key"], "UNIT_27")

    def test_explicit_per_100g_values_are_preserved(self):
        result = mod.extract_official_nutrition(
            {
                "nutrition": {
                    "energyValue": "123.5",
                    "hierarchicalNutrients": [
                        {
                            "name": "Protein",
                            "valuePer100g": "8,25",
                            "unit": {"key": "UNIT_27", "abbreviation": "g"},
                        }
                    ],
                }
            }
        )
        self.assertTrue(result["hasPer100gValues"])
        self.assertEqual(result["energyPer100gValue"], 123.5)
        nutrient = result["hierarchicalNutrients"][0]
        self.assertEqual(nutrient["valuePer100g"], 8.25)
        self.assertEqual(nutrient["basisQuantity"], 100)
        self.assertEqual(nutrient["basisUnit"], "g")
        self.assertEqual(nutrient["unit"]["abbreviation"], "g")

    def test_flat_quantity_remains_basis_unspecified(self):
        result = mod.extract_official_nutrition(
            {
                "nutrition": {
                    "nutrients": [
                        {
                            "key": "CARBOHYDRATES",
                            "quantity": 17.4,
                            "unit": {"abbreviation": "g"},
                        }
                    ]
                }
            }
        )
        nutrient = result["nutrients"][0]
        self.assertEqual(nutrient["quantity"], 17.4)
        self.assertEqual(nutrient["basis"], "unspecified")
        self.assertFalse(result["hasPer100gValues"])

    def test_nested_hierarchical_values_are_flattened_with_path(self):
        result = mod.extract_official_nutrition(
            {
                "nutrition": {
                    "hierarchicalNutrients": [
                        {
                            "name": "Carbohydrates",
                            "hierarchicalNutrients": [
                                {
                                    "name": "Sugars",
                                    "valuePer100g": 4.2,
                                    "unit": {"name": "gram"},
                                }
                            ],
                        }
                    ]
                }
            }
        )
        self.assertEqual(len(result["hierarchicalNutrients"]), 1)
        row = result["hierarchicalNutrients"][0]
        self.assertEqual(row["path"], ["Carbohydrates", "Sugars"])
        self.assertEqual(row["valuePer100g"], 4.2)


if __name__ == "__main__":
    unittest.main()
