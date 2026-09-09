from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import recipe_languages
from . import websocket as legacy
from . import websocket_v8 as v8
from . import websocket_v9 as v9
from . import websocket_v10 as v10
from . import websocket_v13 as v13
from . import websocket_v18 as v18
from . import websocket_v22 as v22
from . import websocket_v28 as v28
from .const import CONF_COUNTRY, CONF_LANGUAGE, DATA_BRIDGES, DEFAULT_COUNTRY, DEFAULT_LANGUAGE, DOMAIN
from .food_intelligence import nutrition_goal_bonus, normalize_nutrition_goal
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .online_cache import online_cache_for_bridge
from .operation_progress import publish_operation_progress
from .recipe_book import recipe_book_store_for_bridge
from .recipe_cache import stable_cache_key
from .release_catalog import release_catalog
from .request_coordinator import request_coordinator
from .today_logic import (
    calorie_target_bonus,
    normalize_meal_types,
    recipe_identity,
    recipe_matches_meal_types,
)
from .today_multilang import select_catalog_balanced
from .today_store import today_store_for_bridge
from .vendor import cook4me_phonefree as c4m
from .vendor import cook4me_recipe_catalog as base_catalog
from .vendor import cook4me_recipe_detail_enriched as enriched_detail


def _text(value: Any) -> str:
    return str(value or "").strip()


def _iso(stamp: Any) -> str:
    try:
        return datetime.fromtimestamp(float(stamp), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _op(msg: dict[str, Any]) -> str:
    return _text(msg.get("client_operation_id"))


def _minimal_entry(entry_id: str, bridge) -> dict[str, Any]:
    return {
        "entry_id": entry_id,
        "title": bridge.entry.title,
        "connected": bool(bridge.available),
        "canAcceptRecipe": bool(bridge.can_accept_recipe),
        "loadedRecipe": v28.v27._loaded_recipe_summary(bridge.loaded_recipe),
        "state": v28.v27._state_summary(getattr(bridge, "data", None)),
        "configuredLanguage": str(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)),
        "country": str(bridge.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)),
    }


async def _minimal_seed_entry(hass: HomeAssistant, entry_id: str, bridge) -> tuple[dict[str, Any], dict[str, Any]]:
    book = await recipe_book_store_for_bridge(bridge)
    catalog = release_catalog()
    return _minimal_entry(entry_id, bridge), {
        "capabilities": {
            **v28._capabilities(hass, bridge),
            "releaseCatalog": catalog.metadata(),
        },
        "uiPreferences": deepcopy(bridge.recipe_hub.ui_preferences),
        "bookState": {
            **book.snapshot(),
            "deviceConnected": bool(bridge.available),
            "deviceCanAccept": bool(bridge.can_accept_recipe),
            "loadedRecipe": v28.v27._loaded_recipe_summary(bridge.loaded_recipe),
        },
        "todayOptions": v28._today_options(bridge),
        "ingredientCatalog": [],
        "ingredientCatalogLanguage": "",
        "results": [],
        "recommendations": [],
        "todayResults": [],
        "todayMeta": None,
        "searchQuery": "",
    }


def _decorate_release_rows(bridge, rows: list[dict[str, Any]], language: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in rows:
        source = deepcopy(raw)
        catalog_nutrition = deepcopy(source.get("nutrition")) if isinstance(source.get("nutrition"), dict) else None
        row = bridge.recipe_hub.annotate(source)
        row["deviceCanAccept"] = bridge.can_accept_recipe
        row["officialCatalogLanguage"] = language
        if catalog_nutrition is not None:
            row["catalogNutrition"] = catalog_nutrition
        out.append(row)
    return out


async def _ingredient_catalog(hass: HomeAssistant, bridge, language: str, *, refresh: bool) -> dict[str, Any]:
    snapshot = release_catalog()
    if snapshot.usable and not refresh:
        items = snapshot.ingredient_rows(language)
        return {
            "language": language,
            "items": items,
            "source": "cook4me_release_catalog",
            "releaseCatalog": snapshot.metadata(),
            "cacheHit": True,
            "checkedOnline": False,
            "changed": False,
            "stale": False,
            "houseIngredients": bridge.recipe_hub.profile.get("houseIngredients") or [],
        }
    cached = await v28._cached_catalog(bridge, language)
    result = cached if cached is not None and not refresh else await v28._fetch_catalog(hass, bridge, language)
    result["houseIngredients"] = bridge.recipe_hub.profile.get("houseIngredients") or []
    result["releaseCatalog"] = snapshot.metadata()
    return result


async def _official_search(
    hass: HomeAssistant,
    bridge,
    *,
    languages: list[str],
    query: str,
    page: int,
    size: int,
    strict_language: bool,
    operation_id: str,
) -> dict[str, Any]:
    snapshot = release_catalog()
    if not snapshot.usable:
        return await v22._official_search(
            hass,
            bridge,
            languages=languages,
            query=query,
            page=page,
            size=size,
            strict_language=strict_language,
        )

    rows: list[dict[str, Any]] = []
    catalogs: list[dict[str, Any]] = []
    total = max(1, len(languages))
    for index, language in enumerate(languages, start=1):
        candidates = snapshot.recipes_for_language(
            language,
            query=query,
            size=max(1, (page + 1) * size),
        )
        start = max(0, page * size)
        decorated = _decorate_release_rows(bridge, candidates[start:start + size], language)
        rows.extend(decorated)
        catalogs.append(
            {
                "language": language,
                "ok": True,
                "count": len(decorated),
                "cacheHit": True,
                "checkedOnline": False,
                "changed": False,
                "source": "cook4me_release_catalog",
            }
        )
        publish_operation_progress(
            hass,
            operation_id,
            phase="catalog_lookup",
            message=f"{language.upper()} catalog",
            completed=index,
            total=total,
        )
    deduped = v13._dedupe_recipes(rows)
    return {
        "items": deduped,
        "languages": languages,
        "catalogs": catalogs,
        "count": len(deduped),
        "deviceCanAccept": bridge.can_accept_recipe,
        "loadedRecipe": bridge.loaded_recipe,
        "releaseCatalog": snapshot.metadata(),
        "offlineCatalog": True,
    }


async def _fetch_enriched_detail(hass: HomeAssistant, bridge, variant_id: str, language: str) -> dict[str, Any]:
    (
        storage_home,
        _device_country,
        display_country,
        _configured_language,
        requested_language,
        app_version,
    ) = v8._catalog_context(bridge, language)

    def load() -> dict[str, Any]:
        return enriched_detail.recipe_detail(
            c4m.read_apk_config(None),
            legacy._catalog_tokens(storage_home),
            variant_id,
            country=display_country,
            language=requested_language,
            configured_language=requested_language,
            app_version=app_version,
        )

    try:
        return await hass.async_add_executor_job(load)
    except base_catalog.CatalogAuthError:
        await v9._refresh_catalog_auth(hass, bridge)
        return await hass.async_add_executor_job(load)


async def _recipe_detail(
    hass: HomeAssistant,
    bridge,
    *,
    variant_id: str,
    language: str,
    refresh: bool,
    operation_id: str,
) -> dict[str, Any]:
    cache = await online_cache_for_bridge(bridge)
    key = stable_cache_key("seb_recipe_detail_v30", variant_id, language.lower())
    cached = cache.get(key)
    row = cache.row(key) or {}
    if isinstance(cached, dict) and not refresh:
        result = deepcopy(cached)
        cache_hit = True
        checked_online = False
        changed = False
    else:
        publish_operation_progress(
            hass,
            operation_id,
            phase="recipe_detail",
            message="Fetching recipe detail",
            completed=0,
            total=1,
        )
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "recipe_detail",
            "Official recipe detail",
            entry_ids=[bridge.entry.entry_id],
        ):
            try:
                fetched = await _fetch_enriched_detail(hass, bridge, variant_id, language)
            except Exception as exc:
                if not isinstance(cached, dict):
                    raise
                result = deepcopy(cached)
                cache_hit = True
                checked_online = True
                changed = False
                await cache.async_record_failure(key, exc)
            else:
                meta = await cache.async_record(key, fetched, source="seb_recipe_detail")
                result = deepcopy(fetched)
                cache_hit = isinstance(cached, dict)
                checked_online = True
                changed = bool(meta.get("changed"))
                row = cache.row(key) or {}
        publish_operation_progress(
            hass,
            operation_id,
            phase="recipe_detail",
            message="Recipe detail ready",
            completed=1,
            total=1,
        )
    annotated = bridge.recipe_hub.annotate(result)
    annotated["deviceCanAccept"] = bridge.can_accept_recipe
    annotated["cacheHit"] = cache_hit
    annotated["checkedOnline"] = checked_online
    annotated["changed"] = changed
    annotated["checkedAt"] = _iso(row.get("checkedAt"))
    annotated["updatedAt"] = _iso(row.get("updatedAt"))
    annotated["lastError"] = _text(row.get("lastError"))
    annotated["detailCacheContract"] = "cache-first-explicit-refresh-v1"
    return annotated


async def _today_candidates(
    hass: HomeAssistant,
    bridge,
    *,
    languages: list[str],
    query: str,
    catalog_size: int,
    refresh: bool,
    operation_id: str,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], bool]:
    snapshot = release_catalog()
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    use_release = snapshot.usable and not refresh
    total = max(1, len(languages))
    for index, language in enumerate(languages, start=1):
        if use_release:
            rows = snapshot.recipes_for_language(language, query=query, size=catalog_size)
            rows = _decorate_release_rows(bridge, rows, language)
        else:
            try:
                result = await v10._search_with_diagnostic(
                    hass,
                    bridge,
                    query=query,
                    page=0,
                    size=catalog_size,
                    language=language,
                    strict_language=True,
                    refresh=refresh,
                )
            except Exception as exc:
                errors.append({"language": language, "reason": type(exc).__name__})
                rows = []
            else:
                if not result.get("ok", True):
                    errors.append(
                        {
                            "language": language,
                            "reason": _text(result.get("reason") or result.get("error") or "catalog_error")[:120],
                        }
                    )
                rows = []
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
                    rows.append(row)
        for row in rows:
            row["todayCatalogLanguage"] = language
        candidates.extend(rows)
        publish_operation_progress(
            hass,
            operation_id,
            phase="catalogs",
            message=f"{language.upper()} catalog",
            completed=index,
            total=total,
        )
    return candidates, errors, use_release


async def _build_today(hass: HomeAssistant, bridge, msg: dict[str, Any]) -> dict[str, Any]:
    operation_id = _op(msg)
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

    candidates, catalog_errors, offline_catalog = await _today_candidates(
        hass,
        bridge,
        languages=languages,
        query=query,
        catalog_size=int(msg.get("catalog_size", 40)),
        refresh=bool(msg.get("refresh")),
        operation_id=operation_id,
    )
    if meal_types:
        candidates = [row for row in candidates if recipe_matches_meal_types(row, meal_types)]

    history_store = await meal_history_store_for_bridge(bridge)
    recent = v18._recent_identities(history_store.recent(200), days=avoid_recent_days)
    if recent:
        candidates = [row for row in candidates if recipe_identity(row) not in recent]

    ranked: list[dict[str, Any]] = []
    for language in languages:
        language_rows = [
            row for row in candidates
            if _text(row.get("todayCatalogLanguage")).lower() == language
        ]
        if language_rows:
            ranked.extend(v13._rank_filtered(bridge, language_rows, diet=diet, limit=30))

    nutrition_store = await nutrition_store_for_bridge(bridge)
    house = bridge.recipe_hub.profile.get("houseIngredients") or []
    scored: list[dict[str, Any]] = []
    total_ranked = max(1, len(ranked))
    for index, item in enumerate(ranked, start=1):
        match = item.setdefault("match", {})
        if only_home and not bool(match.get("fullyAvailableByQuantity")):
            continue
        shortages = match.get("quantityShortages") if isinstance(match.get("quantityShortages"), list) else []
        if max_missing is not None and len(shortages) > int(max_missing):
            continue
        current_score = float(match.get("score") or 0.0)
        if not prefer_expiring:
            current_score -= float(match.get("expiryBonus") or 0.0)
            match["todayExpiryBonusSuppressed"] = True

        if isinstance(item.get("nutrition"), dict) and "catalogNutrition" not in item:
            item["catalogNutrition"] = deepcopy(item["nutrition"])
        nutrition = calculate_recipe_nutrition_fefo(
            item,
            house,
            generic=nutrition_store.generic,
            stock_lots=nutrition_store.stock_lots,
        )
        item["nutrition"] = nutrition
        nutrition_hint = nutrition_goal_bonus(nutrition, goal)
        calorie_hint = calorie_target_bonus(
            nutrition,
            msg.get("calorie_target"),
            tolerance_fraction=calorie_tolerance,
        )
        match["nutritionGoal"] = goal
        match["nutritionGoalBonus"] = nutrition_hint.get("bonus", 0.0)
        match["nutritionGoalCoverage"] = nutrition_hint.get("coverage", 0.0)
        match["calorieTarget"] = calorie_hint.get("target")
        match["caloriePerServing"] = calorie_hint.get("calories")
        match["calorieDelta"] = calorie_hint.get("delta")
        match["calorieTargetBonus"] = calorie_hint.get("bonus", 0.0)
        match["todayBaseScore"] = round(current_score, 1)
        match["score"] = round(
            current_score
            + float(nutrition_hint.get("bonus") or 0.0)
            + float(calorie_hint.get("bonus") or 0.0),
            1,
        )
        item["deviceCanAccept"] = bridge.can_accept_recipe
        scored.append(item)
        publish_operation_progress(
            hass,
            operation_id,
            phase="nutrition",
            message="Calculating nutrition",
            completed=index,
            total=total_ranked,
        )

    scored.sort(key=lambda row: row.get("match", {}).get("score", -1000), reverse=True)
    chosen = select_catalog_balanced(
        scored,
        meal_count,
        languages,
        diversity=bool(msg.get("variety", True)),
    )
    candidate_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in candidates)
    ranked_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in scored)
    selected_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in chosen)
    result = {
        "date": dt_util.now().date().isoformat(),
        "items": chosen,
        "candidateCount": len(candidates),
        "rankedCount": len(scored),
        "catalogErrors": catalog_errors,
        "catalogCandidateCounts": {language: int(candidate_counts.get(language, 0)) for language in languages},
        "catalogRankedCounts": {language: int(ranked_counts.get(language, 0)) for language in languages},
        "catalogSelectedCounts": {language: int(selected_counts.get(language, 0)) for language in languages},
        "catalogLanguagesUsed": [language for language in languages if selected_counts.get(language, 0)],
        "offlineCatalog": offline_catalog,
        "releaseCatalog": release_catalog().metadata(),
        "filters": {
            "languages": languages,
            "diet": diet,
            "mealTypes": meal_types,
            "onlyHome": only_home,
            "nutritionGoal": goal,
            "mealCount": meal_count,
            "calorieTarget": msg.get("calorie_target"),
            "calorieTolerancePercent": int(msg.get("calorie_tolerance", 25)),
            "maxMissing": max_missing,
            "preferExpiring": prefer_expiring,
            "avoidRecentDays": avoid_recent_days,
            "variety": bool(msg.get("variety", True)),
            "query": query,
        },
    }
    store = await today_store_for_bridge(bridge)
    await store.async_save(result)
    publish_operation_progress(
        hass,
        operation_id,
        phase="done",
        message="Today's suggestions ready",
        completed=1,
        total=1,
        done=True,
    )
    return result


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_ui_seed,
        ws_catalog_info,
        ws_ingredient_catalog,
        ws_official_search,
        ws_recipe_detail,
        ws_today_state,
        ws_today_suggest,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v30/ui_seed"})
@websocket_api.async_response
async def ws_ui_seed(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    try:
        bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
        entries: list[dict[str, Any]] = []
        per_entry: dict[str, dict[str, Any]] = {}
        for entry_id, bridge in bridges.items():
            entry, cached = await _minimal_seed_entry(hass, entry_id, bridge)
            entries.append(entry)
            per_entry[entry_id] = cached
        connection.send_result(
            msg["id"],
            {
                "entries": entries,
                "perEntry": per_entry,
                "selectedEntryId": entries[0]["entry_id"] if entries else "",
                "fullOverviewCached": False,
                "serverSeedContract": "minimal-shell-v2",
                "onlineRequests": 0,
                "releaseCatalog": release_catalog().metadata(),
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v30/catalog_info"})
@callback
def ws_catalog_info(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    connection.send_result(msg["id"], release_catalog().metadata())


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/ingredient_catalog",
    vol.Optional("entry_id"): str,
    vol.Optional("language"): str,
    vol.Optional("refresh", default=False): bool,
    vol.Optional("client_operation_id", default=""): str,
})
@websocket_api.async_response
async def ws_ingredient_catalog(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        language = recipe_languages.normalize_catalog_language(
            _text(msg.get("language")),
            v28.v11._device_language(bridge),
        )
        result = await _ingredient_catalog(hass, bridge, language, refresh=bool(msg.get("refresh")))
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/official_search",
    vol.Optional("entry_id"): str,
    vol.Optional("query", default=""): str,
    vol.Optional("page", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
    vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
    vol.Optional("languages", default=[]): [str],
    vol.Optional("strict_language", default=True): bool,
    vol.Optional("client_operation_id", default=""): str,
})
@websocket_api.async_response
async def ws_official_search(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    operation_id = _op(msg)
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        languages = v22._selected_languages(bridge, msg.get("languages"))
        result = await _official_search(
            hass,
            bridge,
            languages=languages,
            query=_text(msg.get("query")),
            page=int(msg.get("page", 0)),
            size=int(msg.get("size", 20)),
            strict_language=bool(msg.get("strict_language", True)),
            operation_id=operation_id,
        )
        publish_operation_progress(hass, operation_id, phase="done", message="Catalog search ready", completed=1, total=1, done=True)
    except Exception as exc:
        publish_operation_progress(hass, operation_id, phase="error", message="Catalog search failed", done=True, error=str(exc))
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/recipe_detail",
    vol.Optional("entry_id"): str,
    vol.Required("variant_id"): str,
    vol.Optional("language", default="de"): str,
    vol.Optional("refresh", default=False): bool,
    vol.Optional("client_operation_id", default=""): str,
})
@websocket_api.async_response
async def ws_recipe_detail(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    operation_id = _op(msg)
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await _recipe_detail(
            hass,
            bridge,
            variant_id=_text(msg.get("variant_id")),
            language=_text(msg.get("language")) or "de",
            refresh=bool(msg.get("refresh")),
            operation_id=operation_id,
        )
        publish_operation_progress(hass, operation_id, phase="done", message="Recipe ready", completed=1, total=1, done=True)
    except Exception as exc:
        publish_operation_progress(hass, operation_id, phase="error", message="Recipe failed", done=True, error=str(exc))
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/today_state",
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def ws_today_state(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await today_store_for_bridge(bridge)
        result = store.snapshot()
        result["isCurrentDate"] = _text(result.get("date")) == dt_util.now().date().isoformat()
        result["serverPersisted"] = True
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/today_suggest",
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
    vol.Optional("catalog_size", default=40): vol.All(vol.Coerce(int), vol.Range(min=10, max=50)),
    vol.Optional("refresh", default=False): bool,
    vol.Optional("client_operation_id", default=""): str,
})
@websocket_api.async_response
async def ws_today_suggest(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    operation_id = _op(msg)
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await _build_today(hass, bridge, msg)
    except Exception as exc:
        publish_operation_progress(hass, operation_id, phase="error", message="Today's suggestions failed", done=True, error=str(exc))
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)
