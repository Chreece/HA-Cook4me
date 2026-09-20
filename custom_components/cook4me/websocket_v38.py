from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import websocket as legacy
from .costs import cost_store_for_bridge
from .costing import calculate_consumption_cost
from .expiry import update_expiry_notification
from .meal_history import meal_history_store_for_bridge
from .meal_lifecycle import meal_lifecycle_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_inventory import async_reconcile_nutrition_inventory


def _report_from_meal(meal: Any) -> dict[str, list[dict[str, Any]]]:
    row = meal if isinstance(meal, dict) else {}
    return {
        "deducted": [
            dict(item) for item in row.get("ingredients") or [] if isinstance(item, dict)
        ],
        "deductedLots": [
            dict(item) for item in row.get("stockLots") or [] if isinstance(item, dict)
        ],
        "skipped": [],
        "depleted": [],
    }


def _requests_from_report(report: Any) -> list[dict[str, Any]]:
    """Recreate exact old requests for rollback, keeping stable lot IDs."""
    result = []
    for row in report.get("deductedLots") if isinstance(report, dict) else []:
        if not isinstance(row, dict):
            continue
        quantity = row.get("quantity")
        if quantity in (None, ""):
            continue
        result.append(
            {
                "identity": str(row.get("identity") or ""),
                "name": str(row.get("name") or ""),
                "consume": True,
                "quantity": quantity,
                "unit": str(row.get("unit") or ""),
                **(
                    {"lotId": str(row.get("lotId"))}
                    if row.get("lotId")
                    else {}
                ),
            }
        )
    return result


async def _food_state(bridge, history, *, limit: int = 30) -> dict[str, Any]:
    profile = bridge.recipe_hub.profile
    return {
        "profile": profile,
        "houseIngredients": profile.get("houseIngredients") or [],
        "householdMembers": profile.get("householdMembers") or [],
        "history": history.recent(limit),
        "summary": history.summary(now=dt_util.now()),
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_history_update)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v38/history_update",
        vol.Optional("entry_id"): str,
        vol.Required("meal_id"): str,
        vol.Optional("ingredients"): [dict],
        vol.Optional("allocations"): [dict],
    }
)
@websocket_api.async_response
async def ws_history_update(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        history = await meal_history_store_for_bridge(bridge)
        previous = history.get(str(msg["meal_id"]))
        if previous is None:
            raise ValueError("Meal history record was not found")

        revision = None
        report = _report_from_meal(previous)
        new_report = report
        if "ingredients" in msg:
            revision = await bridge.recipe_hub.async_revise_consumption(
                report,
                list(msg.get("ingredients") or []),
                strict=True,
            )
            new_report = revision.get("report") or {}
        try:
            meal = await history.async_update(
                str(msg["meal_id"]),
                allocations=(
                    list(msg.get("allocations") or [])
                    if "allocations" in msg
                    else previous.get("allocations")
                ),
                consumption=new_report if "ingredients" in msg else None,
            )
        except BaseException:
            if revision is not None:
                # Compensate inventory if the history store could not commit.
                await bridge.recipe_hub.async_revise_consumption(
                    new_report,
                    _requests_from_report(report),
                    strict=False,
                )
            raise

        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        meal_cost = lifecycle.meal_cost(str(meal.get("id") or "")) or {}
        if "ingredients" in msg:
            nutrition_store = await nutrition_store_for_bridge(bridge)
            await async_reconcile_nutrition_inventory(
                nutrition_store,
                bridge.recipe_hub.profile.get("houseIngredients") or [],
            )
            cost_store = await cost_store_for_bridge(bridge)
            meal_cost = calculate_consumption_cost(new_report, cost_store)
            await lifecycle.async_record_meal_cost(
                str(meal.get("id") or ""), meal_cost
            )
        leftover = await lifecycle.async_sync_leftover_from_meal(
            meal, cost=meal_cost
        )
        update_expiry_notification(bridge)
        state = await _food_state(bridge, history, limit=30)
        connection.send_result(
            msg["id"],
            {
                **state,
                "mealHistoryRecord": meal,
                "report": new_report,
                "restored": (revision or {}).get("restored"),
                "leftover": leftover,
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
