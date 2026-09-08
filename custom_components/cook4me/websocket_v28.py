from __future__ import annotations

from copy import deepcopy
import time
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from . import recipe_languages
from . import websocket as legacy
from . import websocket_v5 as v5
from . import websocket_v9 as v9
from . import websocket_v11 as v11
from . import websocket_v18 as v18
from . import websocket_v27 as v27
from .const import CONF_COUNTRY, CONF_LANGUAGE, DATA_BRIDGES, DEFAULT_COUNTRY, DEFAULT_LANGUAGE, DOMAIN
from .ingredient_catalog import _clean_catalog_rows
from .recipe_book import recipe_book_store_for_bridge

_MIN_CHECK_AGE = 24 * 60 * 60
_CATALOG_STORE_VERSION = 1


def _now() -> float:
    return time.time()


async def _catalog_store(bridge):
    store = getattr(bridge, "_v28_ingredient_catalog_store", None)
    data = getattr(bridge, "_v28_ingredient_catalog_data", None)
    if store is not None and isinstance(data, dict):
        return store, data
    store = Store(
        bridge.hass,
        _CATALOG_STORE_VERSION,
        f"{DOMAIN}.{bridge.entry.entry_id}.ingredient_catalog",
    )
    saved = await store.async_load()
    data = {}
    if isinstance(saved, dict):
        for language, raw in saved.items():
            if not isinstance(raw, dict) or not isinstance(raw.get("items"), list):
                continue
            stamp = float(raw.get("checkedAt") or raw.get("timestamp") or 0)
            updated = float(raw.get("updatedAt") or raw.get("timestamp") or stamp)
            data[str(language)] = {
                "checkedAt": stamp,
                "updatedAt": updated,
                "source": str(raw.get("source") or ""),
                "items": deepcopy(_clean_catalog_rows(raw.get("items") or [])),
            }
    bridge._v28_ingredient_catalog_store = store
    bridge._v28_ingredient_catalog_data = data
    return store, data


async def _cached_catalog(bridge, language: str) -> dict[str, Any] | None:
    _store, data = await _catalog_store(bridge)
    row = data.get(str(language))
    if not isinstance(row, dict) or not isinstance(row.get("items"), list):
        return None
    checked = float(row.get("checkedAt") or 0)
    return {
        "language": str(language),
        "items": deepcopy(row.get("items") or []),
        "source": str(row.get("source") or ""),
        "cacheHit": True,
        "checkedAt": checked or None,
        "updatedAt": float(row.get("updatedAt") or 0) or None,
        "stale": not checked or _now() - checked >= _MIN_CHECK_AGE,
        "minimumOnlineCheckHours": 24,
    }


async def _save_catalog(bridge, language: str, items: list[dict[str, str]], source: str) -> dict[str, Any]:
    store, data = await _catalog_store(bridge)
    now = _now()
    clean = deepcopy(_clean_catalog_rows(items))
    previous = data.get(language) if isinstance(data.get(language), dict) else None
    changed = not previous or previous.get("items") != clean or str(previous.get("source") or "") != str(source)
    updated = now if changed else float(previous.get("updatedAt") or now)
    data[language] = {
        "checkedAt": now,
        "updatedAt": updated,
        "source": str(source),
        "items": clean,
    }
    await store.async_save(deepcopy(data))
    result = await _cached_catalog(bridge, language)
    assert result is not None
    result["cacheHit"] = False
    result["changed"] = changed
    result["stale"] = False
    return result


async def _fetch_catalog(hass: HomeAssistant, bridge, language: str) -> dict[str, Any]:
    language = recipe_languages.normalize_catalog_language(language, v11._device_language(bridge))
    try:
        items, source = await hass.async_add_executor_job(v11._marketing_food_catalog_sync, bridge, language)
    except v11.recipe_catalog.CatalogAuthError:
        await v9._refresh_catalog_auth(hass, bridge)
        try:
            items, source = await hass.async_add_executor_job(v11._marketing_food_catalog_sync, bridge, language)
        except Exception:
            items = await v11._recipe_fallback_catalog(hass, bridge, language)
            source = v11._RECIPE_FALLBACK_SOURCE
    except Exception:
        items = await v11._recipe_fallback_catalog(hass, bridge, language)
        source = v11._RECIPE_FALLBACK_SOURCE
    if not items:
        raise ValueError("Cook4Me ingredient catalog returned no usable ingredients")
    return await _save_catalog(bridge, language, items, source)


def _today_options(bridge) -> dict[str, Any]:
    return {
        "languages": recipe_languages.language_options(),
        "defaultLanguage": v11._device_language(bridge),
        "maxLanguages": v18._MAX_LANGUAGES,
        "mealTypes": list(v18.MEAL_TYPES),
        "nutritionGoals": [
            "balanced",
            "high_protein",
            "lower_calorie",
            "high_fiber",
            "lower_saturated_fat",
        ],
        "dietOptions": list(v18._DIET_FILTERS),
    }


def _capabilities(hass: HomeAssistant, bridge) -> dict[str, Any]:
    device_language = v11._device_language(bridge)
    ai_task = v5._default_ai_task_entity_id(hass)
    return {
        "languages": recipe_languages.language_options(),
        "deviceCatalogLanguage": device_language,
        "ingredientCatalogLanguage": device_language,
        "defaultAiTaskAvailable": ai_task is not None,
        "defaultAiTaskEntityId": ai_task,
        "preferences": bridge.recipe_hub.ui_preferences,
    }


async def _seed_entry(hass: HomeAssistant, entry_id: str, bridge) -> tuple[dict[str, Any], dict[str, Any]]:
    hub = bridge.recipe_hub.snapshot()
    profile = hub.get("profile") if isinstance(hub.get("profile"), dict) else {}
    language = v11._device_language(bridge)
    book = await recipe_book_store_for_bridge(bridge)
    catalog = await _cached_catalog(bridge, language)
    entry = {
        "entry_id": entry_id,
        "title": bridge.entry.title,
        "connected": bool(bridge.available),
        "canAcceptRecipe": bool(bridge.can_accept_recipe),
        "loadedRecipe": v27._loaded_recipe_summary(bridge.loaded_recipe),
        "state": v27._state_summary(getattr(bridge, "data", None)),
        "profile": deepcopy(profile),
        "recipes": deepcopy(hub.get("recipes") or []),
        "history": deepcopy(hub.get("history") or []),
        "habitTerms": bridge.recipe_hub.habit_terms,
        "configuredLanguage": str(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)),
        "country": str(bridge.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)),
    }
    per_entry = {
        "capabilities": _capabilities(hass, bridge),
        "uiPreferences": deepcopy(bridge.recipe_hub.ui_preferences),
        "bookState": {
            **book.snapshot(),
            "deviceConnected": bool(bridge.available),
            "deviceCanAccept": bool(bridge.can_accept_recipe),
            "loadedRecipe": v27._loaded_recipe_summary(bridge.loaded_recipe),
            "myRecipes": deepcopy(hub.get("recipes") or []),
        },
        "todayOptions": _today_options(bridge),
        "ingredientCatalog": deepcopy(catalog.get("items") if catalog else []),
        "ingredientCatalogLanguage": language if catalog else "",
        "houseIngredients": deepcopy(profile.get("houseIngredients") or []),
        "houseStateLoaded": True,
        "pendingConsumption": deepcopy(hub.get("pendingConsumption")),
        "results": [],
        "recommendations": [],
        "todayResults": [],
        "todayMeta": None,
        "searchQuery": "",
        "serverCatalogCache": deepcopy(catalog),
    }
    return entry, per_entry


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_ui_seed)
    websocket_api.async_register_command(hass, ws_ingredient_catalog)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v28/ui_seed"})
@websocket_api.async_response
async def ws_ui_seed(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    try:
        bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
        entries: list[dict[str, Any]] = []
        per_entry: dict[str, dict[str, Any]] = {}
        for entry_id, bridge in bridges.items():
            entry, cached = await _seed_entry(hass, entry_id, bridge)
            entries.append(entry)
            per_entry[entry_id] = cached
        connection.send_result(
            msg["id"],
            {
                "entries": entries,
                "perEntry": per_entry,
                "selectedEntryId": entries[0]["entry_id"] if entries else "",
                "fullOverviewCached": True,
                "serverSeedContract": "local-persistent-ui-v1",
                "onlineRequests": 0,
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v28/ingredient_catalog",
        vol.Optional("entry_id"): str,
        vol.Optional("language"): str,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_ingredient_catalog(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        language = recipe_languages.normalize_catalog_language(
            str(msg.get("language") or v11._device_language(bridge)),
            v11._device_language(bridge),
        )
        cached = await _cached_catalog(bridge, language)
        if cached is not None and not bool(msg.get("refresh")):
            result = cached
        else:
            result = await _fetch_catalog(hass, bridge, language)
        result["houseIngredients"] = bridge.recipe_hub.profile.get("houseIngredients") or []
        connection.send_result(msg["id"], result)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
