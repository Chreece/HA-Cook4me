from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import persistent_notification, websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from .expiry import update_expiry_notification
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_inventory import (
    async_consume_nutrition_report,
    async_reconcile_nutrition_inventory,
)


def _notification_id(entry_id: str) -> str:
    return f"cook4me_consumption_{entry_id}"


def _state(bridge) -> dict[str, Any]:
    profile = bridge.recipe_hub.profile
    return {
        "houseIngredients": profile.get("houseIngredients") or [],
        "pendingConsumption": bridge.recipe_hub.pending_consumption,
    }


async def _reconcile_nutrition(bridge) -> None:
    store = await nutrition_store_for_bridge(bridge)
    await async_reconcile_nutrition_inventory(
        store, bridge.recipe_hub.profile.get("houseIngredients") or []
    )


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_inventory_state, ws_inventory_add, ws_inventory_update,
        ws_inventory_remove, ws_consumption_confirm, ws_consumption_clear,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v14/inventory_state",
    vol.Optional("entry_id"): str,
})
@callback
def ws_inventory_state(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = _state(bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v14/inventory_add",
    vol.Optional("entry_id"): str,
    vol.Required("ingredient"): dict,
    vol.Optional("quantity"): vol.Any(int, float, str),
    vol.Optional("unit", default=""): str,
    vol.Optional("unlimited", default=False): bool,
    vol.Optional("best_before", default=""): str,
    vol.Optional("lot_metadata"): dict,
})
@websocket_api.async_response
async def ws_inventory_add(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        await bridge.recipe_hub.async_inventory_add(
            dict(msg["ingredient"]), quantity=msg.get("quantity"),
            unit=str(msg.get("unit") or ""), unlimited=bool(msg.get("unlimited")),
            best_before=str(msg.get("best_before") or ""),
            lot_metadata=dict(msg["lot_metadata"]) if "lot_metadata" in msg else None,
        )
        await _reconcile_nutrition(bridge)
        update_expiry_notification(bridge)
        result = _state(bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v14/inventory_update",
    vol.Optional("entry_id"): str,
    vol.Required("identity"): str,
    vol.Optional("quantity"): vol.Any(int, float, str),
    vol.Optional("unit", default=""): str,
    vol.Optional("unlimited", default=False): bool,
    vol.Optional("best_before"): str,
    vol.Optional("lots"): [dict],
})
@websocket_api.async_response
async def ws_inventory_update(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        kwargs: dict[str, Any] = {}
        if "best_before" in msg: kwargs["best_before"] = str(msg.get("best_before") or "")
        if "lots" in msg: kwargs["lots"] = list(msg.get("lots") or [])
        await bridge.recipe_hub.async_inventory_update(
            str(msg["identity"]), quantity=msg.get("quantity"),
            unit=str(msg.get("unit") or ""), unlimited=bool(msg.get("unlimited")), **kwargs,
        )
        await _reconcile_nutrition(bridge)
        update_expiry_notification(bridge)
        result = _state(bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v14/inventory_remove",
    vol.Optional("entry_id"): str,
    vol.Required("identity"): str,
})
@websocket_api.async_response
async def ws_inventory_remove(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        await bridge.recipe_hub.async_inventory_remove(str(msg["identity"]))
        await _reconcile_nutrition(bridge)
        update_expiry_notification(bridge)
        result = _state(bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v14/consumption_confirm",
    vol.Optional("entry_id"): str,
    vol.Required("pending_id"): str,
    vol.Required("ingredients"): [dict],
    vol.Optional("allocations"): [dict],
})
@websocket_api.async_response
async def ws_consumption_confirm(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await bridge.recipe_hub.async_confirm_consumption(
            str(msg["pending_id"]), list(msg.get("ingredients") or [])
        )
        nutrition_store = await nutrition_store_for_bridge(bridge)
        consumed_nutrition = await async_consume_nutrition_report(
            nutrition_store, result.get("report") or {}
        )
        await async_reconcile_nutrition_inventory(
            nutrition_store, bridge.recipe_hub.profile.get("houseIngredients") or []
        )
        result["mealNutrition"] = consumed_nutrition
        if consumed_nutrition.get("totals"): result["nutrition"] = consumed_nutrition
        completed = result.get("completedRecipe") if isinstance(result.get("completedRecipe"), dict) else {}
        history = await meal_history_store_for_bridge(bridge)
        result["mealHistoryRecord"] = await history.async_record(
            recipe=completed, nutrition=consumed_nutrition,
            allocations=list(msg.get("allocations") or []),
            consumption=result.get("report") or {},
        )
        persistent_notification.async_dismiss(hass, _notification_id(bridge.entry.entry_id))
        update_expiry_notification(bridge)
        result.update(_state(bridge))
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v14/consumption_clear",
    vol.Optional("entry_id"): str,
    vol.Required("pending_id"): str,
})
@websocket_api.async_response
async def ws_consumption_clear(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        cleared = await bridge.recipe_hub.async_clear_pending_consumption(str(msg["pending_id"]))
        if cleared: persistent_notification.async_dismiss(hass, _notification_id(bridge.entry.entry_id))
        result = {"cleared": cleared, **_state(bridge)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)
