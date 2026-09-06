from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

import voluptuous as vol
from homeassistant.components import ai_task, websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_APP_VERSION,
    CONF_COUNTRY,
    CONF_LANGUAGE,
    DEFAULT_APP_VERSION,
    DEFAULT_COUNTRY,
    DEFAULT_LANGUAGE,
    DOMAIN,
)
from .recipe_cache import Cook4MeRecipeCache, stable_cache_key, translation_cache_key
from .recipe_grouping import merge_hydrated_catalogs
from . import recipe_languages
from .vendor import cook4me_phonefree as c4m
from .vendor import cook4me_recipe_catalog as recipe_catalog
from . import websocket as legacy
from . import websocket_v5 as v5

_CACHE_DATA_KEY = "recipe_cache_v7"


async def _cache_for(hass: HomeAssistant, bridge) -> Cook4MeRecipeCache:
    domain_data = hass.data.setdefault(DOMAIN, {})
    caches = domain_data.setdefault(_CACHE_DATA_KEY, {})
    cache = caches.get(bridge.entry.entry_id)
    if cache is None:
        cache = Cook4MeRecipeCache(hass, bridge.entry.entry_id)
        caches[bridge.entry.entry_id] = cache
        await cache.async_load()
    return cache


def _catalog_context(bridge, language: str) -> tuple[str, str, str, str, str, str]:
    device_country = str(bridge.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)).upper()
    configured_language = str(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)).lower()
    app_version = str(bridge.entry.data.get(CONF_APP_VERSION, DEFAULT_APP_VERSION))
    requested_language = str(language or configured_language).lower().replace("_", "-").split("-", 1)[0]
    display_country = recipe_languages.country_for_language(requested_language, device_country)
    return (
        str(bridge.storage_home),
        device_country,
        display_country,
        configured_language,
        requested_language,
        app_version,
    )


def _catalog_search_full_sync(
    storage_home: str,
    device_country: str,
    display_country: str,
    configured_language: str,
    requested_language: str,
    app_version: str,
    query: str,
    page: int,
    requested_size: int,
    strict_language: bool,
) -> dict[str, Any]:
    """Return fully hydrated, grouping-deduplicated recipes before UI render."""
    cfg = c4m.read_apk_config(None)
    tokens = legacy._catalog_tokens(storage_home)
    # A few extra raw variants are requested because one logical recipe can
    # have multiple serving variants. They are collapsed only after detail has
    # exposed the proven groupingId.
    fetch_size = min(50, max(int(requested_size), 24))

    device_result = recipe_catalog.search_recipes(
        cfg,
        tokens,
        query,
        page=page,
        size=fetch_size,
        max_details=fetch_size,
        country=device_country,
        language=configured_language,
        configured_language=configured_language,
        app_version=app_version,
    )

    same_locale = (
        requested_language == configured_language
        and display_country.upper() == device_country.upper()
    )
    if same_locale:
        display_result = deepcopy(device_result)
    else:
        display_result = recipe_catalog.search_recipes(
            cfg,
            tokens,
            query,
            page=page,
            size=fetch_size,
            max_details=fetch_size,
            country=display_country,
            language=requested_language,
            configured_language=requested_language,
            app_version=app_version,
        )

    result = merge_hydrated_catalogs(
        display_result,
        device_result,
        target_language=requested_language,
        configured_language=configured_language,
        device_country=device_country,
        strict_language=strict_language,
    )
    result["items"] = list(result.get("items") or [])[: max(1, int(requested_size))]
    result["displayCountry"] = display_country
    result["deviceCountry"] = device_country
    result["fetchSize"] = fetch_size
    return result


async def _raw_search(
    hass: HomeAssistant,
    bridge,
    *,
    query: str,
    page: int,
    size: int,
    language: str,
    strict_language: bool,
    refresh: bool,
) -> tuple[dict[str, Any], bool]:
    (
        storage_home,
        device_country,
        display_country,
        configured_language,
        requested_language,
        app_version,
    ) = _catalog_context(bridge, language)
    cache = await _cache_for(hass, bridge)
    key = stable_cache_key(
        "search-v7",
        device_country,
        display_country,
        configured_language,
        requested_language,
        query.casefold(),
        int(page),
        int(size),
        bool(strict_language),
    )
    if not refresh:
        cached = cache.get("search", key)
        if isinstance(cached, dict):
            return cached, True

    result = await legacy._async_catalog_call(
        hass,
        bridge,
        _catalog_search_full_sync,
        storage_home,
        device_country,
        display_country,
        configured_language,
        requested_language,
        app_version,
        query,
        int(page),
        int(size),
        bool(strict_language),
    )
    await cache.async_set("search", key, result)

    detail_values: dict[str, Any] = {}
    for recipe in result.get("items") or []:
        if not isinstance(recipe, dict):
            continue
        for variant in recipe.get("servingVariants") or []:
            if not isinstance(variant, dict):
                continue
            display_variant = str(variant.get("displayVariantId") or "")
            if display_variant and display_variant == str(recipe.get("displayVariantId") or ""):
                dkey = stable_cache_key("detail-v7", display_country, requested_language, display_variant)
                detail_values[dkey] = recipe
    await cache.async_set_many("detail", detail_values)
    return result, False


async def _raw_detail(
    hass: HomeAssistant,
    bridge,
    *,
    variant_id: str,
    language: str,
    refresh: bool,
) -> tuple[dict[str, Any], bool]:
    (
        storage_home,
        _device_country,
        display_country,
        _configured_language,
        requested_language,
        app_version,
    ) = _catalog_context(bridge, language)
    cache = await _cache_for(hass, bridge)
    key = stable_cache_key("detail-v7", display_country, requested_language, str(variant_id))
    if not refresh:
        cached = cache.get("detail", key)
        if isinstance(cached, dict):
            return cached, True
    result = await legacy._async_catalog_call(
        hass,
        bridge,
        legacy._catalog_detail_sync,
        storage_home,
        display_country,
        requested_language,
        app_version,
        str(variant_id),
    )
    await cache.async_set("detail", key, result)
    return result, False


def _translation_prompt(prepared: list[dict[str, Any]], target_language: str) -> str:
    return (
        f"Translate the following recipe display text to language code {target_language}. "
        "Translate only human-readable text. Never change, round, invent, remove, or reorder "
        "numbers, quantities, units, temperatures, times, ingredient entries, or steps. "
        "Do not add cooking advice. Keep each id exactly unchanged. Return ONLY valid JSON "
        "with exactly this shape: "
        '{"recipes":[{"id":"0","title":"...","ingredients":["..."],'
        '"steps":["..."],"missing":["..."]}]}. '
        "Each output ingredients/steps/missing array must preserve the input order and length. "
        "Input: " + json.dumps({"recipes": prepared}, ensure_ascii=False, separators=(",", ":"))
    )


async def _translate_cached(
    hass: HomeAssistant,
    bridge,
    recipes: list[dict[str, Any]],
    target_language: str,
) -> dict[str, Any]:
    entity_id = v5._default_ai_task_entity_id(hass)
    if entity_id is None:
        return {"available": False, "items": []}

    cache = await _cache_for(hass, bridge)
    output: dict[int, dict[str, Any]] = {}
    missing: list[tuple[int, str, dict[str, Any], dict[str, Any]]] = []
    for index, recipe in enumerate(recipes[:20]):
        key = translation_cache_key(recipe, target_language)
        cached = cache.get("translation", key)
        if isinstance(cached, dict):
            output[index] = {"id": str(index), **deepcopy(cached), "cached": True}
        else:
            missing.append((index, key, recipe, v5._translation_payload(recipe)))

    generated = 0
    for offset in range(0, len(missing), 8):
        batch = missing[offset : offset + 8]
        prepared = [{"id": str(pos), **payload} for pos, (_index, _key, _recipe, payload) in enumerate(batch)]
        try:
            result = await ai_task.async_generate_data(
                hass,
                task_name="Cook4Me recipe translation",
                entity_id=None,
                instructions=_translation_prompt(prepared, target_language),
            )
        except Exception:
            # Translation is optional; leave untranslated source content intact.
            continue
        parsed = v5._parse_ai_json(result.data)
        rows = parsed.get("recipes") if isinstance(parsed, dict) else None
        if not isinstance(rows, list):
            continue
        by_id = {str(row.get("id")): row for row in rows if isinstance(row, dict)}
        cache_values: dict[str, Any] = {}
        for pos, (original_index, key, _recipe, source_payload) in enumerate(batch):
            row = by_id.get(str(pos))
            if not isinstance(row, dict):
                continue
            translated: dict[str, Any] = {}
            title = str(row.get("title") or "").strip()
            if title:
                translated["title"] = title
            for name in ("ingredients", "steps", "missing"):
                source_values = source_payload.get(name) or []
                values = row.get(name)
                if isinstance(values, list) and len(values) == len(source_values):
                    translated[name] = [str(value).strip() for value in values]
            if not translated:
                continue
            cache_values[key] = translated
            output[original_index] = {"id": str(original_index), **translated, "cached": False}
            generated += 1
        await cache.async_set_many("translation", cache_values)

    return {
        "available": True,
        "items": [output[index] for index in sorted(output)],
        "cachedCount": sum(1 for row in output.values() if row.get("cached")),
        "generatedCount": generated,
        "entity_id": entity_id,
    }


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


@websocket_api.websocket_command({vol.Required("type"): "cook4me/v7/capabilities"})
@websocket_api.async_response
async def ws_capabilities(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    entity_id = v5._default_ai_task_entity_id(hass)
    connection.send_result(
        msg["id"],
        {
            "languages": recipe_languages.language_options(),
            "defaultAiTaskAvailable": entity_id is not None,
            "defaultAiTaskEntityId": entity_id,
            "persistentCache": True,
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v7/search",
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
        raw, cache_hit = await _raw_search(
            hass,
            bridge,
            query=str(msg.get("query", "")).strip(),
            page=int(msg.get("page", 0)),
            size=int(msg.get("size", 20)),
            language=str(msg["language"]),
            strict_language=bool(msg.get("strict_language")),
            refresh=bool(msg.get("refresh")),
        )
        result = deepcopy(raw)
        items = []
        for item in result.get("items") or []:
            if not isinstance(item, dict):
                continue
            row = bridge.recipe_hub.annotate(item)
            row["deviceCanAccept"] = bridge.can_accept_recipe
            items.append(row)
        result["items"] = items
        result["cacheHit"] = cache_hit
        result["defaultAiTaskAvailable"] = v5._default_ai_task_entity_id(hass) is not None
        result["deviceCanAccept"] = bridge.can_accept_recipe
        result["loadedRecipe"] = bridge.loaded_recipe
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v7/recipe_detail",
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
        raw, cache_hit = await _raw_detail(
            hass,
            bridge,
            variant_id=str(msg["variant_id"]),
            language=str(msg["language"]),
            refresh=bool(msg.get("refresh")),
        )
        result = bridge.recipe_hub.annotate(raw)
        result["deviceCanAccept"] = bridge.can_accept_recipe
        result["cacheHit"] = cache_hit
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v7/recommend",
        vol.Optional("entry_id"): str,
        vol.Optional("limit", default=12): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Optional("catalog_size", default=24): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Required("language"): str,
        vol.Optional("strict_language", default=False): bool,
        vol.Optional("refresh", default=False): bool,
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
        raw, cache_hit = await _raw_search(
            hass,
            bridge,
            query="",
            page=0,
            size=int(msg.get("catalog_size", 24)),
            language=str(msg["language"]),
            strict_language=bool(msg.get("strict_language")),
            refresh=bool(msg.get("refresh")),
        )
        ranked = bridge.recipe_hub.rank(raw.get("items") or [], limit=int(msg.get("limit", 12)))
        for item in ranked:
            item["deviceCanAccept"] = bridge.can_accept_recipe
        result = {
            "items": ranked,
            "cacheHit": cache_hit,
            "defaultAiTaskAvailable": v5._default_ai_task_entity_id(hass) is not None,
            "deviceCanAccept": bridge.can_accept_recipe,
            "loadedRecipe": bridge.loaded_recipe,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v7/translate",
        vol.Optional("entry_id"): str,
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
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await _translate_cached(
            hass,
            bridge,
            [row for row in msg.get("recipes") or [] if isinstance(row, dict)],
            str(msg["target_language"]),
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
