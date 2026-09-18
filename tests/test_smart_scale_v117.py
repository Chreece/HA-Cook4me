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
WS37 = COMPONENT / "websocket_v37.py"
V117 = COMPONENT / "frontend" / "cook4me-panel-v117.js"


def _pure_scale_namespace():
    source = SMART.read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {"_text", "_number", "_unit_token", "mass_to_grams", "grams_to_mass"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    code = "from __future__ import annotations\n" + "\n\n".join(ast.unparse(node) for node in nodes)
    namespace = {"math": math, "re": re, "Any": Any}
    exec(compile(code, str(SMART), "exec"), namespace)
    return namespace


class SmartScaleMinimalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = _pure_scale_namespace()

    def test_mass_conversion_stays_strict(self):
        self.assertEqual(self.ns["mass_to_grams"](2, "kg"), 2000)
        self.assertAlmostEqual(self.ns["mass_to_grams"](1, "oz"), 28.349523125)
        self.assertIsNone(self.ns["mass_to_grams"](250, "ml"))
        self.assertIsNone(self.ns["mass_to_grams"](3, "pcs"))

    def test_v117_runtime_contract(self):
        panel = PANEL.read_text(encoding="utf-8")
        ui = V117.read_text(encoding="utf-8")
        ws = WS37.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v117", panel)
        self.assertIn("cook4me-panel-v117-bundle.js", panel)
        self.assertIn("async_register_websocket_v37", panel)
        self.assertIn("data-v78-pane=\"places\"", ui)
        self.assertIn("data-v78-section=\"scale\"", ui)
        self.assertIn("data-v117-container", ui)
        self.assertIn("v117ReadWeight", ui)
        self.assertIn("container_id", ws)


if __name__ == "__main__":
    unittest.main()
