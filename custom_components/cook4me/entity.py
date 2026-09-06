from __future__ import annotations
from homeassistant.helpers.entity import DeviceInfo, Entity
from .const import DOMAIN

class Cook4MeEntity(Entity):
    _attr_has_entity_name = True
    def __init__(self, bridge, key: str) -> None:
        self.bridge = bridge
        self.key = key
        self._attr_unique_id = f"{bridge.device_uuid}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, bridge.device_uuid)},
            name="Cook4Me",
            manufacturer="Groupe SEB / KRUPS",
            model="Cook4Me",
            sw_version=bridge.data.get("uiFirmware"),
        )
    @property
    def available(self) -> bool:
        return True
    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.bridge.async_add_listener(self._handle_update))
    def _handle_update(self) -> None:
        self.async_write_ha_state()
