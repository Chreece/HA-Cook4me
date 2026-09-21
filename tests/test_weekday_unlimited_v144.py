from pathlib import Path
import importlib.util
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


def load_weekly_plan():
    path=ROOT/"custom_components"/"cook4me"/"weekly_plan.py"
    spec=importlib.util.spec_from_file_location("cook4me_weekly_plan_v144_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WeekdayUnlimitedV144Tests(unittest.TestCase):
    def test_v144_is_inherited_by_active_v145(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v144.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v159",panel)
        self.assertIn("cook4me-panel-v159.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.24",panel)
        self.assertIn("?v=2026.9.21.24",panel)
        self.assertIn('"version": "2026.9.21.24"',manifest)
        self.assertIn(
            "if(!customElements.get(V143))await import('./cook4me-panel-v143.js?v=2026.9.21.8')",
            ui,
        )

    def test_week_slots_are_chronological_and_default_filters_preserve_saved_slots(self):
        weekly=load_weekly_plan()
        self.assertEqual(
            weekly.ordered_meal_slots(["dinner","breakfast","snack","lunch"]),
            ["breakfast","lunch","afternoonSnack","dinner"],
        )
        all_filters={"mealTypes":["breakfast","starter","salad","soup","main","side","dessert","snack"]}
        self.assertEqual(
            weekly.meal_slots(all_filters,["breakfast","lunch","snack","dinner"]),
            ["breakfast","lunch","afternoonSnack","dinner"],
        )

    def test_weekday_pattern_can_omit_breakfast_or_every_meal(self):
        weekly=load_weekly_plan()
        settings={
            "mealTypes":["breakfast","lunch","snack","dinner"],
            "weekdayMealTypes":{
                "monday":["lunch","dinner"],
                "tuesday":[],
            },
        }
        self.assertEqual(
            weekly.meal_slots_for_date(None,settings,"2026-09-21"),
            ["lunch","dinner"],
        )
        self.assertEqual(
            weekly.meal_slots_for_date(None,settings,"2026-09-22"),
            [],
        )

    def test_weekday_pattern_is_persisted_and_used_by_generation(self):
        lifecycle=(ROOT/"custom_components"/"cook4me"/"meal_lifecycle.py").read_text(encoding="utf-8")
        websocket=(ROOT/"custom_components"/"cook4me"/"websocket_v20.py").read_text(encoding="utf-8")
        self.assertIn('"weekdayMealTypes"',lifecycle)
        self.assertIn("weekday_meal_types: Any = None",lifecycle)
        self.assertIn("settings[\"weekdayMealTypes\"] = _weekday_meal_types(",lifecycle)
        self.assertIn("rows.sort(key=_slot_sort_key)",lifecycle)
        self.assertIn("key=_slot_sort_key",lifecycle)
        self.assertIn('vol.Optional("weekday_meal_types"): dict',websocket)
        self.assertIn("weekday_meal_types=msg.get(\"weekday_meal_types\")",websocket)
        self.assertIn("meal_slots_for_date(shared_filters, settings, stamp)",websocket)

    def test_week_ui_has_per_day_pattern_and_visual_chronological_sort(self):
        ui=(FRONTEND/"cook4me-panel-v144.js").read_text(encoding="utf-8")
        self.assertIn("const V144_MEALS=['breakfast','lunch','snack','dinner']",ui)
        self.assertIn("data-v144-week-pattern",ui)
        self.assertIn("data-v144-day",ui)
        self.assertIn("data-v144-meal",ui)
        self.assertIn("data-v144-none",ui)
        self.assertIn("weekday_meal_types:schedule",ui)
        self.assertIn("_v144SortedSlots(original.slots)",ui)
        self.assertIn("this._v144MealRank(a?.mealType)-this._v144MealRank(b?.mealType)",ui)

    def test_scanner_unlimited_uses_real_inventory_unlimited_state(self):
        hub=(ROOT/"custom_components"/"cook4me"/"recipe_hub.py").read_text(encoding="utf-8")
        websocket=(ROOT/"custom_components"/"cook4me"/"websocket_v33.py").read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v144.js").read_text(encoding="utf-8")
        self.assertIn("unlimited=False",hub)
        self.assertIn("unlimited=True, best_before=best_before",hub)
        self.assertIn('"unlimited": bool(unlimited)',hub)
        self.assertIn('vol.Optional("unlimited", default=False): bool',websocket)
        self.assertIn("if unlimited and msg.get(\"edit_lot_id\")",websocket)
        self.assertIn("package_count=count, unlimited=unlimited",websocket)
        self.assertIn("if unlimited:",websocket)
        self.assertIn('await store.async_remove_reference("lot:" + lot_id)',websocket)
        self.assertIn("await async_reconcile_nutrition_inventory(store, inventory)",websocket)
        self.assertIn("unlimited:false",ui)
        self.assertIn("result.unlimited=true",ui)
        self.assertIn("data-v144-unlimited",ui)
        self.assertIn("d.packageCount=1",ui)
        self.assertIn("v144-unlimited-badge",ui)

    def test_unlimited_scanner_does_not_store_fake_package_price_or_nutrition(self):
        ui=(FRONTEND/"cook4me-panel-v144.js").read_text(encoding="utf-8")
        websocket=(ROOT/"custom_components"/"cook4me"/"websocket_v33.py").read_text(encoding="utf-8")
        self.assertIn("delete result.paid_price",ui)
        self.assertIn("d.nutrition={basisUnit:'',values:{}}",ui)
        self.assertIn("if unlimited and msg.get(\"paid_price\") is not None",websocket)
        self.assertIn('if "nutrition" in msg and not unlimited',websocket)
        self.assertIn('"quantity": None if unlimited else msg["quantity"]',websocket)
        self.assertIn('"unit": "" if unlimited else msg["unit"]',websocket)


if __name__=="__main__":
    unittest.main()
