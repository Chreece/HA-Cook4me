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
            {"measurements": [{
                "ingredientIndex": 0,
                "ingredientIdentity": "key:M_FOOD_RICE",
                "grams": 243,
                "recordedAt": "2026-09-18T12:00:00+00:00",
            }]},
        )
        self.assertEqual(measured["functionalId"], "R_TEST")
        self.assertEqual(recipe["ingredients"][0]["quantity"], 250)
        self.assertEqual(measured["ingredients"][0]["quantity"], 243)
        self.assertEqual(measured["ingredients"][0]["unit"], "g")
        self.assertTrue(measured["ingredients"][0]["scaleMeasured"])
        self.assertEqual(measured["ingredients"][1]["quantity"], 500)

    def test_recipe_scaling_is_display_only(self):
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
        self.assertEqual(recipe["ingredients"][0]["quantity"], 500)

    def test_weighed_portion_uses_batch_fraction(self):
        result = self.scale.portion_nutrition(
            {"totals": {"energyKcal": 1000.0, "protein": 50.0}},
            batch_grams=1000,
            portion_grams=250,
        )
        self.assertEqual(result["fraction"], 0.25)
        self.assertEqual(result["nutrition"]["energyKcal"], 250)
        self.assertEqual(result["nutrition"]["protein"], 12.5)

    def test_stock_reweigh_preserves_lot_metadata(self):
        inventory = [{
            "key": "M_FOOD_RICE",
            "name": "Rice",
            "unit": "kg",
            "lots": [{"id": "lot-1", "quantity": 1.0, "bestBefore": "2026-10-01", "storage": "pantry"}],
        }]
        identity = self.scale.inventory_identity(inventory[0])
        plan = self.scale.prepare_inventory_reweigh(inventory, identity, grams=500, lot_id="lot-1")
        self.assertEqual(plan["lots"][0]["quantity"], 0.5)
        self.assertEqual(plan["lots"][0]["bestBefore"], "2026-10-01")
        self.assertEqual(plan["lots"][0]["storage"], "pantry")


class SmartScaleV116ContractTests(unittest.TestCase):
    def test_v116_is_active_and_v37_is_registered(self):
        panel = (INTEGRATION / "panel.py").read_text(encoding="utf-8")
        manifest = (INTEGRATION / "manifest.json").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v116", panel)
        self.assertIn("cook4me-panel-v116-bundle.js", panel)
        self.assertIn("async_register_websocket_v37", panel)
        self.assertIn("_V37_REGISTERED", panel)
        self.assertIn("/cook4me_static/2026.9.18.2", panel)
        self.assertIn('"version": "2026.9.18.2"', manifest)

    def test_frontend_extends_v115_and_uses_v37(self):
        source = (INTEGRATION / "frontend" / "cook4me-panel-v116.js").read_text(encoding="utf-8")
        self.assertIn("import './cook4me-panel-v115.js'", source)
        self.assertIn("cook4me-recipe-hub-panel-v116", source)
        for endpoint in (
            "scale_state", "scale_select", "container_save", "inventory_reweigh",
            "measurement_record", "recipe_scale", "batch_weight_set",
            "portion_nutrition", "leftover_weight_set", "leftover_consume_weight",
        ):
            self.assertIn(f"cook4me/v37/{endpoint}", source)
        self.assertIn("tareButtonEntityId", source)
        self.assertIn("stableEntityId", source)
        self.assertIn("_v116DecorateCapture", source)
        self.assertIn("data-v112-edit-lot", source)

    def test_cosori_sleeping_scale_adapter_is_discoverable(self):
        source = (INTEGRATION / "smart_scale.py").read_text(encoding="utf-8")
        self.assertIn('platform", "")) != "ha_vesync_bt"', source)
        self.assertIn('unique_id.endswith("_measurement")', source)
        self.assertIn('"provider": "VeSync Local BT"', source)
        self.assertIn('"tareButtonEntityId"', source)
        self.assertIn('"stableEntityId"', source)
        self.assertIn("scale_sleeping_or_disconnected", source)

    def test_post_cook_consumption_uses_measured_recipe(self):
        setup = (INTEGRATION / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("apply_recipe_measurements", setup)
        self.assertIn("scale_session = scale_store.session_for(recipe)", setup)
        self.assertIn("recipe = apply_recipe_measurements(recipe, scale_session)", setup)

    def test_backend_refuses_implicit_volume_or_count_mass_conversion(self):
        source = (INTEGRATION / "smart_scale.py").read_text(encoding="utf-8")
        self.assertIn('"kg": 1000.0', source)
        self.assertNotIn('"ml":', source)
        self.assertNotIn('"pcs":', source)


if __name__ == "__main__":
    unittest.main()
