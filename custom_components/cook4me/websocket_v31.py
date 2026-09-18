from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v14 as v14
from .expiry import update_expiry_notification
from .meal_history import meal_history_store_for_bridge
from .meal_lifecycle import meal_lifecycle_store_for_bridge
from .smart_scale import (
    portion_nutrition,
    prepare_inventory_reweigh,
    scale_entity_candidates,
    scale_reading,
    scale_recipe_guide,
    smart_scale_store_for_bridge,
)


async def _state(
    hass: HomeAssistant, bridge: Any, *, recipe: dict[str, Any] | None = None
) -> dict[str, Any]:
    store = await smart_scale_store_for_bridge(bridge)
    lifecycle = await meal_lifecycle_store_for_bridge(bridge)
    selected = store.selected_entity_id
    return {
        **store.snapshot(recipe=recipe),
        "candidates": scale_entity_candidates(hass),
        "reading": scale_reading(hass, selected),
        "leftovers": lifecycle.leftovers,
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_scale_state,
        ws_scale_select,
        ws_container_save,
        ws_container_delete,
        ws_measurement_record,
        ws_batch_weight_set,
        ws_session_clear,
        ws_recipe_scale,
        ws_portion_nutrition,
        ws_inventory_reweigh,
        ws_leftover_weight_set,
        ws_leftover_consume_weight,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/scale_state",
        vol.Optional("entry_id"): str,
        vol.Optional("recipe"): dict,
    }
)
@websocket_api.async_response
async def ws_scale_state(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"]) if isinstance(msg.get("recipe"), dict) else None
        result = await _state(hass, bridge, recipe=recipe)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/scale_select",
        vol.Optional("entry_id"): str,
        vol.Optional("entity_id", default=""): str,
    }
)
@websocket_api.async_response
async def ws_scale_select(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        entity_id = str(msg.get("entity_id") or "").strip()
        if entity_id:
            candidates = {row["entityId"] for row in scale_entity_candidates(hass)}
            if entity_id not in candidates:
                raise ValueError("Selected entity is not a supported mass sensor")
        store = await smart_scale_store_for_bridge(bridge)
        await store.async_select_entity(entity_id)
        result = await _state(hass, bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/container_save",
        vol.Optional("entry_id"): str,
        vol.Required("name"): str,
        vol.Required("tare_grams"): vol.Any(int, float, str),
        vol.Optional("container_id", default=""): str,
    }
)
@websocket_api.async_response
async def ws_container_save(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await smart_scale_store_for_bridge(bridge)
        saved = await store.async_save_container(
            str(msg["name"]),
            msg.get("tare_grams"),
            container_id=str(msg.get("container_id") or ""),
        )
        result = {"container": saved, **await _state(hass, bridge)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/container_delete",
        vol.Optional("entry_id"): str,
        vol.Required("container_id"): str,
    }
)
@websocket_api.async_response
async def ws_container_delete(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await smart_scale_store_for_bridge(bridge)
        deleted = await store.async_delete_container(str(msg["container_id"]))
        result = {"deleted": deleted, **await _state(hass, bridge)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/measurement_record",
        vol.Optional("entry_id"): str,
        vol.Required("recipe"): dict,
        vol.Required("ingredient_index"): vol.Coerce(int),
        vol.Required("ingredient"): dict,
        vol.Required("grams"): vol.Any(int, float, str),
    }
)
@websocket_api.async_response
async def ws_measurement_record(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"])
        store = await smart_scale_store_for_bridge(bridge)
        session = await store.async_record_measurement(
            recipe,
            ingredient_index=int(msg["ingredient_index"]),
            ingredient=dict(msg["ingredient"]),
            grams=msg.get("grams"),
        )
        result = {"session": session, **await _state(hass, bridge, recipe=recipe)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/batch_weight_set",
        vol.Optional("entry_id"): str,
        vol.Required("recipe"): dict,
        vol.Required("grams"): vol.Any(int, float, str),
    }
)
@websocket_api.async_response
async def ws_batch_weight_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"])
        store = await smart_scale_store_for_bridge(bridge)
        session = await store.async_set_batch_weight(recipe, msg.get("grams"))
        result = {"session": session, **await _state(hass, bridge, recipe=recipe)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/session_clear",
        vol.Optional("entry_id"): str,
        vol.Required("recipe"): dict,
    }
)
@websocket_api.async_response
async def ws_session_clear(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"])
        store = await smart_scale_store_for_bridge(bridge)
        cleared = await store.async_clear_session(recipe)
        result = {"cleared": cleared, **await _state(hass, bridge, recipe=recipe)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/recipe_scale",
        vol.Optional("entry_id"): str,
        vol.Required("recipe"): dict,
        vol.Required("anchor_index"): vol.Coerce(int),
        vol.Required("measured_grams"): vol.Any(int, float, str),
    }
)
@callback
def ws_recipe_scale(hass, connection, msg) -> None:
    try:
        result = scale_recipe_guide(
            dict(msg["recipe"]),
            anchor_index=int(msg["anchor_index"]),
            measured_grams=msg.get("measured_grams"),
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/portion_nutrition",
        vol.Optional("entry_id"): str,
        vol.Required("recipe"): dict,
        vol.Required("portion_grams"): vol.Any(int, float, str),
        vol.Optional("batch_grams"): vol.Any(int, float, str),
    }
)
@websocket_api.async_response
async def ws_portion_nutrition(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"])
        batch_grams = msg.get("batch_grams")
        if batch_grams in (None, ""):
            store = await smart_scale_store_for_bridge(bridge)
            session = store.session_for(recipe) or {}
            batch_grams = session.get("batchWeightGrams")
        nutrition = recipe.get("nutrition")
        if not isinstance(nutrition, dict) or not (
            nutrition.get("totals") or nutrition.get("perServing")
        ):
            nutrition = recipe.get("catalogNutrition") or {}
        result = portion_nutrition(
            nutrition, batch_grams=batch_grams, portion_grams=msg.get("portion_grams")
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/inventory_reweigh",
        vol.Optional("entry_id"): str,
        vol.Required("identity"): str,
        vol.Required("grams"): vol.Any(int, float, str),
        vol.Optional("lot_id", default=""): str,
    }
)
@websocket_api.async_response
async def ws_inventory_reweigh(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        plan = prepare_inventory_reweigh(
            bridge.recipe_hub.profile.get("houseIngredients") or [],
            str(msg["identity"]),
            grams=msg.get("grams"),
            lot_id=str(msg.get("lot_id") or ""),
        )
        if plan.get("remove"):
            await bridge.recipe_hub.async_inventory_remove(str(msg["identity"]))
        elif "lots" in plan:
            await bridge.recipe_hub.async_inventory_update(
                str(msg["identity"]),
                unit=str(plan.get("unit") or ""),
                unlimited=False,
                lots=list(plan.get("lots") or []),
            )
        else:
            await bridge.recipe_hub.async_inventory_update(
                str(msg["identity"]),
                quantity=plan.get("quantity"),
                unit=str(plan.get("unit") or ""),
                unlimited=False,
            )
        await v14._reconcile_nutrition(bridge)
        update_expiry_notification(bridge)
        result = {**v14._state(bridge), "reweigh": plan}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/leftover_weight_set",
        vol.Optional("entry_id"): str,
        vol.Required("leftover_id"): str,
        vol.Required("grams"): vol.Any(int, float, str),
    }
)
@websocket_api.async_response
async def ws_leftover_weight_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        leftover = await lifecycle.async_set_leftover_weight(
            str(msg["leftover_id"]), msg.get("grams")
        )
        result = {
            "leftover": leftover,
            "leftovers": lifecycle.leftovers,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v31/leftover_consume_weight",
        vol.Optional("entry_id"): str,
        vol.Required("leftover_id"): str,
        vol.Required("grams"): vol.Any(int, float, str),
    }
)
@websocket_api.async_response
async def ws_leftover_consume_weight(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        consumed = await lifecycle.async_consume_leftover_weight(
            str(msg["leftover_id"]), msg.get("grams")
        )
        history = await meal_history_store_for_bridge(bridge)
        record = await history.async_record(
            recipe={
                "title": consumed.get("title"),
                "servings": consumed.get("servings"),
            },
            nutrition=consumed.get("nutrition") or {},
            consumption={},
        )
        await lifecycle.async_record_meal_cost(
            record.get("id"),
            {
                "totalsByCurrency": consumed.get("costByCurrency") or {},
                "source": "leftover_scale",
            },
        )
        result = {
            "consumed": consumed,
            "mealHistoryRecord": record,
            "leftovers": lifecycle.leftovers,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
