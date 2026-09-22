from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
UI=FRONTEND/"cook4me-panel-v180.js"


class WeekStockLanguageV188Tests(unittest.TestCase):
    def test_active_frontend_is_cache_busted(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=UI.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.8",panel)
        self.assertIn("?v=2026.9.22.8",panel)
        self.assertIn('"version": "2026.9.22.8"',manifest)
        self.assertIn("data-cook4me-build','2026.9.22.8",ui)

    def test_week_rows_use_ui_market_recipe_language_contract(self):
        ui=UI.read_text(encoding="utf-8")
        self.assertIn("_v180IngredientLabel(row)",ui)
        self.assertIn("this._v112Local?.({...row",ui)
        self.assertIn("this._v140IngredientKey?.(row)",ui)
        self.assertIn("this._v140SupermarketLanguage?.()",ui)
        self.assertIn("this._v140MarketNames?.get(key)",ui)
        self.assertIn("row.originalName||row.recipeName||row.sourceName||row.name",ui)
        self.assertIn("marketLanguage&&marketLanguage!==uiLanguage",ui)
        self.assertIn("parts.some(value=>same(value,candidate))",ui)
        self.assertIn("parts.slice(1).map",ui)

    def test_every_week_stock_name_path_uses_same_formatter(self):
        ui=UI.read_text(encoding="utf-8")
        self.assertIn("_v110Disclosure(kind,rows,empty,extra='')",ui)
        self.assertIn("e(this._v180IngredientLabel(row))",ui)
        self.assertIn("_shoppingDeltaHtml()",ui)
        self.assertIn("data-week-stock-unknown",ui)
        self.assertGreaterEqual(ui.count("_v180IngredientLabel(row)"),3)


if __name__=="__main__":
    unittest.main()
