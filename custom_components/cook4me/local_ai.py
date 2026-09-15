"""Resolve a loaded, available Ollama AI Task without a cloud fallback."""


def translation_capabilities(hass):
    from homeassistant.components.ai_task.const import (
        AITaskEntityFeature, DATA_COMPONENT, DATA_PREFERENCES,
    )

    component = hass.data.get(DATA_COMPONENT)
    preferred = getattr(hass.data.get(DATA_PREFERENCES), "gen_data_entity_id", None)
    candidates = []
    available = []
    for entity in getattr(component, "entities", ()):
        # Platform provenance is authoritative; entity names are user editable.
        if getattr(getattr(entity, "platform", None), "platform_name", None) != "ollama":
            continue
        if not (getattr(entity, "supported_features", 0) & AITaskEntityFeature.GENERATE_DATA):
            continue
        entity_id = entity.entity_id
        candidates.append(entity_id)
        state = hass.states.get(entity_id)
        if getattr(entity, "available", False) and state and state.state not in ("unavailable", "unknown"):
            available.append(entity_id)
    available.sort(key=lambda entity_id: (entity_id != preferred, entity_id))
    return {
        "localAiTaskAvailable": bool(available),
        "localAiTaskEntityId": available[0] if available else None,
        "localAiTaskEntityIds": sorted(candidates),
    }
