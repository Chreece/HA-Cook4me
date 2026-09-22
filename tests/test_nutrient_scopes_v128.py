from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "cook4me" / "nutrient_targets.py"
spec = importlib.util.spec_from_file_location("cook4me_nutrient_targets_v128", MODULE)
targets = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(targets)


class NutrientScopeV128Tests(unittest.TestCase):
    def test_scoped_targets_keep_daily_and_meal_types_separate(self):
        value = targets.normalize_scoped_targets({
            "daily": {"calorieTarget": 2100, "proteinTarget": 110},
            "mealTypes": {
                "breakfast": {"calorieTarget": 500, "proteinTarget": 30},
                "main": {"calorieTarget": 800},
                "invalid": {"calorieTarget": 999},
            },
        })
        self.assertEqual(value["daily"]["calorieTarget"], 2100)
        self.assertEqual(value["daily"]["proteinTarget"], 110)
        self.assertEqual(value["mealTypes"]["breakfast"]["calorieTarget"], 500)
        self.assertEqual(value["mealTypes"]["main"]["calorieTarget"], 800)
        self.assertNotIn("invalid", value["mealTypes"])

    def test_legacy_targets_are_never_reinterpreted_as_daily(self):
        self.assertIsNone(targets.normalize_scoped_targets(None))
        self.assertIsNone(targets.normalize_scoped_targets("2100"))

    def test_daily_progress_scores_projected_day_at_current_fraction(self):
        result = targets.daily_progress_bonus(
            [{"perServing": {"energyKcal": 500, "protein": 25}}],
            {"perServing": {"energyKcal": 500, "protein": 25}},
            {"calorieTarget": 2000, "proteinTarget": 100},
            fraction=0.5,
        )
        self.assertGreater(result["bonus"], 0)
        self.assertEqual(result["applied"]["calorieTarget"]["actual"], 1000)
        self.assertEqual(result["applied"]["calorieTarget"]["expected"], 1000)
        self.assertEqual(result["applied"]["proteinTarget"]["actual"], 50)

    def test_v128_ui_exposes_expand_and_scope_controls(self):
        ui = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v128.js").read_text(encoding="utf-8")
        self.assertIn("v128-expand-hint", ui)
        self.assertIn("manageBlocked", ui)
        self.assertIn("data-v128-scope", ui)
        self.assertIn("nutrientTargets", ui)
        self.assertIn("V128_MEALS", ui)

    def test_v128_is_inherited_by_active_v140(self):
        panel = (ROOT / "custom_components" / "cook4me" / "panel.py").read_text(encoding="utf-8")
        manifest = (ROOT / "custom_components" / "cook4me" / "manifest.json").read_text(encoding="utf-8")
        v129 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v129.js").read_text(encoding="utf-8")
        v130 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v130.js").read_text(encoding="utf-8")
        v131 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v131.js").read_text(encoding="utf-8")
        v132 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v132.js").read_text(encoding="utf-8")
        v133 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v133.js").read_text(encoding="utf-8")
        v134 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v177",panel)
        self.assertIn("cook4me-panel-v177.js",panel)
        self.assertIn('2026.9.22.4', panel)
        self.assertIn('"version": "2026.9.22.4"', manifest)
        self.assertIn("if(!customElements.get(V133))await import('./cook4me-panel-v133.js?v=2026.9.20.7')", v134)
        self.assertIn("if(!customElements.get(V132))await import('./cook4me-panel-v132.js?v=2026.9.20.6')", v133)
        self.assertIn("if(!customElements.get(V131))await import('./cook4me-panel-v131.js?v=2026.9.20.5')", v132)
        self.assertIn("if(!customElements.get(V130))await import('./cook4me-panel-v130.js?v=2026.9.20.4')", v131)
        self.assertIn("if(!customElements.get(V129))await import('./cook4me-panel-v129.js?v=2026.9.20.3')", v130)
        self.assertIn("if(!customElements.get(V128))await import('./cook4me-panel-v128.js?v=2026.9.20.2')", v129)


if __name__ == "__main__":
    unittest.main()
