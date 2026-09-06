from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .const import CONF_APP_VERSION, CONF_COUNTRY, CONF_LANGUAGE, DEFAULT_APP_VERSION, DEFAULT_COUNTRY, DEFAULT_LANGUAGE
from .ingredient_catalog import (
    Cook4MeIngredientCatalogCache,
    catalog_items_from_recipes,
    marketing_food_items,
    shopping_item_name,
)
from . import recipe_languages
from . import websocket as legacy
from . import websocket_v5 as v5
from . import websocket_v9 as v9
from .vendor import cook4me_phonefree as c4m
from .vendor import cook4me_recipe_catalog as recipe_catalog

_RECIPE_FALLBACK_SOURCE = "hydrated_official_recipes_fallback:v2_amount_clean"


async def _cache(bridge) -> Cook4MeIngredientCatalogCache:
    cache = getattr(bridge, "_ingredient_catalog_cache", None)
    if cache is None:
        cache = Cook4MeIngredientCatalogCache(bridge.hass, bridge.entry.entry_id)
        await cache.async_load()
        bridge._ingredient_catalog_cache = cache
    return cache


def _device_language(bridge) -> str:
    configured = str(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)).lower()
    return recipe_languages.normalize_catalog_language(configured, "de")


def _marketing_food_catalog_sync(bridge, language: str) -> tuple[list[dict[str, str]], str]:
    device_country = str(bridge.entry.data.get(CONF_COUNTRY, DEFAULT_COUNTRY)).upper()
    app_version = str(bridge.entry.data.get(CONF_APP_VERSION, DEFAULT_APP_VERSION))
    configured_language = str(bridge.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)).lower()
    country = recipe_languages.country_for_language(language, device_country)
    market = f"GS_{country}"
    cfg = c4m.read_apk_config(None)
    tokens = legacy._catalog_tokens(str(bridge.storage_home))
    pcfg = recipe_catalog._platform_context(cfg, country, configured_language, app_version)
    url = cfg["platform_base_url"].rstrip("/") + "/common-api/datarefs/marketingFoods/search"
    payload, auth_mode = recipe_catalog._http_json(
        "POST",
        url,
        headers_iter=recipe_catalog._request_headers(
            cfg,
            tokens,
            country,
            configured_language,
            app_version,
            url,
            pcfg,
        ),
        params={"lang": language, "market": market, "size": 5000},
        # The endpoint and query parameters are proven from the APK. The exact
        # th0.d body is not yet recovered, so send only its empty/default shape;
        # rejection is handled by the bounded recipe-derived fallback below.
        body={},
    )
    items = marketing_food_items(payload, language)
    if not items:
        raise recipe_catalog.CatalogError("SEB marketing-food catalog returned no ingredients")
    return items, f"seb_marketing_foods:{auth_mode}"


async def _recipe_fallback_catalog(hass: HomeAssistant, bridge, language: str) -> list[dict[str, str]]:
    recipes: list[dict[str, Any]] = []
    # Sample separate source-page windows to keep the fallback bounded while
    # avoiding repeatedly walking only the first serving variants.
    for page in (0, 10, 20, 30):
        raw, _cache_hit = await v9._raw_search(
            hass,
            bridge,
            query="",
            page=page,
            size=50,
            language=language,
            strict_language=True,
            refresh=True,
        )
        recipes.extend(row for row in raw.get("items") or [] if isinstance(row, dict))
        if len(recipes) >= 200:
            break
    return catalog_items_from_recipes(recipes)


async def _ingredient_catalog(
    hass: HomeAssistant, bridge, language: str, *, refresh: bool = False
) -> dict[str, Any]:
    language = recipe_languages.normalize_catalog_language(language, _device_language(bridge))
    cache = await _cache(bridge)
    if not refresh and (cached := cache.get(language)) is not None:
        return {
            "language": language,
            "items": cached.get("items") or [],
            "source": cached.get("source"),
            "cacheHit": True,
        }

    try:
        items, source = await hass.async_add_executor_job(
            _marketing_food_catalog_sync, bridge, language
        )
    except recipe_catalog.CatalogAuthError:
        await v9._refresh_catalog_auth(hass, bridge)
        try:
            items, source = await hass.async_add_executor_job(
                _marketing_food_catalog_sync, bridge, language
            )
        except Exception:
            items = await _recipe_fallback_catalog(hass, bridge, language)
            source = _RECIPE_FALLBACK_SOURCE
    except Exception:
        items = await _recipe_fallback_catalog(hass, bridge, language)
        source = _RECIPE_FALLBACK_SOURCE

    if not items:
        raise HomeAssistantError("Cook4Me ingredient catalog returned no usable ingredients")
    await cache.async_set(language, items, source=source)
    return {
        "language": language,
        "items": items,
        "source": source,
        "cacheHit": False,
    }


def _shopping_list_entity(hass: HomeAssistant) -> str | None:
    registry = er.async_get(hass)
    for entry in registry.entities.values():
        if entry.domain == "todo" and entry.platform == "shopping_list":
            return entry.entity_id
    return "todo.shopping_list" if hass.states.get("todo.shopping_list") else None


async def _shopping_names(hass: HomeAssistant) -> set[str]:
    entity_id = _shopping_list_entity(hass)
    if not entity_id or not hass.services.has_service("todo", "get_items"):
        return set()
    try:
        response = await hass.services.async_call(
            "todo",
            "get_items",
            {"entity_id": entity_id},
            blocking=True,
            return_response=True,
        )
    except Exception:
        return set()
    items: list[Any] = []
    if isinstance(response, dict):
        if isinstance(response.get("items"), list):
            items = response["items"]
        else:
            for value in response.values():
                if isinstance(value, dict) and isinstance(value.get("items"), list):
                    items.extend(value["items"])
    return {
        str(row.get("summary") or row.get("name") or "").strip().casefold()
        for row in items
        if isinstance(row, dict) and str(row.get("summary") or row.get("name") or "").strip()
    }


async def _add_to_shopping_list(hass: HomeAssistant, ingredients: list[Any]) -> dict[str, Any]:
    if not hass.services.has_service("shopping_list", "add_item"):
        raise HomeAssistantError("Home Assistant Shopping List is not available")
    existing = await _shopping_names(hass)
    added: list[str] = []
    skipped: list[str] = []
    seen = set(existing)
    for ingredient in ingredients:
        name = shopping_item_name(ingredient)
        if not name:
            continue
        folded = name.casefold()
        if folded in seen:
            skipped.append(name)
            continue
        await hass.services.async_call(
            "shopping_list", "add_item", {"name": name}, blocking=True
        )
        seen.add(folded)
        added.append(name)
    return {"added": added, "skippedExisting": skipped, "count": len(added)}


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_capabilities, ws_ingredient_catalog, ws_shopping_add):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v11/capabilities",
        vol.Optional("entry_id"): str,
    }
)
@callback
def ws_capabilities(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        device_language = _device_language(bridge)
        ai_task = v5._default_ai_task_entity_id(hass)
        result = {
            "languages": recipe_languages.language_options(),
            "deviceCatalogLanguage": device_language,
            "ingredientCatalogLanguage": device_language,
            "defaultAiTaskAvailable": ai_task is not None,
            "defaultAiTaskEntityId": ai_task,
            "preferences": bridge.recipe_hub.ui_preferences,
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v11/ingredient_catalog",
        vol.Optional("entry_id"): str,
        vol.Optional("language"): str,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_ingredient_catalog(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        language = str(msg.get("language") or _device_language(bridge))
        result = await _ingredient_catalog(
            hass, bridge, language, refresh=bool(msg.get("refresh"))
        )
        result["houseIngredients"] = bridge.recipe_hub.profile.get("houseIngredients") or []
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v11/shopping_add",
        vol.Optional("entry_id"): str,
        vol.Required("ingredients"): [vol.Any(str, dict)],
    }
)
@websocket_api.async_response
async def ws_shopping_add(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        legacy._bridge(hass, msg.get("entry_id"))
        result = await _add_to_shopping_list(hass, list(msg.get("ingredients") or []))
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
