from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_APP_VERSION,
    CONF_COUNTRY,
    CONF_LANGUAGE,
    DEFAULT_APP_VERSION,
    DEFAULT_COUNTRY,
    DEFAULT_LANGUAGE,
)
from .recipe_cache import stable_cache_key
from .recipe_grouping import merge_hydrated_catalogs
from . import recipe_languages
from . import recipe_search_v8
from .vendor import cook4me_phonefree as c4m
from . import websocket as legacy
from . import websocket_v5 as v5
from . import websocket_v7 as v7


def _catalog_context(bridge, language: str) -> tuple[str, str, str, str, str, str]:
    device_country = str(bridge.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)).upper()
    configured_language = str(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)).lower()
    app_version = str(bridge.entry.data.get(CONF_APP_VERSION, DEFAULT_APP_VERSION))
    requested_language = str(language or configured_language).lower().replace("_", "-").split("-", 1)[0]
    display_country = recipe_languages.country_for_language(requested_language, device_country)
    return (
        str(bridge.storage_home),
        device_country,
        display_country,
        configured_language,
        requested_language,
        app_version,
    )


def _catalog_search_full_sync(
    storage_home: str,
    device_country: str,
    display_country: str,
    configured_language: str,
    requested_language: str,
    app_version: str,
    query: str,
    page: int,
    requested_size: int,
    strict_language: bool,
) -> dict[str, Any]:
    """Search using the current APK SearchRecipesV2 body and hydrate first."""
    cfg = c4m.read_apk_config(None)
    tokens = legacy._catalog_tokens(storage_home)
    fetch_size = min(50, max(int(requested_size) * 2, 24))

    device_result = recipe_search_v8.search_recipes(
        cfg,
        tokens,
        query,
        page=page,
        size=fetch_size,
        max_details=fetch_size,
        country=device_country,
        language=configured_language,
        configured_language=configured_language,
        app_version=app_version,
    )

    same_locale = (
        requested_language == configured_language
        and display_country.upper() == device_country.upper()
    )
    if same_locale:
        display_result = deepcopy(device_result)
    else:
        display_result = recipe_search_v8.search_recipes(
            cfg,
            tokens,
            query,
            page=page,
            size=fetch_size,
            max_details=fetch_size,
            country=display_country,
            language=requested_language,
            configured_language=requested_language,
            app_version=app_version,
        )

    result = merge_hydrated_catalogs(
        display_result,
        device_result,
        target_language=requested_language,
        configured_language=configured_language,
        device_country=device_country,
        strict_language=strict_language,
    )
    result["items"] = list(result.get("items") or [])[: max(1, int(requested_size))]
    result["displayCountry"] = display_country
    result["deviceCountry"] = device_country
    result["fetchSize"] = fetch_size
    result["searchContract"] = "apk-searchrecipesv2-v4"
    return result


async def _raw_search(
    hass: HomeAssistant,
    bridge,
    *,
    query: str,
    page: int,
    size: int,
    language: str,
    strict_language: bool,
    refresh: bool,
) -> tuple[dict[str, Any], bool]:
    (
        storage_home,
        device_country,
        display_country,
        configured_language,
        requested_language,
        app_version,
    ) = _catalog_context(bridge, language)
    cache = await v7._cache_for(hass, bridge)
    key = stable_cache_key(
        "search-v8",
        "apk-searchrecipesv2-v4",
        device_country,
        display_country,
        configured_language,
        requested_language,
        query.casefold(),
        int(page),
        int(size),
        bool(strict_language),
    )
    if not refresh:
        cached = cache.get("search", key)
        if isinstance(cached, dict):
            return cached, True

    result = await legacy._async_catalog_call(
        hass,
        bridge,
        _catalog_search_full_sync,
        storage_home,
        device_country,
        display_country,
        configured_language,
        requested_language,
        app_version,
        query,
        int(page),
        int(size),
        bool(strict_language),
    )
    await cache.async_set("search", key, result)
    return result, False


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_capabilities,
        ws_preferences_set,
        ws_search,
        ws_recommend,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v8/capabilities",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_capabilities(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        entity_id = v5._default_ai_task_entity_id(hass)
        result = {
            "languages": recipe_languages.language_options(),
            "defaultAiTaskAvailable": entity_id is not None,
            "defaultAiTaskEntityId": entity_id,
            "persistentCache": True,
            "persistentPreferences": True,
            "preferences": bridge.recipe_hub.ui_preferences,
            "searchContract": "apk-searchrecipesv2-v4",
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v8/preferences_set",
        vol.Optional("entry_id"): str,
        vol.Required("preferences"): dict,
    }
)
@websocket_api.async_response
async def ws_preferences_set(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await bridge.recipe_hub.async_set_ui_preferences(msg["preferences"])
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], {"preferences": result})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v8/search",
        vol.Optional("entry_id"): str,
        vol.Optional("query", default=""): str,
        vol.Optional("page", default=0): vol.Coerce(int),
        vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Required("language"): str,
        vol.Optional("strict_language", default=False): bool,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_search(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        raw, cache_hit = await _raw_search(
            hass,
            bridge,
            query=str(msg.get("query", "")).strip(),
            page=int(msg.get("page", 0)),
            size=int(msg.get("size", 20)),
            language=str(msg["language"]),
            strict_language=bool(msg.get("strict_language")),
            refresh=bool(msg.get("refresh")),
        )
        result = deepcopy(raw)
        items = []
        for item in result.get("items") or []:
            if not isinstance(item, dict):
                continue
            row = bridge.recipe_hub.annotate(item)
            row["deviceCanAccept"] = bridge.can_accept_recipe
            items.append(row)
        result["items"] = items
        result["cacheHit"] = cache_hit
        result["defaultAiTaskAvailable"] = v5._default_ai_task_entity_id(hass) is not None
        result["deviceCanAccept"] = bridge.can_accept_recipe
        result["loadedRecipe"] = bridge.loaded_recipe
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v8/recommend",
        vol.Optional("entry_id"): str,
        vol.Optional("limit", default=12): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Optional("catalog_size", default=24): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Required("language"): str,
        vol.Optional("strict_language", default=False): bool,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_recommend(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        raw, cache_hit = await _raw_search(
            hass,
            bridge,
            query="",
            page=0,
            size=int(msg.get("catalog_size", 24)),
            language=str(msg["language"]),
            strict_language=bool(msg.get("strict_language")),
            refresh=bool(msg.get("refresh")),
        )
        ranked = bridge.recipe_hub.rank(
            raw.get("items") or [], limit=int(msg.get("limit", 12))
        )
        for item in ranked:
            item["deviceCanAccept"] = bridge.can_accept_recipe
        result = {
            "items": ranked,
            "profile": bridge.recipe_hub.profile,
            "cacheHit": cache_hit,
            "defaultAiTaskAvailable": v5._default_ai_task_entity_id(hass) is not None,
            "deviceCanAccept": bridge.can_accept_recipe,
            "loadedRecipe": bridge.loaded_recipe,
            "searchContract": "apk-searchrecipesv2-v4",
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
