from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
V41 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v41.js"
V42 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v42.js"
V43 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v43.js"
V44 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v44.js"
V45 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v45.js"
V46 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v46.js"
V47 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v47.js"
V48 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v48.js"
V51 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v51.js"
V52 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v52.js"
V53 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v53.js"
V54 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v54.js"
V55 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v55.js"
V56 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v56.js"
V57 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v57.js"
V58 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v58.js"
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

    def test_v58_is_active_server_seeded_and_cache_busted(self):
        panel = PANEL.read_text(encoding="utf-8")
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn('cook4me-recipe-hub-panel-v58', panel)
        self.assertIn('cook4me-panel-v58.js', panel)
        self.assertIn('?v=2026.9.9.1', panel)
        self.assertIn('"version": "2026.9.9.1"', manifest)
        for version in (20, 21, 22, 23, 24, 25, 26, 27, 28, 29):
            self.assertIn(f'async_register_websocket_v{version}', panel)
        self.assertIn('this._v51AllowedResources=new Set(["overview"])', V51.read_text(encoding="utf-8"))
        self.assertIn('data propagation, not a reason to poll', V52.read_text(encoding="utf-8"))
        self.assertIn('cook4me/v27/bootstrap', V53.read_text(encoding="utf-8"))
        self.assertIn('cook4me.ui.snapshot.v54.', V54.read_text(encoding="utf-8"))
        self.assertIn('missingOnly:true,force:false', V55.read_text(encoding="utf-8"))
        self.assertIn('data-v54-element-loading', V56.read_text(encoding="utf-8"))
        seeded = V57.read_text(encoding="utf-8")
        self.assertIn('cook4me/v28/ui_seed', seeded)
        self.assertIn('cook4me/v28/ingredient_catalog', seeded)
        self.assertIn('_renderDeferredSection', seeded)
        active = V58.read_text(encoding="utf-8")
        self.assertIn('cook4me/v29/today_suggest', active)
        self.assertIn('_v58StashImages()', active)
        self.assertIn('_v58RestoreImages()', active)

    def test_cache_first_layer_disables_render_triggered_nutrition_enrichment(self):
        text = V54.read_text(encoding="utf-8")
        self.assertIn('async _maybeAutoFillNutritionCatalog()', text)
        method = text.split('async _maybeAutoFillNutritionCatalog(){', 1)[1].split('_renderShopping(c){', 1)[0]
        self.assertNotIn('_api("cook4me/v16/nutrition_catalog_fill"', method)
        self.assertIn('return;', method)

    def test_v42_autofills_catalog_and_keeps_official_values_separate_historically(self):
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

    def test_v44_exposes_full_meal_lifecycle(self):
        text = V44.read_text(encoding="utf-8")
        for token in (
            'cook4me/v20/week_generate',
            'cook4me/v20/week_add_shopping',
            'cook4me/v20/lot_cost_set',
            'cook4me/v20/global_price_lookup',
            'cook4me/v20/shopping_reconcile_preview',
            'cook4me/v20/feedback_set',
            'cook4me/v20/substitution_suggest',
            'cook4me/v20/leftover_consume',
        ):
            self.assertIn(token, text)
        self.assertIn('currencyConversionApplied', (ROOT / "custom_components/cook4me/costing.py").read_text(encoding="utf-8"))

    def test_v45_currency_control_and_fx_contract(self):
        text = V45.read_text(encoding="utf-8")
        backend = (ROOT / "custom_components/cook4me/websocket_v21.py").read_text(encoding="utf-8")
        fx = (ROOT / "custom_components/cook4me/currency_fx.py").read_text(encoding="utf-8")
        self.assertIn('cook4meCurrencyControl', text)
        self.assertIn('cook4me/v21/currency_state', text)
        self.assertIn('cook4me/v21/currency_set', text)
        self.assertIn('source==="EUR"?1:Number(rates[source])', text)
        self.assertIn('default_currency_for_language', backend)
        self.assertIn('convert_currency_map', backend)
        self.assertIn('eurofxref-daily.xml', fx)
        self.assertIn('"bg": "EUR"', fx)

    def test_v46_keeps_bulk_menu_open_and_explicitly_toggles_filters(self):
        text = V46.read_text(encoding="utf-8")
        self.assertIn('this._rememberTodayFromUi(c)', text)
        self.assertNotIn('this._renderToday(c);', text.split('_toggleTodayBulk(c,group){', 1)[1].split('_bindExplicitDetails', 1)[0])
        self.assertIn('event.preventDefault()', text)
        self.assertIn('details.setAttribute("open","")', text)
        self.assertIn('summary.setAttribute("aria-expanded"', text)
        self.assertIn('details.rx-today-picker,details.rx-advanced', text)

    def test_v47_keeps_language_decoration_idempotent(self):
        text = V47.read_text(encoding="utf-8")
        self.assertIn('MAX_DOM_PASSES=80', text)
        self.assertIn('this._modernObserver?.disconnect?.()', text)
        self.assertIn('this.dataset.cook4meUiGuard="tripped"', text)
        self.assertIn('if(option.textContent!==next)option.textContent=next', text)

    def test_v48_guard_never_blocks_core_navigation_and_languages_always_have_picker(self):
        text = V48.read_text(encoding="utf-8")
        self.assertIn('if(kind==="render")return true', text)
        self.assertIn('Navigation and core controls remain available', text)
        self.assertIn('data-today-bulk="languages"', text)
        self.assertIn('anchor.dataset.todayLanguage=""', text)
        self.assertIn('data-rx-picker="languages"', text)
        self.assertIn('data.cook4meCatalogLanguageState', text.replace('dataset.', 'data.'))


if __name__ == "__main__":
    unittest.main()
