from __future__ import annotations

from copy import deepcopy
import json
import re
from typing import Any

import voluptuous as vol
from homeassistant.components import ai_task, websocket_api
from homeassistant.components.ai_task.const import (
    AITaskEntityFeature,
    DATA_COMPONENT as AI_TASK_COMPONENT,
    DATA_PREFERENCES as AI_TASK_PREFERENCES,
)
from homeassistant.core import HomeAssistant, callback

from . import recipe_languages
from . import websocket as legacy


def _default_ai_task_entity_id(hass: HomeAssistant) -> str | None:
    """Return the preferred/default data AI Task entity when it is usable."""
    preferences = hass.data.get(AI_TASK_PREFERENCES)
    component = hass.data.get(AI_TASK_COMPONENT)
    if preferences is None or component is None:
        return None
    entity_id = getattr(preferences, "gen_data_entity_id", None)
    if not entity_id:
        return None
    entity = component.get_entity(entity_id)
    if entity is None:
        return None
    try:
        if not (entity.supported_features & AITaskEntityFeature.GENERATE_DATA):
            return None
    except Exception:
        return None
    return str(entity_id)


def _parse_ai_json(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _clean_string_list(value: Any, max_items: int = 80) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value[:max_items] if str(item).strip()]


def _translation_payload(recipe: dict[str, Any]) -> dict[str, Any]:
    ingredients: list[str] = []
    for item in recipe.get("ingredients") or []:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            parts = []
            if item.get("quantity") not in (None, ""):
                parts.append(str(item["quantity"]))
            if item.get("unit"):
                parts.append(str(item["unit"]))
            name = item.get("name") or item.get("foodName") or item.get("applicationDescription")
            if name:
                parts.append(str(name))
            text = " ".join(parts).strip()
        else:
            text = ""
        if text:
            ingredients.append(text)

    steps: list[str] = []
    for item in recipe.get("steps") or []:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(
                item.get("instruction")
                or item.get("applicationDescription")
                or item.get("applianceDescription")
                or item.get("programName")
                or ""
            ).strip()
        else:
            text = ""
        if text:
            steps.append(text)

    missing = _clean_string_list((recipe.get("match") or {}).get("missingIngredients"), 30)
    return {
        "title": str(recipe.get("title") or "").strip(),
        "ingredients": ingredients[:80],
        "steps": steps[:80],
        "missing": missing,
    }


async def _translate_with_default_ai_task(
    hass: HomeAssistant,
    recipes: list[dict[str, Any]],
    target_language: str,
) -> dict[str, Any]:
    entity_id = _default_ai_task_entity_id(hass)
    if entity_id is None:
        return {"available": False, "items": []}

    prepared = [
        {"id": str(index), **_translation_payload(recipe)}
        for index, recipe in enumerate(recipes[:8])
    ]
    instructions = (
        f"Translate the following recipe display text to language code {target_language}. "
        "Translate only human-readable text. Never change, round, invent, remove, or reorder "
        "numbers, quantities, units, temperatures, times, ingredient entries, or steps. "
        "Do not add cooking advice. Keep each id exactly unchanged. Return ONLY valid JSON "
        "with exactly this shape: "
        '{"recipes":[{"id":"0","title":"...","ingredients":["..."],'
        '"steps":["..."],"missing":["..."]}]}. '
        "Each output ingredients/steps array must have the same length and order as its input. "
        "Input: " + json.dumps({"recipes": prepared}, ensure_ascii=False, separators=(",", ":"))
    )
    try:
        result = await ai_task.async_generate_data(
            hass,
            task_name="Cook4Me recipe translation",
            entity_id=None,  # intentionally use Home Assistant's preferred/default AI Task
            instructions=instructions,
        )
    except Exception:
        # Translation is optional. A provider/task failure must never hide the
        # original SEB recipe or turn search into an error.
        return {"available": True, "items": [], "failed": True}

    parsed = _parse_ai_json(result.data)
    rows = parsed.get("recipes") if isinstance(parsed, dict) else None
    if not isinstance(rows, list):
        return {"available": True, "items": [], "failed": True}

    output: list[dict[str, Any]] = []
    for row in rows[:8]:
        if not isinstance(row, dict):
            continue
        output.append(
            {
                "id": str(row.get("id") or ""),
                "title": str(row.get("title") or "").strip(),
                "ingredients": _clean_string_list(row.get("ingredients")),
                "steps": _clean_string_list(row.get("steps")),
                "missing": _clean_string_list(row.get("missing"), 30),
            }
        )
    return {"available": True, "items": output, "entity_id": entity_id}


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_capabilities,
        ws_search,
        ws_recipe_detail,
        ws_recommend,
        ws_translate,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v5/capabilities"})
@callback
def ws_capabilities(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    entity_id = _default_ai_task_entity_id(hass)
    connection.send_result(
        msg["id"],
        {
            "languages": recipe_languages.language_options(),
            "defaultAiTaskAvailable": entity_id is not None,
            "defaultAiTaskEntityId": entity_id,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v5/search",
        vol.Optional("entry_id"): str,
        vol.Optional("query", default=""): str,
        vol.Optional("page", default=0): vol.Coerce(int),
        vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Required("language"): str,
        vol.Optional("strict_language", default=False): bool,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_search(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        (
            storage_home,
            device_country,
            _display_country,
            configured_language,
            language,
            app_version,
        ) = legacy._catalog_context(bridge, msg["language"])
        display_country = recipe_languages.country_for_language(language, device_country)
        result = await legacy._async_catalog_call(
            hass,
            bridge,
            legacy._catalog_search_pair_sync,
            storage_home,
            device_country,
            display_country,
            configured_language,
            language,
            app_version,
            str(msg.get("query", "")),
            int(msg.get("page", 0)),
            int(msg.get("size", 20)),
        )
        items = [x for x in result.get("items") or [] if isinstance(x, dict)]
        if msg.get("strict_language"):
            wanted = str(language).lower().split("-", 1)[0]
            items = [
                item
                for item in items
                if str(item.get("language") or "").lower().split("-", 1)[0] == wanted
            ]
        annotated = []
        for item in items:
            row = bridge.recipe_hub.annotate(item)
            row["deviceCanAccept"] = bridge.can_accept_recipe
            annotated.append(row)
        result = deepcopy(result)
        result["items"] = annotated
        result["strictLanguage"] = bool(msg.get("strict_language"))
        result["defaultAiTaskAvailable"] = _default_ai_task_entity_id(hass) is not None
        result["deviceCanAccept"] = bridge.can_accept_recipe
        result["loadedRecipe"] = bridge.loaded_recipe
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v5/recipe_detail",
        vol.Optional("entry_id"): str,
        vol.Required("variant_id"): str,
        vol.Required("language"): str,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_recipe_detail(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        (
            storage_home,
            device_country,
            _display_country,
            _configured_language,
            language,
            app_version,
        ) = legacy._catalog_context(bridge, msg["language"])
        display_country = recipe_languages.country_for_language(language, device_country)
        result = await legacy._async_catalog_call(
            hass,
            bridge,
            legacy._catalog_detail_sync,
            storage_home,
            display_country,
            language,
            app_version,
            str(msg["variant_id"]),
        )
        result = bridge.recipe_hub.annotate(result)
        result["deviceCanAccept"] = bridge.can_accept_recipe
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v5/recommend",
        vol.Optional("entry_id"): str,
        vol.Optional("limit", default=12): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Optional("catalog_size", default=24): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Required("language"): str,
        vol.Optional("strict_language", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_recommend(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        (
            storage_home,
            device_country,
            _display_country,
            configured_language,
            language,
            app_version,
        ) = legacy._catalog_context(bridge, msg["language"])
        display_country = recipe_languages.country_for_language(language, device_country)
        catalog = await legacy._async_catalog_call(
            hass,
            bridge,
            legacy._catalog_search_pair_sync,
            storage_home,
            device_country,
            display_country,
            configured_language,
            language,
            app_version,
            "",
            0,
            int(msg["catalog_size"]),
        )
        items = [x for x in catalog.get("items") or [] if isinstance(x, dict)]
        if msg.get("strict_language"):
            wanted = str(language).lower().split("-", 1)[0]
            items = [
                item
                for item in items
                if str(item.get("language") or "").lower().split("-", 1)[0] == wanted
            ]
        ranked = bridge.recipe_hub.rank(items, limit=int(msg["limit"]))
        for item in ranked:
            item["deviceCanAccept"] = bridge.can_accept_recipe
        result = {
            "items": ranked,
            "requestedLanguage": language,
            "strictLanguage": bool(msg.get("strict_language")),
            "defaultAiTaskAvailable": _default_ai_task_entity_id(hass) is not None,
            "deviceCanAccept": bridge.can_accept_recipe,
            "loadedRecipe": bridge.loaded_recipe,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v5/translate",
        vol.Required("target_language"): str,
        vol.Required("recipes"): [dict],
    }
)
@websocket_api.async_response
async def ws_translate(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    recipes = [x for x in msg.get("recipes") or [] if isinstance(x, dict)][:8]
    result = await _translate_with_default_ai_task(
        hass,
        recipes,
        str(msg["target_language"]),
    )
    connection.send_result(msg["id"], result)
