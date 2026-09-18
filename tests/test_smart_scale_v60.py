from __future__ import annotations

from pathlib import Path
import importlib
import math
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "cook4me"


def _load_smart_scale():
    for name in list(sys.modules):
        if name == "_cook4me_scale_test" or name.startswith("_cook4me_scale_test."):
            sys.modules.pop(name, None)

    ha = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    helpers = types.ModuleType("homeassistant.helpers")
    storage = types.ModuleType("homeassistant.helpers.storage")

    class DummyStore:
        def __class_getitem__(cls, _item):
            return cls

    core.HomeAssistant = object
    storage.Store = DummyStore
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.storage"] = storage

    package = types.ModuleType("_cook4me_scale_test")
    package.__path__ = [str(INTEGRATION)]
    sys.modules["_cook4me_scale_test"] = package
    return importlib.import_module("_cook4me_scale_test.smart_scale")


class SmartScaleLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scale = _load_smart_scale()

    def test_mass_conversion_is_dimensionally_strict(self):
        self.assertEqual(self.scale.mass_to_grams(2, "kg"), 2000)
        self.assertAlmostEqual(self.scale.mass_to_grams(1, "oz"), 28.349523125)
        self.assertEqual(self.scale.grams_to_mass(500, "kg"), 0.5)
        self.assertIsNone(self.scale.mass_to_grams(250, "ml"))
        self.assertIsNone(self.scale.grams_to_mass(250, "pcs"))

    def test_actual_recipe_weight_overlays_only_consumption_amount(self):
        recipe = {
            "functionalId": "R_TEST",
            "title": "Rice",
            "ingredients": [
                {"key": "M_FOOD_RICE", "name": "Rice", "quantity": 250, "unit": "g"},
                {"key": "M_FOOD_WATER", "name": "Water", "quantity": 500, "unit": "ml"},
            ],
        }
        measured = self.scale.apply_recipe_measurements(
            recipe,
            {
                "measurements": [
                    {
                        "ingredientIndex": 0,
                        "ingredientIdentity": "key:M_FOOD_RICE",
                        "grams": 243,
                        "recordedAt": "2026-09-18T12:00:00+00:00",
                    }
                ]
            },
        )
        self.assertEqual(measured["functionalId"], "R_TEST")
        self.assertEqual(recipe["ingredients"][0]["quantity"], 250)
        self.assertEqual(measured["ingredients"][0]["quantity"], 243)
        self.assertEqual(measured["ingredients"][0]["unit"], "g")
        self.assertTrue(measured["ingredients"][0]["scaleMeasured"])
        self.assertEqual(measured["ingredients"][1]["quantity"], 500)

    def test_recipe_scaling_is_explicitly_display_only(self):
        recipe = {
            "functionalId": "R_SCALE",
            "servings": 4,
            "ingredients": [
                {"name": "Rice", "quantity": 500, "unit": "g"},
                {"name": "Water", "quantity": 1000, "unit": "ml"},
            ],
        }
        scaled = self.scale.scale_recipe_guide(recipe, anchor_index=0, measured_grams=250)
        self.assertTrue(math.isclose(scaled["scaleGuide"]["factor"], 0.5))
        self.assertTrue(scaled["scaleGuide"]["displayOnly"])
        self.assertEqual(scaled["functionalId"], "R_SCALE")
        self.assertEqual(scaled["servings"], 2)
        self.assertEqual(scaled["ingredients"][0]["quantity"], 250)
        self.assertEqual(scaled["ingredients"][1]["quantity"], 500)
        self.assertEqual(recipe["ingredients"][0]["quantity"], 500)

    def test_weighed_portion_nutrition_uses_cooked_batch_fraction(self):
        result = self.scale.portion_nutrition(
            {"totals": {"energyKcal": 1000.0, "protein": 50.0, "fat": 20.0}},
            batch_grams=1000,
            portion_grams=250,
        )
        self.assertEqual(result["fraction"], 0.25)
        self.assertEqual(result["nutrition"]["energyKcal"], 250)
        self.assertEqual(result["nutrition"]["protein"], 12.5)
        with self.assertRaisesRegex(ValueError, "cannot exceed"):
            self.scale.portion_nutrition(
                {"totals": {"energyKcal": 1000.0}},
                batch_grams=1000,
                portion_grams=1001,
            )

    def test_stock_reweigh_preserves_batch_metadata_and_converts_mass_unit(self):
        inventory = [
            {
                "key": "M_FOOD_RICE",
                "name": "Rice",
                "unit": "kg",
                "lots": [
                    {
                        "id": "lot-1",
                        "quantity": 1.0,
                        "bestBefore": "2026-10-01",
                        "storage": "pantry",
                    }
                ],
            }
        ]
        identity = self.scale.inventory_identity(inventory[0])
        plan = self.scale.prepare_inventory_reweigh(
            inventory, identity, grams=500, lot_id="lot-1"
        )
        self.assertEqual(plan["unit"], "kg")
        self.assertEqual(plan["lots"][0]["quantity"], 0.5)
        self.assertEqual(plan["lots"][0]["bestBefore"], "2026-10-01")
        self.assertEqual(plan["lots"][0]["storage"], "pantry")

    def test_multiple_batches_require_explicit_batch_choice(self):
        inventory = [
            {
                "key": "M_FOOD_RICE",
                "name": "Rice",
                "unit": "g",
                "lots": [
                    {"id": "a", "quantity": 100},
                    {"id": "b", "quantity": 200},
                ],
            }
        ]
        identity = self.scale.inventory_identity(inventory[0])
        with self.assertRaisesRegex(ValueError, "Choose which stock batch"):
            self.scale.prepare_inventory_reweigh(inventory, identity, grams=150)


class SmartScaleArchitectureContractTests(unittest.TestCase):
    def test_v60_is_active_and_v31_is_registered(self):
        panel = (INTEGRATION / "panel.py").read_text(encoding="utf-8")
        self.assertIn('cook4me-recipe-hub-panel-v60', panel)
        self.assertIn('cook4me-panel-v60.js', panel)
        self.assertIn('async_register_websocket_v31', panel)
        self.assertIn('_V31_REGISTERED', panel)

    def test_frontend_exposes_all_primary_scale_workflows(self):
        source = (INTEGRATION / "frontend" / "cook4me-panel-v60.js").read_text(
            encoding="utf-8"
        )
        for token in (
            "cook4me/v31/scale_select",
            "cook4me/v31/container_save",
            "cook4me/v31/inventory_reweigh",
            "cook4me/v31/measurement_record",
            "cook4me/v31/recipe_scale",
            "cook4me/v31/batch_weight_set",
            "cook4me/v31/portion_nutrition",
            "cook4me/v31/leftover_weight_set",
            "cook4me/v31/leftover_consume_weight",
        ):
            self.assertIn(token, source)
        self.assertIn("display", source.lower())
        self.assertIn("Cook4me", source)

    def test_post_cook_consumption_uses_measured_recipe_copy(self):
        setup = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("apply_recipe_measurements", setup)
        self.assertIn("scale_session = scale_store.session_for(recipe)", setup)
        self.assertIn(
            "recipe = apply_recipe_measurements(recipe, scale_session)",
            setup,
        )

    def test_backend_refuses_density_guess_for_stock_reweigh(self):
        source = (INTEGRATION / "smart_scale.py").read_text(encoding="utf-8")
        self.assertIn("Stock unit {unit or 'unitless'} is not a mass unit", source)
        self.assertNotIn("density", source.casefold())


if __name__ == "__main__":
    unittest.main()
