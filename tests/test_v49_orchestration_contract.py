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
V54 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v54.js"
V55 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v55.js"
V56 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v56.js"
V57 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v57.js"
V22 = ROOT / "custom_components" / "cook4me" / "websocket_v22.py"
V23 = ROOT / "custom_components" / "cook4me" / "websocket_v23.py"
V24 = ROOT / "custom_components" / "cook4me" / "websocket_v24.py"
V25 = ROOT / "custom_components" / "cook4me" / "websocket_v25.py"
V26 = ROOT / "custom_components" / "cook4me" / "websocket_v26.py"
V27 = ROOT / "custom_components" / "cook4me" / "websocket_v27.py"
V28 = ROOT / "custom_components" / "cook4me" / "websocket_v28.py"
CACHE = ROOT / "custom_components" / "cook4me" / "online_cache.py"
RECIPE_CACHE = ROOT / "custom_components" / "cook4me" / "recipe_cache.py"
V9 = ROOT / "custom_components" / "cook4me" / "websocket_v9.py"
COORD = ROOT / "custom_components" / "cook4me" / "request_coordinator.py"


class V49OrchestrationContractTests(unittest.TestCase):
    def test_v57_is_active_and_all_new_backends_are_registered(self):
        panel = PANEL.read_text(encoding="utf-8")
        manifest = MANIFEST.read_text(encoding="utf-8")
        self.assertIn('cook4me-recipe-hub-panel-v57', panel)
        self.assertIn('cook4me-panel-v57.js', panel)
        self.assertIn('?v=2026.9.8.9', panel)
        self.assertIn('"version": "2026.9.8.9"', manifest)
        for version in (22, 23, 24, 25, 26, 27, 28):
            self.assertIn(f'async_register_websocket_v{version}', panel)
        self.assertIn('import "./cook4me-panel-v50.js"', V51.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v51.js"', V52.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v52.js"', V53.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v53.js"', V54.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v54.js"', V55.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v55.js"', V56.read_text(encoding="utf-8"))
        self.assertIn('import "./cook4me-panel-v56.js"', V57.read_text(encoding="utf-8"))

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
        for token in ('id="aiRequest"','id="aiDiet"','id="aiNutritionGoal"','id="aiCalories"','data-ai-meal-type','data-ai-language','id="aiIngredients"','id="aiCalTolerance"','id="aiMaxMissing"','id="aiRecent"','id="aiPreferExpiring"','id="aiOnlyHome"','id="aiCreate"'):
            self.assertIn(token, ui)
        for old in ('aiBatchPrompt', 'aiAddQueue', 'aiRunQueue', 'aiStopQueue'):
            self.assertNotIn(old, ui)
        self.assertIn('cook4me/v22/ai_create', ui)
        self.assertIn('profile["diet"] = previous_diet', backend)

    def test_ai_notification_uses_same_id_for_running_done_and_failure(self):
        v25 = V25.read_text(encoding="utf-8")
        self.assertIn('notification_id = f"cook4me_ai_recipe_{bridge.entry.entry_id}"', v25)
        self.assertGreaterEqual(v25.count('notification_id=notification_id'), 3)

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

    def test_historical_v51_v53_guards_are_physically_neutralized_by_v57(self):
        self.assertIn('id="cook4meLoadSection"', V51.read_text(encoding="utf-8"))
        active = V57.read_text(encoding="utf-8")
        self.assertIn('_renderDeferredSection', active)
        self.assertIn('whole-section Load wall', active)
        self.assertIn('this._v51PreparedSections.add(tab)', active)

    def test_v52_hass_updates_do_zero_render_work(self):
        ui = V52.read_text(encoding="utf-8")
        self.assertIn('data propagation, not a reason to poll', ui)
        self.assertIn('if(!this.shadowRoot.innerHTML)this._renderShell()', ui)
        self.assertNotIn('this._updateHeader()', ui)

    def test_v53_bootstrap_is_minimal(self):
        backend = V27.read_text(encoding="utf-8")
        self.assertIn('"bootstrapContract": "minimal-device-header-v1"', backend)
        self.assertIn('_BOOTSTRAP_STATE_KEYS', backend)

    def test_v54_v57_make_ui_cache_first_and_server_seeded(self):
        v54 = V54.read_text(encoding="utf-8")
        v55 = V55.read_text(encoding="utf-8")
        v56 = V56.read_text(encoding="utf-8")
        v57 = V57.read_text(encoding="utf-8")
        self.assertIn('cook4me.ui.snapshot.v54.', v54)
        self.assertIn('missingOnly:true,force:false', v55)
        self.assertIn('data-v54-element-loading', v56)
        self.assertIn('cook4me/v28/ui_seed', v57)
        self.assertIn('cook4me/v28/ingredient_catalog', v57)
        self.assertIn('if(!force&&!this._v54HadUiCache&&!this._v57ServerSeedDone)', v57)
        self.assertIn('current in-memory device status', v57)

    def test_v28_server_seed_is_local_only_and_retains_catalog(self):
        text = V28.read_text(encoding="utf-8")
        seed = text.split('async def _seed_entry', 1)[1].split('@callback\ndef async_register', 1)[0]
        endpoint = text.split('async def ws_ui_seed', 1)[1].split('@websocket_api.websocket_command', 1)[0]
        self.assertNotIn('_fetch_catalog(', seed)
        self.assertNotIn('async_add_executor_job', seed)
        self.assertNotIn('_fetch_catalog(', endpoint)
        self.assertIn('serverSeedContract', text)
        self.assertIn('onlineRequests', text)
        self.assertIn('_catalog_store', text)
        self.assertIn('checkedAt', text)
        self.assertIn('minimumOnlineCheckHours', text)
        self.assertNotIn('<= _MIN_CHECK_AGE', text)


if __name__ == "__main__":
    unittest.main()
