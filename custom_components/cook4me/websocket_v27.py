from __future__ import annotations

from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DATA_BRIDGES, DOMAIN

# First-paint data is intentionally tiny. Do not add profile, recipes, history,
# inventory, habits, nutrition, book state, catalog data, prices or AI metadata
# here. Those belong to explicit, user-activated section loaders.
_BOOTSTRAP_STATE_KEYS = (
    "phase",
    "status",
    "recipeTitle",
    "currentInstruction",
)


def _state_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        key: value[key]
        for key in _BOOTSTRAP_STATE_KEYS
        if key in value and value[key] is not None
    }


def _loaded_recipe_summary(value: Any) -> dict[str, str] | None:
    if isinstance(value, dict):
        title = str(value.get("title") or value.get("name") or "").strip()
    else:
        title = str(value or "").strip()
    return {"title": title[:300]} if title else None


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_bootstrap)


@websocket_api.websocket_command(
    {websocket_api.vol.Required("type"): "cook4me/v27/bootstrap"}
)
@callback
def ws_bootstrap(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
    entries: list[dict[str, Any]] = []
    for entry_id, bridge in bridges.items():
        entries.append(
            {
                "entry_id": entry_id,
                "title": bridge.entry.title,
                "connected": bool(bridge.available),
                "canAcceptRecipe": bool(bridge.can_accept_recipe),
                "loadedRecipe": _loaded_recipe_summary(bridge.loaded_recipe),
                "state": _state_summary(getattr(bridge, "data", None)),
            }
        )
    connection.send_result(
        msg["id"],
        {
            "entries": entries,
            "bootstrapContract": "minimal-device-header-v1",
        },
    )
