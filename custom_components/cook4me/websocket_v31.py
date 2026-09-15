from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import release_catalog
from . import websocket as legacy
from . import websocket_v30 as v30
from .multilingual_query import resolve_multilingual_query
from .request_coordinator import request_coordinator


def _text(value: Any) -> str:
    return str(value or "").strip()


def _language(value: Any) -> str:
    return _text(value).lower().replace("_", "-").split("-", 1)[0]


def _selected_languages(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple, set)):
        return ()
    return tuple(dict.fromkeys(lang for value in values if (lang := _language(value))))


def _allowed_indices(prepared: dict[str, Any], languages: tuple[str, ...]) -> frozenset[int] | None:
    if not languages:
        return None
    by_language = prepared.get("recipeLanguages") or {}
    allowed: set[int] = set()
    for language in languages:
        allowed.update(by_language.get(language, ()))
    return frozenset(allowed)


def _display_language(prepared: dict[str, Any], recipe_index: int, languages: tuple[str, ...], fallback: str) -> str:
    by_language = prepared.get("recipeLanguages") or {}
    for language in languages:
        if recipe_index in by_language.get(language, ()):
            return language
    return fallback


def _offline_search(bridge, *, query: str, query_language: str, languages: tuple[str, ...], page: int, size: int) -> dict[str, Any]:
    payload = release_catalog.load_release_catalog()
    prepared = payload.get("_runtimeSearchIndex") or {}
    resolved_query, query_recovered = resolve_multilingual_query(prepared, query)
    allowed = _allowed_indices(prepared, languages)
    match = release_catalog._core.search_index(
        prepared,
        resolved_query,
        language="",
        strict_language=False,
        allowed_indices=allowed,
        page=page,
        size=size,
    )
    recipes = payload.get("recipes") or []
    scores = match.get("scores") if isinstance(match.get("scores"), dict) else {}
    configured = v30._device_language(bridge)
    country = v30._device_country(bridge)
    fallback_language = _language(query_language) or configured
    items: list[dict[str, Any]] = []
    for recipe_index in match.get("indices") or []:
        try:
            raw = recipes[recipe_index]
        except (IndexError, TypeError):
            continue
        if not isinstance(raw, dict):
            continue
        row_language = _display_language(prepared, recipe_index, languages, fallback_language)
        row = release_catalog._core._enrich_recipe_row(
            payload,
            release_catalog._core._legacy._recipe_row(
                raw,
                language=row_language,
                configured_language=configured,
                country=country,
            ),
        )
        if not row:
            continue
        if recipe_index in scores:
            row["searchScore"] = scores[recipe_index]
        row["catalogLanguage"] = row_language
        items.append(row)
    total = int(match.get("total") or 0)
    total_pages = (total + size - 1) // size if total else 0
    result = {
        "ok": True,
        "query": _text(query),
        "resolvedQuery": resolved_query,
        "queryRecovered": query_recovered,
        "queryLanguage": _language(query_language),
        "catalogLanguages": list(languages),
        "page": {"number": page, "size": size, "totalElements": total, "totalPages": total_pages},
        "groupedRecipeCount": len(items),
        "items": items,
        "cacheHit": True,
        "checkedOnline": False,
        "offline": True,
        "serverFetch": False,
        "catalogMode": "release_offline",
        "searchContract": "release-multilingual-index-v31-script-recovery",
        "releaseCatalog": release_catalog.release_catalog_summary(),
    }
    return v30._annotate_search(bridge, result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v31/official_search",
    vol.Optional("entry_id"): str,
    vol.Optional("query", default=""): str,
    vol.Optional("query_language", default=""): str,
    vol.Optional("languages", default=[]): [str],
    vol.Optional("page", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
    vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
})
@websocket_api.async_response
async def ws_official_search(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        if not release_catalog.release_catalog_ready():
            raise RuntimeError("offline release catalog is unavailable")
        result = _offline_search(
            bridge,
            query=_text(msg.get("query")),
            query_language=_text(msg.get("query_language")) or v30._device_language(bridge),
            languages=_selected_languages(msg.get("languages")),
            page=int(msg.get("page", 0)),
            size=int(msg.get("size", 20)),
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v31/recipe_detail",
    vol.Optional("entry_id"): str,
    vol.Required("variant_id"): str,
    vol.Optional("language", default=""): str,
    vol.Optional("refresh", default=False): bool,
})
@websocket_api.async_response
async def ws_recipe_detail(hass: HomeAssistant, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        language = _language(msg.get("language")) or v30._device_language(bridge)
        variant_id = _text(msg.get("variant_id"))
        local = None
        if release_catalog.release_catalog_ready() and not bool(msg.get("refresh")):
            local = release_catalog.recipe_by_variant(
                variant_id,
                language=language,
                configured_language=v30._device_language(bridge),
                country=v30._device_country(bridge),
            )
        if isinstance(local, dict):
            result = bridge.recipe_hub.annotate(deepcopy(local))
            result["deviceCanAccept"] = bridge.can_accept_recipe
            result["cacheHit"] = True
            result["checkedOnline"] = False
            result["offline"] = True
            result["serverFetch"] = False
            result["catalogMode"] = "release_offline"
            result["releaseCatalog"] = release_catalog.release_catalog_summary()
        else:
            coordinator = await request_coordinator(hass)
            async with coordinator.operation("recipe_detail", "Official recipe detail", entry_ids=[bridge.entry.entry_id]) as operation:
                result = await v30._recipe_detail(
                    hass,
                    bridge,
                    variant_id=variant_id,
                    language=language,
                    refresh=bool(msg.get("refresh")),
                    coordinator=coordinator,
                    operation=operation,
                )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_official_search, ws_recipe_detail):
        websocket_api.async_register_command(hass, command)
