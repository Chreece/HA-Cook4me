from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class WeekUiStateV179Tests(unittest.TestCase):
    def test_v179_is_active_and_cache_busted(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v179.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v179",panel)
        self.assertIn("cook4me-panel-v179.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.6",panel)
        self.assertIn("?v=2026.9.22.6",panel)
        self.assertIn('"version": "2026.9.22.6"',manifest)
        self.assertIn("cook4me-panel-v178.js?v=2026.9.22.5",ui)

    def test_week_sections_default_closed_and_persist_per_user_entry(self):
        ui=(FRONTEND/"cook4me-panel-v179.js").read_text(encoding="utf-8")
        self.assertIn("cook4me.weekUi.v1.",ui)
        self.assertIn("this._hass?.user?.id",ui)
        self.assertIn("this._entryId",ui)
        self.assertIn("return this._v179LoadState().folds?.[key]===true",ui)
        for key in (
            "weekdayPattern","mealSlots","reservedStock","shoppingDelta",
            "leftovers","summary","priceInventory","completedPurchases",
        ):
            self.assertIn(f"'{key}'",ui)
        self.assertIn("body.hidden=!open",ui)
        self.assertIn("this._v179SetFold(key,open)",ui)

    def test_open_week_recipe_and_scroll_restore_after_navigation(self):
        ui=(FRONTEND/"cook4me-panel-v179.js").read_text(encoding="utf-8")
        self.assertIn("state.openRecipe={token,slotId:",ui)
        self.assertIn("_v179RestoreRecipe()",ui)
        self.assertIn("_v179WatchExplicitRecipeClose",ui)
        self.assertIn("event.key==='Escape'",ui)
        self.assertIn("state.scrollTop=Number(content.scrollTop||0)",ui)
        self.assertIn("content.scrollTop=top",ui)

    def test_week_shopping_restores_backend_ui_first_label(self):
        ui=(FRONTEND/"cook4me-panel-v179.js").read_text(encoding="utf-8")
        self.assertIn("display_language:this._uiIngredientLanguage?.()",ui)
        self.assertIn("supermarket_language:this._v140SupermarketLanguage?.()",ui)
        self.assertIn("row.shoppingDisplayName",ui)
        self.assertIn("name:row.shoppingDisplayName",ui)


if __name__=="__main__":
    unittest.main()
