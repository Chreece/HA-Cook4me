from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "custom_components" / "cook4me" / "panel.py"
MANIFEST = ROOT / "custom_components" / "cook4me" / "manifest.json"
V49 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v49.js"
V50 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v50.js"
V51 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v51.js"
V52 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v52.js"
V53 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v53.js"
V22 = ROOT / "custom_components" / "cook4me" / "websocket_v22.py"
V23 = ROOT / "custom_components" / "cook4me" / "websocket_v23.py"
V24 = ROOT / "custom_components" / "cook4me" / "websocket_v24.py"
V25 = ROOT / "custom_components" / "cook4me" / "websocket_v25.py"
V26 = ROOT / "custom_components" / "cook4me" / "websocket_v26.py"
V27 = ROOT / "custom_components" / "cook4me" / "websocket_v27.py"
CACHE = ROOT / "custom_components" / "cook4me" / "online_cache.py"
RECIPE_CACHE = ROOT / "custom_components" / "cook4me" / "recipe_cache.py"
V9 = ROOT / "custom_components" / "cook4me" / "websocket_v9.py"
COORD = ROOT / "custom_components" / "cook4me" / "request_coordinator.py"


class V49OrchestrationContractTests(unittest.TestCase):
    def test_v53_is_active_and_all_new_backends_are_registered(self):
        panel = PANEL.read_text(encoding="utf-8")
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn('cook4me-recipe-hub-panel-v53', panel)
        self.assertIn('cook4me-panel-v53.js', panel)
        self.assertIn('?v=2026.9.8.7', panel)
        self.assertIn('"version": "2026.9.8.7"', manifest)
        for version in (22, 23, 24, 25, 26, 27):
            self.assertIn(f'async_register_websocket_v{version}', panel)
        self.assertIn('import "./cook4me-panel-v50.js"', V51.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v51.js"', V52.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v52.js"', V53.read_text(encoding="utf-8"))

    def test_online_cache_keeps_content_and_requires_daily_recheck(self):
        text = CACHE.read_text(encoding="utf-8")
        recipe = RECIPE_CACHE.read_text(encoding="utf-8")
        v9 = V9.read_text(encoding="utf-8")
        self.assertIn('_MIN_CHECK_AGE = 24 * 60 * 60', text)
        self.assertIn('"updatedAt": updated_at', text)
        self.assertIn('row["checkedAt"] = now', text)
        self.assertIn('_MIN_ONLINE_CHECK_AGE = 24 * 60 * 60', recipe)
        self.assertIn('should_revalidate("search", key)', v9)
        self.assertIn('should_revalidate("detail", key)', v9)

    def test_global_serialization_exists_on_frontend_and_backend(self):
        ui = V49.read_text(encoding="utf-8")
        backend = COORD.read_text(encoding="utf-8")
        self.assertIn('this._cook4meApiTail=Promise.resolve()', ui)
        self.assertIn('this._cook4meApiInflight=new Map()', ui)
        self.assertIn('this._cook4meApiTail.then(execute,execute)', ui)
        self.assertIn('self._lock = asyncio.Lock()', backend)
        self.assertIn('async def operation(', backend)
        self.assertIn('_OWNER: ContextVar', backend)

    def test_official_search_is_multilanguage_and_serial(self):
        ui = V49.read_text(encoding="utf-8")
        backend = V22.read_text(encoding="utf-8")
        self.assertIn('data-official-language', ui)
        self.assertIn('cook4me/v22/official_search', ui)
        self.assertIn('languages:this._loadOfficialLanguages()', ui)
        self.assertIn('for language in languages:', backend)
        self.assertNotIn('asyncio.gather', backend.split('async def _official_search', 1)[1].split('def _recent_titles', 1)[0])

    def test_ai_queue_is_replaced_by_direct_today_style_create(self):
        ui = V49.read_text(encoding="utf-8")
        backend = V25.read_text(encoding="utf-8")
        for token in (
            'id="aiRequest"', 'id="aiDiet"', 'id="aiNutritionGoal"',
            'id="aiCalories"', 'data-ai-meal-type', 'data-ai-language',
            'id="aiIngredients"', 'id="aiCalTolerance"', 'id="aiMaxMissing"',
            'id="aiRecent"', 'id="aiPreferExpiring"', 'id="aiOnlyHome"',
            'id="aiCreate"',
        ):
            self.assertIn(token, ui)
        for old in ('aiBatchPrompt', 'aiAddQueue', 'aiRunQueue', 'aiStopQueue'):
            self.assertNotIn(old, ui)
        self.assertIn('cook4me/v22/ai_create', ui)
        self.assertIn('profile["diet"] = previous_diet', backend)

    def test_ai_notification_uses_same_id_for_running_done_and_failure(self):
        v25 = V25.read_text(encoding="utf-8")
        self.assertIn('notification_id = f"cook4me_ai_recipe_{bridge.entry.entry_id}"', v25)
        self.assertGreaterEqual(v25.count('notification_id=notification_id'), 3)
        self.assertIn('_notification_text(language, "running")', v25)
        self.assertIn('_notification_text(language, "done"', v25)
        self.assertIn('_notification_text(language, "failed"', v25)

    def test_multiple_devices_are_persisted_and_sends_fan_out_serially(self):
        ui = V49.read_text(encoding="utf-8")
        backend = V25.read_text(encoding="utf-8")
        self.assertIn('cook4me.targetDevices.v1.', ui)
        self.assertIn('data-target-entry', ui)
        self.assertIn('entry_ids:targets', ui)
        self.assertIn('for bridge in selected:', backend)
        self.assertIn('await _send_one_exact(bridge, recipe)', backend)
        self.assertNotIn('asyncio.gather', backend)

    def test_active_online_endpoints_route_through_daily_cache(self):
        v50 = V50.read_text(encoding="utf-8")
        v23 = V23.read_text(encoding="utf-8")
        v24 = V24.read_text(encoding="utf-8")
        v26 = V26.read_text(encoding="utf-8")
        self.assertIn('cook4me/v24/currency_state', v50)
        self.assertIn('cook4me/v24/recipe_detail', v50)
        self.assertIn('cook4me/v26/barcode_scan', v50)
        self.assertIn('async_get_or_revalidate', v23)
        self.assertIn('async_get_or_revalidate', v24)
        self.assertIn('await v23._cached_product', v26)

    def test_v51_startup_contract_blocks_inherited_auto_loaders(self):
        ui = V51.read_text(encoding="utf-8")
        self.assertIn('this._v51AllowedResources=new Set(["overview"])', ui)
        self.assertIn('HA state propagation must never become a polling trigger', ui)
        self.assertIn('async _loadOverview(silent=false,rerender=true)', ui)
        self.assertIn('if(!this._resourceAllowed("book"))return', ui)
        self.assertIn('if(!this._resourceAllowed("today"))return', ui)
        self.assertIn('if(!this._resourceAllowed("catalog"))return', ui)
        self.assertIn('if(!this._resourceAllowed("week"))return', ui)
        self.assertIn('if(!this._resourceAllowed("currency"))', ui)
        self.assertIn('id="cook4meLoadSection"', ui)
        self.assertIn('aria-live","polite"', ui)

    def test_v52_hass_updates_do_zero_render_work_and_loading_is_continuous(self):
        ui = V52.read_text(encoding="utf-8")
        self.assertIn('data propagation, not a reason to poll', ui)
        self.assertIn('if(!this.shadowRoot.innerHTML)this._renderShell()', ui)
        self.assertNotIn('this._updateHeader()', ui)
        self.assertIn('const token=this._beginLoad(this._sectionTitle(tab))', ui)
        self.assertIn('return await super._prepareSection(tab)', ui)
        self.assertIn('this._endLoad(token)', ui)

    def test_v53_bootstrap_is_minimal_and_full_overview_is_deferred(self):
        ui = V53.read_text(encoding="utf-8")
        backend = V27.read_text(encoding="utf-8")
        self.assertIn('cook4me/v27/bootstrap', ui)
        self.assertIn('if(this._resourceAllowed("fullOverview"))', ui)
        self.assertIn('FULL_OVERVIEW_SECTIONS', ui)
        self.assertIn('await this._loadFullOverview(true,false,false)', ui)
        self.assertIn('"bootstrapContract": "minimal-device-header-v1"', backend)
        self.assertIn('_BOOTSTRAP_STATE_KEYS', backend)
        for forbidden in ('"profile"', '"recipes"', '"history"', '"habitTerms"', '"houseIngredients"', '"nutrition"'):
            self.assertNotIn(forbidden, backend)


if __name__ == "__main__":
    unittest.main()
