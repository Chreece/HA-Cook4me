from __future__ import annotations

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import async_panel_exists
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_URL_BASE = "/cook4me_static"
_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v11"
_PANEL_MODULE = "cook4me-panel-v11.js"


async def async_register_panel(hass: HomeAssistant) -> None:
    if async_panel_exists(hass, DOMAIN):
        return
    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_URL_BASE, path=str(frontend_dir), cache_headers=False)]
    )
    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=DOMAIN,
        webcomponent_name=_PANEL_ELEMENT,
        module_url=f"{_URL_BASE}/{_PANEL_MODULE}?v=2026.9.6.13",
        sidebar_title="Cook4Me",
        sidebar_icon="mdi:pot-steam",
        embed_iframe=False,
        require_admin=False,
        handle_safe_area=True,
    )
