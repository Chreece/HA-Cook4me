from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class WeekFoldCleanBackgroundV136Tests(unittest.TestCase):
    def test_model_blends_against_real_card_background(self):
        ui=(FRONTEND/"cook4me-panel-v136.js").read_text(encoding="utf-8")
        self.assertIn("isolation:auto!important",ui)
        self.assertIn("background:transparent!important",ui)
        self.assertIn("mix-blend-mode:multiply!important",ui)
        self.assertNotIn("device-v134.webp",ui)

    def test_week_recipe_sections_start_folded(self):
        ui=(FRONTEND/"cook4me-panel-v136.js").read_text(encoding="utf-8")
        self.assertIn("_v136FoldWeekSections(container)",ui)
        self.assertIn("state?.sections?.clear?.()",ui)
        self.assertIn("details.open=false",ui)
        self.assertIn("details.removeAttribute('open')",ui)
        self.assertIn("if(this._tab==='week')",ui)

    def test_v136_inherits_v135_title_fit_and_device_photo(self):
        v135=(FRONTEND/"cook4me-panel-v135.js").read_text(encoding="utf-8")
        v136=(FRONTEND/"cook4me-panel-v136.js").read_text(encoding="utf-8")
        self.assertIn("./assets/device-v133.jpg?v=2026.9.20.9",v135)
        self.assertIn("_v71FitTitle(title)",v135)
        self.assertIn(
            "if(!customElements.get(V135))await import('./cook4me-panel-v135.js?v=2026.9.20.9')",
            v136,
        )

    def test_v136_is_inherited_by_active_v139(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v139",panel)
        self.assertIn("cook4me-panel-v139.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.4",panel)
        self.assertIn("?v=2026.9.21.4",panel)
        self.assertIn('"version": "2026.9.21.4"',manifest)


if __name__=="__main__":
    unittest.main()
