from __future__ import annotations

from copy import deepcopy
from functools import partial
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


def _offline_search(bridge, *, query: str, query_language: str, languages: tuple[str, ...], page: int, size: int, filter_rows=None, diet="") -> dict[str, Any]:
    result = release_catalog.search_release_recipes(
        query,
        language=_language(query_language),
        configured_language=v30._device_language(bridge),
        country=v30._device_country(bridge),
        catalog_languages=languages or None,
        page=page,
        size=size,
        group_families=True,
        filter_rows=filter_rows,
        diet=diet,
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
    vol.Optional("shared_filters"): dict,
})
@websocket_api.async_response
async def ws_official_search(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        if not release_catalog.release_catalog_ready():
            raise RuntimeError("offline release catalog is unavailable")
        filters = msg.get("shared_filters")
        filter_rows = None
        diet = ""
        if isinstance(filters, dict):
            from .shared_recipe_runtime import processor
            filter_rows = await processor(bridge, filters, language=_language(msg.get("query_language")))
        result = await hass.async_add_executor_job(partial(_offline_search,
            bridge,
            query=_text(msg.get("query")),
            query_language=_text(msg.get("query_language")) or v30._device_language(bridge),
            languages=_selected_languages(msg.get("languages")),
            page=int(msg.get("page", 0)),
            size=int(msg.get("size", 20)),
            filter_rows=filter_rows, diet=diet,
        ))
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
                group_families=True,
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


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v31/ingredient_catalog",
    vol.Optional("entry_id"): str,
    vol.Optional("language", default="en"): str,
    vol.Optional("refresh", default=False): bool,
})
@websocket_api.async_response
async def ws_ingredient_catalog(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        language = _language(msg.get("language")) or "en"
        items = await hass.async_add_executor_job(release_catalog.ingredient_choices, language)
        connection.send_result(msg["id"], {"items": items, "language": language, "presentationVersion": 63, "offline": True, "houseIngredients": bridge.recipe_hub.profile.get("houseIngredients") or []})
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v31/ingredient_info",
    vol.Optional("entry_id"): str,
    vol.Required("ingredient"): dict,
    vol.Optional("language"): str,
    vol.Optional("include_official_usage", default=True): bool,
})
@websocket_api.async_response
async def ws_ingredient_info(hass, connection, msg) -> None:
    from .websocket_v18 import ws_ingredient_info as ingredient_info
    await ingredient_info(hass, connection, msg)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v31/ui_preferences",
    vol.Optional("entry_id"): str,
    vol.Optional("preferences"): dict,
})
@websocket_api.async_response
async def ws_ui_preferences(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        user_id = str(connection.user.id)
        if "preferences" in msg:
            result = await bridge.recipe_hub.async_set_user_ui_preferences(user_id, msg["preferences"])
        else:
            result = bridge.recipe_hub.user_ui_preferences(user_id)
        connection.send_result(msg["id"], result)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_official_search, ws_recipe_detail, ws_ingredient_catalog, ws_ingredient_info, ws_ui_preferences):
        websocket_api.async_register_command(hass, command)
