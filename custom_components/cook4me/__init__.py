from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.helpers.typing import ConfigType
from homeassistant.exceptions import HomeAssistantError

from .bridge import Cook4MeBridge
from .const import DATA_BRIDGES, DOMAIN, PLATFORMS
from .panel import async_register_panel
from .websocket import async_register as async_register_websocket
from .websocket_v5 import async_register as async_register_websocket_v5
from .websocket_v7 import async_register as async_register_websocket_v7
from .websocket_v8 import async_register as async_register_websocket_v8
from .websocket_v9 import async_register as async_register_websocket_v9
from .websocket_v10 import async_register as async_register_websocket_v10

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


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    data = hass.data.setdefault(DOMAIN, {})
    data.setdefault(DATA_BRIDGES, {})

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
        return await bridge.async_search_recipes(
            call.data.get("query", ""),
            page=call.data.get("page", 0),
            size=call.data.get("size", 20),
            max_details=call.data.get("size", 20),
            refresh=call.data.get("refresh", False),
        )

    async def handle_recommend(call: ServiceCall) -> dict[str, Any]:
        bridge = _get_bridge(hass, call.data.get("entry_id"))
        return await bridge.async_recommend_recipes(
            limit=call.data.get("limit", 12), catalog_size=call.data.get("catalog_size", 18)
        )

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
    await async_register_panel(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    bridge = Cook4MeBridge(hass, entry)
    await bridge.async_start()
    entry.runtime_data = bridge
    hass.data.setdefault(DOMAIN, {}).setdefault(DATA_BRIDGES, {})[entry.entry_id] = bridge
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await entry.runtime_data.async_stop()
        hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {}).pop(entry.entry_id, None)
    return ok