from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v11 as v11
from . import websocket_v14 as v14
from . import websocket_v15 as v15
from . import websocket_v20 as v20
from .barcode import (
    confident_match,
    lookup_open_food_facts,
    normalize_barcode,
    suggest_catalog_matches,
)
from .costs import cost_store_for_bridge
from .costing import lookup_open_prices_safe, store_best_open_price
from .inventory import inventory_identity
from .online_cache import online_cache_for_bridge
from .request_coordinator import request_coordinator

_MAX_GLOBAL_PRICE_LOOKUPS = 4


def _text(value: Any) -> str:
    return str(value or "").strip()


async def _cached_product(hass: HomeAssistant, bridge, barcode: str) -> dict[str, Any]:
    cache = await online_cache_for_bridge(bridge)
    code = normalize_barcode(barcode)

    async def fetch() -> dict[str, Any]:
        return await hass.async_add_executor_job(lookup_open_food_facts, code)

    result = await cache.async_get_or_revalidate(
        f"open_food_facts:{code}",
        fetch,
        source="open_food_facts",
    )
    product = dict(result.get("value") or {})
    product["onlineCache"] = {
        key: result.get(key)
        for key in ("cacheHit", "checkedOnline", "changed", "checkedAt", "updatedAt", "lastError")
    }
    return product


async def _cached_open_price(
    hass: HomeAssistant,
    bridge,
    barcode: str,
    *,
    currency: str,
    country: str,
) -> dict[str, Any]:
    cache = await online_cache_for_bridge(bridge)
    key = f"open_prices:{_text(barcode)}:{currency.upper()}:{country.upper()}"

    async def fetch() -> dict[str, Any]:
        return await hass.async_add_executor_job(
            lambda: lookup_open_prices_safe(
                _text(barcode), currency=currency, country=country
            )
        )

    result = await cache.async_get_or_revalidate(
        key,
        fetch,
        source="open_prices",
    )
    payload = dict(result.get("value") or {})
    payload["onlineCache"] = {
        name: result.get(name)
        for name in ("cacheHit", "checkedOnline", "changed", "checkedAt", "updatedAt", "lastError")
    }
    return payload


async def _hydrate_global_prices_cached(hass, bridge, cost_store, recipe: dict[str, Any]) -> int:
    settings = cost_store.settings
    if not settings.get("autoGlobalPrices"):
        return 0
    inventory = bridge.recipe_hub.profile.get("houseIngredients") or []
    wanted = {
        inventory_identity(row)
        for row in recipe.get("ingredients") or []
        if isinstance(row, dict)
    }
    barcodes: list[str] = []
    for row in inventory:
        if not isinstance(row, dict) or inventory_identity(row) not in wanted:
            continue
        for lot in row.get("lots") or []:
            if not isinstance(lot, dict):
                continue
            barcode = _text(lot.get("barcode"))
            if not barcode or barcode in barcodes:
                continue
            barcodes.append(barcode)
            if len(barcodes) >= _MAX_GLOBAL_PRICE_LOOKUPS:
                break
        if len(barcodes) >= _MAX_GLOBAL_PRICE_LOOKUPS:
            break

    stored = 0
    for barcode in barcodes:
        result = await _cached_open_price(
            hass,
            bridge,
            barcode,
            currency=_text(settings.get("currency")),
            country=_text(settings.get("country")),
        )
        if result.get("ok") and await store_best_open_price(
            cost_store,
            result,
            currency=_text(settings.get("currency")),
            country=_text(settings.get("country")),
        ):
            stored += 1
    return stored


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_barcode_scan,
        ws_barcode_map_add,
        ws_global_price_lookup,
        ws_recipe_cost,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v23/barcode_scan",
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
        mapping_store = await v15._store(bridge)
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "barcode_lookup",
            "Barcode product lookup",
            entry_ids=[bridge.entry.entry_id],
        ):
            known = mapping_store.get(code)
            product: dict[str, Any] = {}
            if known is not None and known.get("nutrition"):
                product = {"barcode": code, "nutrition": known.get("nutrition")}
            else:
                try:
                    product = await _cached_product(hass, bridge, code)
                except Exception as exc:
                    product = {
                        "barcode": code,
                        "found": False,
                        "source": "open_food_facts",
                        "lookupError": f"{type(exc).__name__}: {exc}",
                    }

            if known is not None and known.get("quantity") is not None:
                if not known.get("nutrition") and product.get("nutrition"):
                    known = await mapping_store.async_set(code, {
                        "ingredient": dict(known.get("ingredient") or {}),
                        "quantity": known.get("quantity"),
                        "unit": str(known.get("unit") or ""),
                        "productName": known.get("productName") or product.get("productName") or product.get("name"),
                        "brand": known.get("brand") or product.get("brand"),
                        "nutrition": product.get("nutrition"),
                    })
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
                    mapping = await mapping_store.async_set(code, {
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
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v23/barcode_map_add",
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
            mapping_store = await v15._store(bridge)
            try:
                product = await _cached_product(hass, bridge, code)
            except Exception:
                product = {}
            mapping = await mapping_store.async_set(code, {
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
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v23/global_price_lookup",
    vol.Optional("entry_id"): str,
    vol.Required("barcode"): str,
    vol.Optional("currency", default=""): str,
    vol.Optional("country", default=""): str,
})
@websocket_api.async_response
async def ws_global_price_lookup(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await cost_store_for_bridge(bridge)
        currency = _text(msg.get("currency")) or _text(store.settings.get("currency"))
        country = _text(msg.get("country")) or _text(store.settings.get("country"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "price_lookup",
            "Worldwide product price lookup",
            entry_ids=[bridge.entry.entry_id],
        ):
            result = await _cached_open_price(
                hass, bridge, _text(msg["barcode"]), currency=currency, country=country
            )
            stored = await store_best_open_price(
                store, result, currency=currency, country=country
            ) if result.get("ok") else None
            result["storedReference"] = stored
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v23/recipe_cost",
    vol.Optional("entry_id"): str,
    vol.Required("recipe"): dict,
    vol.Optional("refresh_global", default=False): bool,
})
@websocket_api.async_response
async def ws_recipe_cost(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"])
        store = await cost_store_for_bridge(bridge)
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "price_lookup",
            "Recipe cost references",
            entry_ids=[bridge.entry.entry_id],
        ):
            global_added = 0
            if bool(msg.get("refresh_global")) or store.settings.get("autoGlobalPrices"):
                global_added = await _hydrate_global_prices_cached(hass, bridge, store, recipe)
            result = v20._recipe_cost_with_store(bridge, recipe, store)
            result["globalReferencesAdded"] = global_added
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)
