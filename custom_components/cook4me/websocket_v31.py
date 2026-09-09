from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v23 as v23
from .costing import calculate_recipe_cost, lookup_open_prices_safe, store_best_open_price
from .costs import cost_store_for_bridge
from .inventory import inventory_identity
from .online_cache import online_cache_for_bridge
from .operation_progress import publish_operation_progress
from .recipe_cost_cache import recipe_cost_cache_for_bridge
from .request_coordinator import request_coordinator

_MAX_GLOBAL_PRICE_LOOKUPS = 4


def _text(value: Any) -> str:
    return str(value or "").strip()


def _relevant_barcodes(bridge: Any, recipe: dict[str, Any]) -> list[str]:
    wanted = {
        inventory_identity(row)
        for row in recipe.get("ingredients") or []
        if isinstance(row, dict)
    }
    out: list[str] = []
    for row in bridge.recipe_hub.profile.get("houseIngredients") or []:
        if not isinstance(row, dict) or inventory_identity(row) not in wanted:
            continue
        for lot in row.get("lots") or []:
            if not isinstance(lot, dict):
                continue
            barcode = _text(lot.get("barcode"))
            if not barcode or barcode in out:
                continue
            out.append(barcode)
            if len(out) >= _MAX_GLOBAL_PRICE_LOOKUPS:
                return out
    return out


async def _force_global_prices(
    hass: HomeAssistant,
    bridge: Any,
    cost_store: Any,
    recipe: dict[str, Any],
    operation_id: str,
) -> int:
    """Force an upstream Open Prices check for relevant known barcodes.

    Unlike automatic price maintenance this intentionally bypasses the 24-hour
    online-cache revalidation throttle because the user explicitly requested a
    refresh. The newly fetched result is still recorded in the shared online
    cache so later automatic checks remain cheap.
    """
    barcodes = _relevant_barcodes(bridge, recipe)
    if not barcodes:
        return 0
    settings = cost_store.settings
    currency = _text(settings.get("currency"))
    country = _text(settings.get("country"))
    cache = await online_cache_for_bridge(bridge)
    stored = 0
    total = len(barcodes)

    coordinator = await request_coordinator(hass)
    async with coordinator.operation(
        "price_lookup",
        "Forced recipe price refresh",
        entry_ids=[bridge.entry.entry_id],
    ):
        for index, barcode in enumerate(barcodes, start=1):
            publish_operation_progress(
                hass,
                operation_id,
                phase="pricing",
                message=f"Refreshing product price {index}/{total}",
                completed=index - 1,
                total=total,
            )

            def fetch() -> dict[str, Any]:
                return lookup_open_prices_safe(
                    barcode,
                    currency=currency,
                    country=country,
                )

            result = await hass.async_add_executor_job(fetch)
            cache_key = f"open_prices:{barcode}:{currency.upper()}:{country.upper()}"
            await cache.async_record(cache_key, result, source="open_prices")
            if result.get("ok"):
                reference = await store_best_open_price(
                    cost_store,
                    result,
                    currency=currency,
                    country=country,
                )
                if reference is not None:
                    stored += 1
            publish_operation_progress(
                hass,
                operation_id,
                phase="pricing",
                message=f"Refreshed product price {index}/{total}",
                completed=index,
                total=total,
            )
    return stored


async def _calculate_and_cache(
    bridge: Any,
    recipe: dict[str, Any],
    cost_store: Any,
    *,
    global_added: int = 0,
    forced: bool = False,
) -> dict[str, Any]:
    inventory = bridge.recipe_hub.profile.get("houseIngredients") or []
    cost_cache = await recipe_cost_cache_for_bridge(bridge)
    value = calculate_recipe_cost(recipe, inventory, cost_store)
    result = await cost_cache.async_set(recipe, inventory, cost_store, value)
    result["globalReferencesAdded"] = int(global_added)
    result["forcedGlobalRefresh"] = bool(forced)
    return result


async def _recipe_cost_cached(
    hass: HomeAssistant,
    bridge: Any,
    recipe: dict[str, Any],
    operation_id: str,
) -> dict[str, Any]:
    cost_store = await cost_store_for_bridge(bridge)
    inventory = bridge.recipe_hub.profile.get("houseIngredients") or []
    cost_cache = await recipe_cost_cache_for_bridge(bridge)
    cached = cost_cache.get(recipe, inventory, cost_store)
    if cached is not None:
        cached["globalReferencesAdded"] = 0
        cached["forcedGlobalRefresh"] = False
        return cached

    global_added = 0
    if cost_store.settings.get("autoGlobalPrices"):
        publish_operation_progress(
            hass,
            operation_id,
            phase="pricing",
            message="Checking cached product prices",
        )
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "price_lookup",
            "Recipe cost references",
            entry_ids=[bridge.entry.entry_id],
        ):
            global_added = await v23._hydrate_global_prices_cached(
                hass,
                bridge,
                cost_store,
                recipe,
            )
        # A relevant price observation may have changed the fingerprint. If the
        # previously calculated cost now matches the updated evidence, reuse it.
        cached = cost_cache.get(recipe, inventory, cost_store)
        if cached is not None:
            cached["globalReferencesAdded"] = global_added
            cached["forcedGlobalRefresh"] = False
            return cached

    return await _calculate_and_cache(
        bridge,
        recipe,
        cost_store,
        global_added=global_added,
        forced=False,
    )


async def _forced_recipe_cost(
    hass: HomeAssistant,
    bridge: Any,
    recipe: dict[str, Any],
    operation_id: str,
) -> dict[str, Any]:
    cost_store = await cost_store_for_bridge(bridge)
    global_added = await _force_global_prices(
        hass,
        bridge,
        cost_store,
        recipe,
        operation_id,
    )
    return await _calculate_and_cache(
        bridge,
        recipe,
        cost_store,
        global_added=global_added,
        forced=True,
    )


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_recipe_cost)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v31/recipe_cost",
    vol.Optional("entry_id"): str,
    vol.Required("recipe"): dict,
    vol.Optional("refresh_global", default=False): bool,
    vol.Optional("client_operation_id", default=""): str,
})
@websocket_api.async_response
async def ws_recipe_cost(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    operation_id = _text(msg.get("client_operation_id"))
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"])
        if bool(msg.get("refresh_global")):
            result = await _forced_recipe_cost(
                hass,
                bridge,
                recipe,
                operation_id,
            )
        else:
            result = await _recipe_cost_cached(
                hass,
                bridge,
                recipe,
                operation_id,
            )
        publish_operation_progress(
            hass,
            operation_id,
            phase="done",
            message="Recipe cost ready",
            completed=1,
            total=1,
            done=True,
        )
    except Exception as exc:
        publish_operation_progress(
            hass,
            operation_id,
            phase="error",
            message="Recipe cost failed",
            done=True,
            error=str(exc),
        )
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
