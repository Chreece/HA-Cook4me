from __future__ import annotations

import asyncio
from copy import deepcopy
import pathlib
import sys
from typing import Any, Callable

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_APP_VERSION,
    CONF_COUNTRY,
    CONF_LANGUAGE,
    DEFAULT_APP_VERSION,
    DEFAULT_COUNTRY,
    DEFAULT_LANGUAGE,
)
from .recipe_cache import stable_cache_key
from . import websocket as legacy
from . import websocket_v5 as v5
from . import websocket_v7 as v7
from . import websocket_v8 as v8
from .vendor import cook4me_recipe_catalog as recipe_catalog


def _friendly_process_error(raw: bytes | str, fallback: str) -> str:
    text = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else str(raw or "")
    low = text.lower()
    if "websockettimeoutexception" in low or "connection timed out" in low:
        return "Cook4Me cloud request timed out"
    if "timed out" in low or "timeout" in low:
        return "Cook4Me cloud request timed out"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.startswith("File ") or line.startswith("Traceback") or line.startswith("~~~"):
            continue
        if line.startswith("^"):
            continue
        return line[:500]
    return fallback


async def _refresh_catalog_auth(hass: HomeAssistant, bridge) -> None:
    vendor = pathlib.Path(__file__).parent / "vendor"
    cmd = [
        sys.executable,
        "-u",
        str(vendor / "cook4me_auto.py"),
        "--country",
        str(bridge.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)),
        "--language",
        str(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)),
        "--app-version",
        str(bridge.entry.data.get(CONF_APP_VERSION, DEFAULT_APP_VERSION)),
        "--device-uuid",
        bridge.device_uuid,
        "--json-lines",
        "--force-login",
        "--auth-only",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(vendor),
        env=bridge._env(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=75)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise HomeAssistantError("KRUPS browserless authentication refresh timed out") from exc
    if proc.returncode:
        message = _friendly_process_error(
            err or out,
            f"KRUPS authentication refresh failed with code {proc.returncode}",
        )
        raise HomeAssistantError(message)


async def _async_catalog_call(
    hass: HomeAssistant,
    bridge,
    func: Callable[..., dict[str, Any]],
    *args,
) -> dict[str, Any]:
    try:
        return await hass.async_add_executor_job(func, *args)
    except recipe_catalog.CatalogAuthError:
        await _refresh_catalog_auth(hass, bridge)
        try:
            return await hass.async_add_executor_job(func, *args)
        except recipe_catalog.CatalogAuthError as exc:
            raise HomeAssistantError(
                "KRUPS recipe-catalog authentication is still rejected after refresh"
            ) from exc


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
    ) = v8._catalog_context(bridge, language)
    cache = await v7._cache_for(hass, bridge)
    key = stable_cache_key(
        "search-v9",
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
    cached = cache.get("search", key)
    # Cache content survives indefinitely. Once a result exists, the normal
    # shared catalog path may revalidate it only after >=24h. Explicit refresh
    # remains supported for internal callers whose own outer cache already
    # enforces the same daily rule.
    if isinstance(cached, dict) and not refresh and not cache.should_revalidate("search", key):
        return cached, True

    try:
        result = await _async_catalog_call(
            hass,
            bridge,
            v8._catalog_search_full_sync,
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
    except Exception as exc:
        if isinstance(cached, dict) and not refresh:
            await cache.async_mark_checked("search", key, error=exc)
            return cached, True
        raise
    await cache.async_set("search", key, result)
    return result, isinstance(cached, dict)


async def _raw_detail(
    hass: HomeAssistant,
    bridge,
    *,
    variant_id: str,
    language: str,
    refresh: bool,
) -> tuple[dict[str, Any], bool]:
    (
        storage_home,
        _device_country,
        display_country,
        _configured_language,
        requested_language,
        app_version,
    ) = v8._catalog_context(bridge, language)
    cache = await v7._cache_for(hass, bridge)
    key = stable_cache_key(
        "detail-v9", display_country, requested_language, str(variant_id)
    )
    cached = cache.get("detail", key)
    if isinstance(cached, dict) and not refresh and not cache.should_revalidate("detail", key):
        return cached, True

    try:
        result = await _async_catalog_call(
            hass,
            bridge,
            legacy._catalog_detail_sync,
            storage_home,
            display_country,
            requested_language,
            app_version,
            str(variant_id),
        )
    except Exception as exc:
        if isinstance(cached, dict) and not refresh:
            await cache.async_mark_checked("detail", key, error=exc)
            return cached, True
        raise
    await cache.async_set("detail", key, result)
    return result, isinstance(cached, dict)


async def _preferences(hass: HomeAssistant, bridge) -> dict[str, Any]:
    cache = await v7._cache_for(hass, bridge)
    extra = cache.get("ui", "preferences")
    result = bridge.recipe_hub.ui_preferences
    if isinstance(extra, dict):
        result = {**result, **extra}
    return result


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_capabilities,
        ws_preferences_set,
        ws_search,
        ws_recipe_detail,
        ws_recommend,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v9/capabilities",
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
            "languages": v8.recipe_languages.language_options(),
            "defaultAiTaskAvailable": entity_id is not None,
            "defaultAiTaskEntityId": entity_id,
            "persistentCache": True,
            "persistentPreferences": True,
            "preferences": await _preferences(hass, bridge),
            "searchContract": "apk-searchrecipesv2-v4",
            "catalogAuthRefresh": "krups-http-only",
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v9/preferences_set",
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
        incoming = dict(msg["preferences"])
        draft = str(incoming.pop("searchDraft", "") or "")[:500]
        saved = await bridge.recipe_hub.async_set_ui_preferences(incoming)
        cache = await v7._cache_for(hass, bridge)
        await cache.async_set("ui", "preferences", {"searchDraft": draft})
        result = {**saved, "searchDraft": draft}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], {"preferences": result})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v9/search",
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
        vol.Required("type"): "cook4me/v9/recipe_detail",
        vol.Optional("entry_id"): str,
        vol.Required("variant_id"): str,
        vol.Required("language"): str,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_recipe_detail(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        raw, cache_hit = await _raw_detail(
            hass,
            bridge,
            variant_id=str(msg["variant_id"]),
            language=str(msg["language"]),
            refresh=bool(msg.get("refresh")),
        )
        result = bridge.recipe_hub.annotate(raw)
        result["deviceCanAccept"] = bridge.can_accept_recipe
        result["cacheHit"] = cache_hit
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v9/recommend",
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
