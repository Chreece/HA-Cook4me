from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v11 as v11
from .nutrition import (
    DEMO_KEY,
    ingredient_identity,
    lookup_food_data_central,
    nutrition_store_for_bridge,
)
from .nutrition_fefo import calculate_recipe_nutrition_fefo

_FDC_OPTION = "fdc_api_key"


def _api_key(bridge) -> tuple[str, bool]:
    options = dict(bridge.entry.options or {})
    value = str(options.get(_FDC_OPTION) or "").strip()
    return (value or DEMO_KEY, bool(value))


async def _english_catalog(hass: HomeAssistant, bridge) -> list[dict[str, Any]]:
    cached = getattr(bridge, "_nutrition_english_catalog", None)
    if isinstance(cached, list) and cached:
        return cached
    result = await v11._ingredient_catalog(hass, bridge, "en", refresh=False)
    rows = [row for row in result.get("items") or [] if isinstance(row, dict)]
    bridge._nutrition_english_catalog = rows
    return rows


async def _english_name(hass: HomeAssistant, bridge, ingredient: dict[str, Any]) -> str:
    key = str(ingredient.get("foodKey") or ingredient.get("key") or "").strip()
    if key:
        for row in await _english_catalog(hass, bridge):
            if str(row.get("key") or "") == key and str(row.get("name") or "").strip():
                return str(row["name"]).strip()
    return str(ingredient.get("foodName") or ingredient.get("name") or "").strip()


def _recipe_ingredients(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in recipe.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        ident = ingredient_identity(row)
        if not ident or ident in seen:
            continue
        seen.add(ident)
        out.append(row)
    return out


async def _resolve_missing(
    hass: HomeAssistant,
    bridge,
    ingredients: list[dict[str, Any]],
    *,
    requested_limit: int,
) -> dict[str, Any]:
    store = await nutrition_store_for_bridge(bridge)
    api_key, custom = _api_key(bridge)
    limit = max(0, min(int(requested_limit), 25 if custom else 3))
    resolved = 0
    attempted = 0
    unresolved: list[dict[str, Any]] = []
    for ingredient in ingredients:
        ident = ingredient_identity(ingredient)
        if not ident or store.get_generic(ident) is not None:
            continue
        if attempted >= limit:
            unresolved.append({"identity": ident, "reason": "resolution_limit"})
            continue
        query = await _english_name(hass, bridge, ingredient)
        if not query:
            unresolved.append({"identity": ident, "reason": "no_english_name"})
            continue
        attempted += 1
        result = await hass.async_add_executor_job(
            lookup_food_data_central,
            query,
            api_key,
        )
        if not result.get("ok"):
            unresolved.append(
                {
                    "identity": ident,
                    "query": query,
                    "reason": result.get("reason") or "not_resolved",
                    "confidence": result.get("confidence"),
                }
            )
            continue
        await store.async_set_generic(
            ident,
            ingredient,
            result["nutrition"],
            query=query,
            confidence=result.get("confidence"),
        )
        resolved += 1
    return {
        "resolved": resolved,
        "attempted": attempted,
        "unresolved": unresolved,
        "customApiKey": custom,
        "mode": "custom" if custom else "demo",
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_nutrition_recipe,
        ws_nutrition_settings,
        ws_nutrition_settings_set,
        ws_nutrition_catalog_fill,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v16/nutrition_recipe",
        vol.Optional("entry_id"): str,
        vol.Required("recipe"): dict,
        vol.Optional("resolve_missing", default=True): bool,
        vol.Optional("max_resolve", default=8): vol.All(vol.Coerce(int), vol.Range(min=0, max=25)),
    }
)
@websocket_api.async_response
async def ws_nutrition_recipe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"])
        store = await nutrition_store_for_bridge(bridge)
        resolution = {"resolved": 0, "attempted": 0, "unresolved": []}
        if bool(msg.get("resolve_missing", True)):
            resolution = await _resolve_missing(
                hass,
                bridge,
                _recipe_ingredients(recipe),
                requested_limit=int(msg.get("max_resolve", 8)),
            )
        nutrition = calculate_recipe_nutrition_fefo(
            recipe,
            bridge.recipe_hub.profile.get("houseIngredients") or [],
            generic=store.generic,
            stock_lots=store.stock_lots,
        )
        _key, custom = _api_key(bridge)
        result = {
            "nutrition": nutrition,
            "catalogCount": store.generic_count,
            "resolvedNow": int(resolution.get("resolved") or 0),
            "resolution": resolution,
            "fdcApiKeyConfigured": custom,
            "fdcMode": "custom" if custom else "demo",
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v16/nutrition_settings",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_nutrition_settings(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        _key, custom = _api_key(bridge)
        store = await nutrition_store_for_bridge(bridge)
        result = {
            "fdcApiKeyConfigured": custom,
            "fdcMode": "custom" if custom else "demo",
            "catalogCount": store.generic_count,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v16/nutrition_settings_set",
        vol.Optional("entry_id"): str,
        vol.Optional("api_key", default=""): str,
    }
)
@websocket_api.async_response
async def ws_nutrition_settings_set(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        api_key = str(msg.get("api_key") or "").strip()
        options = dict(bridge.entry.options or {})
        if api_key:
            options[_FDC_OPTION] = api_key
        else:
            options.pop(_FDC_OPTION, None)
        hass.config_entries.async_update_entry(bridge.entry, options=options)
        store = await nutrition_store_for_bridge(bridge)
        connection.send_result(
            msg["id"],
            {
                "fdcApiKeyConfigured": bool(api_key),
                "fdcMode": "custom" if api_key else "demo",
                "catalogCount": store.generic_count,
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v16/nutrition_catalog_fill",
        vol.Optional("entry_id"): str,
        vol.Optional("limit", default=12): vol.All(vol.Coerce(int), vol.Range(min=1, max=25)),
    }
)
@websocket_api.async_response
async def ws_nutrition_catalog_fill(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        catalog = await _english_catalog(hass, bridge)
        store = await nutrition_store_for_bridge(bridge)
        missing = [
            row
            for row in catalog
            if ingredient_identity(row) and store.get_generic(ingredient_identity(row)) is None
        ]
        resolution = await _resolve_missing(
            hass,
            bridge,
            missing,
            requested_limit=int(msg.get("limit", 12)),
        )
        remaining = max(0, len(catalog) - store.generic_count)
        result = {
            **resolution,
            "catalogCount": store.generic_count,
            "catalogTotal": len(catalog),
            "remaining": remaining,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
