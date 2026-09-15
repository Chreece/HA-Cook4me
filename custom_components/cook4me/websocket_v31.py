from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import release_catalog
from . import websocket as legacy
from . import websocket_v30 as v30
from .request_coordinator import request_coordinator


def _text(value: Any) -> str:
    return str(value or "").strip()


def _language(value: Any) -> str:
    return _text(value).lower().replace("_", "-").split("-", 1)[0]


def _selected_languages(values: Any) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple, set)):
        return ()
    return tuple(dict.fromkeys(lang for value in values if (lang := _language(value))))


def _offline_search(bridge, *, query: str, query_language: str, languages: tuple[str, ...], page: int, size: int) -> dict[str, Any]:
    result = release_catalog.search_release_recipes(
        query,
        language=_language(query_language),
        configured_language=v30._device_language(bridge),
        country=v30._device_country(bridge),
        catalog_languages=languages or None,
        page=page,
        size=size,
    )
    result.update({
        "queryLanguage": _language(query_language),
        "catalogLanguages": list(languages),
        "serverFetch": False,
        "catalogMode": "release_offline",
        "searchContract": "release-multilingual-index-v31-exact-query-translations",
        "releaseCatalog": release_catalog.release_catalog_summary(),
    })
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
