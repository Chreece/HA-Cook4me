"""Regression coverage for Today substitution persistence across page returns."""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from typing import Any
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "cook4me"


def load_function(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(
        item
        for item in tree.body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    node.decorator_list = []
    namespace = {"Any": Any, "deepcopy": deepcopy}
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
            str(path),
            "exec",
        ),
        namespace,
    )
    return namespace[name]


class TodaySubstitutionPersistenceTests(unittest.TestCase):
    def test_server_compact_match_preserves_complete_adaptation_proof(self):
        compact = load_function(COMP / "today_plan_store.py", "_compact_match")
        match = {
            "safe": False,
            "diet": "vegetarian",
            "dietCheckVersion": 76,
            "dietRulesSignature": "sig",
            "requiresSubstitutions": True,
            "eligibleWithSubstitutions": True,
            "substitutionCoverageComplete": True,
            "substitutionCandidateCount": 2,
            "substitutionSources": ["ingredient_catalog"],
            "substitutions": [
                {
                    "ingredientIndex": 1,
                    "original": "chicken",
                    "replacement": {"key": "tofu", "name": "Tofu"},
                    "alternatives": [
                        {"key": "tofu", "name": "Tofu"},
                        {"key": "seitan", "name": "Seitan"},
                    ],
                }
            ],
            "ingredientChanges": [{"ingredientIndex": 1}],
            "violations": ["diet:vegetarian"],
        }
        saved = compact(match)
        self.assertTrue(saved["substitutionCoverageComplete"])
        self.assertTrue(saved["eligibleWithSubstitutions"])
        self.assertTrue(saved["requiresSubstitutions"])
        self.assertEqual(saved["substitutions"], match["substitutions"])
        self.assertEqual(saved["substitutionCandidateCount"], 2)
        self.assertEqual(saved["substitutionSources"], ["ingredient_catalog"])

    def test_v260_server_snapshot_is_losslessly_migrated(self):
        compact = load_function(COMP / "today_plan_store.py", "_compact_match")
        old = {
            "safe": False,
            "diet": "vegetarian",
            "dietCheckVersion": 76,
            "requiresSubstitutions": True,
            "eligibleWithSubstitutions": True,
            "substitutions": [
                {
                    "ingredientIndex": 0,
                    "replacement": {"key": "tofu", "name": "Tofu"},
                    "alternatives": [{"key": "tofu", "name": "Tofu"}],
                }
            ],
        }
        saved = compact(old)
        self.assertIs(saved["substitutionCoverageComplete"], True)

    def test_runtime_keeps_v261_fast_shell_under_v269_panel(self):
        mixin = (
            COMP / "frontend" / "today-substitution-persistence-v261.js"
        ).read_text(encoding="utf-8")
        panel = (COMP / "frontend" / "cook4me-panel-v180.js").read_text(encoding="utf-8")
        registration = (COMP / "panel.py").read_text(encoding="utf-8")
        self.assertIn("cook4me.ui.shell.v261.", mixin)
        self.assertIn("substitutionCoverageComplete", mixin)
        self.assertIn("eligibleWithSubstitutions", mixin)
        self.assertIn("requiresSubstitutions", mixin)
        self.assertIn("substitutions", mixin)
        self.assertIn("TodaySubstitutionPersistenceMixin", panel)
        self.assertIn("data-cook4me-ui-revision','268'", panel)
        self.assertIn("runtime-v272", registration)
        self.assertIn("today=261", registration)
        self.assertIn("stability=262", registration)
        self.assertIn("seasonal=263", registration)


if __name__ == "__main__":
    unittest.main(verbosity=2)
