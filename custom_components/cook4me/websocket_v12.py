from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from . import websocket as legacy
from . import websocket_v11 as v11
from . import websocket_v19 as v19


_REPLACEABLE_RECIPE_PHASES = {"idle", "stopped", "preparation", "add_ingredient", "done"}


def _extract_todo_items(response: Any) -> list[dict[str, Any]]:
    raw: list[Any] = []
    if isinstance(response, dict):
        if isinstance(response.get("items"), list):
            raw.extend(response["items"])
        else:
            for value in response.values():
                if isinstance(value, dict) and isinstance(value.get("items"), list):
                    raw.extend(value["items"])

    items: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        summary = str(row.get("summary") or row.get("name") or "").strip()
        if not summary:
            continue
        uid = str(row.get("uid") or row.get("id") or summary).strip()
        status = str(row.get("status") or "needs_action").strip()
        items.append({"uid": uid, "summary": summary, "status": status})
    return items


async def _shopping_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    entity_id = v11._shopping_list_entity(hass)
    if not entity_id:
        return {"available": False, "entityId": None, "items": []}
    if not hass.services.has_service("todo", "get_items"):
        return {"available": False, "entityId": entity_id, "items": []}

    response = await hass.services.async_call(
        "todo",
        "get_items",
        {"entity_id": entity_id},
        blocking=True,
        return_response=True,
    )
    items = _extract_todo_items(response)
    return {
        "available": True,
        "entityId": entity_id,
        "items": items,
        "activeCount": sum(row["status"] != "completed" for row in items),
        "completedCount": sum(row["status"] == "completed" for row in items),
    }


async def _shopping_action(
    hass: HomeAssistant, *, action: str, uid: str | None = None
) -> dict[str, Any]:
    entity_id = v11._shopping_list_entity(hass)
    if not entity_id:
        raise HomeAssistantError("Home Assistant Shopping List is not available")

    if action in {"complete", "incomplete"}:
        if not uid:
            raise HomeAssistantError("Shopping List item id is required")
        if not hass.services.has_service("todo", "update_item"):
            raise HomeAssistantError("Home Assistant Shopping List cannot update items")
        await hass.services.async_call(
            "todo",
            "update_item",
            {
                "entity_id": entity_id,
                "item": uid,
                "status": "completed" if action == "complete" else "needs_action",
            },
            blocking=True,
        )
    elif action in {"complete_all", "incomplete_all"}:
        if not hass.services.has_service("todo", "update_item"):
            raise HomeAssistantError("Home Assistant Shopping List cannot update items")
        snapshot = await _shopping_snapshot(hass)
        target_status = "completed" if action == "complete_all" else "needs_action"
        for row in snapshot.get("items") or []:
            if not isinstance(row, dict) or row.get("status") == target_status:
                continue
            item_uid = str(row.get("uid") or "").strip()
            if not item_uid:
                continue
            await hass.services.async_call(
                "todo",
                "update_item",
                {
                    "entity_id": entity_id,
                    "item": item_uid,
                    "status": target_status,
                },
                blocking=True,
            )
    elif action == "remove":
        if not uid:
            raise HomeAssistantError("Shopping List item id is required")
        if not hass.services.has_service("todo", "remove_item"):
            raise HomeAssistantError("Home Assistant Shopping List cannot remove items")
        await hass.services.async_call(
            "todo",
            "remove_item",
            {"entity_id": entity_id, "item": [uid]},
            blocking=True,
        )
    elif action == "clear_completed":
        if not hass.services.has_service("todo", "remove_completed_items"):
            raise HomeAssistantError("Home Assistant Shopping List cannot clear completed items")
        await hass.services.async_call(
            "todo",
            "remove_completed_items",
            {"entity_id": entity_id},
            blocking=True,
        )
    else:
        raise HomeAssistantError(f"Unsupported Shopping List action: {action}")

    return await _shopping_snapshot(hass)


def _recipe_phase(bridge) -> str:
    return str(bridge.data.get("phase") or bridge.data.get("status") or "").strip().lower()


def _loaded_variant(bridge) -> str:
    return str(bridge.data.get("variantFunctionalId") or "").strip()


async def _wait_for_loaded_variant(bridge, variant_id: str, timeout: float = 90.0) -> bool:
    from .delivery_confirmation import wait_for_recipe
    return await wait_for_recipe(bridge, variant_id, timeout=timeout)


async def _send_recipe_replaceable(bridge, variant_id: str, *, diet: str | None = None, diet_filters: dict | None = None, verify_loaded: bool = False) -> dict[str, Any]:
    lock = getattr(bridge, "_send_lock", None)
    if lock is None:
        lock = bridge._send_lock = asyncio.Lock()
    async with lock:
        record = getattr(bridge, "record_recipe_delivery", lambda *args: None)
        record("resolving", variant_id)
        try:
            result = await _send_recipe_replaceable_locked(bridge, variant_id, diet=diet, verify_loaded=verify_loaded, **({"diet_filters": diet_filters} if diet_filters is not None else {}))
        except asyncio.CancelledError:
            record("cancelled", variant_id)
            raise
        except Exception:
            record("failed", variant_id)
            raise
        record("unconfirmed" if result.get("confirmation") == "unconfirmed" else "completed", variant_id)
        return result


async def _send_recipe_replaceable_locked(bridge, variant_id: str, *, diet: str | None = None, diet_filters: dict | None = None, verify_loaded: bool = False) -> dict[str, Any]:
    """Send a recipe, replacing only a safely pre-cook loaded recipe.

    The proven cloud route writes a new recipe reference into the appliance
    shadow. There is no proven independent cloud command that forcibly exits a
    recipe, so replacement is attempted only in non-cooking phases and then
    verified from live/current appliance state. If firmware keeps the old
    recipe, report that explicitly instead of pretending it was removed.
    """

    variant_id = str(variant_id).strip()
    if not variant_id:
        raise HomeAssistantError("Recipe variant ID is required")

    meta = await bridge.async_recipe_detail(variant_id)
    record = getattr(bridge, "record_recipe_delivery", lambda *args: None)
    record("resolved", variant_id, meta)
    grouping = str(meta.get("groupingFunctionalId") or "").strip()
    recipe = str(meta.get("recipeFunctionalId") or "").strip()
    if not grouping or not recipe:
        raise HomeAssistantError(
            "Official recipe does not contain the SEB IDs required for Cook4Me delivery"
        )
    if verify_loaded and recipe != variant_id:
        raise HomeAssistantError("Official recipe identity does not match the selected original edition")
    if not bridge.available:
        raise HomeAssistantError("Cook4Me is not connected to the cloud")

    annotated = bridge._profile_match_or_raise(meta, **({"diet": diet} if diet is not None else {}), **({"diet_filters": diet_filters} if diet_filters is not None else {}))
    loaded = bridge.loaded_recipe
    replacing = False
    phase = _recipe_phase(bridge)

    if loaded:
        if _loaded_variant(bridge) == recipe:
            return {
                "accepted": {"alreadyLoaded": True},
                "recipe": annotated,
                "replacedLoadedRecipe": False,
                "verified": True,
            }
        if phase not in _REPLACEABLE_RECIPE_PHASES:
            loaded_title = loaded.get("title") or loaded.get("groupingFunctionalId") or "another recipe"
            shown_phase = phase or "unknown"
            raise HomeAssistantError(
                f"Cook4Me already has an active recipe/session ({loaded_title}, {shown_phase}). "
                "It will not be replaced while cooking or while the appliance state is uncertain."
            )
        replacing = True

    record("sending", variant_id)
    accepted = await bridge._run_client_json("send-recipe", grouping, recipe, timeout=45)
    record("cloud_accepted", variant_id)

    verified = True
    if replacing or verify_loaded:
        verified = await _wait_for_loaded_variant(bridge, recipe, timeout=90)
        if not verified:
            # Silence is not rejection: the cooker may load after the deadline.
            # Do not record a verified send or queue/repeat an accepted write.
            return {"accepted": accepted, "recipe": annotated,
                    "replacedLoadedRecipe": replacing, "verified": False,
                    "confirmation": "unconfirmed", "confirmationTimeout": 90,
                    "reason": "device_confirmation_unavailable"}

    await bridge.recipe_hub.async_record_send(annotated)
    return {
        "accepted": accepted,
        "recipe": annotated,
        "replacedLoadedRecipe": replacing,
        "verified": verified,
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_shopping_list, ws_shopping_action, ws_send_recipe_replaceable):
        websocket_api.async_register_command(hass, command)
    v19.async_register(hass)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v12/shopping_list",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_shopping_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        legacy._bridge(hass, msg.get("entry_id"))
        result = await _shopping_snapshot(hass)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v12/shopping_action",
        vol.Optional("entry_id"): str,
        vol.Required("action"): vol.In(
            [
                "complete",
                "incomplete",
                "complete_all",
                "incomplete_all",
                "remove",
                "clear_completed",
            ]
        ),
        vol.Optional("uid"): str,
    }
)
@websocket_api.async_response
async def ws_shopping_action(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        legacy._bridge(hass, msg.get("entry_id"))
        result = await _shopping_action(
            hass,
            action=str(msg["action"]),
            uid=str(msg.get("uid") or "") or None,
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v12/send_recipe_replaceable",
        vol.Optional("entry_id"): str,
        vol.Required("variant_id"): str,
    }
)
@websocket_api.async_response
async def ws_send_recipe_replaceable(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await _send_recipe_replaceable(bridge, str(msg["variant_id"]))
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
