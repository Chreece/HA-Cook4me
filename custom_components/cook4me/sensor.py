from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import UnitOfTime

from .entity import Cook4MeEntity


@dataclass(frozen=True, kw_only=True)
class Cook4MeSensorDescription(SensorEntityDescription):
    data_key: str
    timestamp_ms: bool = False


# v0.3.0 exposes one summary entity by default. Legacy entities remain available
# but are disabled by default for backwards compatibility / opt-in automations.
DESCRIPTIONS = (
    Cook4MeSensorDescription(
        key="summary", name="State", data_key="phase", icon="mdi:pot-steam",
        entity_registry_enabled_default=True,
    ),
    Cook4MeSensorDescription(key="phase", name="Cooking phase", data_key="phase", icon="mdi:pot-steam", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="status", name="Cooking status", data_key="status", icon="mdi:state-machine", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="recipe", name="Recipe", data_key="recipeTitle", icon="mdi:book-open-variant", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="step", name="Step", data_key="stepIndex", icon="mdi:format-list-numbered", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="instruction", name="Current instruction", data_key="currentInstruction", icon="mdi:format-text", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="step_type", name="Step type", data_key="stepTypeKey", icon="mdi:format-list-bulleted-type", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="program", name="Program", data_key="programKey", icon="mdi:chef-hat", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="progress", name="Phase progress", data_key="progress", native_unit_of_measurement="%", icon="mdi:progress-clock", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="remaining_time", name="Remaining time", data_key="remainingTime", native_unit_of_measurement=UnitOfTime.SECONDS, device_class=SensorDeviceClass.DURATION, icon="mdi:timer-sand", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="elapsed_time", name="Elapsed time", data_key="elapsedTime", native_unit_of_measurement=UnitOfTime.SECONDS, device_class=SensorDeviceClass.DURATION, icon="mdi:timer-outline", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="last_connection", name="Last connection", data_key="lastConnection", device_class=SensorDeviceClass.TIMESTAMP, timestamp_ms=True, icon="mdi:lan-connect", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="last_disconnection", name="Last disconnection", data_key="lastDisconnection", device_class=SensorDeviceClass.TIMESTAMP, timestamp_ms=True, icon="mdi:lan-disconnect", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="ui_firmware", name="UI firmware", data_key="uiFirmware", icon="mdi:chip", entity_registry_enabled_default=False),
    Cook4MeSensorDescription(key="wifi_firmware", name="Wi-Fi firmware", data_key="wifiFirmware", icon="mdi:wifi-cog", entity_registry_enabled_default=False),
)


async def async_setup_entry(hass, entry, async_add_entities):
    bridge = entry.runtime_data
    async_add_entities([Cook4MeSensor(bridge, d) for d in DESCRIPTIONS])


class Cook4MeSensor(Cook4MeEntity, SensorEntity):
    entity_description: Cook4MeSensorDescription

    def __init__(self, bridge, description):
        super().__init__(bridge, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        if self.entity_description.key == "summary":
            return self.bridge.data.get("phase") or self.bridge.data.get("status") or ("online" if self.bridge.available else "offline")
        value = self.bridge.data.get(self.entity_description.data_key)
        if self.entity_description.timestamp_ms and isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        if self.entity_description.key == "instruction" and isinstance(value, str) and len(value) > 255:
            return value[:252] + "…"
        return value

    @property
    def entity_picture(self) -> str | None:
        if self.entity_description.key == "summary":
            value = self.bridge.data.get("recipeImage")
            return str(value) if value else None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        d = self.bridge.data
        if self.entity_description.key == "summary":
            keys = (
                "connected", "updating", "available", "active", "mode", "status", "phase",
                "recipeTitle", "recipeFunctionalId", "variantFunctionalId", "groupingFunctionalId",
                "recipeImage", "recipeStepCount", "recipeIngredients", "recipeExcludedFoods",
                "recipeDurations", "recipeYield", "stepIndex", "stepFunctionalId", "stepTypeKey",
                "stepTypeName", "currentInstruction", "currentInstructions", "nextInstruction",
                "nextStepFunctionalId", "programKey", "programName", "operationParameters",
                "progress", "remainingTime", "elapsedTime", "operationStart", "cookingVersion",
                "lastConnection", "lastDisconnection", "uiFirmware", "wifiFirmware", "_receivedAt", "_topic",
            )
            attrs = {k: d.get(k) for k in keys if d.get(k) is not None}
            attrs["can_accept_recipe"] = self.bridge.can_accept_recipe
            if self.bridge.loaded_recipe:
                attrs["loaded_recipe"] = self.bridge.loaded_recipe
            return attrs
        if self.entity_description.key == "recipe":
            return {k: d.get(k) for k in ("recipeFunctionalId", "variantFunctionalId", "groupingFunctionalId", "stepFunctionalId", "stepTypeName", "operationStart", "cookingVersion") if d.get(k) is not None}
        if self.entity_description.key == "step":
            return {k: d.get(k) for k in ("stepFunctionalId", "stepTypeKey", "stepTypeName", "currentInstruction", "nextInstruction", "nextStepFunctionalId", "recipeStepCount") if d.get(k) is not None}
        if self.entity_description.key == "instruction":
            return {k: d.get(k) for k in ("currentInstruction", "currentInstructions", "nextInstruction", "stepFunctionalId", "stepIndex", "recipeStepCount", "recipeTitle") if d.get(k) is not None}
        if self.entity_description.key == "program":
            return {k: d.get(k) for k in ("programName", "operationParameters") if d.get(k) is not None}
        if self.entity_description.key == "phase":
            return {k: d.get(k) for k in ("active", "mode", "_receivedAt", "_topic") if d.get(k) is not None}
        return None
