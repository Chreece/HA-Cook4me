from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from . import recipe_catalog_diagnostics as catalog_diag
from . import release_catalog as release_index
from . import websocket as legacy
from . import websocket_v5 as v5
from . import websocket_v7 as v7
from . import websocket_v8 as v8
from . import websocket_v9 as v9
from .vendor import cook4me_recipe_catalog as recipe_catalog


async def _diagnose(hass: HomeAssistant, bridge, *, query: str, language: str) -> dict[str, Any]:
    (
        storage_home,
        device_country,
        _display_country,
        configured_language,
        requested_language,
        app_version,
    ) = v8._catalog_context(bridge, language)
    country = device_country
    probe_language = configured_language
    if requested_language != configured_language:
        probe_language = configured_language
    return await hass.async_add_executor_job(
        lambda: catalog_diag.diagnose_search(
            storage_home,
            country=country,
            configured_language=probe_language,
            app_version=app_version,
            query=query,
        )
    )


async def _legacy_fallback(
    hass: HomeAssistant,
    bridge,
    *,
    query: str,
    page: int,
    size: int,
    language: str,
    strict_language: bool,
) -> dict[str, Any]:
    (
        storage_home,
        device_country,
        display_country,
        configured_language,
        requested_language,
        app_version,
    ) = v8._catalog_context(bridge, language)
    return await hass.async_add_executor_job(
        v7._catalog_search_full_sync,
        storage_home,
        device_country,
        display_country,
        configured_language,
        requested_language,
        app_version,
        query,
        page,
        size,
        strict_language,
    )


def _decorate_result(bridge, raw: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(raw)
    items = []
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
    result["ok"] = True
    return result


def _release_search(
    bridge,
    *,
    query: str,
    page: int,
    size: int,
    language: str,
    strict_language: bool,
) -> dict[str, Any]:
    (
        _storage_home,
        device_country,
        _display_country,
        configured_language,
        requested_language,
        _app_version,
    ) = v8._catalog_context(bridge, language)
    raw = release_index.search_release_recipes(
        query,
        language=requested_language,
        configured_language=configured_language,
        country=device_country,
        page=page,
        size=size,
        strict_language=strict_language,
    )
    result = _decorate_result(bridge, raw)
    result.update({
        "cacheHit": True,
        "checkedOnline": False,
        "offline": True,
        "searchContract": raw.get("searchContract") or "repo-release-merged-catalog-v1",
        "catalogVersion": raw.get("catalogVersion") or "",
        "catalogAuthRefresh": "not-required-offline-release-catalog",
    })
    return result


def _is_catalog_rejection(exc: Exception) -> bool:
    """Return True only for a recipe-catalog rejection worth diagnosing."""
    if isinstance(exc, (recipe_catalog.CatalogAuthError, recipe_catalog.CatalogError)):
        return True
    return isinstance(exc, HomeAssistantError) and str(exc) == (
        "KRUPS recipe-catalog authentication is still rejected after refresh"
    )


async def _search_with_diagnostic(
    hass: HomeAssistant,
    bridge,
    *,
    query: str,
    page: int,
    size: int,
    language: str,
    strict_language: bool,
    refresh: bool,
) -> dict[str, Any]:
    # Common offline-first layer: Today, Week, AI mapping, recommendations and
    # older internal callers all inherit the reviewed release catalog.
    if release_index.release_catalog_ready() and not refresh:
        return _release_search(
            bridge,
            query=query,
            page=page,
            size=size,
            language=language,
            strict_language=strict_language,
        )

    try:
        raw, cache_hit = await v9._raw_search(
            hass,
            bridge,
            query=query,
            page=page,
            size=size,
            language=language,
            strict_language=strict_language,
            refresh=refresh,
        )
        result = _decorate_result(bridge, raw)
        result["cacheHit"] = cache_hit
        result["searchContract"] = raw.get("searchContract") or "apk-searchrecipesv2-v4"
        result["catalogAuthRefresh"] = "krups-http-only"
        return result
    except Exception as exc:
        if not _is_catalog_rejection(exc):
            raise
        diagnostic = await _diagnose(hass, bridge, query=query, language=language)
        if diagnostic.get("bodyMismatchProven"):
            try:
                raw = await _legacy_fallback(
                    hass,
                    bridge,
                    query=query,
                    page=page,
                    size=size,
                    language=language,
                    strict_language=strict_language,
                )
            except Exception as fallback_exc:
                diagnostic["fallbackError"] = type(fallback_exc).__name__
            else:
                result = _decorate_result(bridge, raw)
                result.update({
                    "cacheHit": False,
                    "fallbackUsed": True,
                    "fallbackReason": "v8_app_body_rejected_legacy_body_accepted",
                    "searchContract": "legacy-empty-body-compatibility-fallback",
                    "catalogAuthRefresh": "krups-http-only",
                    "catalogDiagnostic": diagnostic,
                    "catalogDiagnosticSummary": catalog_diag.diagnostic_summary(diagnostic),
                })
                return result
        return {
            "ok": False,
            "items": [],
            "errorCode": "catalog_request_rejected",
            "error": catalog_diag.diagnostic_summary(diagnostic),
            "catalogDiagnostic": diagnostic,
            "catalogAuthRefresh": "krups-http-only",
            "deviceCanAccept": bridge.can_accept_recipe,
            "loadedRecipe": bridge.loaded_recipe,
        }


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_search, ws_recommend, ws_catalog_diagnostic):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v10/search",
    vol.Optional("entry_id"): str,
    vol.Optional("query", default=""): str,
    vol.Optional("page", default=0): vol.Coerce(int),
    vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
    vol.Required("language"): str,
    vol.Optional("strict_language", default=False): bool,
    vol.Optional("refresh", default=False): bool,
})
@websocket_api.async_response
async def ws_search(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await _search_with_diagnostic(
            hass,
            bridge,
            query=str(msg.get("query", "")).strip(),
            page=int(msg.get("page", 0)),
            size=int(msg.get("size", 20)),
            language=str(msg["language"]),
            strict_language=bool(msg.get("strict_language")),
            refresh=bool(msg.get("refresh")),
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v10/recommend",
    vol.Optional("entry_id"): str,
    vol.Optional("limit", default=12): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
    vol.Optional("catalog_size", default=24): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
    vol.Required("language"): str,
    vol.Optional("strict_language", default=False): bool,
    vol.Optional("refresh", default=False): bool,
})
@websocket_api.async_response
async def ws_recommend(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        search = await _search_with_diagnostic(
            hass,
            bridge,
            query="",
            page=0,
            size=int(msg.get("catalog_size", 24)),
            language=str(msg["language"]),
            strict_language=bool(msg.get("strict_language")),
            refresh=bool(msg.get("refresh")),
        )
        if not search.get("ok", True):
            connection.send_result(msg["id"], search)
            return
        ranked = bridge.recipe_hub.rank(search.get("items") or [], limit=int(msg.get("limit", 12)))
        for item in ranked:
            item["deviceCanAccept"] = bridge.can_accept_recipe
        result = {
            **{key: value for key, value in search.items() if key != "items"},
            "items": ranked,
            "profile": bridge.recipe_hub.profile,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v10/catalog_diagnostic",
    vol.Optional("entry_id"): str,
    vol.Optional("query", default=""): str,
    vol.Required("language"): str,
})
@websocket_api.async_response
async def ws_catalog_diagnostic(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        diagnostic = await _diagnose(
            hass,
            bridge,
            query=str(msg.get("query", "")).strip(),
            language=str(msg["language"]),
        )
        result = {"diagnostic": diagnostic, "summary": catalog_diag.diagnostic_summary(diagnostic)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
