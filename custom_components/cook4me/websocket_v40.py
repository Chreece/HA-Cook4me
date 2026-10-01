"""Authorized persistent recipe blacklist actions."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback

from . import websocket as legacy
from .recipe_blacklist import add_blacklist, remove_blacklist
from .websocket_v32 import _authorized


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v40/recipe_blacklist",
    vol.Required("entry_id"): str,
    vol.Required("action"): vol.In(("add", "remove")),
    vol.Optional("recipe"): dict,
    vol.Optional("keys"): [str],
})
@websocket_api.async_response
async def ws_recipe_blacklist(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        current = bridge.recipe_hub.profile.get("recipeBlacklist") or []
        action = msg["action"]
        if action == "add":
            recipe = msg.get("recipe")
            if not isinstance(recipe, dict):
                raise ValueError("Recipe is required")
            updated = add_blacklist(current, recipe)
        else:
            updated = remove_blacklist(current, msg.get("keys") or [])
        profile = await bridge.recipe_hub.async_set_profile({"recipeBlacklist": updated})
        connection.send_result(msg["id"], {
            "recipeBlacklist": profile.get("recipeBlacklist") or [],
            "profile": profile,
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@callback
def async_register(hass):
    websocket_api.async_register_command(hass, ws_recipe_blacklist)
