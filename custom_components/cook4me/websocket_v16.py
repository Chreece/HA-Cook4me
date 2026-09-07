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
    nutrition_store_for_bridge,
)
from .nutrition_fdc import lookup_food_data_central_strict
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .nutrition_resolution import nutrition_resolution_store_for_bridge

_FDC_OPTION = "fdc_api_key"
_MAX_UNRESOLVED_DETAILS = 80


def _api_key(bridge) -> tuple[str, bool]:
    options = dict(bridge.entry.options or {})
    value = str(options.get(_FDC_OPTION) or "").strip()
    return (value or DEMO_KEY, bool(value))


def _mode(custom: bool) -> str:
    return "custom" if custom else "demo"


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


def _catalog_identity_rows(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in catalog:
        if not isinstance(row, dict):
            continue
        ident = ingredient_identity(row)
        if not ident or ident in seen:
            continue
        seen.add(ident)
        rows.append(row)
    return rows


def _append_detail(details: list[dict[str, Any]], detail: dict[str, Any]) -> None:
    if len(details) < _MAX_UNRESOLVED_DETAILS:
        details.append(detail)


async def _catalog_status(hass: HomeAssistant, bridge) -> dict[str, Any]:
    nutrition_store = await nutrition_store_for_bridge(bridge)
    resolution_store = await nutrition_resolution_store_for_bridge(bridge)
    _key, custom = _api_key(bridge)
    mode = _mode(custom)
    result: dict[str, Any] = {
        "fdcApiKeyConfigured": custom,
        "fdcMode": mode,
        "cachedGenericCount": nutrition_store.generic_count,
        "resolutionFailureCount": resolution_store.failure_count,
    }
    try:
        catalog = _catalog_identity_rows(await _english_catalog(hass, bridge))
    except Exception:
        # Settings must remain usable even when the SEB ingredient catalog is
        # temporarily unavailable. Exact catalog progress is added when known.
        result["catalogCount"] = nutrition_store.generic_count
        return result

    identities = {ingredient_identity(row) for row in catalog}
    mapped = sum(1 for ident in identities if nutrition_store.get_generic(ident) is not None)
    blocked = resolution_store.active_count(identities, mode=mode)
    remaining = max(0, len(identities) - mapped)
    result.update(
        {
            "catalogCount": mapped,
            "catalogTotal": len(identities),
            "remaining": remaining,
            "blockedFailures": min(remaining, blocked),
            "actionableRemaining": max(0, remaining - blocked),
        }
    )
    return result


async def _resolve_missing(
    hass: HomeAssistant,
    bridge,
    ingredients: list[dict[str, Any]],
    *,
    requested_limit: int,
) -> dict[str, Any]:
    store = await nutrition_store_for_bridge(bridge)
    resolution_store = await nutrition_resolution_store_for_bridge(bridge)
    api_key, custom = _api_key(bridge)
    mode = _mode(custom)
    limit = max(0, min(int(requested_limit), 25 if custom else 3))
    resolved = 0
    attempted = 0
    failed = 0
    cached_failures = 0
    deferred = 0
    unresolved_count = 0
    unresolved: list[dict[str, Any]] = []

    for ingredient in ingredients:
        ident = ingredient_identity(ingredient)
        if not ident or store.get_generic(ident) is not None:
            continue

        query = await _english_name(hass, bridge, ingredient)
        cached = resolution_store.get_blocked(
            ident,
            query=query,
            mode=mode,
        )
        if cached is not None:
            cached_failures += 1
            unresolved_count += 1
            _append_detail(
                unresolved,
                {
                    "identity": ident,
                    "query": query,
                    "reason": "cached_failure",
                    "cachedReason": cached.get("reason"),
                    "confidence": cached.get("confidence"),
                    "retryAfter": cached.get("retryAt"),
                },
            )
            continue

        if not query:
            failed += 1
            unresolved_count += 1
            cached = await resolution_store.async_record_failure(
                ident,
                query="",
                mode=mode,
                reason="no_english_name",
            )
            _append_detail(
                unresolved,
                {
                    "identity": ident,
                    "reason": "no_english_name",
                    "retryAfter": cached.get("retryAt"),
                },
            )
            continue

        if attempted >= limit:
            deferred += 1
            continue

        attempted += 1
        result = await hass.async_add_executor_job(
            lookup_food_data_central_strict,
            query,
            api_key,
        )
        if not result.get("ok"):
            failed += 1
            unresolved_count += 1
            reason = str(result.get("reason") or "not_resolved")
            cached = await resolution_store.async_record_failure(
                ident,
                query=query,
                mode=mode,
                reason=reason,
                confidence=result.get("confidence"),
            )
            _append_detail(
                unresolved,
                {
                    "identity": ident,
                    "query": query,
                    "reason": reason,
                    "confidence": result.get("confidence"),
                    "runnerUpConfidence": result.get("runnerUpConfidence"),
                    "confidenceMargin": result.get("confidenceMargin"),
                    "retryAfter": cached.get("retryAt"),
                },
            )
            continue

        await store.async_set_generic(
            ident,
            ingredient,
            result["nutrition"],
            query=query,
            confidence=result.get("confidence"),
        )
        await resolution_store.async_clear(ident)
        resolved += 1

    return {
        "resolved": resolved,
        "attempted": attempted,
        "failed": failed,
        "cachedFailures": cached_failures,
        "deferred": deferred,
        "unresolved": unresolved,
        "unresolvedCount": unresolved_count,
        "unresolvedTruncated": max(0, unresolved_count - len(unresolved)),
        "customApiKey": custom,
        "mode": mode,
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
            "cachedGenericCount": store.generic_count,
            "resolvedNow": int(resolution.get("resolved") or 0),
            "resolution": resolution,
            "fdcApiKeyConfigured": custom,
            "fdcMode": _mode(custom),
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
        result = await _catalog_status(hass, bridge)
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
        resolution_store = await nutrition_resolution_store_for_bridge(bridge)
        cleared = await resolution_store.async_clear_transient()
        result = await _catalog_status(hass, bridge)
        result["clearedTransientFailures"] = cleared
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


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
        catalog = _catalog_identity_rows(await _english_catalog(hass, bridge))
        store = await nutrition_store_for_bridge(bridge)
        missing = [
            row
            for row in catalog
            if store.get_generic(ingredient_identity(row)) is None
        ]
        resolution = await _resolve_missing(
            hass,
            bridge,
            missing,
            requested_limit=int(msg.get("limit", 12)),
        )
        status = await _catalog_status(hass, bridge)
        result = {**resolution, **status}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
