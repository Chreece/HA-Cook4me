from __future__ import annotations

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v11 as v11
from . import websocket_v14 as v14
from . import websocket_v15 as v15
from . import websocket_v23 as v23
from .barcode import confident_match, normalize_barcode, suggest_catalog_matches
from .request_coordinator import request_coordinator


async def _refresh_known_mapping(store, code: str, known: dict, product: dict) -> dict:
    next_row = {
        "ingredient": dict(known.get("ingredient") or {}),
        "quantity": known.get("quantity"),
        "unit": str(known.get("unit") or ""),
        "productName": product.get("productName") or product.get("name") or known.get("productName"),
        "brand": product.get("brand") or known.get("brand"),
        "nutrition": product.get("nutrition") or known.get("nutrition"),
    }
    changed = any(
        next_row.get(key) != known.get(key)
        for key in ("productName", "brand", "nutrition")
    )
    return await store.async_set(code, next_row) if changed else known


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_barcode_scan, ws_barcode_map_add):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v26/barcode_scan",
    vol.Optional("entry_id"): str,
    vol.Required("barcode"): str,
    vol.Optional("language"): str,
    vol.Optional("best_before", default=""): str,
    vol.Optional("lot_metadata"): dict,
})
@websocket_api.async_response
async def ws_barcode_scan(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        code = normalize_barcode(msg["barcode"])
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "barcode_lookup",
            "Barcode product lookup",
            entry_ids=[bridge.entry.entry_id],
        ):
            store = await v15._store(bridge)
            known = store.get(code)
            try:
                # Exact-barcode metadata is always read through the persistent
                # online cache. The cache itself decides whether >=24h has
                # elapsed and therefore whether an upstream request is allowed.
                product = await v23._cached_product(hass, bridge, code)
            except Exception as exc:
                product = {
                    "barcode": code,
                    "found": False,
                    "source": "open_food_facts",
                    "lookupError": f"{type(exc).__name__}: {exc}",
                }

            if known is not None and known.get("quantity") is not None:
                known = await _refresh_known_mapping(store, code, known, product)
                state = await v15._add_mapping_stock(
                    bridge,
                    known,
                    best_before=str(msg.get("best_before") or ""),
                    lot_metadata=msg.get("lot_metadata"),
                )
                result = {
                    "status": "added",
                    "barcode": code,
                    "knownMapping": True,
                    "mapping": known,
                    "product": product,
                    "nutritionCaptured": bool(known.get("nutrition")),
                    **state,
                }
            else:
                language = str(msg.get("language") or v11._device_language(bridge))
                catalog = await v11._ingredient_catalog(hass, bridge, language, refresh=False)
                suggestions = suggest_catalog_matches(product, catalog.get("items") or [])
                confident = confident_match(suggestions)
                package_quantity = product.get("quantity")
                package_unit = str(product.get("unit") or "")
                if confident is not None and package_quantity is not None and package_unit:
                    mapping = await store.async_set(code, {
                        "ingredient": confident["ingredient"],
                        "quantity": package_quantity,
                        "unit": package_unit,
                        "productName": product.get("productName") or product.get("name"),
                        "brand": product.get("brand"),
                        "nutrition": product.get("nutrition"),
                    })
                    state = await v15._add_mapping_stock(
                        bridge,
                        mapping,
                        best_before=str(msg.get("best_before") or ""),
                        lot_metadata=msg.get("lot_metadata"),
                    )
                    result = {
                        "status": "added",
                        "barcode": code,
                        "knownMapping": False,
                        "autoMapped": True,
                        "mapping": mapping,
                        "product": product,
                        "suggestions": suggestions,
                        "nutritionCaptured": bool(mapping.get("nutrition")),
                        **state,
                    }
                else:
                    result = {
                        "status": "needs_mapping",
                        "barcode": code,
                        "knownMapping": known is not None,
                        "mapping": known,
                        "product": product,
                        "suggestions": suggestions,
                        **v14._state(bridge),
                    }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v26/barcode_map_add",
    vol.Optional("entry_id"): str,
    vol.Required("barcode"): str,
    vol.Required("ingredient"): dict,
    vol.Required("quantity"): vol.Any(int, float, str),
    vol.Optional("unit", default=""): str,
    vol.Optional("best_before", default=""): str,
    vol.Optional("product_name", default=""): str,
    vol.Optional("brand", default=""): str,
    vol.Optional("lot_metadata"): dict,
})
@websocket_api.async_response
async def ws_barcode_map_add(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        code = normalize_barcode(msg["barcode"])
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "barcode_lookup",
            "Barcode product mapping",
            entry_ids=[bridge.entry.entry_id],
        ):
            store = await v15._store(bridge)
            try:
                product = await v23._cached_product(hass, bridge, code)
            except Exception:
                product = {}
            mapping = await store.async_set(code, {
                "ingredient": dict(msg["ingredient"]),
                "quantity": msg.get("quantity"),
                "unit": str(msg.get("unit") or ""),
                "productName": str(msg.get("product_name") or product.get("productName") or ""),
                "brand": str(msg.get("brand") or product.get("brand") or ""),
                "nutrition": product.get("nutrition"),
            })
            state = await v15._add_mapping_stock(
                bridge,
                mapping,
                best_before=str(msg.get("best_before") or ""),
                lot_metadata=msg.get("lot_metadata"),
            )
            result = {
                "status": "added",
                "barcode": code,
                "knownMapping": False,
                "mapping": mapping,
                "product": product,
                "nutritionCaptured": bool(mapping.get("nutrition")),
                **state,
            }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
