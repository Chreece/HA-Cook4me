from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUSTOM = ROOT / "custom_components"
COOK4ME = CUSTOM / "cook4me"

# Load the pure-Python Cook4Me quantity modules without executing the Home
# Assistant integration package __init__.
custom_pkg = types.ModuleType("custom_components")
custom_pkg.__path__ = [str(CUSTOM)]
cook_pkg = types.ModuleType("custom_components.cook4me")
cook_pkg.__path__ = [str(COOK4ME)]
sys.modules.setdefault("custom_components", custom_pkg)
sys.modules.setdefault("custom_components.cook4me", cook_pkg)

from custom_components.cook4me.food_intelligence import recipe_quantity_feasibility


def garlic_recipe(*, count=1, quantity=1, unit="clove"):
    ingredient = {
        "key": "test:garlic",
        "foodKey": "test:garlic",
        "foodName": "garlic",
        "canonicalName": "garlic",
        "name": "garlic",
        "quantity": quantity,
        "unit": unit,
    }
    if unit == "clove":
        ingredient["unitKey"] = "UNIT_28"
    return {"ingredients": [dict(ingredient) for _ in range(count)]}


def garlic_stock(grams):
    return [{
        "key": "test:garlic",
        "name": "garlic",
        "unit": "g",
        "lots": [{"id": "garlic-lot", "quantity": grams}],
    }]


class ReviewedPortionStockCoverageTests(unittest.TestCase):
    def test_140g_garlic_covers_one_clove(self):
        result = recipe_quantity_feasibility(
            garlic_recipe(),
            garlic_stock(140),
            availability=[{"key": "test:garlic", "name": "garlic", "status": "at_home"}],
        )
        row = result["items"][0]
        self.assertEqual(row["status"], "enough")
        self.assertEqual(row["coverage"], 1.0)
        self.assertEqual(row["requiredQuantity"], 1)
        self.assertEqual(row["requiredUnit"], "clove")
        self.assertEqual(row["availableQuantity"], 1)
        self.assertEqual(row["missingQuantity"], 0)
        self.assertEqual(row["confidence"], "reviewed_portion")
        self.assertEqual(row["conversion"]["quantity"], 3)
        self.assertEqual(row["conversion"]["unit"], "g")
        self.assertEqual(row["conversion"]["kind"], "food_portion")

    def test_partial_gram_stock_maps_back_to_partial_clove(self):
        result = recipe_quantity_feasibility(
            garlic_recipe(),
            garlic_stock(1.5),
            availability=[{"key": "test:garlic", "name": "garlic", "status": "at_home"}],
        )
        row = result["items"][0]
        self.assertEqual(row["status"], "shortage")
        self.assertEqual(row["coverage"], 0.5)
        self.assertEqual(row["availableQuantity"], 0.5)
        self.assertEqual(row["missingQuantity"], 0.5)
        self.assertEqual(row["missingUnit"], "clove")

    def test_shared_gram_stock_is_not_double_counted_between_cloves(self):
        result = recipe_quantity_feasibility(
            garlic_recipe(count=2),
            garlic_stock(4.5),
            availability=[{"key": "test:garlic", "name": "garlic", "status": "at_home"}],
        )
        coverages = sorted(row["coverage"] for row in result["items"])
        self.assertEqual(coverages, [0.5, 1.0])
        self.assertEqual(result["quantityCoverage"], 0.75)
        self.assertFalse(result["fullyAvailable"])

    def test_direct_mass_comparison_stays_exact(self):
        result = recipe_quantity_feasibility(
            garlic_recipe(quantity=3, unit="g"),
            garlic_stock(140),
            availability=[{"key": "test:garlic", "name": "garlic", "status": "at_home"}],
        )
        row = result["items"][0]
        self.assertEqual(row["coverage"], 1.0)
        self.assertEqual(row["confidence"], "exact")
        self.assertNotIn("conversion", row)


if __name__ == "__main__":
    unittest.main()
