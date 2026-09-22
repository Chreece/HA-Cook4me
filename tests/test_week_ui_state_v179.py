from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class PersistentUiStateV179Tests(unittest.TestCase):
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

    def test_state_is_application_wide_per_user_entry_and_per_tab(self):
        ui=(FRONTEND/"cook4me-panel-v179.js").read_text(encoding="utf-8")
        self.assertIn("cook4me.uiState.v2.",ui)
        self.assertIn("cook4me.weekUi.v1.",ui)  # one-time migration only
        self.assertIn("this._hass?.user?.id",ui)
        self.assertIn("this._entryId",ui)
        self.assertIn("tabs:{}",ui)
        self.assertIn("_v179TabState(tab=this._tab)",ui)
        self.assertIn("scrollTop",ui)
        self.assertIn("recipeScrollTop",ui)
        self.assertIn("openRecipe",ui)
        self.assertIn("openFilter",ui)

    def test_native_details_filter_and_recipe_dialog_state_are_restored_across_tabs(self):
        ui=(FRONTEND/"cook4me-panel-v179.js").read_text(encoding="utf-8")
        self.assertIn("_v179PersistDetails(root,scope='content',tab=this._tab)",ui)
        self.assertIn("node.addEventListener('toggle'",ui)
        self.assertIn("_v179RestoreFilter()",ui)
        self.assertIn("_showFilter(key)",ui)
        self.assertIn("_v179StoreOpenRecipe(recipe,custom=false,tab=this._tab)",ui)
        self.assertIn("_v179RecipeCandidates()",ui)
        self.assertIn("this._results",ui)
        self.assertIn("this._todayResults",ui)
        self.assertIn("this._entry?.()?.recipes",ui)
        self.assertIn("this._weekState?.slots",ui)
        self.assertIn("_v179RestoreRecipe()",ui)
        self.assertIn("dialog.scrollTop=top",ui)
        self.assertIn("_v179CaptureViewState()",ui)
        self.assertIn("disconnectedCallback()",ui)

    def test_week_sections_default_closed_but_persist_in_shared_state(self):
        ui=(FRONTEND/"cook4me-panel-v179.js").read_text(encoding="utf-8")
        self.assertIn("return this._v179TabState(tab).folds?.[key]===true",ui)
        for key in (
            "weekdayPattern","mealSlots","reservedStock","shoppingDelta",
            "leftovers","summary","priceInventory","completedPurchases",
        ):
            self.assertIn(f"'{key}'",ui)
        self.assertIn("body.hidden=!open",ui)
        self.assertIn("this._v179SetFold(key,open)",ui)

    def test_shopping_requests_send_ui_and_supermarket_languages_separately(self):
        ui=(FRONTEND/"cook4me-panel-v179.js").read_text(encoding="utf-8")
        self.assertIn("display_language:this._uiIngredientLanguage?.()",ui)
        self.assertIn("supermarket_language:this._v140SupermarketLanguage?.()",ui)
        self.assertIn("row.shoppingDisplayName",ui)
        self.assertIn("name:row.shoppingDisplayName",ui)


if __name__=="__main__":
    unittest.main()
