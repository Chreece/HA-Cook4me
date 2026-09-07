from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import persistent_notification, websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from .expiry import update_expiry_notification


def _notification_id(entry_id: str) -> str:
    return f"cook4me_consumption_{entry_id}"


def _state(bridge) -> dict[str, Any]:
    profile = bridge.recipe_hub.profile
    return {
        "houseIngredients": profile.get("houseIngredients") or [],
        "pendingConsumption": bridge.recipe_hub.pending_consumption,
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_inventory_state,
        ws_inventory_add,
        ws_inventory_update,
        ws_inventory_remove,
        ws_consumption_confirm,
        ws_consumption_clear,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v14/inventory_state",
        vol.Optional("entry_id"): str,
    }
)
@callback
def ws_inventory_state(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = _state(bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v14/inventory_add",
        vol.Optional("entry_id"): str,
        vol.Required("ingredient"): dict,
        vol.Optional("quantity"): vol.Any(int, float, str),
        vol.Optional("unit", default=""): str,
        vol.Optional("unlimited", default=False): bool,
        vol.Optional("best_before", default=""): str,
    }
)
@websocket_api.async_response
async def ws_inventory_add(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        await bridge.recipe_hub.async_inventory_add(
            dict(msg["ingredient"]),
            quantity=msg.get("quantity"),
            unit=str(msg.get("unit") or ""),
            unlimited=bool(msg.get("unlimited")),
            best_before=str(msg.get("best_before") or ""),
        )
        update_expiry_notification(bridge)
        result = _state(bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v14/inventory_update",
        vol.Optional("entry_id"): str,
        vol.Required("identity"): str,
        vol.Optional("quantity"): vol.Any(int, float, str),
        vol.Optional("unit", default=""): str,
        vol.Optional("unlimited", default=False): bool,
        vol.Optional("best_before"): str,
    }
)
@websocket_api.async_response
async def ws_inventory_update(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        kwargs: dict[str, Any] = {}
        if "best_before" in msg:
            kwargs["best_before"] = str(msg.get("best_before") or "")
        await bridge.recipe_hub.async_inventory_update(
            str(msg["identity"]),
            quantity=msg.get("quantity"),
            unit=str(msg.get("unit") or ""),
            unlimited=bool(msg.get("unlimited")),
            **kwargs,
        )
        update_expiry_notification(bridge)
        result = _state(bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v14/inventory_remove",
        vol.Optional("entry_id"): str,
        vol.Required("identity"): str,
    }
)
@websocket_api.async_response
async def ws_inventory_remove(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        await bridge.recipe_hub.async_inventory_remove(str(msg["identity"]))
        update_expiry_notification(bridge)
        result = _state(bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v14/consumption_confirm",
        vol.Optional("entry_id"): str,
        vol.Required("pending_id"): str,
        vol.Required("ingredients"): [dict],
    }
)
@websocket_api.async_response
async def ws_consumption_confirm(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await bridge.recipe_hub.async_confirm_consumption(
            str(msg["pending_id"]), list(msg.get("ingredients") or [])
        )
        persistent_notification.async_dismiss(
            hass, _notification_id(bridge.entry.entry_id)
        )
        update_expiry_notification(bridge)
        result.update(_state(bridge))
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v14/consumption_clear",
        vol.Optional("entry_id"): str,
        vol.Required("pending_id"): str,
    }
)
@websocket_api.async_response
async def ws_consumption_clear(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        cleared = await bridge.recipe_hub.async_clear_pending_consumption(
            str(msg["pending_id"])
        )
        if cleared:
            persistent_notification.async_dismiss(
                hass, _notification_id(bridge.entry.entry_id)
            )
        result = {"cleared": cleared, **_state(bridge)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
