from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
V45 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v45.js"
V46 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v46.js"
V47 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v47.js"
V48 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v48.js"
V49 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v49.js"
V50 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v50.js"
V51 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v51.js"
V52 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v52.js"
V53 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v53.js"
V54 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v54.js"
V55 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v55.js"
V56 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v56.js"
V57 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v57.js"
V58 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v58.js"
PANEL = ROOT / "custom_components/cook4me/panel.py"


class CurrencyFxUiContractTests(unittest.TestCase):
    def test_currency_control_is_next_to_language_and_auto_follows_ui_language(self):
        text = V45.read_text(encoding="utf-8")
        self.assertIn('cook4meCurrencyControl', text)
        self.assertIn('language.after(control)', text)
        self.assertIn('cook4meUiLanguage', text)
        self.assertIn('mode:auto?"auto":"fixed"', text)
        self.assertIn('setTimeout(()=>void this._setCurrency("__auto__"),0)', text)

    def test_money_is_collapsed_through_euro_cross_rate(self):
        text = V45.read_text(encoding="utf-8")
        self.assertIn('amount/fromRate)*toRate', text)
        self.assertIn('super._money(result.unconverted)', text)
        self.assertIn('minimumFractionDigits:2', text)

    def test_currency_api_is_registered_with_active_cache_first_panel(self):
        panel = PANEL.read_text(encoding="utf-8")
        self.assertIn('websocket_v21', panel)
        self.assertIn('websocket_v24', panel)
        self.assertIn('cook4me-recipe-hub-panel-v58', panel)
        self.assertIn('cook4me-panel-v58.js', panel)
        self.assertIn('import "./cook4me-panel-v45.js"', V46.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v46.js"', V47.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v47.js"', V48.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v48.js"', V49.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v49.js"', V50.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v50.js"', V51.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v51.js"', V52.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v52.js"', V53.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v53.js"', V54.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v54.js"', V55.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v55.js"', V56.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v56.js"', V57.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v57.js"', V58.read_text(encoding="utf-8"))
        self.assertIn('cook4me/v24/currency_state', V50.read_text(encoding="utf-8"))
        self.assertIn('if(!this._resourceAllowed("currency"))', V51.read_text(encoding="utf-8"))
        self.assertIn('currencyState', V54.read_text(encoding="utf-8"))
        self.assertIn('missingOnly:true,force:false', V55.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
