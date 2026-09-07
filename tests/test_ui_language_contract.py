from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v21.js"


class UiLanguageContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = FRONTEND.read_text(encoding="utf-8")

    def test_ui_language_selector_supports_current_translations_and_auto(self):
        self.assertIn('new Set(["auto","en","de","el"])', self.source)
        self.assertIn('interfaceLanguage:', self.source)
        self.assertIn('automaticUiLanguage:', self.source)

    def test_ui_language_is_per_home_assistant_user_on_client(self):
        self.assertIn('this._hass?.user?.id', self.source)
        self.assertIn('cook4me.recipeHub.uiLanguage.', self.source)
        self.assertIn('localStorage?.setItem', self.source)

    def test_recipe_translation_stays_on_home_assistant_language(self):
        self.assertIn('target_language:this._haLangCode()', self.source)
        self.assertIn('source!==this._haLangCode()', self.source)
        self.assertIn('recipe.language=this._haLangCode()', self.source)


if __name__ == "__main__":
    unittest.main()
