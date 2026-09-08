from __future__ import annotations

from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import async_panel_exists
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .websocket_v20 import async_register as async_register_websocket_v20
from .websocket_v21 import async_register as async_register_websocket_v21
from .websocket_v22 import async_register as async_register_websocket_v22
from .websocket_v23 import async_register as async_register_websocket_v23
from .websocket_v24 import async_register as async_register_websocket_v24

_URL_BASE = "/cook4me_static"
_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v49"
_PANEL_MODULE = "cook4me-panel-v49.js"
_V20_REGISTERED = "websocket_v20_registered"
_V21_REGISTERED = "websocket_v21_registered"
_V22_REGISTERED = "websocket_v22_registered"
_V23_REGISTERED = "websocket_v23_registered"
_V24_REGISTERED = "websocket_v24_registered"


async def async_register_panel(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get(_V20_REGISTERED):
        async_register_websocket_v20(hass)
        domain_data[_V20_REGISTERED] = True
    if not domain_data.get(_V21_REGISTERED):
        async_register_websocket_v21(hass)
        domain_data[_V21_REGISTERED] = True
    if not domain_data.get(_V22_REGISTERED):
        async_register_websocket_v22(hass)
        domain_data[_V22_REGISTERED] = True
    if not domain_data.get(_V23_REGISTERED):
        async_register_websocket_v23(hass)
        domain_data[_V23_REGISTERED] = True
    if not domain_data.get(_V24_REGISTERED):
        async_register_websocket_v24(hass)
        domain_data[_V24_REGISTERED] = True
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
        module_url=f"{_URL_BASE}/{_PANEL_MODULE}?v=2026.9.8.5",
        sidebar_title="Cook4Me",
        sidebar_icon="mdi:pot-steam",
        embed_iframe=False,
        require_admin=False,
        handle_safe_area=True,
    )
