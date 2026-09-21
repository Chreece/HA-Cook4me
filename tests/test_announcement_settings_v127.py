from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
SETTINGS=ROOT/"custom_components"/"cook4me"/"device_settings.py"
ANNOUNCEMENTS=ROOT/"custom_components"/"cook4me"/"announcements.py"


class AnnouncementSettingsV127Tests(unittest.TestCase):
    def test_v127_features_are_inherited_by_active_v138(self):
        panel=PANEL.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v127.js").read_text(encoding="utf-8")
        v128=(FRONTEND/"cook4me-panel-v128.js").read_text(encoding="utf-8")
        v129=(FRONTEND/"cook4me-panel-v129.js").read_text(encoding="utf-8")
        v130=(FRONTEND/"cook4me-panel-v130.js").read_text(encoding="utf-8")
        v131=(FRONTEND/"cook4me-panel-v131.js").read_text(encoding="utf-8")
        v132=(FRONTEND/"cook4me-panel-v132.js").read_text(encoding="utf-8")
        v133=(FRONTEND/"cook4me-panel-v133.js").read_text(encoding="utf-8")
        v134=(FRONTEND/"cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v149",panel)
        self.assertIn("cook4me-panel-v149.js",panel)
        self.assertIn('/cook4me_static/2026.9.21.14',panel)
        self.assertIn("if(!customElements.get(V133))await import('./cook4me-panel-v133.js?v=2026.9.20.7')",v134)
        self.assertIn("if(!customElements.get(V132))await import('./cook4me-panel-v132.js?v=2026.9.20.6')",v133)
        self.assertIn("if(!customElements.get(V131))await import('./cook4me-panel-v131.js?v=2026.9.20.5')",v132)
        self.assertIn("if(!customElements.get(V130))await import('./cook4me-panel-v130.js?v=2026.9.20.4')",v131)
        self.assertIn("if(!customElements.get(V129))await import('./cook4me-panel-v129.js?v=2026.9.20.3')",v130)
        self.assertIn("if(!customElements.get(V128))await import('./cook4me-panel-v128.js?v=2026.9.20.2')",v129)
        self.assertIn("if(!customElements.get(V127))await import('./cook4me-panel-v127.js?v=2026.9.20.1')",v128)
        self.assertIn("if(!customElements.get(V126))await import('./cook4me-panel-v126-bundle.js?v=2026.9.19.5')",ui)
        self.assertIn("data-cook4me-build','2026.9.20.1'",ui)

    def test_home_stock_is_folded_by_default(self):
        ui=(FRONTEND/"cook4me-panel-v127.js").read_text(encoding="utf-8")
        legacy=(FRONTEND/"cook4me-panel-v112.js").read_text(encoding="utf-8")
        self.assertIn("stock.parentElement.open=false",ui)
        self.assertIn("stock.parentElement.open=true",legacy)

    def test_tts_language_is_limited_to_selected_service_and_defaults_to_service_language(self):
        ui=(FRONTEND/"cook4me-panel-v127.js").read_text(encoding="utf-8")
        settings=SETTINGS.read_text(encoding="utf-8")
        self.assertIn("languages.includes(selectedTts.defaultLanguage)?selectedTts.defaultLanguage",ui)
        self.assertIn("if(!option.value||!supported.has(option.value))option.remove()",ui)
        self.assertIn('default_language = entity.default_language',settings)
        self.assertIn('if default_language not in languages:',settings)
        self.assertIn('result["language"] = tts["defaultLanguage"]',settings)
        self.assertIn('result["language"] not in tts["languages"]',settings)

    def test_default_ai_task_is_dynamic_and_all_tts_ai_is_supported(self):
        ui=(FRONTEND/"cook4me-panel-v127.js").read_text(encoding="utf-8")
        settings=SETTINGS.read_text(encoding="utf-8")
        announcements=ANNOUNCEMENTS.read_text(encoding="utf-8")
        self.assertIn("const AI_DEFAULT='__home_assistant_default__'",ui)
        self.assertIn("data-v127-ai-all-input",ui)
        self.assertIn('DEFAULT_AI_TASK = "__home_assistant_default__"',settings)
        self.assertIn('"defaultAiTaskId": default_ai_task',settings)
        self.assertIn('"ai_all": False',settings)
        self.assertIn('result["ai_all"] and not result["ai"]',settings)
        self.assertIn("selected == DEFAULT_AI_TASK",announcements)
        self.assertIn("entity_id = None",announcements)
        self.assertIn('bool(settings.get("ai_all")) or any(',announcements)
        self.assertIn("spoken formatting",announcements.lower())
        self.assertIn('translate=bool(settings.get("ai_all"))',announcements)


if __name__=="__main__":
    unittest.main()
