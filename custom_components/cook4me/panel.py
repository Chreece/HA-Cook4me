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
from .websocket_v25 import async_register as async_register_websocket_v25
from .websocket_v26 import async_register as async_register_websocket_v26
from .websocket_v27 import async_register as async_register_websocket_v27
from .websocket_v28 import async_register as async_register_websocket_v28
from .websocket_v29 import async_register as async_register_websocket_v29
from .websocket_v30 import async_register as async_register_websocket_v30
from .websocket_v31 import async_register as async_register_websocket_v31
from .websocket_v32 import async_register as async_register_websocket_v32
from .websocket_v33 import async_register as async_register_websocket_v33
from .websocket_v34 import async_register as async_register_websocket_v34
from .websocket_v35 import async_register as async_register_websocket_v35
from .websocket_v36 import async_register as async_register_websocket_v36
from .websocket_v37 import async_register as async_register_websocket_v37
from .websocket_v38 import async_register as async_register_websocket_v38
from .websocket_v39 import async_register as async_register_websocket_v39

_URL_BASE = "/cook4me_static/2026.9.22.7"
_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180"
_PANEL_MODULE = "cook4me-panel-v180.js"
_V20_REGISTERED = "websocket_v20_registered"
_V21_REGISTERED = "websocket_v21_registered"
_V22_REGISTERED = "websocket_v22_registered"
_V23_REGISTERED = "websocket_v23_registered"
_V24_REGISTERED = "websocket_v24_registered"
_V25_REGISTERED = "websocket_v25_registered"
_V26_REGISTERED = "websocket_v26_registered"
_V27_REGISTERED = "websocket_v27_registered"
_V28_REGISTERED = "websocket_v28_registered"
_V29_REGISTERED = "websocket_v29_registered"
_V30_REGISTERED = "websocket_v30_registered"
_V31_REGISTERED = "websocket_v31_registered"
_V32_REGISTERED = "websocket_v32_registered"
_V33_REGISTERED = "websocket_v33_registered"
_V34_REGISTERED = "websocket_v34_registered"
_V35_REGISTERED = "websocket_v35_registered"
_V36_REGISTERED = "websocket_v36_registered"
_V37_REGISTERED = "websocket_v37_registered"
_V38_REGISTERED = "websocket_v38_registered"
_V39_REGISTERED = "websocket_v39_registered"


async def async_register_panel(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get(_V20_REGISTERED):
        async_register_websocket_v20(hass); domain_data[_V20_REGISTERED] = True
    if not domain_data.get(_V21_REGISTERED):
        async_register_websocket_v21(hass); domain_data[_V21_REGISTERED] = True
    if not domain_data.get(_V22_REGISTERED):
        async_register_websocket_v22(hass); domain_data[_V22_REGISTERED] = True
    if not domain_data.get(_V23_REGISTERED):
        async_register_websocket_v23(hass); domain_data[_V23_REGISTERED] = True
    if not domain_data.get(_V24_REGISTERED):
        async_register_websocket_v24(hass); domain_data[_V24_REGISTERED] = True
    if not domain_data.get(_V25_REGISTERED):
        async_register_websocket_v25(hass); domain_data[_V25_REGISTERED] = True
    if not domain_data.get(_V26_REGISTERED):
        async_register_websocket_v26(hass); domain_data[_V26_REGISTERED] = True
    if not domain_data.get(_V27_REGISTERED):
        async_register_websocket_v27(hass); domain_data[_V27_REGISTERED] = True
    if not domain_data.get(_V28_REGISTERED):
        async_register_websocket_v28(hass); domain_data[_V28_REGISTERED] = True
    if not domain_data.get(_V29_REGISTERED):
        async_register_websocket_v29(hass); domain_data[_V29_REGISTERED] = True
    if not domain_data.get(_V30_REGISTERED):
        async_register_websocket_v30(hass); domain_data[_V30_REGISTERED] = True
    if not domain_data.get(_V31_REGISTERED):
        async_register_websocket_v31(hass); domain_data[_V31_REGISTERED] = True
    if not domain_data.get(_V32_REGISTERED):
        async_register_websocket_v32(hass); domain_data[_V32_REGISTERED] = True
    if not domain_data.get(_V33_REGISTERED):
        async_register_websocket_v33(hass); domain_data[_V33_REGISTERED] = True
    if not domain_data.get(_V34_REGISTERED):
        async_register_websocket_v34(hass); domain_data[_V34_REGISTERED] = True
    if not domain_data.get(_V35_REGISTERED):
        async_register_websocket_v35(hass); domain_data[_V35_REGISTERED] = True
    if not domain_data.get(_V36_REGISTERED):
        async_register_websocket_v36(hass); domain_data[_V36_REGISTERED] = True
    if not domain_data.get(_V37_REGISTERED):
        async_register_websocket_v37(hass); domain_data[_V37_REGISTERED] = True
    if not domain_data.get(_V38_REGISTERED):
        async_register_websocket_v38(hass); domain_data[_V38_REGISTERED] = True
    if not domain_data.get(_V39_REGISTERED):
        async_register_websocket_v39(hass); domain_data[_V39_REGISTERED] = True
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
        module_url=f"{_URL_BASE}/{_PANEL_MODULE}?v=2026.9.22.7&scanner=194",
        sidebar_title="Cook4Me",
        sidebar_icon="mdi:pot-steam",
        embed_iframe=False,
        require_admin=False,
        handle_safe_area=True,
    )
