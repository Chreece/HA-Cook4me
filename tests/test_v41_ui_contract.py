from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
V41 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v41.js"
PANEL = ROOT / "custom_components" / "cook4me" / "panel.py"
MANIFEST = ROOT / "custom_components" / "cook4me" / "manifest.json"


class V41UIContractTests(unittest.TestCase):
    def test_last_open_section_is_remembered_per_ha_user(self):
        text = V41.read_text(encoding="utf-8")
        self.assertIn('LAST_SECTION_PREFIX="cook4me.ui.lastSection.v1."', text)
        self.assertIn('localStorage.setItem(this._lastSectionKey(),value)', text)
        self.assertIn('const saved=this._loadLastSection(user)', text)
        self.assertIn('if(saved)this._tab=saved', text)
        self.assertIn('this._rememberSection(this._tab)', text)

    def test_outside_pointer_closes_custom_selectors_and_menus(self):
        text = V41.read_text(encoding="utf-8")
        self.assertIn('document.addEventListener("pointerdown",this._outsidePointerHandler,true)', text)
        self.assertIn('document.removeEventListener("pointerdown",this._outsidePointerHandler,true)', text)
        self.assertIn('details.rx-today-picker[open]', text)
        self.assertIn('details.rx-advanced[open]', text)
        self.assertIn('if(!path.includes(menu))menu.removeAttribute("open")', text)

    def test_v41_is_active_and_cache_busted(self):
        panel = PANEL.read_text(encoding="utf-8")
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn('cook4me-recipe-hub-panel-v41', panel)
        self.assertIn('cook4me-panel-v41.js', panel)
        self.assertIn('?v=2026.9.7.20', panel)
        self.assertIn('"version": "2026.9.7.20"', manifest)


if __name__ == "__main__":
    unittest.main()
