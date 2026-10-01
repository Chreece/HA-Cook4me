"""Authorized persistent recipe blacklist actions."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback

from . import websocket as legacy
from .recipe_blacklist import add_blacklist, remove_blacklist
from .websocket_v32 import _authorized


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/recipe_blacklist_add",
    vol.Required("entry_id"): str,
    vol.Required("recipe"): dict,
})
@websocket_api.async_response
async def ws_recipe_blacklist_add(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        current = bridge.recipe_hub.profile.get("recipeBlacklist") or []
        updated = add_blacklist(current, dict(msg["recipe"]))
        profile = await bridge.recipe_hub.async_set_profile({"recipeBlacklist": updated})
        connection.send_result(msg["id"], {
            "recipeBlacklist": profile.get("recipeBlacklist") or [],
            "profile": profile,
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/recipe_blacklist_remove",
    vol.Required("entry_id"): str,
    vol.Required("identity"): str,
})
@websocket_api.async_response
async def ws_recipe_blacklist_remove(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        current = bridge.recipe_hub.profile.get("recipeBlacklist") or []
        updated = remove_blacklist(current, [msg["identity"]])
        profile = await bridge.recipe_hub.async_set_profile({"recipeBlacklist": updated})
        connection.send_result(msg["id"], {
            "recipeBlacklist": profile.get("recipeBlacklist") or [],
            "profile": profile,
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@callback
def async_register(hass):
    websocket_api.async_register_command(hass, ws_recipe_blacklist_add)
    websocket_api.async_register_command(hass, ws_recipe_blacklist_remove)
