from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"


class WeekPanelsTransparentDeviceV137Tests(unittest.TestCase):
    def test_only_large_week_panels_are_folded(self):
        ui=(FRONTEND/"cook4me-panel-v137.js").read_text(encoding="utf-8")
        self.assertIn("this._t('leftovers')",ui)
        self.assertIn("this._t('nutritionDashboard')",ui)
        self.assertIn("this._t('priceInventory')",ui)
        self.assertIn("details.className='card rx-v137-week-panel'",ui)
        self.assertIn("details.dataset.v137WeekPanel=key",ui)
        self.assertIn("_v136FoldWeekSections(_container)",ui)
        self.assertNotIn("state?.sections?.clear?.()",ui)

    def test_week_panels_start_closed_with_expandable_summary(self):
        ui=(FRONTEND/"cook4me-panel-v137.js").read_text(encoding="utf-8")
        self.assertIn("document.createElement('details')",ui)
        self.assertIn("document.createElement('summary')",ui)
        self.assertIn("mdi:chevron-down",ui)
        self.assertIn(".rx-v137-week-panel[open]>summary ha-icon",ui)
        self.assertNotIn("details.open=true",ui)

    def test_cooker_photo_is_clipped_to_device_silhouette(self):
        ui=(FRONTEND/"cook4me-panel-v137.js").read_text(encoding="utf-8")
        self.assertIn("clip-path:polygon(",ui)
        self.assertIn("mix-blend-mode:multiply!important",ui)
        self.assertIn("background:transparent!important",ui)
        self.assertNotIn("radial-gradient(circle at 50% 49%,#d8dcdd",ui)

    def test_v137_inherits_previous_fixes(self):
        v136=(FRONTEND/"cook4me-panel-v136.js").read_text(encoding="utf-8")
        v137=(FRONTEND/"cook4me-panel-v137.js").read_text(encoding="utf-8")
        self.assertIn(
            "if(!customElements.get(V136))await import('./cook4me-panel-v136.js?v=2026.9.21.1')",
            v137,
        )
        self.assertIn("isolation:auto!important",v136)

    def test_v137_is_inherited_by_active_v140(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v177",panel)
        self.assertIn("cook4me-panel-v177.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.4",panel)
        self.assertIn("?v=2026.9.22.4",panel)
        self.assertIn('"version": "2026.9.22.4"',manifest)


if __name__=="__main__":
    unittest.main()
