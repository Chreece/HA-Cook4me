"""End-to-end non-mutating audit of infinite staples in recipe stock coverage.

The regression is intentionally ingredient-generic. Salt is the reported case,
but the same contract applies to every saved unlimited stock item and to
source-language/catalog aliases.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
PKG = "stock_infinite_v293"
pkg = types.ModuleType(PKG)
pkg.__path__ = [str(COMPONENT)]
sys.modules[PKG] = pkg

from stock_infinite_v293.stock_coverage import warm_stock_catalog
from stock_infinite_v293.food_intelligence import recipe_quantity_feasibility
from stock_infinite_v293.inventory import stock_for_ingredient


def item(key, quantity=None, unit="g", name=None):
    return {
        "key": key, "foodKey": key, "foodName": name or key,
        "quantity": quantity, "unit": unit
    }


def stock(key, *, unlimited=True, quantity=None, links=None):
    row = {"key": key, "name": key, "unit": "g"}
    if unlimited:
        row["unlimited"] = True
        row["storageLocationId"] = "pantry"
    elif quantity is not None:
        row["lots"] = [{"id": "lot-" + key, "quantity": quantity}]
    if links is not None:
        row["ingredientLinks"] = links
    return [row]


def feasibility(recipe, house, availability=None):
    return recipe_quantity_feasibility(
        {"ingredients": recipe}, house, availability=availability
    )


class InfiniteIngredientCoverageAudit(unittest.TestCase):
    def setUp(self):
        warm_stock_catalog({"ingredients": []})

    def test_all_stored_infinite_staples_resolve_even_with_unknown_recipe_amounts(self):
        # A previous early unknown_requirement check produced a dash for all
        # these cases despite the saved infinite stock.
        examples = (
            ("salt", "Salt"), ("pepper", "Pfeffer"), ("sugar", "Ζάχαρη"),
            ("water", "Water"), ("flour", "Flour"), ("oil", "Olive oil"),
            ("vinegar", "Vinegar"), ("rice", "米"),
        )
        for key, name in examples:
            for quantity, unit in ((None, "g"), (None, ""), ("", "g"), (None, "unknown-unit")):
                with self.subTest(key=key, quantity=quantity, unit=unit):
                    recipe = [item(key, quantity=quantity, unit=unit, name=name)]
                    house = stock(key)
                    untouched = deepcopy((recipe, house))
                    result = feasibility(recipe, house)
                    row = result["items"][0]
                    self.assertEqual(row["coverage"], 1.0, row)
                    self.assertEqual(row["status"], "enough", row)
                    self.assertTrue(row["unlimited"], row)
                    self.assertTrue(result["fullyAvailable"], result)
                    self.assertEqual(result["quantityCoverage"], 1.0)
                    self.assertEqual(result["confidence"], 1.0)
                    self.assertEqual(result["unknown"], [])
                    self.assertEqual(result["shortages"], [])
                    self.assertEqual((recipe, house), untouched)

    def test_indefinite_stock_precedes_stale_missing_presence(self):
        recipe = [item("salt", quantity=None, name="塩")]
        result = feasibility(
            recipe, stock("salt"),
            availability=[{"key": "salt", "name": "塩", "status": "missing"}],
        )
        row = result["items"][0]
        self.assertEqual(row["coverage"], 1.0, row)
        self.assertTrue(row["unlimited"])
        self.assertEqual(row["missingQuantity"], 0)
        self.assertEqual(result["unknown"], [])

    def test_localized_linked_infinite_salt_contributes_to_quantity_coverage(self):
        recipe = [item("salt-source-ja", quantity=None, name="塩")]
        house = stock("seasoning-drawer", links=[{"key": "salt-source-ja", "name": "塩"}])
        found = stock_for_ingredient(house, recipe[0])
        self.assertIsNotNone(found)
        self.assertTrue(found["unlimited"])
        result = feasibility(recipe, house)
        self.assertEqual(result["items"][0]["coverage"], 1.0)
        self.assertTrue(result["fullyAvailable"])

    def test_reviewed_multilingual_family_with_legacy_saved_assignment(self):
        warm_stock_catalog({"ingredients": [
            {"id": "salt-english", "canonicalName": "Salt", "classification": "food"},
            {"id": "salt-korean", "canonicalName": "Salt", "classification": "food"},
            {"id": "salt-unknown", "canonicalName": "Salt", "needsSemanticConfirmation": True},
        ]})
        house = stock("salt-box", links=[{"key": "salt-english", "name": "Salt"}])
        result = feasibility([item("salt-korean", None, "g", "소금")], house)
        self.assertEqual(result["items"][0]["coverage"], 1.0, result)
        self.assertTrue(result["items"][0]["unlimited"])
        wrong = feasibility([item("salt-unknown", None, "g", "Salt")], house,
                            availability=[{"key": "salt-unknown", "status": "missing"}])
        self.assertIsNone(wrong["items"][0]["coverage"], wrong)
        self.assertFalse(wrong["fullyAvailable"])

    def test_recipe_with_multiple_infinite_and_finite_requirements(self):
        house = stock("salt") + stock("pepper") + stock("rice", unlimited=False, quantity=50)
        recipe = [item("salt", None), item("rice", 100), item("pepper", None)]
        result = feasibility(recipe, house)
        self.assertEqual([row["coverage"] for row in result["items"]], [1.0, 0.5, 1.0], result)
        self.assertEqual(result["quantityCoverage"], 0.833)
        self.assertEqual(result["confidence"], 1.0)
        self.assertEqual(len(result["shortages"]), 1)
        self.assertFalse(result["fullyAvailable"])
        self.assertEqual(result["unknown"], [])

    def test_repeat_infinite_ingredient_does_not_consume_or_duplicate_physical_stock(self):
        house = stock("salt")
        result = feasibility([item("salt", None), item("salt", 100)], house)
        self.assertEqual([row["coverage"] for row in result["items"]], [1.0, 1.0])
        self.assertEqual(result["shortages"], [])
        self.assertTrue(result["fullyAvailable"])

    def test_finite_or_missing_stock_never_inherits_unlimited_semantics(self):
        cases = [
            (stock("salt", unlimited=False, quantity=0), "unknown_requirement"),
            ([], "unknown_requirement"),
            (stock("pepper"), "unknown_requirement"),
        ]
        for house, status in cases:
            with self.subTest(house=house):
                result = feasibility([item("salt", None)], house,
                                     availability=[{"key":"salt","status":"missing"}])
                self.assertEqual(result["items"][0]["status"], status, result)
                self.assertIsNone(result["items"][0]["coverage"])
                self.assertFalse(result["fullyAvailable"])

    def test_finite_known_quantities_and_incompatible_units_are_not_relaxed(self):
        finite = feasibility([item("salt", 100)], stock("salt", unlimited=False, quantity=20))
        self.assertEqual(finite["items"][0]["coverage"], 0.2, finite)
        mismatch = feasibility([item("salt", 1, "unsupported-unit")],
                               stock("salt", unlimited=False, quantity=100))
        self.assertEqual(mismatch["items"][0]["status"], "incompatible_unit")
        self.assertIsNone(mismatch["items"][0]["coverage"])

if __name__ == "__main__":
    unittest.main()
