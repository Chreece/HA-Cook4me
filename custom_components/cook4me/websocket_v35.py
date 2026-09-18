"""Authorized editing of household and member diet preferences."""
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback
from . import websocket as legacy
from .websocket_v32 import _authorized


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v35/diet_profiles",
    vol.Required("entry_id"): str, vol.Optional("profiles"): dict,
    vol.Optional("preferences"): [str]})
@websocket_api.async_response
async def ws_diet_profiles(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        if "profiles" in msg:
            patch = {"dietProfiles": msg["profiles"]}
            if "preferences" in msg:
                patch["preferences"] = msg["preferences"]
            profile = await bridge.recipe_hub.async_set_profile(patch)
        else:
            profile = bridge.recipe_hub.profile
        connection.send_result(msg["id"], {"profile": profile})
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@callback
def async_register(hass):
    websocket_api.async_register_command(hass, ws_diet_profiles)
