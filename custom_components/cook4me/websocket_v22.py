from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import voluptuous as vol
from homeassistant.components import ai_task, persistent_notification, websocket_api
from homeassistant.core import HomeAssistant, callback

from . import recipe_languages
from . import websocket as legacy
from . import websocket_v5 as v5
from . import websocket_v10 as v10
from . import websocket_v11 as v11
from . import websocket_v12 as v12
from . import websocket_v13 as v13
from . import websocket_v18 as v18
from .const import DATA_BRIDGES, DOMAIN
from .food_intelligence import normalize_nutrition_goal
from .inventory import DEFAULT_EXPIRY_WARNING_DAYS, expiring_inventory_items
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .online_cache import online_cache_for_bridge
from .recipe_book import recipe_book_store_for_bridge
from .recipe_cache import stable_cache_key
from .recipe_experience import ingredient_matches, ingredient_name
from .request_coordinator import request_coordinator

_MAX_LANGUAGES = 8


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _selected_languages(bridge, values: Any) -> list[str]:
    raw = values if isinstance(values, list) else []
    out: list[str] = []
    for value in raw:
        code = _text(value).lower().replace("_", "-").split("-", 1)[0]
        if recipe_languages.is_official_catalog_language(code) and code not in out:
            out.append(code)
        if len(out) >= _MAX_LANGUAGES:
            break
    if not out:
        out = [v11._device_language(bridge)]
    return out


def _cacheable_catalog_result(result: dict[str, Any]) -> dict[str, Any]:
    # Device state, local profile annotations and diagnostic cache metadata are
    # not upstream catalog content. Keep only the online recipe response fields.
    excluded = {
        "deviceCanAccept",
        "loadedRecipe",
        "cacheHit",
        "checkedOnline",
        "changed",
        "checkedAt",
        "updatedAt",
    }
    return {key: deepcopy(value) for key, value in result.items() if key not in excluded}


def _decorate_catalog_items(bridge, result: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in result.get("items") or []:
        if not isinstance(raw, dict):
            continue
        source = {
            key: deepcopy(value)
            for key, value in raw.items()
            if key not in {"match", "deviceCanAccept"}
        }
        row = bridge.recipe_hub.annotate(source)
        row["deviceCanAccept"] = bridge.can_accept_recipe
        out.append(row)
    return out


async def _official_search(
    hass: HomeAssistant,
    bridge,
    *,
    languages: list[str],
    query: str,
    page: int,
    size: int,
    strict_language: bool,
) -> dict[str, Any]:
    cache = await online_cache_for_bridge(bridge)
    rows: list[dict[str, Any]] = []
    catalogs: list[dict[str, Any]] = []

    for language in languages:
        key = stable_cache_key(
            "official-search-v22",
            language,
            query.casefold(),
            int(page),
            int(size),
            bool(strict_language),
        )

        async def fetch(language: str = language) -> dict[str, Any]:
            result = await v10._search_with_diagnostic(
                hass,
                bridge,
                query=query,
                page=page,
                size=size,
                language=language,
                strict_language=strict_language,
                # The persistent v22 cache owns the >=24h revalidation rule.
                refresh=True,
            )
            return _cacheable_catalog_result(result)

        cached = await cache.async_get_or_revalidate(
            key,
            fetch,
            source=f"seb_catalog:{language}",
        )
        result = cached.get("value") if isinstance(cached.get("value"), dict) else {}
        decorated = _decorate_catalog_items(bridge, result)
        for item in decorated:
            item["officialCatalogLanguage"] = language
        rows.extend(decorated)
        catalogs.append(
            {
                "language": language,
                "ok": bool(result.get("ok", True)),
                "count": len(decorated),
                "cacheHit": bool(cached.get("cacheHit")),
                "checkedOnline": bool(cached.get("checkedOnline")),
                "changed": bool(cached.get("changed")),
                "checkedAt": cached.get("checkedAt") or "",
                "updatedAt": cached.get("updatedAt") or "",
                "lastError": cached.get("lastError") or "",
                "error": result.get("error") or "",
            }
        )

    deduped = v13._dedupe_recipes(rows)
    return {
        "items": deduped,
        "languages": languages,
        "catalogs": catalogs,
        "count": len(deduped),
        "deviceCanAccept": bridge.can_accept_recipe,
        "loadedRecipe": bridge.loaded_recipe,
    }


def _recent_titles(rows: Any, days: int) -> list[str]:
    if days <= 0:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[str] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        try:
            stamp = datetime.fromisoformat(_text(row.get("timestamp")))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            if stamp.astimezone(timezone.utc) < cutoff:
                continue
        except (TypeError, ValueError):
            continue
        title = _text(row.get("title"))
        if title and title not in out:
            out.append(title)
        if len(out) >= 20:
            break
    return out


def _ai_prompt(
    request: str,
    *,
    language: str,
    profile: dict[str, Any],
    house: list[dict[str, Any]],
    diet: str,
    meal_types: list[str],
    nutrition_goal: str,
    calorie_target: float | None,
    calorie_tolerance: int,
    max_missing: int | None,
    only_home: bool,
    prefer_expiring: bool,
    preferred_ingredients: list[dict[str, Any]],
    expiring_names: list[str],
    recent_titles: list[str],
) -> str:
    effective_diet = _text(profile.get("diet")) if diet == "profile" else diet
    selected_names = [ingredient_name(row) for row in preferred_ingredients]
    stock_names = [_text(row.get("name")) for row in house if isinstance(row, dict) and _text(row.get("name"))]
    requirements = [
        "Create exactly one Cook4Me-friendly home recipe.",
        f"Write all user-facing text in language code {language}.",
        f"User request: {request or 'Create a suitable recipe from the selected preferences.'}",
        f"Diet: {effective_diet or 'omnivore'}.",
        f"Allergies that must never appear: {', '.join(profile.get('allergies') or []) or 'none'}.",
        f"Avoid/dislike ingredients that must never appear: {', '.join(profile.get('avoid') or []) or 'none'}.",
        f"Meal categories requested: {', '.join(meal_types) or 'not specified'}.",
        f"Nutrition goal: {nutrition_goal}.",
    ]
    if calorie_target is not None:
        requirements.append(
            f"Target approximately {calorie_target:g} kcal per serving, within about ±{calorie_tolerance} percent when practical."
        )
    if selected_names:
        requirements.append(
            "The recipe must contain every explicitly preferred ingredient: " + ", ".join(selected_names) + "."
        )
    if only_home:
        requirements.append(
            "Use only ingredients from this available household list unless a basic cooking staple is unavoidable: "
            + (", ".join(stock_names[:150]) or "none listed")
            + "."
        )
    else:
        requirements.append(
            "Available household ingredients to prefer: " + (", ".join(stock_names[:150]) or "not specified") + "."
        )
    if max_missing is not None:
        requirements.append(f"Use no more than {max_missing} ingredients that are not already in the household stock when possible.")
    if prefer_expiring and expiring_names:
        requirements.append("Prefer using these ingredients that expire soon: " + ", ".join(expiring_names) + ".")
    if recent_titles:
        requirements.append("Do not recreate these recently cooked meals: " + "; ".join(recent_titles) + ".")
    requirements.extend(
        [
            "Return ONLY JSON with this exact schema: "
            '{"title":"...","servings":4,"ingredients":[{"name":"...","quantity":1,"unit":"g"}],'
            '"steps":[{"instruction":"..."}],"notes":"","tags":["..."]}.',
            "Use explicit quantities and units where known.",
            "Do not claim this custom recipe can be uploaded as an official SEB recipe.",
        ]
    )
    return "\n".join(requirements)


async def _map_ai_across_catalogs(hass, bridge, recipe: dict[str, Any], languages: list[str]) -> dict[str, Any]:
    mapped = dict(recipe)
    used: list[str] = []
    for language in languages:
        mapped = await v18._map_ai_ingredients_to_catalog(
            hass,
            bridge,
            mapped,
            language=language,
        )
        used.append(language)
        ingredients = [row for row in mapped.get("ingredients") or [] if isinstance(row, dict)]
        if ingredients and all(bool(row.get("catalogMapped")) for row in ingredients):
            break
    mapped["catalogLanguages"] = used
    return mapped


def _required_ingredients_present(recipe: dict[str, Any], preferred: list[dict[str, Any]]) -> bool:
    if not preferred:
        return True
    ingredients = [row for row in recipe.get("ingredients") or [] if isinstance(row, dict)]
    return all(any(ingredient_matches(item, wanted) for item in ingredients) for wanted in preferred)


def _notification_text(language: str, phase: str, detail: str = "") -> tuple[str, str]:
    language = language.lower().split("-", 1)[0]
    text = {
        "en": {
            "title": "Cook4Me · AI recipe",
            "running": "AI recipe generation is running. Other Cook4Me work waits in the serialized queue.",
            "done": "AI recipe generation finished.",
            "failed": "AI recipe generation failed.",
        },
        "de": {
            "title": "Cook4Me · KI-Rezept",
            "running": "Die KI-Rezepterstellung läuft. Andere Cook4Me-Vorgänge warten in der seriellen Warteschlange.",
            "done": "Die KI-Rezepterstellung ist abgeschlossen.",
            "failed": "Die KI-Rezepterstellung ist fehlgeschlagen.",
        },
        "el": {
            "title": "Cook4Me · Συνταγή AI",
            "running": "Η δημιουργία συνταγής AI εκτελείται. Οι άλλες εργασίες Cook4Me περιμένουν στη σειριακή ουρά.",
            "done": "Η δημιουργία συνταγής AI ολοκληρώθηκε.",
            "failed": "Η δημιουργία συνταγής AI απέτυχε.",
        },
    }.get(language) or {}
    title = text.get("title") or "Cook4Me · AI recipe"
    message = text.get(phase) or phase
    if detail:
        message = f"{message}\n\n{detail}"
    return title, message


async def _create_ai_recipe(hass: HomeAssistant, bridge, msg: dict[str, Any]) -> dict[str, Any]:
    if v5._default_ai_task_entity_id(hass) is None:
        raise ValueError("No default Home Assistant AI Task is configured")

    language = _text(msg.get("language") or "en").lower().split("-", 1)[0]
    catalog_languages = _selected_languages(bridge, msg.get("catalog_languages"))
    diet = _text(msg.get("diet") or "profile")
    meal_types = v18.normalize_meal_types(msg.get("meal_types")) if hasattr(v18, "normalize_meal_types") else [
        _text(value) for value in msg.get("meal_types") or [] if _text(value)
    ]
    nutrition_goal = normalize_nutrition_goal(msg.get("nutrition_goal"))
    calorie_target = _number(msg.get("calorie_target")) if "calorie_target" in msg else None
    calorie_tolerance = int(msg.get("calorie_tolerance", 25))
    max_missing = int(msg["max_missing"]) if "max_missing" in msg else None
    only_home = bool(msg.get("only_home"))
    prefer_expiring = bool(msg.get("prefer_expiring", True))
    avoid_recent_days = int(msg.get("avoid_recent_days", 7))
    preferred = [dict(row) for row in msg.get("ingredients") or [] if isinstance(row, dict)]

    profile = bridge.recipe_hub.profile
    house = profile.get("houseIngredients") or []
    history = await meal_history_store_for_bridge(bridge)
    recent_titles = _recent_titles(history.recent(200), avoid_recent_days)
    expiring_names = [
        _text(row.get("name"))
        for row in expiring_inventory_items(
            house,
            within_days=DEFAULT_EXPIRY_WARNING_DAYS,
            include_past=False,
        )[:20]
        if _text(row.get("name"))
    ]

    instructions = _ai_prompt(
        _text(msg.get("request")),
        language=language,
        profile=profile,
        house=house,
        diet=diet,
        meal_types=meal_types,
        nutrition_goal=nutrition_goal,
        calorie_target=calorie_target,
        calorie_tolerance=calorie_tolerance,
        max_missing=max_missing,
        only_home=only_home,
        prefer_expiring=prefer_expiring,
        preferred_ingredients=preferred,
        expiring_names=expiring_names,
        recent_titles=recent_titles,
    )

    result = await ai_task.async_generate_data(
        hass,
        task_name="Cook4Me recipe generation",
        entity_id=None,
        instructions=instructions,
    )
    recipe = v5._parse_ai_json(result.data)
    if not isinstance(recipe, dict):
        raise ValueError("AI Task did not return a valid recipe JSON object")

    recipe = await _map_ai_across_catalogs(hass, bridge, recipe, catalog_languages)
    if not _required_ingredients_present(recipe, preferred):
        raise ValueError("AI recipe did not contain every selected preferred ingredient")

    ranked = v13._rank_filtered(bridge, [recipe], diet=diet, limit=1)
    if not ranked:
        raise ValueError("AI recipe failed the selected diet/allergy safety rules")
    checked = ranked[0]
    shortages = checked.get("match", {}).get("quantityShortages") or []
    if only_home and not checked.get("match", {}).get("fullyAvailableByQuantity"):
        raise ValueError("AI recipe requires ingredients not proven available at home")
    if max_missing is not None and len(shortages) > max_missing:
        raise ValueError("AI recipe exceeds the selected maximum missing ingredients")

    nutrition_store = await nutrition_store_for_bridge(bridge)
    checked["nutrition"] = calculate_recipe_nutrition_fefo(
        checked,
        house,
        generic=nutrition_store.generic,
        stock_lots=nutrition_store.stock_lots,
    )
    checked["aiPreferences"] = {
        "catalogLanguages": catalog_languages,
        "diet": diet,
        "mealTypes": meal_types,
        "nutritionGoal": nutrition_goal,
        "calorieTarget": calorie_target,
        "calorieTolerance": calorie_tolerance,
        "maxMissing": max_missing,
        "onlyHome": only_home,
        "preferExpiring": prefer_expiring,
        "avoidRecentDays": avoid_recent_days,
        "preferredIngredients": preferred,
    }
    saved = await bridge.recipe_hub.async_save_recipe(checked, source="ai")
    return {
        "recipe": bridge.recipe_hub.annotate(saved),
        "catalogLanguages": catalog_languages,
        "aiTaskEntityId": v5._default_ai_task_entity_id(hass),
    }


async def _send_one(bridge, recipe: dict[str, Any]) -> dict[str, Any]:
    variant = _text(
        recipe.get("sendVariantId")
        or recipe.get("selectedSendVariantId")
        or recipe.get("searchVariantId")
        or recipe.get("variantFunctionalId")
        or recipe.get("recipeFunctionalId")
    )
    if not variant or recipe.get("sendable") is False and not recipe.get("groupingFunctionalId"):
        return {"sent": False, "queued": False, "reason": "custom_recipe_has_no_official_seb_id"}

    if bridge.available:
        try:
            result = await v12._send_recipe_replaceable(bridge, variant)
        except Exception as exc:
            reason = "device_busy" if bridge.available else "device_offline"
            store = await recipe_book_store_for_bridge(bridge)
            queued = await store.async_queue_send(recipe, reason=reason)
            return {"sent": False, "queued": True, "reason": reason, "queuedSend": queued, "error": str(exc)[:300]}
        store = await recipe_book_store_for_bridge(bridge)
        await store.async_clear_queue()
        return {"sent": True, "queued": False, "result": result}

    store = await recipe_book_store_for_bridge(bridge)
    queued = await store.async_queue_send(recipe, reason="device_offline")
    return {"sent": False, "queued": True, "reason": "device_offline", "queuedSend": queued}


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_work_state,
        ws_official_search,
        ws_ai_create,
        ws_send_multi,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v22/work_state",
})
@websocket_api.async_response
async def ws_work_state(hass, connection, msg) -> None:
    coordinator = await request_coordinator(hass)
    connection.send_result(msg["id"], coordinator.snapshot)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v22/official_search",
    vol.Optional("entry_id"): str,
    vol.Optional("query", default=""): str,
    vol.Optional("page", default=0): vol.Coerce(int),
    vol.Optional("size", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
    vol.Optional("languages", default=[]): [str],
    vol.Optional("strict_language", default=True): bool,
})
@websocket_api.async_response
async def ws_official_search(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        languages = _selected_languages(bridge, msg.get("languages"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "official_search",
            "Official recipe catalog search",
            entry_ids=[bridge.entry.entry_id],
        ):
            result = await _official_search(
                hass,
                bridge,
                languages=languages,
                query=_text(msg.get("query")),
                page=int(msg.get("page", 0)),
                size=int(msg.get("size", 20)),
                strict_language=bool(msg.get("strict_language", True)),
            )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v22/ai_create",
    vol.Optional("entry_id"): str,
    vol.Optional("request", default=""): str,
    vol.Optional("language", default="en"): str,
    vol.Optional("catalog_languages", default=[]): [str],
    vol.Optional("diet", default="profile"): vol.In(v18._DIET_FILTERS),
    vol.Optional("meal_types", default=[]): [str],
    vol.Optional("nutrition_goal", default="balanced"): str,
    vol.Optional("calorie_target"): vol.Any(int, float, str),
    vol.Optional("calorie_tolerance", default=25): vol.All(vol.Coerce(int), vol.Range(min=5, max=100)),
    vol.Optional("max_missing"): vol.All(vol.Coerce(int), vol.Range(min=0, max=20)),
    vol.Optional("only_home", default=False): bool,
    vol.Optional("prefer_expiring", default=True): bool,
    vol.Optional("avoid_recent_days", default=7): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
    vol.Optional("ingredients", default=[]): [dict],
})
@websocket_api.async_response
async def ws_ai_create(hass, connection, msg) -> None:
    bridge = None
    notification_id = "cook4me_ai_recipe"
    language = _text(msg.get("language") or "en")
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        notification_id = f"cook4me_ai_recipe_{bridge.entry.entry_id}"
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "ai_recipe",
            "AI recipe generation",
            entry_ids=[bridge.entry.entry_id],
        ):
            title, message = _notification_text(language, "running")
            persistent_notification.async_create(
                hass,
                message,
                title=title,
                notification_id=notification_id,
            )
            result = await _create_ai_recipe(hass, bridge, msg)
            recipe_title = _text(result.get("recipe", {}).get("title"))
            title, message = _notification_text(language, "done", recipe_title)
            persistent_notification.async_create(
                hass,
                message,
                title=title,
                notification_id=notification_id,
            )
    except Exception as exc:
        title, message = _notification_text(language, "failed", str(exc)[:300])
        persistent_notification.async_create(
            hass,
            message,
            title=title,
            notification_id=notification_id,
        )
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v22/send_multi",
    vol.Optional("entry_id"): str,
    vol.Optional("entry_ids", default=[]): [str],
    vol.Required("recipe"): dict,
})
@websocket_api.async_response
async def ws_send_multi(hass, connection, msg) -> None:
    try:
        primary = legacy._bridge(hass, msg.get("entry_id"))
        bridges = hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {})
        requested = [str(value) for value in msg.get("entry_ids") or [] if str(value)]
        if not requested:
            requested = [primary.entry.entry_id]
        selected = []
        seen = set()
        for entry_id in requested:
            bridge = bridges.get(entry_id)
            if bridge is not None and entry_id not in seen:
                selected.append(bridge)
                seen.add(entry_id)
        if not selected:
            raise ValueError("No selected Cook4Me device is currently loaded")

        recipe = dict(msg["recipe"])
        coordinator = await request_coordinator(hass)
        results = []
        async with coordinator.operation(
            "device_send",
            "Send official recipe to selected Cook4Me devices",
            entry_ids=[bridge.entry.entry_id for bridge in selected],
        ):
            for bridge in selected:
                row = await _send_one(bridge, recipe)
                results.append(
                    {
                        "entryId": bridge.entry.entry_id,
                        "title": bridge.entry.title,
                        **row,
                    }
                )
        result = {
            "results": results,
            "targetCount": len(results),
            "sentCount": sum(bool(row.get("sent")) for row in results),
            "queuedCount": sum(bool(row.get("queued")) for row in results),
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)
