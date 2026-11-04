"""Per-device, per-user speech preferences and the legacy entity migration."""
from __future__ import annotations

from copy import deepcopy
import asyncio

from homeassistant.auth.permissions.const import POLICY_CONTROL, POLICY_READ
from homeassistant.helpers.storage import Store

from .const import DOMAIN

DEFAULT_AI_TASK = "__home_assistant_default__"
DEFAULTS = {"enabled": False, "recipe": True, "steps": True, "state": True,
            "connection": False, "players": [], "tts": "", "ai": "",
            "ai_all": False, "language": "", "voice": "",
            "announcement_hub": False, "hub_auto_routing": True,
            "hub_areas": [], "hub_persons": []}
LEGACY_KEYS = {"phase", "status", "recipe", "step", "instruction", "step_type",
               "program", "progress", "remaining_time", "elapsed_time",
               "last_connection", "last_disconnection", "ui_firmware",
               "wifi_firmware", "updating"}


def can_use(user, entity_id):
    return bool(user and user.is_active and all(
        user.permissions.check_entity(entity_id, policy)
        for policy in (POLICY_READ, POLICY_CONTROL)))


def device_access(hass, bridge, user):
    """Require access to this device, not merely another user's speakers."""
    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(hass)
    return any(row.unique_id == f"{bridge.device_uuid}_summary" and can_use(user, row.entity_id)
               for row in er.async_entries_for_config_entry(registry, bridge.entry.entry_id))


def device_read_access(hass, bridge, user):
    """Allow telemetry without requiring permission to control the cooker."""
    from homeassistant.helpers import entity_registry as er
    if not user or not user.is_active:
        return False
    registry = er.async_get(hass)
    return any(row.unique_id == f"{bridge.device_uuid}_summary"
               and user.permissions.check_entity(row.entity_id, POLICY_READ)
               for row in er.async_entries_for_config_entry(registry, bridge.entry.entry_id))


def choices(hass, user):
    from homeassistant.components.media_player import MediaPlayerEntityFeature as Feature
    from homeassistant.components.ai_task.const import AITaskEntityFeature

    def available(entity):
        state = hass.states.get(entity.entity_id)
        return (getattr(entity, "available", False) and state is not None
                and state.state != "unavailable" and can_use(user, entity.entity_id))

    def label(entity_id):
        state = hass.states.get(entity_id)
        return {"id": entity_id, "name": state.attributes.get("friendly_name") or entity_id}

    players = []
    for state in hass.states.async_all("media_player"):
        features = int(state.attributes.get("supported_features", 0))
        if features & Feature.PLAY_MEDIA and state.state != "unavailable" and can_use(user, state.entity_id):
            players.append({**label(state.entity_id), "announce": bool(features & Feature.MEDIA_ANNOUNCE)})
    voices, tasks = [], []
    for entity in getattr(hass.data.get("tts"), "entities", ()):
        if not available(entity):
            continue
        languages = list(entity.supported_languages or [])
        by_language = {}
        for language in languages:
            voice_list = entity.async_get_supported_voices(language) or []
            by_language[language] = [{"id": v.voice_id, "name": v.name} for v in voice_list]
        default_language = entity.default_language
        if default_language not in languages:
            default_language = languages[0] if languages else ""
        voices.append({**label(entity.entity_id), "languages": languages,
                       "defaultLanguage": default_language, "voices": by_language})
    for entity in getattr(hass.data.get("ai_task"), "entities", ()):
        if available(entity) and entity.supported_features & AITaskEntityFeature.GENERATE_DATA:
            tasks.append(label(entity.entity_id))
    default_ai_task = None
    try:
        from homeassistant.components.ai_task.const import (
            DATA_COMPONENT as AI_TASK_COMPONENT,
            DATA_PREFERENCES as AI_TASK_PREFERENCES,
        )
        preferences = hass.data.get(AI_TASK_PREFERENCES)
        component = hass.data.get(AI_TASK_COMPONENT)
        preferred = getattr(preferences, "gen_data_entity_id", None) if preferences is not None else None
        entity = component.get_entity(preferred) if component is not None and preferred else None
        if (entity is not None and available(entity)
                and entity.supported_features & AITaskEntityFeature.GENERATE_DATA):
            default_ai_task = str(preferred)
    except Exception:
        default_ai_task = None
    return {"players": players, "tts": voices, "ai": tasks,
            "defaultAiTaskId": default_ai_task}


def hub_choices(hass, user):
    """The Hub is an exclusive output path, not an alternative TTS provider."""
    from homeassistant.helpers import area_registry as ar

    areas = sorted(
        ({"id": area.id, "name": area.name} for area in ar.async_get(hass).async_list_areas()),
        key=lambda row: row["name"].casefold(),
    )
    persons = sorted(
        ({"id": state.entity_id,
          "name": state.attributes.get("friendly_name") or state.entity_id}
         for state in hass.states.async_all("person")
         if user and user.is_active
         and user.permissions.check_entity(state.entity_id, POLICY_READ)),
        key=lambda row: row["name"].casefold(),
    )
    return {
        "announcementHubAvailable": hass.services.has_service("notify", "announcement_hub"),
        "hubAreas": areas,
        "hubPersons": persons,
    }


class DeviceSettings:
    def __init__(self, bridge):
        self.bridge = bridge
        self.store = Store(bridge.hass, 1, f"{DOMAIN}.{bridge.entry.entry_id}.device_settings")
        self.data = {"users": {}, "entitiesConsolidated": False}
        self.lock = asyncio.Lock()

    async def async_load(self):
        saved = await self.store.async_load()
        if isinstance(saved, dict):
            self.data.update(saved)
        if not isinstance(self.data.get("users"), dict):
            self.data["users"] = {}

    def for_user(self, user_id):
        return deepcopy({**DEFAULTS, **self.data["users"].get(user_id, {})})

    async def async_save(self, user, settings):
        async with self.lock:
            return await self._async_save_locked(user, settings)

    async def _async_save_locked(self, user, settings):
        if set(settings) - set(DEFAULTS):
            raise ValueError("Unknown announcement setting")
        result = {**self.for_user(user.id), **settings}
        for key in ("enabled", "recipe", "steps", "state", "connection", "ai_all",
                    "announcement_hub", "hub_auto_routing"):
            if not isinstance(result[key], bool):
                raise ValueError("Announcement switches must be booleans")
        for key in ("tts", "ai", "language", "voice"):
            if not isinstance(result[key], str) or len(result[key]) > 255:
                raise ValueError("Invalid announcement selection")
        if not isinstance(result["players"], list) or len(result["players"]) > 32 or not all(isinstance(p, str) for p in result["players"]):
            raise ValueError("Select up to 32 media players")
        result["players"] = list(dict.fromkeys(result["players"]))
        for key in ("hub_areas", "hub_persons"):
            values = result[key]
            if (not isinstance(values, list) or len(values) > 64
                    or not all(isinstance(item, str) and 0 < len(item) <= 255 for item in values)):
                raise ValueError("Select up to 64 valid Announcement Hub targets")
            result[key] = list(dict.fromkeys(values))
        if result["announcement_hub"]:
            hub = hub_choices(self.bridge.hass, user)
            if not hub["announcementHubAvailable"]:
                raise ValueError("Announcement Hub is not available in Home Assistant")
            if not result["hub_auto_routing"]:
                if not result["hub_areas"] and not result["hub_persons"]:
                    raise ValueError("Choose a room or person, or enable automatic Hub routing")
                if not set(result["hub_areas"]) <= {row["id"] for row in hub["hubAreas"]}:
                    raise ValueError("Select valid Home Assistant rooms")
                if not set(result["hub_persons"]) <= {row["id"] for row in hub["hubPersons"]}:
                    raise ValueError("Select people you are allowed to access")
        options = choices(self.bridge.hass, user)
        # TTS and speakers must be usable. An optional saved AI selection can
        # remain unavailable: deterministic announcements continue without it.
        if result["enabled"] and not result["announcement_hub"]:
            if not result["players"] or not set(result["players"]) <= {p["id"] for p in options["players"]}:
                raise ValueError("Select available media players you can control")
            tts = next((t for t in options["tts"] if t["id"] == result["tts"]), None)
            if not tts:
                raise ValueError("Select an available TTS entity")
            if not result["language"]:
                result["language"] = tts["defaultLanguage"] or (tts["languages"][0] if tts["languages"] else "")
            if result["language"] not in tts["languages"]:
                raise ValueError("Select one of the languages supported by the selected TTS entity")
            if result["voice"] and result["voice"] not in {v["id"] for v in tts["voices"].get(result["language"], [])}:
                raise ValueError("The selected voice is unavailable for this language")
            if result["ai_all"] and not result["ai"]:
                result["ai"] = DEFAULT_AI_TASK
            if (result["ai"] and result["ai"] != DEFAULT_AI_TASK
                    and result["ai"] not in {a["id"] for a in options["ai"]}
                    and result["ai"] != self.for_user(user.id)["ai"]):
                raise ValueError("The selected AI Task is unavailable")
        data = deepcopy(self.data)
        data["users"][user.id] = result
        await self.store.async_save(data)
        self.data = data
        return self.for_user(user.id)

    async def async_consolidate_entities(self):
        """Restore telemetry hidden by the old consolidation, once per device."""
        async with self.lock:
            await self._async_consolidate_entities_locked()

    async def _async_consolidate_entities_locked(self):
        if self.data.get("entitiesRestoredV104"):
            return
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self.bridge.hass)
        entries = er.async_entries_for_config_entry(registry, self.bridge.entry.entry_id)
        legacy_ids = {f"{self.bridge.device_uuid}_{key}" for key in LEGACY_KEYS}
        for row in entries:
            if (row.platform == DOMAIN and row.unique_id in legacy_ids
                    and row.disabled_by == er.RegistryEntryDisabler.INTEGRATION):
                registry.async_update_entity(row.entity_id, disabled_by=None)
        data = deepcopy(self.data)
        data["entitiesConsolidated"] = True
        data["entitiesRestoredV104"] = True
        await self.store.async_save(data)
        self.data = data
