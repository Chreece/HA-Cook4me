from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import persistent_notification, websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v12 as v12
from . import websocket_v18 as v18
from . import websocket_v22 as v22
from .const import DATA_BRIDGES, DOMAIN
from .recipe_book import recipe_book_store_for_bridge
from .request_coordinator import request_coordinator


def _text(value: Any) -> str:
    return str(value or "").strip()


async def _send_one_exact(bridge, recipe: dict[str, Any]) -> dict[str, Any]:
    variant = _text(
        recipe.get("sendVariantId")
        or recipe.get("selectedSendVariantId")
        or recipe.get("searchVariantId")
        or recipe.get("variantFunctionalId")
        or recipe.get("recipeFunctionalId")
    )
    # Exact official ID is the evidence boundary. `sendable` is a frontend/local
    # snapshot and can be stale when another target device is selected.
    if not variant:
        return {
            "sent": False,
            "queued": False,
            "reason": "custom_recipe_has_no_official_seb_id",
        }

    if bridge.available:
        try:
            result = await v12._send_recipe_replaceable(bridge, variant)
        except Exception as exc:
            reason = "device_busy" if bridge.available else "device_offline"
            store = await recipe_book_store_for_bridge(bridge)
            queued = await store.async_queue_send(recipe, reason=reason)
            return {
                "sent": False,
                "queued": True,
                "reason": reason,
                "queuedSend": queued,
                "error": str(exc)[:300],
            }
        store = await recipe_book_store_for_bridge(bridge)
        await store.async_clear_queue()
        return {"sent": True, "queued": False, "result": result}

    store = await recipe_book_store_for_bridge(bridge)
    queued = await store.async_queue_send(recipe, reason="device_offline")
    return {
        "sent": False,
        "queued": True,
        "reason": "device_offline",
        "queuedSend": queued,
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_ai_create, ws_send_multi):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v25/ai_create",
    vol.Optional("entry_id"): str,
    vol.Optional("request", default=""): str,
    vol.Optional("language", default="en"): str,
    vol.Optional("catalog_languages", default=[]): [str],
    vol.Optional("diet", default="profile"): vol.In(v18._DIET_FILTERS),
    vol.Optional("meal_types", default=[]): [str],
    vol.Optional("nutrition_goal", default="balanced"): str,
    vol.Optional("calorie_target"): vol.Any(int, float, str),
    vol.Optional("calorie_tolerance", default=25): vol.All(vol.Coerce(int), vol.Range(min=5, max=100)),
    vol.Optional("max_missing"): vol.All(vol.Coerce(int), vol.Range(min=0, max=20)),
    vol.Optional("only_home", default=False): bool,
    vol.Optional("prefer_expiring", default=True): bool,
    vol.Optional("avoid_recent_days", default=7): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
    vol.Optional("ingredients", default=[]): [dict],
})
@websocket_api.async_response
async def ws_ai_create(hass, connection, msg) -> None:
    bridge = None
    notification_id = "cook4me_ai_recipe"
    language = _text(msg.get("language") or "en")
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        notification_id = f"cook4me_ai_recipe_{bridge.entry.entry_id}"
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "ai_recipe",
            "AI recipe generation",
            entry_ids=[bridge.entry.entry_id],
        ):
            title, message = v22._notification_text(language, "running")
            persistent_notification.async_create(
                hass,
                message,
                title=title,
                notification_id=notification_id,
            )
            profile = bridge.recipe_hub.profile
            had_diet = "diet" in profile
            previous_diet = profile.get("diet")
            try:
                result = await v22._create_ai_recipe(hass, bridge, msg)
            finally:
                # v13 ranking supports a temporary diet override by mutating the
                # provided profile dict. Never persist that temporary AI choice.
                if had_diet:
                    profile["diet"] = previous_diet
                else:
                    profile.pop("diet", None)
            recipe_title = _text(result.get("recipe", {}).get("title"))
            title, message = v22._notification_text(language, "done", recipe_title)
            persistent_notification.async_create(
                hass,
                message,
                title=title,
                notification_id=notification_id,
            )
    except Exception as exc:
        title, message = v22._notification_text(language, "failed", str(exc)[:300])
        persistent_notification.async_create(
            hass,
            message,
            title=title,
            notification_id=notification_id,
        )
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v25/send_multi",
    vol.Optional("entry_id"): str,
    vol.Optional("entry_ids", default=[]): [str],
    vol.Required("recipe"): dict,
})
@websocket_api.async_response
async def ws_send_multi(hass, connection, msg) -> None:
    try:
        primary = legacy._bridge(hass, msg.get("entry_id"))
        bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
        requested = [str(value) for value in msg.get("entry_ids") or [] if str(value)]
        if not requested:
            requested = [primary.entry.entry_id]
        selected = []
        seen = set()
        for entry_id in requested:
            bridge = bridges.get(entry_id)
            if bridge is not None and entry_id not in seen:
                selected.append(bridge)
                seen.add(entry_id)
        if not selected:
            raise ValueError("No selected Cook4Me device is currently loaded")

        recipe = dict(msg["recipe"])
        coordinator = await request_coordinator(hass)
        results = []
        async with coordinator.operation(
            "device_send",
            "Send official recipe to selected Cook4Me devices",
            entry_ids=[bridge.entry.entry_id for bridge in selected],
        ):
            for bridge in selected:
                row = await _send_one_exact(bridge, recipe)
                results.append({
                    "entryId": bridge.entry.entry_id,
                    "title": bridge.entry.title,
                    **row,
                })
        result = {
            "results": results,
            "targetCount": len(results),
            "sentCount": sum(bool(row.get("sent")) for row in results),
            "queuedCount": sum(bool(row.get("queued")) for row in results),
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
