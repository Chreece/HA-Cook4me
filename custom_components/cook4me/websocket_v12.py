from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from . import websocket as legacy
from . import websocket_v11 as v11


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


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_shopping_list, ws_shopping_action):
        websocket_api.async_register_command(hass, command)


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
            ["complete", "incomplete", "remove", "clear_completed"]
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
