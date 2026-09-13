from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import HomeAssistantError

from . import websocket_v10 as recipe_search_api
from .bridge import Cook4MeBridge
from .const import (
    CONF_LANGUAGE,
    DATA_BRIDGES,
    DEFAULT_LANGUAGE,
    DOMAIN,
    PLATFORMS,
)
from .expiry import (
    dismiss_expiry_notification,
    register_daily_expiry_check,
    update_expiry_notification,
)
from .panel import async_register_panel
from .release_catalog import async_warm_release_catalog
from .websocket import async_register as async_register_websocket
from .websocket_v5 import async_register as async_register_websocket_v5
from .websocket_v7 import async_register as async_register_websocket_v7
from .websocket_v8 import async_register as async_register_websocket_v8
from .websocket_v9 import async_register as async_register_websocket_v9
from .websocket_v10 import async_register as async_register_websocket_v10
from .websocket_v11 import async_register as async_register_websocket_v11
from .websocket_v12 import async_register as async_register_websocket_v12
from .websocket_v13 import async_register as async_register_websocket_v13
from .websocket_v14 import async_register as async_register_websocket_v14
from .websocket_v15 import async_register as async_register_websocket_v15
from .websocket_v16 import async_register as async_register_websocket_v16
from .websocket_v17 import async_register as async_register_websocket_v17
from .websocket_v18 import async_register as async_register_websocket_v18

SERVICE_SEND_RECIPE = "send_recipe"
SERVICE_SEARCH_RECIPES = "search_recipes"
SERVICE_RECOMMEND_RECIPES = "recommend_recipes"


def _get_bridge(hass: HomeAssistant, entry_id: str | None) -> Cook4MeBridge:
    bridges: dict[str, Cook4MeBridge] = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
    if entry_id:
        bridge = bridges.get(entry_id)
        if bridge is None:
            raise HomeAssistantError("Cook4Me config entry not found or not loaded")
        return bridge
    if len(bridges) == 1:
        return next(iter(bridges.values()))
    if not bridges:
        raise HomeAssistantError("No Cook4Me config entry is loaded")
    raise HomeAssistantError("entry_id is required when more than one Cook4Me is configured")


def _consumption_notification_id(entry_id: str) -> str:
    return f"cook4me_consumption_{entry_id}"


def _format_recipe_amount(row: dict[str, Any]) -> str:
    quantity = row.get("quantity")
    if quantity is None:
        return "amount not provided by recipe"
    try:
        number = float(quantity)
        shown = str(int(number)) if number.is_integer() else f"{number:g}"
    except (TypeError, ValueError):
        shown = str(quantity)
    unit = str(row.get("unit") or "").strip()
    return f"{shown} {unit}".strip()


async def _handle_recipe_completed(bridge: Cook4MeBridge) -> None:
    """Create a stock-consumption confirmation only for an explicit done phase."""
    variant = str(bridge.data.get("variantFunctionalId") or "").strip()
    recipe: dict[str, Any] | None = None
    if variant:
        cached = bridge._recipe_cache.get(variant)
        if isinstance(cached, dict):
            recipe = dict(cached)
        else:
            try:
                recipe = await bridge.async_recipe_detail(variant)
            except Exception:
                recipe = None

    if recipe is None:
        recipe = {
            "title": bridge.data.get("recipeTitle"),
            "groupingFunctionalId": bridge.data.get("groupingFunctionalId")
            or bridge.data.get("recipeFunctionalId"),
            "variantFunctionalId": bridge.data.get("variantFunctionalId"),
            "recipeFunctionalId": bridge.data.get("variantFunctionalId"),
            "ingredients": bridge.data.get("recipeIngredients") or [],
        }
    else:
        recipe.setdefault("title", bridge.data.get("recipeTitle"))
        recipe.setdefault("variantFunctionalId", variant)

    pending = await bridge.recipe_hub.async_prepare_consumption(recipe)
    if not pending:
        return

    lines = []
    for row in pending.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        suffix = "∞ stock; no deduction" if row.get("stockUnlimited") else _format_recipe_amount(row)
        lines.append(f"- {row.get('name')}: {suffix}")
    message = (
        f"**{pending.get('recipeTitle') or 'Cook4Me recipe'} finished successfully.**\n\n"
        "Confirm the stock consumed in **Cook4Me → House ingredients & diet**. "
        "Each tracked ingredient defaults to **Yes** and the amount required by the recipe; "
        "you can edit every amount before confirming.\n\n"
        + "\n".join(lines[:30])
        + "\n\n[Open Cook4Me](/cook4me)"
    )
    persistent_notification.async_create(
        bridge.hass,
        message,
        title="Cook4Me · Confirm consumed ingredients",
        notification_id=_consumption_notification_id(bridge.entry.entry_id),
    )


def _register_completion_listener(bridge: Cook4MeBridge) -> None:
    """Watch live state transitions without treating startup state as completion."""
    state = {
        "phase": str(bridge.data.get("phase") or ""),
        "active": bool(bridge.data.get("active")),
        "session": 0,
        "completed_session": None,
    }

    def listener() -> None:
        phase = str(bridge.data.get("phase") or "")
        active = bool(bridge.data.get("active"))
        if active and not state["active"]:
            state["session"] += 1
            state["completed_session"] = None
        if (
            phase == "done"
            and state["phase"] != "done"
            and state["completed_session"] != state["session"]
        ):
            state["completed_session"] = state["session"]
            bridge.hass.async_create_task(_handle_recipe_completed(bridge))
        state["phase"] = phase
        state["active"] = active

    bridge._completion_listener_unsub = bridge.async_add_listener(listener)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    data = hass.data.setdefault(DOMAIN, {})
    data.setdefault(DATA_BRIDGES, {})

    # A complete release catalog can contain thousands of recipes and nutrient
    # profiles. Parse it once in HA's executor during integration setup so the
    # first panel/search request never pays a synchronous JSON parse on the
    # event loop. load_release_catalog() is LRU-cached after this warm-up.
    await async_warm_release_catalog(hass)

    async def handle_send_recipe(call: ServiceCall) -> dict[str, Any] | None:
        bridge = _get_bridge(hass, call.data.get("entry_id"))
        grouping = call.data.get("grouping_functional_id") or call.data.get("functional_id")
        recipe = call.data.get("recipe_functional_id")
        variant = call.data.get("variant_id")
        if grouping:
            recipe = recipe or variant
            if not recipe:
                raise HomeAssistantError("recipe_functional_id (or legacy variant_id) is required")
            result = await bridge.async_send_recipe(str(grouping), str(recipe))
        elif variant:
            result = await bridge.async_send_variant(str(variant))
        else:
            raise HomeAssistantError("Provide variant_id, or grouping_functional_id + recipe_functional_id")
        return result if call.return_response else None

    async def handle_search(call: ServiceCall) -> dict[str, Any]:
        bridge = _get_bridge(hass, call.data.get("entry_id"))
        language = str(
            bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE
        ).lower()
        # Public HA services use the same release-catalog-first contract as the
        # dashboard and planners. `refresh` remains the explicit live-SEB path.
        return await recipe_search_api._search_with_diagnostic(
            hass,
            bridge,
            query=str(call.data.get("query", "") or "").strip(),
            page=int(call.data.get("page", 0)),
            size=int(call.data.get("size", 20)),
            language=language,
            strict_language=True,
            refresh=bool(call.data.get("refresh", False)),
        )

    async def handle_recommend(call: ServiceCall) -> dict[str, Any]:
        bridge = _get_bridge(hass, call.data.get("entry_id"))
        language = str(
            bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE
        ).lower()
        catalog_size = max(
            int(call.data.get("limit", 12)),
            min(int(call.data.get("catalog_size", 18)), 50),
        )
        search = await recipe_search_api._search_with_diagnostic(
            hass,
            bridge,
            query="",
            page=0,
            size=catalog_size,
            language=language,
            strict_language=True,
            refresh=False,
        )
        if not search.get("ok", True):
            return search
        limit = max(1, min(int(call.data.get("limit", 12)), 30))
        ranked = bridge.recipe_hub.rank(search.get("items") or [], limit=limit)
        for item in ranked:
            item["deviceCanAccept"] = bridge.can_accept_recipe
        return {
            **{key: value for key, value in search.items() if key != "items"},
            "items": ranked,
            "profile": bridge.recipe_hub.profile,
            "deviceCanAccept": bridge.can_accept_recipe,
            "loadedRecipe": bridge.loaded_recipe,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_RECIPE,
        handle_send_recipe,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): str,
                vol.Optional("variant_id"): str,
                vol.Optional("grouping_functional_id"): str,
                vol.Optional("recipe_functional_id"): str,
                vol.Optional("functional_id"): str,
            }
        ),
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEARCH_RECIPES,
        handle_search,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): str,
                vol.Optional("query", default=""): str,
                vol.Optional("page", default=0): vol.All(vol.Coerce(int), vol.Range(min=0)),
                vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
                vol.Optional("refresh", default=False): bool,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RECOMMEND_RECIPES,
        handle_recommend,
        schema=vol.Schema(
            {
                vol.Optional("entry_id"): str,
                vol.Optional("limit", default=12): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
                vol.Optional("catalog_size", default=18): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )

    async_register_websocket(hass)
    async_register_websocket_v5(hass)
    async_register_websocket_v7(hass)
    async_register_websocket_v8(hass)
    async_register_websocket_v9(hass)
    async_register_websocket_v10(hass)
    async_register_websocket_v11(hass)
    async_register_websocket_v12(hass)
    async_register_websocket_v13(hass)
    async_register_websocket_v14(hass)
    async_register_websocket_v15(hass)
    async_register_websocket_v16(hass)
    async_register_websocket_v17(hass)
    async_register_websocket_v18(hass)
    await async_register_panel(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    bridge = Cook4MeBridge(hass, entry)
    await bridge.async_start()
    entry.runtime_data = bridge
    hass.data.setdefault(DOMAIN, {}).setdefault(DATA_BRIDGES, {})[entry.entry_id] = bridge
    _register_completion_listener(bridge)
    update_expiry_notification(bridge)
    bridge._expiry_listener_unsub = register_daily_expiry_check(bridge)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        completion_unsub = getattr(entry.runtime_data, "_completion_listener_unsub", None)
        if callable(completion_unsub):
            completion_unsub()
        expiry_unsub = getattr(entry.runtime_data, "_expiry_listener_unsub", None)
        if callable(expiry_unsub):
            expiry_unsub()
        dismiss_expiry_notification(entry.runtime_data)
        await entry.runtime_data.async_stop()
        hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {}).pop(entry.entry_id, None)
    return ok
