from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any
import urllib.parse

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import websocket as legacy
from . import websocket_v8 as v8
from . import websocket_v11 as v11
from . import websocket_v13 as v13
from . import websocket_v18 as v18
from . import websocket_v25 as v25
from . import websocket_v30 as v30
from .const import DATA_BRIDGES, DOMAIN
from .food_intelligence import nutrition_goal_bonus, normalize_nutrition_goal
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .online_cache import online_cache_for_bridge
from .recipe_cache import stable_cache_key
from .recipe_derived_cache import derived_recipe_store_for_bridge
from .reference_catalog import bundled_reference_catalog
from .request_coordinator import request_coordinator
from .today_logic import calorie_target_bonus, normalize_meal_types, recipe_identity, recipe_matches_meal_types
from .today_multilang import select_catalog_balanced
from .ui_state import ui_state_store_for_bridge
from .vendor import cook4me_phonefree as c4m
from .vendor import cook4me_recipe_catalog as recipe_catalog
from .vendor.cook4me_official_nutrition import extract_official_nutrition


def _text(value: Any) -> str:
    return str(value or "").strip()


def _best_nutrition(local: dict[str, Any], bundled: Any) -> dict[str, Any]:
    bundled = bundled if isinstance(bundled, dict) else {}
    if not bundled:
        return local
    if "exact_product" in set(local.get("sourceKinds") or []) and local.get("totals"):
        return local
    if bundled.get("totals") and float(bundled.get("coverage") or 0) >= float(local.get("coverage") or 0):
        result = deepcopy(bundled)
        result["sourceKinds"] = sorted(set(result.get("sourceKinds") or []) | {"bundled_reference"})
        result["referenceFallbackUsed"] = True
        return result
    return local


async def _decorate_economics(bridge, recipe: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(recipe)
    nutrition_store = await nutrition_store_for_bridge(bridge)
    local = calculate_recipe_nutrition_fefo(
        result,
        bridge.recipe_hub.profile.get("houseIngredients") or [],
        generic=nutrition_store.generic,
        stock_lots=nutrition_store.stock_lots,
    )
    result["nutrition"] = _best_nutrition(local, result.get("nutrition"))
    derived = await derived_recipe_store_for_bridge(bridge)
    result["cost"] = await derived.async_recipe_cost(bridge, result)
    return result


def _detail_with_official_sync(storage_home: str, display_country: str, configured_language: str, requested_language: str, app_version: str, variant_id: str) -> dict[str, Any]:
    cfg = c4m.read_apk_config(None)
    tokens = legacy._catalog_tokens(storage_home)
    pcfg = recipe_catalog._platform_context(cfg, display_country, configured_language, app_version)
    variant = recipe_catalog._fid(variant_id)
    if not variant:
        raise recipe_catalog.CatalogError("Recipe variant ID is required")
    base = cfg["platform_base_url"].rstrip("/")
    url = base + "/common-api/v3/recipes/PRO/" + urllib.parse.quote(variant, safe="") + "/?format=mobile"
    payload, auth_mode = recipe_catalog._http_json(
        "GET",
        url,
        headers_iter=recipe_catalog._request_headers(cfg, tokens, display_country, configured_language, app_version, url, pcfg),
    )
    root = recipe_catalog._recipe_root(payload)
    grouping_id = recipe_catalog._fid(root.get("groupingId")) or recipe_catalog._fid(root.get("topRecipeId"))
    recipe_id = recipe_catalog._fid(root.get("fid")) or recipe_catalog._fid(root.get("identifier")) or variant
    steps = recipe_catalog.extract_recipe_steps(root)
    normalized = {
        "groupingFunctionalId": grouping_id,
        "recipeFunctionalId": recipe_id,
        "variantFunctionalId": recipe_id,
        "searchVariantId": variant,
        "title": recipe_catalog._clean_text(root.get("title") or root.get("shortTitle") or root.get("normalizedTitle")),
        "cover": recipe_catalog.extract_recipe_cover(root),
        "stepCount": len(steps),
        "steps": steps,
        "ingredients": recipe_catalog.extract_recipe_ingredients(root),
        "excludedFoods": recipe_catalog._key_name_list(root, "excludedFoods"),
        "detectedExcludedFoods": recipe_catalog._key_name_list(root, "detectedExcludedFoods"),
        "courses": recipe_catalog._key_name_list(root, "courses"),
        "occasions": recipe_catalog._key_name_list(root, "occasions"),
        "durations": recipe_catalog._durations(root),
        "yield": recipe_catalog._yield(root),
        "difficulty": root.get("difficulty"),
        "recipeType": root.get("recipeType"),
        "language": recipe_catalog._clean_text(root.get("lang")) or requested_language,
        "market": recipe_catalog._clean_text(root.get("market")),
        "groupSize": root.get("groupSize"),
        "sendable": bool(grouping_id and recipe_id),
        "source": "sebplatform_mobile_recipe",
        "authMode": auth_mode,
        "officialNutrition": extract_official_nutrition(root),
    }
    return {key: value for key, value in normalized.items() if value is not None}


async def _offline_today(hass: HomeAssistant, bridge, msg: dict[str, Any], coordinator) -> dict[str, Any]:
    reference = bundled_reference_catalog()
    if not reference.metadata.get("recipeCount"):
        raise ValueError("Bundled recipe catalog is not populated")
    languages = v18._languages(bridge, msg.get("languages"))
    diet = str(msg.get("diet") or "profile")
    meal_types = normalize_meal_types(msg.get("meal_types"))
    query = _text(msg.get("query"))
    meal_count = int(msg.get("meal_count", 1))
    only_home = bool(msg.get("only_home"))
    max_missing = msg.get("max_missing") if "max_missing" in msg else None
    goal = normalize_nutrition_goal(msg.get("nutrition_goal"))
    prefer_expiring = bool(msg.get("prefer_expiring", True))
    avoid_recent_days = int(msg.get("avoid_recent_days", 7))
    tolerance = int(msg.get("calorie_tolerance", 25)) / 100.0
    ui_language = _text(msg.get("ui_language") or "en")

    coordinator.update_progress(phase="catalog", completed=0, total=1, message="Reading bundled recipe catalog")
    candidates = v30.reference_recipe_candidates(bridge, languages=languages, query=query, ui_language=ui_language, limit=500)
    coordinator.update_progress(phase="catalog", completed=1, total=1, message="Bundled recipe catalog ready")
    if meal_types:
        candidates = [row for row in candidates if recipe_matches_meal_types(row, meal_types)]
    if avoid_recent_days > 0:
        history = await meal_history_store_for_bridge(bridge)
        recent = v18._recent_identities(history.recent(200), days=avoid_recent_days)
        if recent:
            candidates = [row for row in candidates if recipe_identity(row) not in recent]

    ranked: list[dict[str, Any]] = []
    for index, language in enumerate(languages, 1):
        coordinator.update_progress(phase="ranking", completed=index - 1, total=len(languages), message=f"Ranking {language.upper()}")
        rows = [row for row in candidates if _text(row.get("todayCatalogLanguage")).lower() == language]
        ranked.extend(v13._rank_filtered(bridge, rows, diet=diet, limit=30))
        coordinator.update_progress(phase="ranking", completed=index, total=len(languages), message=f"Ranked {language.upper()}")

    nutrition_store = await nutrition_store_for_bridge(bridge)
    house = bridge.recipe_hub.profile.get("houseIngredients") or []
    scored: list[dict[str, Any]] = []
    total = max(1, len(ranked))
    for index, item in enumerate(ranked, 1):
        coordinator.update_progress(phase="nutrition", completed=index - 1, total=total, message=f"Nutrition {index}/{len(ranked)}")
        match = item.setdefault("match", {})
        if only_home and not bool(match.get("fullyAvailableByQuantity")):
            coordinator.update_progress(phase="nutrition", completed=index, total=total, message=f"Nutrition {index}/{len(ranked)}")
            continue
        shortages = match.get("quantityShortages") if isinstance(match.get("quantityShortages"), list) else []
        if max_missing is not None and len(shortages) > int(max_missing):
            coordinator.update_progress(phase="nutrition", completed=index, total=total, message=f"Nutrition {index}/{len(ranked)}")
            continue
        local = calculate_recipe_nutrition_fefo(item, house, generic=nutrition_store.generic, stock_lots=nutrition_store.stock_lots)
        nutrition = _best_nutrition(local, item.get("nutrition"))
        item["nutrition"] = nutrition
        score = float(match.get("score") or 0)
        if not prefer_expiring:
            score -= float(match.get("expiryBonus") or 0)
        hint = nutrition_goal_bonus(nutrition, goal)
        cal = calorie_target_bonus(nutrition, msg.get("calorie_target"), tolerance_fraction=tolerance)
        match.update({
            "nutritionGoal": goal,
            "nutritionGoalBonus": hint.get("bonus", 0.0),
            "nutritionGoalCoverage": hint.get("coverage", 0.0),
            "calorieTarget": cal.get("target"),
            "caloriePerServing": cal.get("calories"),
            "calorieDelta": cal.get("delta"),
            "calorieTargetBonus": cal.get("bonus", 0.0),
            "score": round(score + float(hint.get("bonus") or 0) + float(cal.get("bonus") or 0), 1),
        })
        item["deviceCanAccept"] = bridge.can_accept_recipe
        scored.append(item)
        coordinator.update_progress(phase="nutrition", completed=index, total=total, message=f"Nutrition {index}/{len(ranked)}")

    scored.sort(key=lambda row: row.get("match", {}).get("score", -1000), reverse=True)
    chosen = select_catalog_balanced(scored, meal_count, languages, diversity=bool(msg.get("variety", True)))
    selected_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in chosen)
    filters = {
        "languages": languages, "diet": diet, "mealTypes": meal_types, "onlyHome": only_home,
        "nutritionGoal": goal, "mealCount": meal_count, "calorieTarget": msg.get("calorie_target"),
        "calorieTolerancePercent": int(msg.get("calorie_tolerance", 25)), "maxMissing": max_missing,
        "preferExpiring": prefer_expiring, "avoidRecentDays": avoid_recent_days,
        "variety": bool(msg.get("variety", True)), "query": query,
    }
    result = {
        "date": dt_util.now().date().isoformat(), "items": chosen,
        "candidateCount": len(candidates), "rankedCount": len(scored),
        "catalogSelectedCounts": {language: int(selected_counts.get(language, 0)) for language in languages},
        "catalogLanguagesUsed": [language for language in languages if selected_counts.get(language, 0)],
        "filters": filters, "catalogSource": "bundled_reference_catalog", "referenceCatalog": reference.metadata,
    }
    coordinator.update_progress(phase="saving", completed=0, total=1, message="Saving today's plan")
    state_store = await ui_state_store_for_bridge(bridge)
    await state_store.async_set_today_plan(date=result["date"], items=chosen, filters=filters, meta={k: deepcopy(v) for k, v in result.items() if k not in {"items", "filters"}})
    coordinator.update_progress(phase="saving", completed=1, total=1, message="Today's plan saved")
    return result


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_today_suggest, ws_recipe_detail, ws_send_multi):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v31/today_suggest",
    vol.Optional("entry_id"): str,
    vol.Optional("languages", default=[]): [str],
    vol.Optional("diet", default="profile"): vol.In(v18._DIET_FILTERS),
    vol.Optional("meal_types", default=[]): [str],
    vol.Optional("only_home", default=False): bool,
    vol.Optional("nutrition_goal", default="balanced"): str,
    vol.Optional("meal_count", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=8)),
    vol.Optional("calorie_target"): vol.Any(int, float, str),
    vol.Optional("calorie_tolerance", default=25): vol.All(vol.Coerce(int), vol.Range(min=5, max=100)),
    vol.Optional("max_missing"): vol.All(vol.Coerce(int), vol.Range(min=0, max=20)),
    vol.Optional("prefer_expiring", default=True): bool,
    vol.Optional("avoid_recent_days", default=7): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
    vol.Optional("variety", default=True): bool,
    vol.Optional("query", default=""): str,
    vol.Optional("ui_language", default="en"): str,
})
@websocket_api.async_response
async def ws_today_suggest(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation("today_suggestions", "Build today's Cook4Me suggestions", entry_ids=[bridge.entry.entry_id]):
            result = await _offline_today(hass, bridge, msg, coordinator)
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v31/recipe_detail",
    vol.Optional("entry_id"): str,
    vol.Required("variant_id"): str,
    vol.Optional("language", default="de"): str,
})
@websocket_api.async_response
async def ws_recipe_detail(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        variant_id = _text(msg.get("variant_id")); language = _text(msg.get("language")) or "de"
        storage_home, _device_country, display_country, configured_language, requested_language, app_version = v8._catalog_context(bridge, language)
        cache = await online_cache_for_bridge(bridge)
        key = stable_cache_key("seb_recipe_detail_v31", display_country, requested_language, variant_id)
        coordinator = await request_coordinator(hass)
        async def fetch() -> dict[str, Any]:
            return await hass.async_add_executor_job(_detail_with_official_sync, storage_home, display_country, configured_language, requested_language, app_version, variant_id)
        async with coordinator.operation("recipe_detail", "Load recipe detail", entry_ids=[bridge.entry.entry_id]):
            coordinator.update_progress(phase="detail", completed=0, total=1, message="Loading recipe")
            cached = await cache.async_get_or_revalidate(key, fetch, source="seb_recipe_detail")
            coordinator.update_progress(phase="detail", completed=1, total=1, message="Recipe loaded")
            raw = cached.get("value") if isinstance(cached.get("value"), dict) else {}
            coordinator.update_progress(phase="nutrition", completed=0, total=1, message="Calculating nutrition and cost")
            result = await _decorate_economics(bridge, raw)
            coordinator.update_progress(phase="nutrition", completed=1, total=1, message="Nutrition and cost ready")
        result = bridge.recipe_hub.annotate(result)
        result.update({
            "deviceCanAccept": bridge.can_accept_recipe, "cacheHit": bool(cached.get("cacheHit")),
            "checkedOnline": bool(cached.get("checkedOnline")), "changed": bool(cached.get("changed")),
            "checkedAt": cached.get("checkedAt") or "", "updatedAt": cached.get("updatedAt") or "",
            "lastError": cached.get("lastError") or "", "minimumOnlineCheckHours": 24,
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v31/send_multi",
    vol.Optional("entry_id"): str,
    vol.Optional("entry_ids", default=[]): [str],
    vol.Required("recipe"): dict,
})
@websocket_api.async_response
async def ws_send_multi(hass, connection, msg) -> None:
    try:
        primary = legacy._bridge(hass, msg.get("entry_id"))
        bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
        requested = [str(value) for value in msg.get("entry_ids") or [] if str(value)] or [primary.entry.entry_id]
        selected=[]; seen=set()
        for entry_id in requested:
            bridge=bridges.get(entry_id)
            if bridge is not None and entry_id not in seen:
                selected.append(bridge); seen.add(entry_id)
        if not selected:
            raise ValueError("No selected Cook4Me device is currently loaded")
        recipe=dict(msg["recipe"]); coordinator=await request_coordinator(hass); results=[]
        async with coordinator.operation("device_send", "Send official recipe to selected Cook4Me devices", entry_ids=[bridge.entry.entry_id for bridge in selected]):
            for index, bridge in enumerate(selected,1):
                coordinator.update_progress(phase="devices", completed=index-1, total=len(selected), message=f"Sending to {bridge.entry.title}")
                row=await v25._send_one_exact(bridge, recipe)
                results.append({"entryId":bridge.entry.entry_id,"title":bridge.entry.title,**row})
                coordinator.update_progress(phase="devices", completed=index, total=len(selected), message=f"Finished {bridge.entry.title}")
        result={"results":results,"targetCount":len(results),"sentCount":sum(bool(row.get("sent")) for row in results),"queuedCount":sum(bool(row.get("queued")) for row in results)}
    except Exception as exc:
        legacy._send_error(connection,msg,exc); return
    connection.send_result(msg["id"],result)
