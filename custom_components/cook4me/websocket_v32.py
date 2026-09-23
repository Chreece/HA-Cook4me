"""Device settings and announcements, scoped to the authenticated HA user."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

from . import websocket as legacy
from .device_settings import choices, device_access, device_read_access


def _authorized(hass, connection, msg):
    bridge = legacy._bridge(hass, msg.get("entry_id"))
    if not device_access(hass, bridge, connection.user):
        raise PermissionError("You cannot control this Cook4Me device")
    return bridge


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v32/device_settings",
    vol.Required("entry_id"): str,
    vol.Optional("settings"): dict,
})
@websocket_api.async_response
async def ws_device_settings(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        if "settings" in msg:
            await bridge.device_settings.async_save(connection.user, msg["settings"])
        connection.send_result(msg["id"], {
            "settings": bridge.device_settings.for_user(connection.user.id),
            "choices": choices(hass, connection.user),
            "status": bridge.announcements.status.get(connection.user.id),
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v32/announcement_test",
    vol.Required("entry_id"): str,
})
@websocket_api.async_response
async def ws_announcement_test(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        await bridge.announcements.test(connection.user)
        connection.send_result(msg["id"], {"done": True})
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v32/announcement_subscribe",
    vol.Required("entry_id"): str,
})
@websocket_api.async_response
async def ws_announcement_subscribe(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        listeners = bridge.announcements.listeners.setdefault(connection.user.id, [])
        def listener(status):
            connection.send_event(msg["id"], status)
        listeners.append(listener)
        def unsubscribe():
            if listener in listeners:
                listeners.remove(listener)
        connection.subscriptions[msg["id"]] = unsubscribe
        connection.send_result(msg["id"])
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


def _header_device(bridge):
    """Read the HA name for this cooker only; never publish the registry."""
    device = dr.async_get(bridge.hass).async_get_device(
        identifiers={(DOMAIN, bridge.device_uuid)}
    )
    names = (getattr(device, "name_by_user", None),
             getattr(device, "name", None), bridge.entry.title, "Cook4Me")
    name = next(value.strip() for value in names
                if isinstance(value, str) and value.strip())
    return getattr(device, "id", None), name[:300]


def _device_snapshot(bridge):
    # Only display telemetry crosses this channel; no profiles or raw shadow data.
    keys = ("active", "phase", "status", "updating", "recipeTitle", "currentInstruction",
            "variantFunctionalId", "stepFunctionalId", "stepIndex", "recipeStepCount",
            "programName", "remainingTime", "elapsedTime", "progress",
            "uiFirmware", "wifiFirmware", "lastConnection", "lastDisconnection")
    data = bridge.data or {}
    state = {key: data[key] for key in keys
             if isinstance(data.get(key), (str, bool, int, float))}
    state["deviceName"] = _header_device(bridge)[1]
    loaded = bridge.loaded_recipe
    title = (loaded.get("title") or loaded.get("name")) if isinstance(loaded, dict) else loaded
    return {"entry_id": bridge.entry.entry_id, "accessible": True,
            "connected": bool(bridge.available), "canAcceptRecipe": bool(bridge.can_accept_recipe),
            "loadedRecipe": {"title": str(title)[:300]} if title else None, "state": state}


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v32/device_state_subscribe",
    vol.Required("entry_id"): str,
})
@websocket_api.async_response
async def ws_device_state_subscribe(hass, connection, msg):
    try:
        bridge = legacy._bridge(hass, msg["entry_id"])
        if not device_read_access(hass, bridge, connection.user):
            raise PermissionError("You cannot view this Cook4Me device")
        active = True
        remove = None
        remove_registry = None
        watched_device = _header_device(bridge)[0]

        def unsubscribe():
            nonlocal active
            if not active:
                return
            active = False
            if remove_registry:
                remove_registry()
            if remove:
                remove()

        def listener():
            if not active:
                return
            if not device_read_access(hass, bridge, connection.user):
                unsubscribe()
                connection.send_event(msg["id"], {"entry_id": bridge.entry.entry_id,
                    "accessible": False, "connected": False, "canAcceptRecipe": False,
                    "loadedRecipe": None, "state": {}})
                return
            connection.send_event(msg["id"], _device_snapshot(bridge))

        @callback
        def registry_updated(event):
            nonlocal watched_device
            current = _header_device(bridge)[0]
            if event.data.get("device_id") in {watched_device, current} - {None}:
                watched_device = current
                listener()  # Recheck this user's read permission before sending.

        remove = bridge.async_add_listener(listener)
        remove_registry = hass.bus.async_listen(
            dr.EVENT_DEVICE_REGISTRY_UPDATED, registry_updated
        )
        connection.subscriptions[msg["id"]] = unsubscribe
        connection.send_result(msg["id"])
        listener()
    except Exception as exc:
        if "unsubscribe" in locals():
            unsubscribe()
        legacy._send_error(connection, msg, exc)


@callback
def async_register(hass):
    for command in (ws_device_settings, ws_announcement_test, ws_announcement_subscribe,
                    ws_device_state_subscribe):
        websocket_api.async_register_command(hass, command)
