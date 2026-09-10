from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components/cook4me/frontend/cook4me-panel-v59.js"
WS = ROOT / "custom_components/cook4me/websocket_v30.py"
COORD = ROOT / "custom_components/cook4me/request_coordinator.py"
BUILDER = ROOT / "tools/build_release_catalog.py"
CATALOG = ROOT / "custom_components/cook4me/catalog/merged_catalog.v1.json"
RELEASE = ROOT / "custom_components/cook4me/release_catalog.py"
INIT = ROOT / "custom_components/cook4me/__init__.py"
COST_CACHE = ROOT / "custom_components/cook4me/recipe_cost_cache.py"
TODAY = ROOT / "custom_components/cook4me/today_plan_store.py"
V10 = ROOT / "custom_components/cook4me/websocket_v10.py"
V11 = ROOT / "custom_components/cook4me/websocket_v11.py"


class V59ArchitectureContractTests(unittest.TestCase):
    def test_startup_shell_is_bounded_and_old_rich_snapshot_is_not_parsed(self):
        source = FRONTEND.read_text(encoding="utf-8")
        self.assertIn("MAX_SYNC_SHELL_BYTES=120000", source)
        self.assertIn("cook4me.ui.shell.v2", source)
        self.assertIn("requestIdleCallback", source)
        self.assertIn("raw.length<=MAX_SYNC_SHELL_BYTES", source)
        hydrate = source[source.index("_hydrateUiSnapshot(user)"):source.index("_v59ScheduleLegacySnapshotCleanup()", source.index("_hydrateUiSnapshot(user)"))]
        self.assertNotIn("cook4me.ui.snapshot.v54", hydrate)
        self.assertNotIn("ingredientCatalog:copySmall", source)
        self.assertNotIn("results:copySmall", source)

    def test_progress_contract_is_shared_and_nonblocking(self):
        frontend = FRONTEND.read_text(encoding="utf-8")
        coordinator = COORD.read_text(encoding="utf-8")
        self.assertIn('PROGRESS_EVENT="cook4me_operation_progress"', frontend)
        self.assertIn('EVENT_OPERATION_PROGRESS = "cook4me_operation_progress"', coordinator)
        self.assertIn("clientOperationId", coordinator)
        self.assertIn("completed", coordinator)
        self.assertIn("total", coordinator)
        self.assertIn("percent", coordinator)
        self.assertIn("position:fixed", frontend)
        self.assertNotIn("rx-overlay", frontend)
        self.assertNotIn("processCancel", frontend)

    def test_release_catalog_is_explicitly_inactive_until_exhaustive_build(self):
        import json
        payload = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertFalse(payload["complete"])
        self.assertEqual(payload["source"]["auditedCatalogCount"], 28)
        self.assertEqual(payload["source"]["sourceCatalogCount"], 21)
        builder = BUILDER.read_text(encoding="utf-8")
        self.assertIn("AUDITED_CATALOGS", builder)
        self.assertIn('(\"da\", \"DK\")', builder)
        self.assertIn('(\"el\", \"GR\")', builder)
        self.assertIn('(\"sv\", \"SE\")', builder)
        self.assertIn("PAGE_SIZE = 5000", builder)
        self.assertIn("provider catalog exceeds proven single-page", builder)
        self.assertIn("single-page response row count does not match provider total", builder)
        self.assertIn("duplicate provider functional IDs", builder)
        self.assertNotIn("while total_pages is None or page < total_pages", builder)
        self.assertIn("hydratedVariants", builder)
        self.assertIn("canonicalEnglishNeedsReview", builder)
        self.assertIn("nutritionRequiredForComplete", builder)
        self.assertIn("normalized-ingredient-references-v1", builder)
        self.assertIn("officialSebDetailStored", builder)
        self.assertIn("secretsPersisted", builder)
        self.assertNotIn("extract_official_nutrition", builder)

    def test_large_release_catalog_is_warmed_outside_home_assistant_event_loop(self):
        release = RELEASE.read_text(encoding="utf-8")
        setup = INIT.read_text(encoding="utf-8")
        self.assertIn("async def async_warm_release_catalog", release)
        self.assertIn("await hass.async_add_executor_job(load_release_catalog)", release)
        self.assertIn("_prepare_runtime_indexes(payload)", release)
        self.assertIn("_runtimeRecipeByLanguage", release)
        self.assertIn("from .release_catalog import async_warm_release_catalog", setup)
        self.assertIn("await async_warm_release_catalog(hass)", setup)

    def test_ingredient_picker_payload_omits_nutrient_blobs_by_default(self):
        release = RELEASE.read_text(encoding="utf-8")
        self.assertIn("include_nutrition: bool = False", release)
        self.assertIn("if include_nutrition and isinstance(raw.get(\"nutrition\"), dict):", release)
        self.assertIn("limit: int | None = None", release)
        self.assertIn("_runtimeIngredientById", release)

    def test_runtime_paths_are_offline_first_with_safe_live_fallback(self):
        source = WS.read_text(encoding="utf-8")
        self.assertIn("release_catalog_ready() and not refresh", source)
        self.assertIn('"catalogMode"] = "release_offline"', source)
        self.assertIn('"live_fallback"', source)
        self.assertIn("today_plan_store_for_bridge", source)
        self.assertIn("sticky-until-refresh-or-release-v1", source)

    def test_common_catalog_layers_switch_all_internal_callers_offline(self):
        recipes = V10.read_text(encoding="utf-8")
        ingredients = V11.read_text(encoding="utf-8")
        self.assertIn("release_index.release_catalog_ready() and not refresh", recipes)
        self.assertIn("release_index.search_release_recipes", recipes)
        self.assertIn("not-required-offline-release-catalog", recipes)
        self.assertIn("release_index.release_catalog_ready() and not refresh", ingredients)
        self.assertIn("release_index.ingredient_rows(language)", ingredients)
        self.assertIn('"source": "cook4me_release_catalog"', ingredients)

    def test_public_home_assistant_recipe_services_use_same_offline_first_search(self):
        setup = INIT.read_text(encoding="utf-8")
        service_section = setup[setup.index("async def handle_search"):setup.index("hass.services.async_register(")]
        self.assertIn("recipe_search_api._search_with_diagnostic", service_section)
        self.assertIn("strict_language=True", service_section)
        self.assertIn('refresh=bool(call.data.get("refresh", False))', service_section)
        self.assertNotIn("bridge.async_search_recipes", service_section)
        self.assertNotIn("bridge.async_recommend_recipes", service_section)

    def test_cost_cache_invalidates_from_price_evidence_fingerprint(self):
        source = COST_CACHE.read_text(encoding="utf-8")
        self.assertIn("pricing_fingerprint", source)
        self.assertIn("references", source)
        self.assertIn("lot:", source)
        self.assertIn("barcode:", source)
        self.assertIn("costCacheHit", source)
        self.assertIn("price-evidence-fingerprint-v1", source)

    def test_today_server_cache_stores_card_summary_not_recipe_detail(self):
        source = TODAY.read_text(encoding="utf-8")
        self.assertIn("compact_today_recipe", source)
        self.assertIn("_MAX_ITEMS = 16", source)
        self.assertNotIn('"steps"', source)
        self.assertNotIn('"ingredients"', source)

    def test_official_seb_nutrition_is_visually_separate_from_calculated_nutrition(self):
        source = FRONTEND.read_text(encoding="utf-8")
        self.assertIn("officialSebNutrition", source)
        self.assertIn("basisUnspecified", source)
        self.assertIn("official.hierarchicalNutrients", source)
        self.assertIn("recipe.officialNutrition", source)
        self.assertIn("nutrition.coverage", source)
        self.assertIn("values?.fiber", source)


if __name__ == "__main__":
    unittest.main()
