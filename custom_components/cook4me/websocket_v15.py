from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v11 as v11
from . import websocket_v14 as v14
from .barcode import (
    Cook4MeBarcodeMappingStore,
    confident_match,
    lookup_open_food_facts,
    normalize_barcode,
    suggest_catalog_matches,
)
from .expiry import update_expiry_notification
from .nutrition import nutrition_store_for_bridge


async def _store(bridge) -> Cook4MeBarcodeMappingStore:
    store = getattr(bridge, "_barcode_mapping_store", None)
    if store is None:
        store = Cook4MeBarcodeMappingStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._barcode_mapping_store = store
    return store


async def _add_mapping_stock(
    bridge, mapping: dict[str, Any], *, best_before: str = ""
) -> dict[str, Any]:
    ingredient = mapping.get("ingredient") if isinstance(mapping.get("ingredient"), dict) else {}
    quantity = mapping.get("quantity")
    unit = str(mapping.get("unit") or "")
    if quantity is None:
        raise ValueError("This barcode mapping has no package amount; remap it with an amount")
    await bridge.recipe_hub.async_inventory_add(
        dict(ingredient),
        quantity=quantity,
        unit=unit,
        unlimited=False,
        best_before=best_before,
    )
    nutrition_store = await nutrition_store_for_bridge(bridge)
    await nutrition_store.async_add_stock_lot(
        dict(ingredient),
        quantity=quantity,
        unit=unit,
        best_before=best_before,
        nutrition=mapping.get("nutrition"),
        barcode=str(mapping.get("barcode") or ""),
        product_name=str(mapping.get("productName") or ""),
        brand=str(mapping.get("brand") or ""),
    )
    await nutrition_store.async_reconcile_inventory(
        bridge.recipe_hub.profile.get("houseIngredients") or []
    )
    update_expiry_notification(bridge)
    return v14._state(bridge)


async def _upgrade_known_nutrition(
    hass: HomeAssistant,
    store: Cook4MeBarcodeMappingStore,
    code: str,
    known: dict[str, Any],
) -> dict[str, Any]:
    """Backfill nutrition once for mappings created before nutrition support."""
    if known.get("nutrition"):
        return known
    try:
        product = await hass.async_add_executor_job(lookup_open_food_facts, code)
    except Exception:
        return known
    if not product.get("nutrition"):
        return known
    return await store.async_set(
        code,
        {
            "ingredient": dict(known.get("ingredient") or {}),
            "quantity": known.get("quantity"),
            "unit": str(known.get("unit") or ""),
            "productName": known.get("productName") or product.get("productName") or product.get("name"),
            "brand": known.get("brand") or product.get("brand"),
            "nutrition": product.get("nutrition"),
        },
    )


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_barcode_scan, ws_barcode_map_add):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v15/barcode_scan",
        vol.Optional("entry_id"): str,
        vol.Required("barcode"): str,
        vol.Optional("language"): str,
    }
)
@websocket_api.async_response
async def ws_barcode_scan(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        code = normalize_barcode(msg["barcode"])
        store = await _store(bridge)
        known = store.get(code)
        if known is not None and known.get("quantity") is not None:
            known = await _upgrade_known_nutrition(hass, store, code, known)
            state = await _add_mapping_stock(bridge, known)
            connection.send_result(
                msg["id"],
                {
                    "status": "added",
                    "barcode": code,
                    "knownMapping": True,
                    "mapping": known,
                    "nutritionCaptured": bool(known.get("nutrition")),
                    **state,
                },
            )
            return

        try:
            product = await hass.async_add_executor_job(lookup_open_food_facts, code)
        except Exception as exc:
            product = {
                "barcode": code,
                "found": False,
                "source": "open_food_facts",
                "lookupError": f"{type(exc).__name__}: {exc}",
            }

        language = str(msg.get("language") or v11._device_language(bridge))
        catalog = await v11._ingredient_catalog(hass, bridge, language, refresh=False)
        suggestions = suggest_catalog_matches(product, catalog.get("items") or [])
        confident = confident_match(suggestions)
        package_quantity = product.get("quantity")
        package_unit = str(product.get("unit") or "")

        if confident is not None and package_quantity is not None and package_unit:
            mapping = await store.async_set(
                code,
                {
                    "ingredient": confident["ingredient"],
                    "quantity": package_quantity,
                    "unit": package_unit,
                    "productName": product.get("productName") or product.get("name"),
                    "brand": product.get("brand"),
                    "nutrition": product.get("nutrition"),
                },
            )
            state = await _add_mapping_stock(bridge, mapping)
            connection.send_result(
                msg["id"],
                {
                    "status": "added",
                    "barcode": code,
                    "knownMapping": False,
                    "autoMapped": True,
                    "mapping": mapping,
                    "product": product,
                    "suggestions": suggestions,
                    "nutritionCaptured": bool(mapping.get("nutrition")),
                    **state,
                },
            )
            return

        connection.send_result(
            msg["id"],
            {
                "status": "needs_mapping",
                "barcode": code,
                "knownMapping": known is not None,
                "mapping": known,
                "product": product,
                "suggestions": suggestions,
                **v14._state(bridge),
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v15/barcode_map_add",
        vol.Optional("entry_id"): str,
        vol.Required("barcode"): str,
        vol.Required("ingredient"): dict,
        vol.Required("quantity"): vol.Any(int, float, str),
        vol.Optional("unit", default=""): str,
        vol.Optional("best_before", default=""): str,
        vol.Optional("product_name", default=""): str,
        vol.Optional("brand", default=""): str,
    }
)
@websocket_api.async_response
async def ws_barcode_map_add(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        code = normalize_barcode(msg["barcode"])
        store = await _store(bridge)
        product: dict[str, Any] = {}
        try:
            product = await hass.async_add_executor_job(lookup_open_food_facts, code)
        except Exception:
            product = {}
        mapping = await store.async_set(
            code,
            {
                "ingredient": dict(msg["ingredient"]),
                "quantity": msg.get("quantity"),
                "unit": str(msg.get("unit") or ""),
                "productName": str(msg.get("product_name") or product.get("productName") or ""),
                "brand": str(msg.get("brand") or product.get("brand") or ""),
                "nutrition": product.get("nutrition"),
            },
        )
        state = await _add_mapping_stock(
            bridge, mapping, best_before=str(msg.get("best_before") or "")
        )
        connection.send_result(
            msg["id"],
            {
                "status": "added",
                "barcode": code,
                "knownMapping": False,
                "mapping": mapping,
                "nutritionCaptured": bool(mapping.get("nutrition")),
                **state,
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
