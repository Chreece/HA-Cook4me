"""Per-device, per-user speech preferences and the legacy entity migration."""
from __future__ import annotations

from copy import deepcopy
import asyncio

from homeassistant.auth.permissions.const import POLICY_CONTROL, POLICY_READ
from homeassistant.helpers.storage import Store

from .const import DOMAIN

DEFAULTS = {"enabled": False, "recipe": True, "steps": True, "state": True,
            "connection": False, "players": [], "tts": "", "ai": "",
            "language": "", "voice": ""}
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
        voices.append({**label(entity.entity_id), "languages": languages,
                       "defaultLanguage": entity.default_language, "voices": by_language})
    for entity in getattr(hass.data.get("ai_task"), "entities", ()):
        if available(entity) and entity.supported_features & AITaskEntityFeature.GENERATE_DATA:
            tasks.append(label(entity.entity_id))
    return {"players": players, "tts": voices, "ai": tasks}


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
        for key in ("enabled", "recipe", "steps", "state", "connection"):
            if not isinstance(result[key], bool):
                raise ValueError("Announcement switches must be booleans")
        for key in ("tts", "ai", "language", "voice"):
            if not isinstance(result[key], str) or len(result[key]) > 255:
                raise ValueError("Invalid announcement selection")
        if not isinstance(result["players"], list) or len(result["players"]) > 32 or not all(isinstance(p, str) for p in result["players"]):
            raise ValueError("Select up to 32 media players")
        result["players"] = list(dict.fromkeys(result["players"]))
        options = choices(self.bridge.hass, user)
        # An unavailable saved selection can be retained when disabling speech.
        # Enabling it always requires current availability and permissions.
        if result["enabled"]:
            if not result["players"] or not set(result["players"]) <= {p["id"] for p in options["players"]}:
                raise ValueError("Select available media players you can control")
            tts = next((t for t in options["tts"] if t["id"] == result["tts"]), None)
            if not tts or result["language"] not in tts["languages"]:
                raise ValueError("Select a TTS entity and one of its supported languages")
            if result["voice"] and result["voice"] not in {v["id"] for v in tts["voices"].get(result["language"], [])}:
                raise ValueError("The selected voice is unavailable for this language")
            if result["ai"] and result["ai"] not in {a["id"] for a in options["ai"]}:
                raise ValueError("The selected AI Task is unavailable")
        data = deepcopy(self.data)
        data["users"][user.id] = result
        await self.store.async_save(data)
        self.data = data
        return self.for_user(user.id)

    async def async_consolidate_entities(self):
        """One migration only; a later manual re-enable is respected."""
        async with self.lock:
            await self._async_consolidate_entities_locked()

    async def _async_consolidate_entities_locked(self):
        if self.data.get("entitiesConsolidated"):
            return
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(self.bridge.hass)
        entries = er.async_entries_for_config_entry(registry, self.bridge.entry.entry_id)
        primary_ids = {f"{self.bridge.device_uuid}_{key}" for key in ("summary", "connected")}
        ready = set()
        for row in entries:
            if row.platform != DOMAIN or row.unique_id not in primary_ids or row.disabled_by is not None:
                continue
            state = self.bridge.hass.states.get(row.entity_id)
            if state is not None and state.state not in ("unavailable", "unknown") and not state.attributes.get("restored"):
                ready.add(row.unique_id)
        if ready != primary_ids:
            # Keep legacy telemetry when either replacement failed to register.
            # Do not mark the migration done; the next successful setup retries.
            return
        legacy_ids = {f"{self.bridge.device_uuid}_{key}" for key in LEGACY_KEYS}
        for row in entries:
            if row.platform == DOMAIN and row.unique_id in legacy_ids and row.disabled_by is None:
                registry.async_update_entity(row.entity_id, disabled_by=er.RegistryEntryDisabler.INTEGRATION)
        data = deepcopy(self.data)
        data["entitiesConsolidated"] = True
        await self.store.async_save(data)
        self.data = data
