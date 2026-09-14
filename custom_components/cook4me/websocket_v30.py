from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import recipe_languages
from . import websocket as legacy
from . import websocket_v5 as v5
from . import websocket_v7 as v7
from . import websocket_v9 as v9
from . import websocket_v10 as v10
from . import websocket_v13 as v13
from . import websocket_v18 as v18
from . import websocket_v20 as v20
from . import websocket_v28 as v28
from .const import CONF_APP_VERSION, CONF_COUNTRY, CONF_LANGUAGE, DATA_BRIDGES, DEFAULT_APP_VERSION, DEFAULT_COUNTRY, DEFAULT_LANGUAGE, DOMAIN
from .costs import cost_store_for_bridge
from .food_intelligence import nutrition_goal_bonus, normalize_nutrition_goal
from .inventory import DEFAULT_EXPIRY_WARNING_DAYS, expiring_inventory_items
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .official_recipe_detail import recipe_detail as official_recipe_detail
from .recipe_cache import stable_cache_key
from .recipe_cost_cache import recipe_cost_cache_for_bridge
from .release_catalog import ingredient_rows, release_catalog_ready, release_catalog_summary, search_release_recipes
from .request_coordinator import request_coordinator
from .today_logic import calorie_target_bonus, normalize_meal_types, recipe_identity, recipe_matches_meal_types
from .today_multilang import select_catalog_balanced
from .today_plan_store import today_plan_store_for_bridge

_PROGRESS_ID = vol.Optional("client_operation_id", default="")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _device_language(bridge) -> str:
    return _text(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)).lower() or "de"


def _device_country(bridge) -> str:
    return _text(bridge.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)).upper() or "DE"


def _app_version(bridge) -> str:
    return _text(bridge.entry.data.get(CONF_APP_VERSION, DEFAULT_APP_VERSION)) or DEFAULT_APP_VERSION


def _client_operation_id(msg: dict[str, Any]) -> str:
    return _text(msg.get("client_operation_id"))[:160]


def _annotate_search(bridge, raw: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(raw)
    items: list[dict[str, Any]] = []
    for item in result.get("items") or []:
        if not isinstance(item, dict):
            continue
        row = bridge.recipe_hub.annotate(item)
        row["deviceCanAccept"] = bridge.can_accept_recipe
        items.append(row)
    result["items"] = items
    result["defaultAiTaskAvailable"] = v5._default_ai_task_entity_id(bridge.hass) is not None
    result["deviceCanAccept"] = bridge.can_accept_recipe
    result["loadedRecipe"] = bridge.loaded_recipe
    return result


async def _search(hass: HomeAssistant, bridge, *, query: str, page: int, size: int, language: str, strict_language: bool, refresh: bool, coordinator=None, operation=None) -> dict[str, Any]:
    if release_catalog_ready() and not refresh:
        if coordinator is not None:
            coordinator.progress(operation, "catalog_index", completed=0, total=1, message="Searching release catalog")
        raw = search_release_recipes(
            query,
            language=language,
            configured_language=_device_language(bridge),
            country=_device_country(bridge),
            page=page,
            size=size,
            strict_language=strict_language,
        )
        if coordinator is not None:
            coordinator.progress(operation, "catalog_index", completed=1, total=1, message="Release catalog ready")
        result = _annotate_search(bridge, raw)
        result["catalogMode"] = "release_offline"
        result["releaseCatalog"] = release_catalog_summary()
        return result
    if coordinator is not None:
        coordinator.progress(operation, "catalog_network", message="Refreshing official Cook4Me catalog" if refresh else "Release catalog unavailable; using live catalog")
    raw = await v10._search_with_diagnostic(
        hass, bridge, query=query, page=page, size=size, language=language,
        strict_language=strict_language, refresh=refresh,
    )
    raw["catalogMode"] = "live_refresh" if refresh else "live_fallback"
    raw["releaseCatalog"] = release_catalog_summary()
    return raw


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        ident = recipe_identity(row)
        if ident and ident in seen:
            continue
        if ident:
            seen.add(ident)
        out.append(row)
    return out


async def _recommend(hass: HomeAssistant, bridge, *, query: str, diet: str, limit: int, catalog_size: int, language: str, strict_language: bool, refresh: bool, coordinator, operation) -> dict[str, Any]:
    search = await _search(
        hass, bridge, query=query, page=0, size=catalog_size, language=language,
        strict_language=strict_language, refresh=refresh, coordinator=coordinator, operation=operation,
    )
    if not search.get("ok", True):
        return search
    candidates = list(search.get("items") or [])
    profile = bridge.recipe_hub.profile
    expiring = expiring_inventory_items(
        profile.get("houseIngredients") or [], today=dt_util.now().date(),
        within_days=DEFAULT_EXPIRY_WARNING_DAYS, include_past=False,
    )
    expiry_candidate_searches = 0
    if not query and expiring:
        coordinator.progress(operation, "expiry_candidates", completed=0, total=min(3, len(expiring)), message="Finding recipes for soon-expiring ingredients")
        for index, stock in enumerate(expiring[:3], start=1):
            name = _text(stock.get("name"))
            if name:
                try:
                    extra = await _search(
                        hass, bridge, query=name, page=0, size=min(20, catalog_size),
                        language=language, strict_language=strict_language, refresh=refresh,
                    )
                except Exception:
                    extra = {"ok": False}
                if extra.get("ok", True):
                    candidates.extend(extra.get("items") or [])
                    expiry_candidate_searches += 1
            coordinator.progress(operation, "expiry_candidates", completed=index, total=min(3, len(expiring)), message=name)
        candidates = _dedupe(candidates)
    coordinator.progress(operation, "ranking", completed=0, total=1, message="Ranking recipes")
    ranked = v13._rank_filtered(bridge, candidates, diet=diet, limit=limit)
    for item in ranked:
        item["deviceCanAccept"] = bridge.can_accept_recipe
    coordinator.progress(operation, "ranking", completed=1, total=1, message="Ranking complete")
    return {
        **{key: value for key, value in search.items() if key != "items"},
        "items": ranked,
        "profile": profile,
        "filters": {
            "query": query, "diet": diet,
            "houseIngredientCount": len(profile.get("houseIngredients") or []),
            "expiringIngredientCount": len(expiring),
            "expiryWarningDays": DEFAULT_EXPIRY_WARNING_DAYS,
            "expiryCandidateSearches": expiry_candidate_searches,
        },
    }


def _detail_sync(storage_home: str, country: str, language: str, app_version: str, variant_id: str) -> dict[str, Any]:
    return official_recipe_detail(
        legacy.c4m.read_apk_config(None), legacy._catalog_tokens(storage_home), variant_id,
        country=country, language=language, configured_language=language, app_version=app_version,
    )


async def _recipe_detail(hass: HomeAssistant, bridge, *, variant_id: str, language: str, refresh: bool, coordinator, operation) -> dict[str, Any]:
    cache = await v7._cache_for(hass, bridge)
    catalog_version = release_catalog_summary().get("catalogVersion") or "none"
    key = stable_cache_key("release-detail-v1", catalog_version, _text(variant_id), _text(language).lower())
    cached = cache.get("detail", key)
    cache_hit = isinstance(cached, dict)
    if cache_hit and not refresh:
        coordinator.progress(operation, "detail_cache", completed=1, total=1, message="Loaded cached recipe")
        raw = deepcopy(cached)
    else:
        coordinator.progress(operation, "detail_network", message="Retrieving official recipe detail")
        try:
            raw = await v9._async_catalog_call(
                hass, bridge, _detail_sync, str(bridge.storage_home),
                recipe_languages.country_for_language(language, _device_country(bridge)),
                language, _app_version(bridge), variant_id,
            )
        except Exception as exc:
            if cache_hit:
                await cache.async_mark_checked("detail", key, error=exc)
                raw = deepcopy(cached)
            else:
                raise
        else:
            await cache.async_set("detail", key, raw)
            cache_hit = False
        coordinator.progress(operation, "detail_normalize", completed=1, total=1, message="Recipe cached locally")
    result = bridge.recipe_hub.annotate(raw)
    result["deviceCanAccept"] = bridge.can_accept_recipe
    result["cacheHit"] = cache_hit
    result["checkedOnline"] = bool(refresh or not cache_hit)
    result["releaseCatalogVersion"] = catalog_version
    result["detailCacheContract"] = "sticky-until-refresh-or-release-v1"
    return result


async def _catalog_candidates(hass: HomeAssistant, bridge, *, languages: list[str], query: str, catalog_size: int, refresh: bool, coordinator, operation) -> tuple[list[dict[str, Any]], list[dict[str, str]], str]:
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    mode = "release_offline" if release_catalog_ready() and not refresh else ("live_refresh" if refresh else "live_fallback")
    total = len(languages)
    for index, language in enumerate(languages, start=1):
        coordinator.progress(operation, "catalogs", completed=index - 1, total=total, message=f"{language} catalog")
        try:
            result = await _search(
                hass, bridge, query=query, page=0, size=catalog_size, language=language,
                strict_language=True, refresh=refresh,
            )
        except Exception as exc:
            errors.append({"language": language, "reason": type(exc).__name__})
            coordinator.progress(operation, "catalogs", completed=index, total=total, message=f"{language} failed")
            continue
        if not result.get("ok", True):
            errors.append({"language": language, "reason": _text(result.get("reason") or result.get("error") or "catalog_error")[:120]})
            coordinator.progress(operation, "catalogs", completed=index, total=total, message=f"{language} failed")
            continue
        seen: set[str] = set()
        for raw in result.get("items") or []:
            if not isinstance(raw, dict):
                continue
            row = dict(raw)
            row["todayCatalogLanguage"] = language
            ident = recipe_identity(row)
            if ident and ident in seen:
                continue
            if ident:
                seen.add(ident)
            candidates.append(row)
        coordinator.progress(operation, "catalogs", completed=index, total=total, message=f"{language} catalog ready")
    return candidates, errors, mode


async def _today(hass: HomeAssistant, bridge, msg: dict[str, Any], *, coordinator, operation) -> dict[str, Any]:
    languages = v18._languages(bridge, msg.get("languages"))
    diet = _text(msg.get("diet") or "profile")
    meal_types = normalize_meal_types(msg.get("meal_types"))
    query = _text(msg.get("query"))
    only_home = bool(msg.get("only_home"))
    prefer_expiring = bool(msg.get("prefer_expiring", True))
    goal = normalize_nutrition_goal(msg.get("nutrition_goal"))
    meal_count = int(msg.get("meal_count", 1))
    max_missing = msg.get("max_missing") if "max_missing" in msg else None
    avoid_recent_days = int(msg.get("avoid_recent_days", 7))
    calorie_tolerance = int(msg.get("calorie_tolerance", 25)) / 100.0
    candidates, catalog_errors, catalog_mode = await _catalog_candidates(
        hass, bridge, languages=languages, query=query,
        catalog_size=int(msg.get("catalog_size", 40)), refresh=bool(msg.get("refresh")),
        coordinator=coordinator, operation=operation,
    )
    if meal_types:
        candidates = [row for row in candidates if recipe_matches_meal_types(row, meal_types)]
    history_store = await meal_history_store_for_bridge(bridge)
    recent = v18._recent_identities(history_store.recent(200), days=avoid_recent_days)
    if recent:
        candidates = [row for row in candidates if recipe_identity(row) not in recent]
    coordinator.progress(operation, "ranking", completed=0, total=len(languages) or 1, message="Ranking selected catalogs")
    ranked: list[dict[str, Any]] = []
    for index, language in enumerate(languages, start=1):
        language_rows = [row for row in candidates if _text(row.get("todayCatalogLanguage")).lower() == language]
        if language_rows:
            ranked.extend(v13._rank_filtered(bridge, language_rows, diet=diet, limit=30))
        coordinator.progress(operation, "ranking", completed=index, total=len(languages) or 1, message=f"{language} ranked")
    nutrition_store = await nutrition_store_for_bridge(bridge)
    house = bridge.recipe_hub.profile.get("houseIngredients") or []
    scored: list[dict[str, Any]] = []
    total_ranked = len(ranked)
    coordinator.progress(operation, "nutrition", completed=0, total=total_ranked or 1, message="Calculating meal nutrition")
    for index, item in enumerate(ranked, start=1):
        match = item.setdefault("match", {})
        if only_home and not bool(match.get("fullyAvailableByQuantity")):
            coordinator.progress(operation, "nutrition", completed=index, total=total_ranked or 1)
            continue
        shortages = match.get("quantityShortages") if isinstance(match.get("quantityShortages"), list) else []
        if max_missing is not None and len(shortages) > int(max_missing):
            coordinator.progress(operation, "nutrition", completed=index, total=total_ranked or 1)
            continue
        current_score = float(match.get("score") or 0.0)
        if not prefer_expiring:
            current_score -= float(match.get("expiryBonus") or 0.0)
            match["todayExpiryBonusSuppressed"] = True
        nutrition = calculate_recipe_nutrition_fefo(
            item, house, generic=nutrition_store.generic, stock_lots=nutrition_store.stock_lots,
        )
        if not (nutrition.get("totals") if isinstance(nutrition, dict) else None):
            nutrition = deepcopy(item.get("catalogNutrition") or item.get("nutrition") or {})
        item["nutrition"] = nutrition
        nutrition_hint = nutrition_goal_bonus(nutrition, goal)
        calorie_hint = calorie_target_bonus(nutrition, msg.get("calorie_target"), tolerance_fraction=calorie_tolerance)
        match["nutritionGoal"] = goal
        match["nutritionGoalBonus"] = nutrition_hint.get("bonus", 0.0)
        match["nutritionGoalCoverage"] = nutrition_hint.get("coverage", 0.0)
        match["calorieTarget"] = calorie_hint.get("target")
        match["caloriePerServing"] = calorie_hint.get("calories")
        match["calorieDelta"] = calorie_hint.get("delta")
        match["calorieTargetBonus"] = calorie_hint.get("bonus", 0.0)
        match["todayBaseScore"] = round(current_score, 1)
        match["score"] = round(current_score + float(nutrition_hint.get("bonus") or 0.0) + float(calorie_hint.get("bonus") or 0.0), 1)
        item["deviceCanAccept"] = bridge.can_accept_recipe
        scored.append(item)
        coordinator.progress(operation, "nutrition", completed=index, total=total_ranked or 1, message=f"{index}/{total_ranked}")
    scored.sort(key=lambda row: row.get("match", {}).get("score", -1000), reverse=True)
    chosen = select_catalog_balanced(scored, meal_count, languages, diversity=bool(msg.get("variety", True)))
    candidate_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in candidates)
    ranked_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in scored)
    selected_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in chosen)
    result = {
        "date": dt_util.now().date().isoformat(), "items": chosen,
        "candidateCount": len(candidates), "rankedCount": len(scored),
        "catalogErrors": catalog_errors, "catalogMode": catalog_mode,
        "catalogVersion": release_catalog_summary().get("catalogVersion") or "",
        "catalogCandidateCounts": {language: int(candidate_counts.get(language, 0)) for language in languages},
        "catalogRankedCounts": {language: int(ranked_counts.get(language, 0)) for language in languages},
        "catalogSelectedCounts": {language: int(selected_counts.get(language, 0)) for language in languages},
        "catalogLanguagesUsed": [language for language in languages if selected_counts.get(language, 0)],
        "filters": {
            "languages": languages, "diet": diet, "mealTypes": meal_types,
            "onlyHome": only_home, "nutritionGoal": goal, "mealCount": meal_count,
            "calorieTarget": msg.get("calorie_target"),
            "calorieTolerancePercent": int(msg.get("calorie_tolerance", 25)),
            "maxMissing": max_missing, "preferExpiring": prefer_expiring,
            "avoidRecentDays": avoid_recent_days, "variety": bool(msg.get("variety", True)),
            "query": query,
        },
    }
    store = await today_plan_store_for_bridge(bridge)
    await store.async_set(result)
    coordinator.progress(operation, "persist", completed=1, total=1, message="Today plan saved locally")
    return result


async def _seed_entry(hass: HomeAssistant, entry_id: str, bridge) -> tuple[dict[str, Any], dict[str, Any]]:
    entry, per_entry = await v28._seed_entry(hass, entry_id, bridge)
    language = _device_language(bridge)
    if release_catalog_ready():
        per_entry["ingredientCatalog"] = ingredient_rows(language)
        per_entry["ingredientCatalogLanguage"] = language
        per_entry["serverCatalogCache"] = {
            "language": language, "source": "cook4me_release_catalog",
            "cacheHit": True, "stale": False, "offline": True, **release_catalog_summary(),
        }
    today_store = await today_plan_store_for_bridge(bridge)
    today = today_store.snapshot
    if isinstance(today, dict):
        per_entry["todayResults"] = deepcopy(today.get("items") or [])
        per_entry["todayMeta"] = {key: deepcopy(value) for key, value in today.items() if key != "items"}
    per_entry["releaseCatalog"] = release_catalog_summary()
    return entry, per_entry


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_search, ws_recommend, ws_recipe_detail, ws_ingredient_catalog, ws_today_suggest, ws_ui_seed, ws_catalog_status, ws_recipe_cost):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/search", vol.Optional("entry_id"): str,
    vol.Optional("query", default=""): str, vol.Optional("page", default=0): vol.Coerce(int),
    vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
    vol.Optional("language", default=""): str, vol.Optional("strict_language", default=False): bool,
    vol.Optional("refresh", default=False): bool, _PROGRESS_ID: str,
})
@websocket_api.async_response
async def ws_search(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation("catalog_search", "Search recipes", entry_ids=[bridge.entry.entry_id], client_operation_id=_client_operation_id(msg)) as operation:
            result = await _search(
                hass, bridge, query=_text(msg.get("query")), page=int(msg.get("page", 0)),
                size=int(msg.get("size", 20)), language=_text(msg.get("language")) or _device_language(bridge),
                strict_language=bool(msg.get("strict_language")), refresh=bool(msg.get("refresh")),
                coordinator=coordinator, operation=operation,
            )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/recommend", vol.Optional("entry_id"): str,
    vol.Optional("limit", default=24): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
    vol.Optional("catalog_size", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
    vol.Optional("query", default=""): str, vol.Optional("diet", default="profile"): vol.In(v13._DIET_FILTERS),
    vol.Optional("language", default=""): str, vol.Optional("strict_language", default=False): bool,
    vol.Optional("refresh", default=False): bool, _PROGRESS_ID: str,
})
@websocket_api.async_response
async def ws_recommend(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation("recommend", "Recipe recommendations", entry_ids=[bridge.entry.entry_id], client_operation_id=_client_operation_id(msg)) as operation:
            result = await _recommend(
                hass, bridge, query=_text(msg.get("query")), diet=_text(msg.get("diet")) or "profile",
                limit=int(msg.get("limit", 24)), catalog_size=int(msg.get("catalog_size", 50)),
                language=_text(msg.get("language")) or _device_language(bridge),
                strict_language=bool(msg.get("strict_language")), refresh=bool(msg.get("refresh")),
                coordinator=coordinator, operation=operation,
            )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/recipe_detail", vol.Optional("entry_id"): str,
    vol.Required("variant_id"): str, vol.Optional("language", default="de"): str,
    vol.Optional("refresh", default=False): bool, _PROGRESS_ID: str,
})
@websocket_api.async_response
async def ws_recipe_detail(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation("recipe_detail", "Official recipe detail", entry_ids=[bridge.entry.entry_id], client_operation_id=_client_operation_id(msg)) as operation:
            result = await _recipe_detail(
                hass, bridge, variant_id=_text(msg.get("variant_id")),
                language=_text(msg.get("language")) or _device_language(bridge),
                refresh=bool(msg.get("refresh")), coordinator=coordinator, operation=operation,
            )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/ingredient_catalog", vol.Optional("entry_id"): str,
    vol.Optional("language"): str, vol.Optional("refresh", default=False): bool, _PROGRESS_ID: str,
})
@websocket_api.async_response
async def ws_ingredient_catalog(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        language = recipe_languages.normalize_catalog_language(_text(msg.get("language")) or _device_language(bridge), _device_language(bridge))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation("ingredient_catalog", "Ingredient catalog", entry_ids=[bridge.entry.entry_id], client_operation_id=_client_operation_id(msg)) as operation:
            if release_catalog_ready() and not bool(msg.get("refresh")):
                coordinator.progress(operation, "catalog_index", completed=0, total=1)
                result = {
                    "language": language, "items": ingredient_rows(language),
                    "source": "cook4me_release_catalog", "cacheHit": True,
                    "stale": False, "offline": True, "releaseCatalog": release_catalog_summary(),
                }
                coordinator.progress(operation, "catalog_index", completed=1, total=1)
            else:
                coordinator.progress(operation, "catalog_network", message="Refreshing ingredient catalog")
                result = await v28._fetch_catalog(hass, bridge, language) if bool(msg.get("refresh")) else (await v28._cached_catalog(bridge, language) or await v28._fetch_catalog(hass, bridge, language))
                result["offline"] = False
                result["releaseCatalog"] = release_catalog_summary()
            result["houseIngredients"] = bridge.recipe_hub.profile.get("houseIngredients") or []
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/today_suggest", vol.Optional("entry_id"): str,
    vol.Optional("languages", default=[]): [str], vol.Optional("diet", default="profile"): vol.In(v18._DIET_FILTERS),
    vol.Optional("meal_types", default=[]): [str], vol.Optional("only_home", default=False): bool,
    vol.Optional("nutrition_goal", default="balanced"): str,
    vol.Optional("meal_count", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=8)),
    vol.Optional("calorie_target"): vol.Any(int, float, str),
    vol.Optional("calorie_tolerance", default=25): vol.All(vol.Coerce(int), vol.Range(min=5, max=100)),
    vol.Optional("max_missing"): vol.All(vol.Coerce(int), vol.Range(min=0, max=20)),
    vol.Optional("prefer_expiring", default=True): bool,
    vol.Optional("avoid_recent_days", default=7): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
    vol.Optional("variety", default=True): bool, vol.Optional("query", default=""): str,
    vol.Optional("catalog_size", default=40): vol.All(vol.Coerce(int), vol.Range(min=10, max=50)),
    vol.Optional("refresh", default=False): bool, _PROGRESS_ID: str,
})
@websocket_api.async_response
async def ws_today_suggest(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation("today_suggest", "Today's suggestions", entry_ids=[bridge.entry.entry_id], client_operation_id=_client_operation_id(msg)) as operation:
            result = await _today(hass, bridge, msg, coordinator=coordinator, operation=operation)
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v30/ui_seed", _PROGRESS_ID: str})
@websocket_api.async_response
async def ws_ui_seed(hass, connection, msg) -> None:
    try:
        bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
        entries: list[dict[str, Any]] = []
        per_entry: dict[str, dict[str, Any]] = {}
        for entry_id, bridge in bridges.items():
            entry, cached = await _seed_entry(hass, entry_id, bridge)
            entries.append(entry)
            per_entry[entry_id] = cached
        connection.send_result(msg["id"], {
            "entries": entries, "perEntry": per_entry,
            "selectedEntryId": entries[0]["entry_id"] if entries else "",
            "fullOverviewCached": True,
            "serverSeedContract": "local-persistent-ui-v2-compact-today-release-catalog",
            "onlineRequests": 0, "releaseCatalog": release_catalog_summary(),
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/recipe_cost", vol.Optional("entry_id"): str,
    vol.Required("recipe"): dict, vol.Optional("currency", default=""): str,
    vol.Optional("country", default=""): str, vol.Optional("force", default=False): bool,
    vol.Optional("refresh_global", default=False): bool, _PROGRESS_ID: str,
})
@websocket_api.async_response
async def ws_recipe_cost(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation("recipe_cost", "Recipe cost", entry_ids=[bridge.entry.entry_id], client_operation_id=_client_operation_id(msg)) as operation:
            coordinator.progress(operation, "cost", completed=0, total=1, message="Calculating current local price")
            store = await cost_store_for_bridge(bridge)
            global_added = 0
            if bool(msg.get("refresh_global")) or store.settings.get("autoGlobalPrices"):
                coordinator.progress(operation, "cost_sources", message="Checking global price references")
                global_added = await v20._hydrate_global_prices(hass, bridge, store, dict(msg["recipe"]))
            cache = await recipe_cost_cache_for_bridge(bridge)
            result = await cache.async_cost(
                dict(msg["recipe"]), bridge.recipe_hub.profile.get("houseIngredients") or [], store,
                currency=_text(msg.get("currency")), country=_text(msg.get("country")),
                force=bool(msg.get("force")),
            )
            result["globalReferencesAdded"] = global_added
            coordinator.progress(operation, "cost", completed=1, total=1, message="Price ready")
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v30/catalog_status"})
@callback
def ws_catalog_status(hass, connection, msg) -> None:
    connection.send_result(msg["id"], {
        **release_catalog_summary(),
        "runtimeUsesReleaseCatalog": release_catalog_ready(),
        "runtimeFallbackEnabled": True,
        "catalogPath": "custom_components/cook4me/catalog/merged_catalog.v1.json",
        "builder": "tools/build_release_catalog.py",
    })
