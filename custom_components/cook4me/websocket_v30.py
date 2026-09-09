from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v27 as v27
from . import websocket_v28 as v28
from . import websocket_v11 as v11
from .const import DATA_BRIDGES, DOMAIN
from .reference_catalog import bundled_reference_catalog
from .request_coordinator import request_coordinator
from .ui_state import ui_state_store_for_bridge


def _text(value: Any) -> str:
    return str(value or "").strip()


def _language(value: Any, fallback: str = "en") -> str:
    code = _text(value).lower().replace("_", "-").split("-", 1)[0]
    return code or fallback


def _minimal_profile(bridge) -> dict[str, Any]:
    profile = bridge.recipe_hub.profile
    return {
        key: deepcopy(profile.get(key))
        for key in ("diet", "allergies", "avoid", "preferences")
        if profile.get(key) not in (None, "")
    }


def _materialize_reference_recipe(raw: dict[str, Any], *, ui_language: str, source_language: str, device_language: str) -> dict[str, Any]:
    catalog = bundled_reference_catalog()
    row = deepcopy(raw)
    recipe_id = _text(row.get("id"))
    full = catalog.recipe(recipe_id, language=ui_language) or row
    display_variant = catalog.variant(recipe_id, language=source_language or ui_language, fallback_language=ui_language)
    send_variant = catalog.variant(recipe_id, language=device_language, fallback_language=source_language or ui_language)
    ingredients: list[dict[str, Any]] = []
    for raw_ingredient in full.get("ingredients") or []:
        if not isinstance(raw_ingredient, dict):
            continue
        ingredient_id = _text(raw_ingredient.get("id") or raw_ingredient.get("key") or raw_ingredient.get("foodKey"))
        ingredient = catalog.ingredient(ingredient_id, language=ui_language)
        item: dict[str, Any] = {
            "foodKey": ingredient_id,
            "key": ingredient_id,
            "foodName": _text((ingredient or {}).get("name") or (ingredient or {}).get("canonicalName") or ingredient_id),
        }
        item["name"] = item["foodName"]
        if raw_ingredient.get("quantity") not in (None, ""):
            item["quantity"] = raw_ingredient.get("quantity")
        if raw_ingredient.get("unit") not in (None, ""):
            item["unit"] = raw_ingredient.get("unit")
        ingredients.append(item)

    result: dict[str, Any] = {
        "id": recipe_id,
        "referenceRecipeId": recipe_id,
        "groupingFunctionalId": _text(full.get("groupingFunctionalId") or recipe_id),
        "title": _text(full.get("title") or full.get("canonicalName") or recipe_id),
        "canonicalName": _text(full.get("canonicalName")),
        "cover": full.get("cover"),
        "ingredients": ingredients,
        "nutrition": deepcopy(full.get("nutrition") or {}),
        "yield": deepcopy(full.get("yield")) if isinstance(full.get("yield"), dict) else {},
        "groupSize": full.get("servings"),
        "source": "bundled_reference_catalog",
        "referenceCatalogVersion": catalog.metadata.get("catalogVersion"),
        "language": _text((display_variant or {}).get("language") or source_language or ui_language),
        "market": _text((display_variant or {}).get("market")),
        "sendable": bool(send_variant and _text(send_variant.get("variantId"))),
    }
    if display_variant:
        variant_id = _text(display_variant.get("variantId"))
        if variant_id:
            result["searchVariantId"] = variant_id
            result["variantFunctionalId"] = _text(display_variant.get("recipeFunctionalId") or variant_id)
            result["recipeFunctionalId"] = result["variantFunctionalId"]
    if send_variant:
        send_id = _text(send_variant.get("variantId"))
        if send_id:
            result["sendVariantId"] = send_id
            result["sendRecipeFunctionalId"] = _text(send_variant.get("recipeFunctionalId") or send_id)
            result["sendGroupingFunctionalId"] = result["groupingFunctionalId"]
    return {key: value for key, value in result.items() if value not in (None, "")}


def reference_recipe_candidates(bridge, *, languages: list[str], query: str, ui_language: str, limit: int = 500) -> list[dict[str, Any]]:
    catalog = bundled_reference_catalog()
    if not catalog.metadata.get("recipeCount"):
        return []
    device_language = v11._device_language(bridge)
    rows = catalog.recipes(language=ui_language, query=query, source_languages=languages, limit=limit)
    out: list[dict[str, Any]] = []
    for row in rows:
        variants = [variant for variant in row.get("variants") or [] if isinstance(variant, dict)]
        available_languages = {_language(variant.get("language")) for variant in variants if _text(variant.get("language"))}
        for source_language in languages:
            if source_language not in available_languages:
                continue
            item = _materialize_reference_recipe(row, ui_language=ui_language, source_language=source_language, device_language=device_language)
            item["todayCatalogLanguage"] = source_language
            out.append(item)
    return out


async def _fast_seed(hass: HomeAssistant) -> dict[str, Any]:
    bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
    catalog = bundled_reference_catalog()
    entries: list[dict[str, Any]] = []
    per_entry: dict[str, dict[str, Any]] = {}
    for entry_id, bridge in bridges.items():
        state_store = await ui_state_store_for_bridge(bridge)
        entry = {
            "entry_id": entry_id,
            "title": bridge.entry.title,
            "connected": bool(bridge.available),
            "canAcceptRecipe": bool(bridge.can_accept_recipe),
            "loadedRecipe": v27._loaded_recipe_summary(bridge.loaded_recipe),
            "state": v27._state_summary(getattr(bridge, "data", None)),
            "profile": _minimal_profile(bridge),
        }
        entries.append(entry)
        per_entry[entry_id] = {
            "uiPreferences": deepcopy(bridge.recipe_hub.ui_preferences),
            "todayOptions": v28._today_options(bridge),
            "todayPlan": state_store.today_plan,
            "referenceCatalog": catalog.metadata,
        }
    return {
        "entries": entries,
        "perEntry": per_entry,
        "selectedEntryId": entries[0]["entry_id"] if entries else "",
        "fullOverviewCached": False,
        "serverSeedContract": "reference-shell-ui-v2",
        "referenceCatalog": catalog.metadata,
        "onlineRequests": 0,
    }


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_ui_seed, ws_reference_meta, ws_reference_ingredients, ws_reference_recipes, ws_progress_state):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v30/ui_seed"})
@websocket_api.async_response
async def ws_ui_seed(hass, connection, msg) -> None:
    try:
        result = await _fast_seed(hass)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v30/reference_meta"})
@callback
def ws_reference_meta(hass, connection, msg) -> None:
    try:
        result = bundled_reference_catalog().metadata
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/reference_ingredients",
    vol.Optional("language", default="en"): str,
    vol.Optional("query", default=""): str,
    vol.Optional("limit", default=5000): vol.All(vol.Coerce(int), vol.Range(min=1, max=5000)),
})
@callback
def ws_reference_ingredients(hass, connection, msg) -> None:
    try:
        catalog = bundled_reference_catalog()
        items = catalog.ingredients(language=_language(msg.get("language")), query=_text(msg.get("query")), limit=int(msg.get("limit", 5000)))
        result = {"items": items, "count": len(items), "referenceCatalog": catalog.metadata, "onlineRequests": 0}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v30/reference_recipes",
    vol.Optional("entry_id"): str,
    vol.Optional("language", default="en"): str,
    vol.Optional("languages", default=[]): [str],
    vol.Optional("query", default=""): str,
    vol.Optional("limit", default=100): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
})
@callback
def ws_reference_recipes(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        selected = [_language(value) for value in msg.get("languages") or [] if _text(value)]
        if not selected:
            selected = [v11._device_language(bridge)]
        items = reference_recipe_candidates(bridge, languages=selected, query=_text(msg.get("query")), ui_language=_language(msg.get("language")), limit=int(msg.get("limit", 100)))
        catalog = bundled_reference_catalog()
        result = {"items": items, "count": len(items), "languages": selected, "referenceCatalog": catalog.metadata, "onlineRequests": 0}
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v30/progress_state"})
@websocket_api.async_response
async def ws_progress_state(hass, connection, msg) -> None:
    try:
        coordinator = await request_coordinator(hass)
        result = coordinator.snapshot
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
