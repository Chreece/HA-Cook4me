from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


def load_weekly_plan():
    path=ROOT/"custom_components"/"cook4me"/"weekly_plan.py"
    spec=importlib.util.spec_from_file_location("cook4me_weekly_plan_v145_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WeekMealTypesV145Tests(unittest.TestCase):
    def test_v145_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v145.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v165",panel)
        self.assertIn("cook4me-panel-v165.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.30",panel)
        self.assertIn("?v=2026.9.21.30",panel)
        self.assertIn('"version": "2026.9.21.30"',manifest)
        self.assertIn(
            "if(!customElements.get(V144))await import('./cook4me-panel-v144.js?v=2026.9.21.9')",
            ui,
        )

    def test_week_meal_types_are_identical_to_today_dayparts(self):
        ui=(FRONTEND/"cook4me-panel-v145.js").read_text(encoding="utf-8")
        today=(FRONTEND/"cook4me-panel-v93.js").read_text(encoding="utf-8")
        expected="['breakfast','morningSnack','lunch','afternoonSnack','dinner','lateSnack']"
        self.assertIn("const V145_MEALS="+expected,ui)
        for meal in ("breakfast","morningSnack","lunch","afternoonSnack","dinner","lateSnack"):
            self.assertIn(meal,today)
        self.assertIn("return this._v93Text?.(meal)||this._t(meal)",ui)

    def test_backend_uses_same_six_chronological_dayparts(self):
        weekly=load_weekly_plan()
        self.assertEqual(
            weekly.MEAL_SLOT_ORDER,
            ("breakfast","morningSnack","lunch","afternoonSnack","dinner","lateSnack"),
        )
        self.assertEqual(
            weekly.ordered_meal_slots([
                "lateSnack","breakfast","dinner","morningSnack","afternoonSnack","lunch"
            ]),
            ["breakfast","morningSnack","lunch","afternoonSnack","dinner","lateSnack"],
        )

    def test_old_generic_snack_migrates_to_afternoon_snack(self):
        weekly=load_weekly_plan()
        lifecycle=(ROOT/"custom_components"/"cook4me"/"meal_lifecycle.py").read_text(encoding="utf-8")
        self.assertEqual(weekly.normalize_meal_slot("snack"),"afternoonSnack")
        self.assertEqual(
            weekly.ordered_meal_slots(["breakfast","snack","dinner"]),
            ["breakfast","afternoonSnack","dinner"],
        )
        self.assertIn('"snack": "afternoonSnack"',lifecycle)

    def test_snack_recipe_taxonomy_serves_all_three_snack_dayparts(self):
        websocket=(ROOT/"custom_components"/"cook4me"/"websocket_v20.py").read_text(encoding="utf-8")
        self.assertIn('meal_type in {"morningSnack", "afternoonSnack", "lateSnack"}',websocket)
        self.assertIn('["snack", "dessert"]',websocket)

    def test_weekday_pattern_is_folded_by_default(self):
        ui=(FRONTEND/"cook4me-panel-v145.js").read_text(encoding="utf-8")
        self.assertIn('<details class="card v144-week-pattern v145-week-pattern"',ui)
        self.assertIn('<summary class="v145-pattern-summary">',ui)
        self.assertIn("section.open=false;section.removeAttribute('open')",ui)
        self.assertIn("v145-fold-chevron",ui)

    def test_weekday_pattern_saves_all_six_dayparts(self):
        ui=(FRONTEND/"cook4me-panel-v145.js").read_text(encoding="utf-8")
        self.assertIn("filter(meal=>V145_MEALS.includes(meal))",ui)
        self.assertIn("meal_types=V145_MEALS",ui.replace("payload.meal_types","meal_types"))
        self.assertIn("weekday_meal_types:schedule",ui)


if __name__=="__main__":
    unittest.main()
