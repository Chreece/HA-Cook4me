from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity

from .entity import Cook4MeEntity


async def async_setup_entry(hass, entry, async_add_entities):
    bridge = entry.runtime_data
    async_add_entities([Cook4MeConnected(bridge), Cook4MeUpdating(bridge)])


class Cook4MeConnected(Cook4MeEntity, BinarySensorEntity):
    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:cloud-check"

    def __init__(self, bridge):
        super().__init__(bridge, "connected")

    @property
    def is_on(self):
        return self.bridge.data.get("connected") is True


class Cook4MeUpdating(Cook4MeEntity, BinarySensorEntity):
    _attr_name = "Updating"
    _attr_device_class = BinarySensorDeviceClass.UPDATE
    _attr_icon = "mdi:update"
    _attr_entity_registry_enabled_default = False

    def __init__(self, bridge):
        super().__init__(bridge, "updating")

    @property
    def is_on(self):
        return self.bridge.data.get("updating") is True
