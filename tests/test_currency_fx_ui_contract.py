from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
V45 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v45.js"
V46 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v46.js"
V47 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v47.js"
V48 = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v48.js"
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

    def test_v21_is_registered_with_active_panel(self):
        panel = PANEL.read_text(encoding="utf-8")
        self.assertIn('websocket_v21', panel)
        self.assertIn('cook4me-recipe-hub-panel-v48', panel)
        self.assertIn('cook4me-panel-v48.js', panel)
        self.assertIn('import "./cook4me-panel-v45.js"', V46.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v46.js"', V47.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v47.js"', V48.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
