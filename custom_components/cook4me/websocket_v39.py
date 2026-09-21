"""Stock dashboard totals and seven-day expiry view."""
from __future__ import annotations

from datetime import date
import math
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from . import websocket as legacy
from .automatic_prices import price_settings
from .costs import _cost_for_amount, cost_store_for_bridge
from .inventory import expiring_inventory_items, inventory_identity
from .nutrition import nutrition_for_amount, nutrition_store_for_bridge
from .storage_locations import normalize_locations
from .websocket_v32 import _authorized


_EXPIRY_WINDOW_DAYS = 7


def _stock_lots(inventory: Any):
    for row in inventory or []:
        if not isinstance(row, dict) or row.get("unlimited"):
            continue
        for lot in row.get("lots") or []:
            if isinstance(lot, dict) and lot.get("quantity") is not None:
                yield row, lot


def _round_totals(values: dict[str, float]) -> dict[str, float]:
    return {
        key: round(float(value), 1 if key in {"energyKcal", "energyKJ"} else 2)
        for key, value in values.items()
        if math.isfinite(float(value))
    }


def _stock_value(inventory, store, settings):
    totals: dict[str, float] = {}
    package_count = 0
    priced_count = 0
    exact_count = 0
    estimated_count = 0

    for row, lot in _stock_lots(inventory):
        package_count += 1
        unit = str(row.get("unit") or "")
        reference = None
        exact = False
        lot_id = str(lot.get("id") or "")
        if lot_id:
            reference = store.best_reference("lot:" + lot_id, unit=unit)
            exact = bool(
                reference
                and (
                    reference.get("source") == "purchase"
                    or reference.get("confidence") == "exact_purchase"
                )
            )

        if reference is None and lot.get("barcode"):
            reference = store.barcode_reference(
                str(lot.get("barcode")),
                currency=settings.get("currency", ""),
                country=settings.get("country", ""),
                unit=unit,
            )
        if reference is None:
            reference = store.best_reference(
                inventory_identity(row),
                currency=settings.get("currency", ""),
                country=settings.get("country", ""),
                unit=unit,
            )
        if reference is None:
            continue
        value = _cost_for_amount(reference, lot.get("quantity"), unit)
        currency = str(reference.get("currency") or "").upper()
        if value is None or not currency:
            continue
        totals[currency] = totals.get(currency, 0.0) + float(value)
        priced_count += 1
        if exact:
            exact_count += 1
        else:
            estimated_count += 1

    return {
        "totalsByCurrency": {
            currency: round(amount, 2) for currency, amount in totals.items()
        },
        "pricedPackages": priced_count,
        "exactPackages": exact_count,
        "estimatedPackages": estimated_count,
        "packageCount": package_count,
        "coverage": round(priced_count / package_count, 3) if package_count else 0.0,
    }


def _generic_profile(generic: dict[str, Any], identity: str):
    row = generic.get(identity) if isinstance(generic, dict) else None
    if isinstance(row, dict) and isinstance(row.get("nutrition"), dict):
        return row["nutrition"]
    return row


def _stock_nutrition(inventory, *, generic, stock_lots):
    exact_by_lot: dict[str, dict[str, Any]] = {}
    for rows in (stock_lots or {}).values():
        if not isinstance(rows, list):
            continue
        for record in rows:
            if not isinstance(record, dict):
                continue
            lot_id = str(record.get("inventoryLotId") or "")
            if lot_id and isinstance(record.get("nutrition"), dict):
                exact_by_lot[lot_id] = record["nutrition"]

    totals: dict[str, float] = {}
    package_count = 0
    covered_count = 0
    exact_count = 0
    generic_count = 0

    for row, lot in _stock_lots(inventory):
        package_count += 1
        identity = inventory_identity(row)
        lot_id = str(lot.get("id") or "")
        profile = exact_by_lot.get(lot_id)
        exact = profile is not None
        if profile is None:
            profile = _generic_profile(generic, identity)
        if profile is None:
            continue
        values = nutrition_for_amount(
            profile, lot.get("quantity"), str(row.get("unit") or "")
        )
        if not values:
            continue
        for key, value in values.items():
            totals[key] = totals.get(key, 0.0) + float(value)
        covered_count += 1
        if exact:
            exact_count += 1
        else:
            generic_count += 1

    return {
        "totals": _round_totals(totals),
        "coveredPackages": covered_count,
        "exactPackages": exact_count,
        "genericPackages": generic_count,
        "packageCount": package_count,
        "coverage": round(covered_count / package_count, 3) if package_count else 0.0,
    }


def _expiry_rows(profile: dict[str, Any], *, today: date):
    locations = {
        row["id"]: row
        for row in normalize_locations(profile.get("storageLocations"))
    }
    rows = []
    for item in expiring_inventory_items(
        profile.get("houseIngredients") or [],
        today=today,
        within_days=_EXPIRY_WINDOW_DAYS,
        include_past=True,
    ):
        location = locations.get(str(item.get("storageLocationId") or ""))
        rows.append(
            {
                "lotId": str(item.get("id") or ""),
                "identity": item.get("identity") or "",
                "ingredientName": item.get("name") or "",
                "productName": item.get("productName") or item.get("name") or "",
                "brand": item.get("brand") or "",
                "quantity": item.get("quantity"),
                "unit": item.get("unit") or "",
                "bestBefore": item.get("bestBefore") or "",
                "effectiveBestBefore": item.get("effectiveBestBefore") or "",
                "daysRemaining": int(item.get("daysRemaining") or 0),
                "pastBestBefore": bool(item.get("pastBestBefore")),
                "openedDrivenExpiry": bool(item.get("openedDrivenExpiry")),
                "storageLocationId": item.get("storageLocationId") or "",
                "storageName": location.get("name") if location else "",
                "storageKind": location.get("kind") if location else item.get("storage") or "",
            }
        )
    return rows[:100]


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v39/stock_summary",
        vol.Required("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_stock_summary(hass, connection, msg):
    try:
        bridge = _authorized(hass, connection, msg)
        profile = bridge.recipe_hub.profile
        inventory = profile.get("houseIngredients") or []
        cost_store = await cost_store_for_bridge(bridge)
        settings = await price_settings(bridge)
        nutrition_store = await nutrition_store_for_bridge(bridge)

        package_count = sum(1 for _row, _lot in _stock_lots(inventory))
        connection.send_result(
            msg["id"],
            {
                "ingredientCount": len(inventory),
                "packageCount": package_count,
                "unlimitedIngredientCount": sum(
                    1 for row in inventory if isinstance(row, dict) and row.get("unlimited")
                ),
                "value": _stock_value(inventory, cost_store, settings),
                "nutrition": _stock_nutrition(
                    inventory,
                    generic=nutrition_store.generic,
                    stock_lots=nutrition_store.stock_lots,
                ),
                "expiryWindowDays": _EXPIRY_WINDOW_DAYS,
                "expiring": _expiry_rows(profile, today=dt_util.now().date()),
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@callback
def async_register(hass):
    websocket_api.async_register_command(hass, ws_stock_summary)
