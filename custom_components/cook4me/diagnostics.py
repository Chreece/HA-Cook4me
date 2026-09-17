"""Home Assistant diagnostics without credentials, device UUIDs or household data."""
from copy import deepcopy

from .const import DOMAIN, DATA_BRIDGES
from .delivery_diagnostics import device_snapshot


async def async_get_config_entry_diagnostics(hass, entry):
    bridge = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {}).get(entry.entry_id)
    return {
        'integrationBuild': '2026.9.17.12',
        'configuredLocale': {key: entry.data.get(key) for key in ('country', 'language', 'app_version')},
        'device': device_snapshot(bridge.data) if bridge else {},
        'lastRecipeInspected': deepcopy(getattr(bridge, '_last_inspected_recipe', None)),
        'lastRecipeDelivery': deepcopy(getattr(bridge, '_last_recipe_delivery', None)),
        'firmwareCompatibility': 'unknown',
    }
