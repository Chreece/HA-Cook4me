from pathlib import Path
import json
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
CUSTOM = ROOT / "custom_components"
COOK4ME = CUSTOM / "cook4me"
PORTIONS = COOK4ME / "catalog" / "price_portions.v1.json"
REFERENCES = COOK4ME / "catalog" / "price_reference_portions.v1.json"

custom_pkg = types.ModuleType("custom_components")
custom_pkg.__path__ = [str(CUSTOM)]
cook_pkg = types.ModuleType("custom_components.cook4me")
cook_pkg.__path__ = [str(COOK4ME)]
sys.modules.setdefault("custom_components", custom_pkg)
sys.modules.setdefault("custom_components.cook4me", cook_pkg)

from custom_components.cook4me.food_intelligence import recipe_quantity_feasibility


def _recipe(name, *, quantity, unit, key):
    ingredient = {
        "key": key,
        "foodKey": key,
        "foodName": name,
        "canonicalName": name,
        "name": name,
        "quantity": quantity,
        "unit": unit,
    }
    return {"ingredients": [ingredient]}


def _stock(name, *, quantity, unit, key):
    return [{
        "key": key,
        "name": name,
        "unit": unit,
        "lots": [{"id": key + ":lot", "quantity": quantity}],
    }]


def _portion_rows():
    rows = json.loads(PORTIONS.read_text(encoding="utf-8"))["portions"]
    rows += json.loads(REFERENCES.read_text(encoding="utf-8"))["portions"]
    return rows


class UniversalReviewedStockCoverageTests(unittest.TestCase):
    def test_every_reviewed_portion_maps_gram_stock_to_recipe_measure(self):
        checked = 0
        for index, portion in enumerate(_portion_rows()):
            measure = portion["measure"]
            grams = float(portion["grams"])
            for alias_index, name in enumerate(portion["names"]):
                key = f"portion:{index}:{alias_index}"
                with self.subTest(name=name, measure=measure, grams=grams):
                    result = recipe_quantity_feasibility(
                        _recipe(name, quantity=1, unit=measure, key=key),
                        _stock(name, quantity=grams, unit="g", key=key),
                    )
                    row = result["items"][0]
                    self.assertEqual(row["status"], "enough")
                    self.assertEqual(row["coverage"], 1.0)
                    self.assertEqual(row["missingQuantity"], 0)
                    self.assertEqual(row["confidence"], "reviewed_portion")
                checked += 1
        self.assertGreaterEqual(checked, 150)

    def test_every_reviewed_portion_reports_partial_stock_instead_of_zero(self):
        checked = 0
        for index, portion in enumerate(_portion_rows()):
            measure = portion["measure"]
            grams = float(portion["grams"])
            name = portion["names"][0]
            key = f"partial:{index}"
            with self.subTest(name=name, measure=measure):
                result = recipe_quantity_feasibility(
                    _recipe(name, quantity=1, unit=measure, key=key),
                    _stock(name, quantity=grams / 2, unit="g", key=key),
                )
                row = result["items"][0]
                self.assertEqual(row["status"], "shortage")
                self.assertAlmostEqual(row["coverage"], 0.5, places=3)
                self.assertGreater(row["coverage"], 0)
                self.assertAlmostEqual(row["missingQuantity"], 0.5, places=6)
            checked += 1
        self.assertGreaterEqual(checked, 129)

    def test_every_reviewed_piece_mapping_works_in_reverse(self):
        checked = 0
        for index, portion in enumerate(_portion_rows()):
            if portion["measure"] != "piece":
                continue
            grams = float(portion["grams"])
            name = portion["names"][0]
            key = f"reverse:{index}"
            with self.subTest(name=name, grams=grams):
                result = recipe_quantity_feasibility(
                    _recipe(name, quantity=grams, unit="g", key=key),
                    _stock(name, quantity=1, unit="pcs", key=key),
                )
                row = result["items"][0]
                self.assertEqual(row["status"], "enough")
                self.assertEqual(row["coverage"], 1.0)
                self.assertEqual(row["missingQuantity"], 0)
            checked += 1
        self.assertGreaterEqual(checked, 20)

    def test_named_sheet_and_pod_counts_use_piece_stock(self):
        cases = [
            ("gelatin sheet", "sheet"),
            ("gelatine leaf", "leaf"),
            ("vanilla pod", "pod"),
        ]
        for index, (name, unit) in enumerate(cases):
            key = f"count:{index}"
            with self.subTest(name=name, unit=unit):
                result = recipe_quantity_feasibility(
                    _recipe(name, quantity=1, unit=unit, key=key),
                    _stock(name, quantity=1, unit="pcs", key=key),
                )
                row = result["items"][0]
                self.assertEqual(row["status"], "enough")
                self.assertEqual(row["coverage"], 1.0)
                self.assertEqual(row["confidence"], "reviewed_portion")

    def test_standard_spoon_volume_can_match_ml_stock(self):
        for unit, ml in (("tsp", 5), ("tbsp", 15)):
            key = "spoon:" + unit
            result = recipe_quantity_feasibility(
                _recipe("olive oil", quantity=1, unit=unit, key=key),
                _stock("olive oil", quantity=ml, unit="ml", key=key),
            )
            row = result["items"][0]
            self.assertEqual(row["status"], "enough")
            self.assertEqual(row["coverage"], 1.0)

    def test_reviewed_density_maps_mass_and_volume_both_directions(self):
        density = 1.031
        mass = 103.1
        volume = 100
        result = recipe_quantity_feasibility(
            _recipe("plain yogurt", quantity=mass, unit="g", key="density:g"),
            _stock("plain yogurt", quantity=volume, unit="ml", key="density:g"),
        )
        self.assertEqual(result["items"][0]["coverage"], 1.0)
        result = recipe_quantity_feasibility(
            _recipe("plain yogurt", quantity=volume, unit="ml", key="density:ml"),
            _stock("plain yogurt", quantity=mass, unit="g", key="density:ml"),
        )
        self.assertEqual(result["items"][0]["coverage"], 1.0)
        self.assertAlmostEqual(mass / volume, density, places=3)

    def test_shared_converted_stock_is_never_double_counted(self):
        recipe = {
            "ingredients": [
                _recipe("apple", quantity=1, unit="piece", key="shared:apple")["ingredients"][0],
                _recipe("apple", quantity=1, unit="piece", key="shared:apple")["ingredients"][0],
            ]
        }
        result = recipe_quantity_feasibility(
            recipe,
            _stock("apple", quantity=273, unit="g", key="shared:apple"),
        )
        self.assertEqual(sorted(row["coverage"] for row in result["items"]), [0.5, 1.0])
        self.assertEqual(result["quantityCoverage"], 0.75)

    def test_unsupported_cross_unit_match_stays_unknown_not_false_zero(self):
        result = recipe_quantity_feasibility(
            _recipe("custom ingredient", quantity=1, unit="slice", key="unsupported"),
            _stock("custom ingredient", quantity=100, unit="g", key="unsupported"),
        )
        row = result["items"][0]
        self.assertEqual(row["status"], "incompatible_unit")
        self.assertIsNone(row["coverage"])
        self.assertNotEqual(row["coverage"], 0)


if __name__ == "__main__":
    unittest.main()
