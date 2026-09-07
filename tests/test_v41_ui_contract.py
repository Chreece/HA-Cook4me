from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
V41 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v41.js"
V42 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v42.js"
V43 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v43.js"
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

    def test_v43_is_active_and_cache_busted(self):
        panel = PANEL.read_text(encoding="utf-8")
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn('cook4me-recipe-hub-panel-v43', panel)
        self.assertIn('cook4me-panel-v43.js', panel)
        self.assertIn('?v=2026.9.7.22', panel)
        self.assertIn('"version": "2026.9.7.22"', manifest)

    def test_v42_autofills_catalog_and_keeps_official_values_separate(self):
        text = V42.read_text(encoding="utf-8")
        self.assertIn('cook4me/v16/nutrition_catalog_fill', text)
        self.assertIn('limit:custom?25:3', text)
        self.assertIn('officialNutrition', text)
        self.assertIn('hierarchicalNutrients', text)
        self.assertIn('valuePer100g', text)
        self.assertIn('data-cook4me-official-nutrition', text)

    def test_v43_surfaces_energy_and_resolution_cache_status(self):
        text = V43.read_text(encoding="utf-8")
        self.assertIn('energyPer100gValue', text)
        self.assertIn('officialEnergyUnknownUnit', text)
        self.assertIn('blockedFailures', text)
        self.assertIn('actionableRemaining', text)
        self.assertIn('Number(settings?.remaining)===0', text)
        self.assertIn('this._nutritionAutoFillEntry=""', text)


if __name__ == "__main__":
    unittest.main()
