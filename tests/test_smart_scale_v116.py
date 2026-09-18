from __future__ import annotations

import ast
import math
from pathlib import Path
import re
import unittest
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
SMART = COMPONENT / "smart_scale.py"
PANEL = COMPONENT / "panel.py"
INIT = COMPONENT / "__init__.py"
WS37 = COMPONENT / "websocket_v37.py"


def _pure_scale_namespace():
    source = SMART.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {
        "_text", "_number", "_unit_token",
        "mass_to_grams", "grams_to_mass", "portion_nutrition",
    }
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    code = "from __future__ import annotations\n" + "\n\n".join(ast.unparse(node) for node in nodes)
    namespace = {"math": math, "re": re, "Any": Any}
    exec(compile(code, str(SMART), "exec"), namespace)
    return namespace


class SmartScaleMinimalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = _pure_scale_namespace()

    def test_mass_conversion_is_strict_and_reversible(self):
        to_g = self.ns["mass_to_grams"]
        from_g = self.ns["grams_to_mass"]
        self.assertEqual(to_g(2, "kg"), 2000)
        self.assertAlmostEqual(to_g(1, "oz"), 28.349523125)
        self.assertEqual(from_g(500, "kg"), 0.5)
        self.assertIsNone(to_g(250, "ml"))
        self.assertIsNone(to_g(3, "pcs"))

    def test_weighed_portion_uses_batch_fraction(self):
        result = self.ns["portion_nutrition"](
            {"totals": {"energyKcal": 1000.0, "protein": 50.0}},
            batch_grams=1000,
            portion_grams=250,
        )
        self.assertEqual(result["fraction"], 0.25)
        self.assertEqual(result["nutrition"]["energyKcal"], 250)
        self.assertEqual(result["nutrition"]["protein"], 12.5)

    def test_v116_runtime_contract(self):
        smart = SMART.read_text(encoding="utf-8")
        panel = PANEL.read_text(encoding="utf-8")
        init = INIT.read_text(encoding="utf-8")
        ws = WS37.read_text(encoding="utf-8")
        for token in (
            'platform", "")) != "ha_vesync_bt"',
            'unique_id.endswith("_measurement")',
            '"tareButtonEntityId"',
            '"stableEntityId"',
            '"provider": "VeSync Local BT"',
            "scale_sleeping_or_disconnected",
        ):
            self.assertIn(token, smart)
        self.assertIn("cook4me-recipe-hub-panel-v116", panel)
        self.assertIn("cook4me-panel-v116-bundle.js", panel)
        self.assertIn("async_register_websocket_v37", panel)
        self.assertIn("apply_recipe_measurements", init)
        for endpoint in (
            "scale_state", "scale_select", "measurement_record", "inventory_reweigh",
            "recipe_scale", "portion_nutrition", "leftover_weight_set",
            "leftover_consume_weight",
        ):
            self.assertIn(f"cook4me/v37/{endpoint}", ws)


if __name__ == "__main__":
    unittest.main()
