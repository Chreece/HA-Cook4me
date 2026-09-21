from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class SupermarketLanguageDeviceV140Tests(unittest.TestCase):
    def test_supermarket_language_is_persisted_with_market_settings(self):
        costs=(ROOT/"custom_components"/"cook4me"/"costs.py").read_text(encoding="utf-8")
        prices=(ROOT/"custom_components"/"cook4me"/"websocket_v34.py").read_text(encoding="utf-8")
        shopping=(ROOT/"custom_components"/"cook4me"/"shopping_presentation.py").read_text(encoding="utf-8")
        self.assertIn('"supermarketLanguage": ""',costs)
        self.assertIn("supermarket_language: Any = None",costs)
        self.assertIn("vol.Optional('supermarket_language'): str",prices)
        self.assertIn("supermarket_language_options()",prices)
        self.assertIn("normalize_supermarket_language",shopping)
        self.assertIn('{"el"}',shopping)

    def test_market_setting_is_shown_beside_country_and_currency(self):
        ui=(FRONTEND/"cook4me-panel-v140.js").read_text(encoding="utf-8")
        self.assertIn("supermarketLanguage:'Supermarket language'",ui)
        self.assertIn("supermarketLanguage:'Supermarktsprache'",ui)
        self.assertIn("supermarketLanguage:'Γλώσσα σούπερ μάρκετ'",ui)
        self.assertIn("data-v79-country",ui)
        self.assertIn("data-v79-currency",ui)
        self.assertIn("data-v140-supermarket-language",ui)
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))",ui)

    def test_shopping_paths_use_supermarket_language_not_general_ui_language(self):
        v68=(FRONTEND/"cook4me-panel-v68.js").read_text(encoding="utf-8")
        v109=(FRONTEND/"cook4me-panel-v109.js").read_text(encoding="utf-8")
        v140=(FRONTEND/"cook4me-panel-v140.js").read_text(encoding="utf-8")
        ws11=(ROOT/"custom_components"/"cook4me"/"websocket_v11.py").read_text(encoding="utf-8")
        ws20=(ROOT/"custom_components"/"cook4me"/"websocket_v20.py").read_text(encoding="utf-8")
        self.assertIn("data.ui_language||this._uiIngredientLanguage()",v68)
        self.assertIn("data.ui_language||this._uiIngredientLanguage()",v109)
        self.assertIn("ui_language:this._v140SupermarketLanguage()",v140)
        self.assertIn("settings.get(\"supermarketLanguage\")",ws11)
        self.assertIn("market_settings.get(\"supermarketLanguage\")",ws20)

    def test_missing_ingredients_are_localized_from_offline_ingredient_catalog(self):
        ui=(FRONTEND/"cook4me-panel-v140.js").read_text(encoding="utf-8")
        self.assertIn("cook4me/v31/ingredient_catalog",ui)
        self.assertIn("_missingIngredientObjects(recipe)",ui)
        self.assertIn("_v140LocalizeRows(super._missingIngredientObjects(recipe)||[])",ui)
        self.assertIn("result?.shoppingDelta",ui)

    def test_device_no_longer_uses_svg_compositor_square(self):
        ui=(FRONTEND/"cook4me-panel-v140.js").read_text(encoding="utf-8")
        self.assertIn("model.querySelector('.v139-model-svg')?.remove()",ui)
        self.assertIn("new Uint8Array(w*h)",ui)
        self.assertIn("edge-connected studio background",ui)
        self.assertIn("canvas.toDataURL('image/png')",ui)
        self.assertIn(".v139-model-svg{display:none!important}",ui)
        self.assertIn("drop-shadow(0 0 4px rgba(220,230,255,.30))",ui)

    def test_v140_is_active_and_versioned(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v140.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v161",panel)
        self.assertIn("cook4me-panel-v161.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.26",panel)
        self.assertIn("?v=2026.9.21.26",panel)
        self.assertIn('"version": "2026.9.21.26"',manifest)
        self.assertIn(
            "if(!customElements.get(V139))await import('./cook4me-panel-v139.js?v=2026.9.21.4')",
            ui,
        )


if __name__=="__main__":
    unittest.main()
