"""Device settings and announcements, scoped to the authenticated HA user."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback

from . import websocket as legacy
from .device_settings import choices, device_access


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


@callback
def async_register(hass):
    for command in (ws_device_settings, ws_announcement_test, ws_announcement_subscribe):
        websocket_api.async_register_command(hass, command)
