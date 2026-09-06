from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import time
from typing import Any, Callable

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_APP_VERSION,
    CONF_COUNTRY,
    CONF_LANGUAGE,
    DATA_BRIDGES,
    DEFAULT_APP_VERSION,
    DEFAULT_COUNTRY,
    DEFAULT_LANGUAGE,
    DOMAIN,
)
from .vendor import cook4me_phonefree as c4m
from .vendor import cook4me_recipe_catalog as recipe_catalog


def _bridge(hass: HomeAssistant, entry_id: str | None):
    bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
    if entry_id:
        bridge = bridges.get(entry_id)
        if bridge is None:
            raise ValueError("Cook4Me config entry is not loaded")
        return bridge
    if len(bridges) == 1:
        return next(iter(bridges.values()))
    raise ValueError("entry_id is required when more than one Cook4Me is configured")


def _send_error(connection, msg, exc: Exception) -> None:
    connection.send_error(msg["id"], "cook4me_error", str(exc))


def _ui_language(value: str | None, fallback: str) -> str:
    text = str(value or fallback or "en").strip().lower().replace("_", "-")
    return text.split("-", 1)[0] or fallback


def _catalog_context(bridge, language: str | None) -> tuple[str, str, str, str, str]:
    country = str(bridge.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)).upper()
    configured_language = str(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)).lower()
    app_version = str(bridge.entry.data.get(CONF_APP_VERSION, DEFAULT_APP_VERSION))
    requested_language = _ui_language(language, configured_language)
    return str(bridge.storage_home), country, configured_language, requested_language, app_version


def _catalog_tokens(storage_home: str) -> dict[str, Any]:
    path = Path(storage_home) / ".config" / "cook4me" / "tokens.json"
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _catalog_search_sync(
    storage_home: str,
    country: str,
    configured_language: str,
    requested_language: str,
    app_version: str,
    query: str,
    page: int,
    size: int,
) -> dict[str, Any]:
    return recipe_catalog.search_recipes(
        c4m.read_apk_config(None),
        _catalog_tokens(storage_home),
        query,
        page=page,
        size=size,
        max_details=size,
        country=country,
        language=requested_language,
        configured_language=configured_language,
        app_version=app_version,
    )


def _catalog_detail_sync(
    storage_home: str,
    country: str,
    configured_language: str,
    requested_language: str,
    app_version: str,
    variant_id: str,
) -> dict[str, Any]:
    return recipe_catalog.recipe_detail(
        c4m.read_apk_config(None),
        _catalog_tokens(storage_home),
        variant_id,
        country=country,
        language=requested_language,
        configured_language=configured_language,
        app_version=app_version,
    )


async def _async_catalog_call(
    hass: HomeAssistant,
    bridge,
    func: Callable[..., dict[str, Any]],
    *args,
) -> dict[str, Any]:
    """Run blocking recipe HTTP work off-loop and refresh login once if needed."""
    try:
        return await hass.async_add_executor_job(func, *args)
    except recipe_catalog.CatalogAuthError:
        # The long-running watcher already owns the proven browserless auth
        # lifecycle.  A one-shot status call makes it refresh KRUPS/AWS tokens,
        # then the recipe request is retried with the freshly saved token file.
        await bridge._run_client_json("status", timeout=75)
        return await hass.async_add_executor_job(func, *args)


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_overview,
        ws_search,
        ws_recipe_detail,
        ws_recommend,
        ws_send_recipe,
        ws_profile_save,
        ws_recipe_save,
        ws_recipe_delete,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/overview"})
@callback
def ws_overview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
    result = []
    for entry_id, bridge in bridges.items():
        result.append(
            {
                "entry_id": entry_id,
                "device_uuid": bridge.device_uuid,
                "title": bridge.entry.title,
                "connected": bridge.available,
                "canAcceptRecipe": bridge.can_accept_recipe,
                "loadedRecipe": bridge.loaded_recipe,
                "state": dict(bridge.data),
                "profile": bridge.recipe_hub.profile,
                "recipes": [bridge.recipe_hub.annotate(recipe) for recipe in bridge.recipe_hub.recipes],
                "history": bridge.recipe_hub.snapshot().get("history", []),
                "habitTerms": bridge.recipe_hub.habit_terms,
                "configuredLanguage": str(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)),
                "country": str(bridge.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)),
            }
        )
    connection.send_result(msg["id"], {"entries": result})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/search",
        vol.Optional("entry_id"): str,
        vol.Optional("query", default=""): str,
        vol.Optional("page", default=0): vol.Coerce(int),
        vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Optional("language"): str,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_search(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        storage_home, country, configured_language, language, app_version = _catalog_context(
            bridge, msg.get("language")
        )
        query = str(msg.get("query", ""))
        page = int(msg.get("page", 0))
        size = int(msg.get("size", 20))
        cache_key = ("recipe_hub_v2", language, query.casefold(), page, size)
        cached = bridge._search_cache.get(cache_key)
        if not msg.get("refresh") and cached and time.monotonic() - cached[0] < 900:
            result = deepcopy(cached[1])
        else:
            result = await _async_catalog_call(
                hass,
                bridge,
                _catalog_search_sync,
                storage_home,
                country,
                configured_language,
                language,
                app_version,
                query,
                page,
                size,
            )
            bridge._search_cache[cache_key] = (time.monotonic(), deepcopy(result))
        items = []
        for item in result.get("items") or []:
            if not isinstance(item, dict):
                continue
            annotated = bridge.recipe_hub.annotate(item)
            annotated["deviceCanAccept"] = bridge.can_accept_recipe
            items.append(annotated)
        result = dict(result)
        result["items"] = items
        result["deviceCanAccept"] = bridge.can_accept_recipe
        result["loadedRecipe"] = bridge.loaded_recipe
    except Exception as exc:
        _send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/recipe_detail",
        vol.Optional("entry_id"): str,
        vol.Required("variant_id"): str,
        vol.Optional("language"): str,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_recipe_detail(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        storage_home, country, configured_language, language, app_version = _catalog_context(
            bridge, msg.get("language")
        )
        variant = str(msg["variant_id"])
        cache_key = f"recipe_hub_v2:{language}:{variant}"
        cached = bridge._recipe_cache.get(cache_key)
        if cached is not None and not msg.get("refresh"):
            result = deepcopy(cached)
        else:
            result = await _async_catalog_call(
                hass,
                bridge,
                _catalog_detail_sync,
                storage_home,
                country,
                configured_language,
                language,
                app_version,
                variant,
            )
            bridge._recipe_cache[cache_key] = deepcopy(result)
        result = bridge.recipe_hub.annotate(result)
        result["deviceCanAccept"] = bridge.can_accept_recipe
    except Exception as exc:
        _send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/recommend",
        vol.Optional("entry_id"): str,
        vol.Optional("limit", default=12): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Optional("catalog_size", default=18): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Optional("language"): str,
    }
)
@websocket_api.async_response
async def ws_recommend(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        storage_home, country, configured_language, language, app_version = _catalog_context(
            bridge, msg.get("language")
        )
        catalog_size = int(msg["catalog_size"])
        cache_key = ("recipe_hub_v2_recommend", language, "", 0, catalog_size)
        cached = bridge._search_cache.get(cache_key)
        if cached and time.monotonic() - cached[0] < 900:
            catalog = deepcopy(cached[1])
        else:
            catalog = await _async_catalog_call(
                hass,
                bridge,
                _catalog_search_sync,
                storage_home,
                country,
                configured_language,
                language,
                app_version,
                "",
                0,
                catalog_size,
            )
            bridge._search_cache[cache_key] = (time.monotonic(), deepcopy(catalog))
        ranked = bridge.recipe_hub.rank(catalog.get("items") or [], limit=int(msg["limit"]))
        for item in ranked:
            item["deviceCanAccept"] = bridge.can_accept_recipe
        result = {
            "items": ranked,
            "profile": bridge.recipe_hub.profile,
            "requestedLanguage": language,
            "deviceCanAccept": bridge.can_accept_recipe,
            "loadedRecipe": bridge.loaded_recipe,
        }
    except Exception as exc:
        _send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/send_recipe",
        vol.Optional("entry_id"): str,
        vol.Required("variant_id"): str,
    }
)
@websocket_api.async_response
async def ws_send_recipe(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        result = await bridge.async_send_variant(msg["variant_id"])
    except Exception as exc:
        _send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/profile_save",
        vol.Optional("entry_id"): str,
        vol.Required("profile"): dict,
    }
)
@websocket_api.async_response
async def ws_profile_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        result = await bridge.recipe_hub.async_set_profile(msg["profile"])
    except Exception as exc:
        _send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/recipe_save",
        vol.Optional("entry_id"): str,
        vol.Required("recipe"): dict,
        vol.Optional("source", default="manual"): vol.In(["manual", "ai"]),
    }
)
@websocket_api.async_response
async def ws_recipe_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        result = await bridge.recipe_hub.async_save_recipe(msg["recipe"], source=msg["source"])
    except Exception as exc:
        _send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/recipe_delete",
        vol.Optional("entry_id"): str,
        vol.Required("recipe_id"): str,
    }
)
@websocket_api.async_response
async def ws_recipe_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        changed = await bridge.recipe_hub.async_delete_recipe(msg["recipe_id"])
    except Exception as exc:
        _send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], {"deleted": changed})
