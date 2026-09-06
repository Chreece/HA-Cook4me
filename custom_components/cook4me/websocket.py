from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DATA_BRIDGES, DOMAIN


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
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_search(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        result = await bridge.async_search_recipes(
            msg.get("query", ""), page=msg.get("page", 0), size=msg.get("size", 20),
            max_details=msg.get("size", 20), refresh=msg.get("refresh", False),
        )
    except Exception as exc:
        _send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/recipe_detail",
        vol.Optional("entry_id"): str,
        vol.Required("variant_id"): str,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_recipe_detail(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        result = await bridge.async_recipe_detail(msg["variant_id"], refresh=msg.get("refresh", False))
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
    }
)
@websocket_api.async_response
async def ws_recommend(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    try:
        bridge = _bridge(hass, msg.get("entry_id"))
        result = await bridge.async_recommend_recipes(limit=msg["limit"], catalog_size=msg["catalog_size"])
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
