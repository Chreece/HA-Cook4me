from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from typing import Any

import voluptuous as vol
from homeassistant.components import ai_task, websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import recipe_languages
from . import websocket as legacy
from . import websocket_v5 as v5
from . import websocket_v10 as v10
from . import websocket_v11 as v11
from . import websocket_v13 as v13
from .barcode import confident_match, suggest_catalog_matches
from .const import DATA_BRIDGES, DOMAIN
from .food_intelligence import nutrition_goal_bonus, normalize_nutrition_goal
from .inventory import inventory_identity
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .recipe_book import recipe_book_store_for_bridge
from .recipe_experience import ingredient_matches, ingredient_name, recipe_storage_key
from .today_logic import (
    MEAL_TYPES,
    calorie_target_bonus,
    normalize_meal_types,
    recipe_identity,
    recipe_matches_meal_types,
    select_diverse,
)

_DIET_FILTERS = ("profile", "omnivore", "pescatarian", "vegetarian", "vegan")
_MAX_LANGUAGES = 8
_QUEUE_POLL_SECONDS = 5


def _languages(bridge, raw: Any) -> list[str]:
    values = raw if isinstance(raw, list) else []
    out: list[str] = []
    for value in values:
        code = str(value or "").strip().lower().replace("_", "-").split("-", 1)[0]
        if recipe_languages.is_official_catalog_language(code) and code not in out:
            out.append(code)
        if len(out) >= _MAX_LANGUAGES:
            break
    if not out:
        out = [v11._device_language(bridge)]
    return out


def _history_identity(row: dict[str, Any]) -> str:
    return recipe_identity(row)


def _recent_identities(rows: Any, *, days: int) -> set[str]:
    if days <= 0 or not isinstance(rows, list):
        return set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        stamp = str(row.get("timestamp") or "").strip()
        try:
            parsed = datetime.fromisoformat(stamp)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            parsed = parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        if parsed < cutoff:
            continue
        ident = _history_identity(row)
        if ident:
            out.add(ident)
    return out


async def _search_catalogs(
    hass: HomeAssistant,
    bridge,
    *,
    languages: list[str],
    query: str,
    catalog_size: int,
    refresh: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    async def one(language: str):
        result = await v10._search_with_diagnostic(
            hass,
            bridge,
            query=query,
            page=0,
            size=catalog_size,
            language=language,
            strict_language=True,
            refresh=refresh,
        )
        return language, result

    responses = await asyncio.gather(
        *(one(language) for language in languages), return_exceptions=True
    )
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for response in responses:
        if isinstance(response, Exception):
            errors.append({"language": "", "reason": type(response).__name__})
            continue
        language, result = response
        if not result.get("ok", True):
            errors.append(
                {
                    "language": language,
                    "reason": str(
                        result.get("reason") or result.get("error") or "catalog_error"
                    )[:120],
                }
            )
            continue
        for raw in result.get("items") or []:
            if not isinstance(raw, dict):
                continue
            row = dict(raw)
            row["todayCatalogLanguage"] = language
            candidates.append(row)
    return v13._dedupe_recipes(candidates), errors


async def _flush_one_queued_send(bridge) -> None:
    if getattr(bridge, "_cook4me_queued_send_running", False):
        return
    if not bridge.can_accept_recipe:
        return
    store = await recipe_book_store_for_bridge(bridge)
    queued = store.queued_send
    if not queued:
        return
    variant = str(queued.get("variantId") or "").strip()
    if not variant:
        await store.async_clear_queue()
        return
    bridge._cook4me_queued_send_running = True
    try:
        await bridge.async_send_variant(variant)
    except Exception:
        # Keep the request cached. Device state and cloud credentials can recover later.
        return
    else:
        await store.async_clear_queue()
    finally:
        bridge._cook4me_queued_send_running = False


async def _send_queue_watch_loop(hass: HomeAssistant) -> None:
    while True:
        try:
            bridges = list(
                hass.data.get(DOMAIN, {}).get(DATA_BRIDGES, {}).values()
            )
            for bridge in bridges:
                if bridge.can_accept_recipe:
                    hass.async_create_task(_flush_one_queued_send(bridge))
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(_QUEUE_POLL_SECONDS)


def _ensure_queue_watch(hass: HomeAssistant) -> None:
    data = hass.data.setdefault(DOMAIN, {})
    task = data.get("recipe_send_queue_watch")
    if task is None or task.done():
        data["recipe_send_queue_watch"] = hass.async_create_background_task(
            _send_queue_watch_loop(hass), "cook4me_recipe_send_queue"
        )


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_today_options,
        ws_today_suggest,
        ws_recipe_book_state,
        ws_recipe_book_toggle,
        ws_send_or_queue,
        ws_send_queue_clear,
        ws_ingredient_info,
        ws_ai_generate,
    ):
        websocket_api.async_register_command(hass, command)
    _ensure_queue_watch(hass)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v18/today_options",
        vol.Optional("entry_id"): str,
    }
)
@callback
def ws_today_options(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        connection.send_result(
            msg["id"],
            {
                "languages": recipe_languages.language_options(),
                "defaultLanguage": v11._device_language(bridge),
                "maxLanguages": _MAX_LANGUAGES,
                "mealTypes": list(MEAL_TYPES),
                "nutritionGoals": [
                    "balanced",
                    "high_protein",
                    "lower_calorie",
                    "high_fiber",
                    "lower_saturated_fat",
                ],
                "dietOptions": list(_DIET_FILTERS),
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v18/today_suggest",
        vol.Optional("entry_id"): str,
        vol.Optional("languages", default=[]): [str],
        vol.Optional("diet", default="profile"): vol.In(_DIET_FILTERS),
        vol.Optional("meal_types", default=[]): [str],
        vol.Optional("only_home", default=False): bool,
        vol.Optional("nutrition_goal", default="balanced"): str,
        vol.Optional("meal_count", default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=8)
        ),
        vol.Optional("calorie_target"): vol.Any(int, float, str),
        vol.Optional("calorie_tolerance", default=25): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=100)
        ),
        vol.Optional("max_missing"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=20)
        ),
        vol.Optional("prefer_expiring", default=True): bool,
        vol.Optional("avoid_recent_days", default=7): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=90)
        ),
        vol.Optional("variety", default=True): bool,
        vol.Optional("query", default=""): str,
        vol.Optional("catalog_size", default=40): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=50)
        ),
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_today_suggest(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        languages = _languages(bridge, msg.get("languages"))
        diet = str(msg.get("diet") or "profile")
        meal_types = normalize_meal_types(msg.get("meal_types"))
        query = str(msg.get("query") or "").strip()
        only_home = bool(msg.get("only_home"))
        prefer_expiring = bool(msg.get("prefer_expiring", True))
        goal = normalize_nutrition_goal(msg.get("nutrition_goal"))
        meal_count = int(msg.get("meal_count", 1))
        max_missing = msg.get("max_missing") if "max_missing" in msg else None
        avoid_recent_days = int(msg.get("avoid_recent_days", 7))
        calorie_tolerance = int(msg.get("calorie_tolerance", 25)) / 100.0

        candidates, catalog_errors = await _search_catalogs(
            hass,
            bridge,
            languages=languages,
            query=query,
            catalog_size=int(msg.get("catalog_size", 40)),
            refresh=bool(msg.get("refresh")),
        )
        if meal_types:
            candidates = [
                row
                for row in candidates
                if recipe_matches_meal_types(row, meal_types)
            ]

        history_store = await meal_history_store_for_bridge(bridge)
        recent = _recent_identities(
            history_store.recent(200), days=avoid_recent_days
        )
        if recent:
            candidates = [
                row for row in candidates if recipe_identity(row) not in recent
            ]

        ranked = v13._rank_filtered(bridge, candidates, diet=diet, limit=30)
        nutrition_store = await nutrition_store_for_bridge(bridge)
        house = bridge.recipe_hub.profile.get("houseIngredients") or []
        scored: list[dict[str, Any]] = []
        for item in ranked:
            match = item.setdefault("match", {})
            if only_home and not bool(match.get("fullyAvailableByQuantity")):
                continue
            shortages = (
                match.get("quantityShortages")
                if isinstance(match.get("quantityShortages"), list)
                else []
            )
            if max_missing is not None and len(shortages) > int(max_missing):
                continue

            current_score = float(match.get("score") or 0.0)
            if not prefer_expiring:
                current_score -= float(match.get("expiryBonus") or 0.0)
                match["todayExpiryBonusSuppressed"] = True

            nutrition = calculate_recipe_nutrition_fefo(
                item,
                house,
                generic=nutrition_store.generic,
                stock_lots=nutrition_store.stock_lots,
            )
            item["nutrition"] = nutrition
            nutrition_hint = nutrition_goal_bonus(nutrition, goal)
            calorie_hint = calorie_target_bonus(
                nutrition,
                msg.get("calorie_target"),
                tolerance_fraction=calorie_tolerance,
            )
            match["nutritionGoal"] = goal
            match["nutritionGoalBonus"] = nutrition_hint.get("bonus", 0.0)
            match["nutritionGoalCoverage"] = nutrition_hint.get("coverage", 0.0)
            match["calorieTarget"] = calorie_hint.get("target")
            match["caloriePerServing"] = calorie_hint.get("calories")
            match["calorieDelta"] = calorie_hint.get("delta")
            match["calorieTargetBonus"] = calorie_hint.get("bonus", 0.0)
            match["todayBaseScore"] = round(current_score, 1)
            match["score"] = round(
                current_score
                + float(nutrition_hint.get("bonus") or 0.0)
                + float(calorie_hint.get("bonus") or 0.0),
                1,
            )
            item["deviceCanAccept"] = bridge.can_accept_recipe
            scored.append(item)

        scored.sort(
            key=lambda row: row.get("match", {}).get("score", -1000),
            reverse=True,
        )
        chosen = select_diverse(
            scored, meal_count, enabled=bool(msg.get("variety", True))
        )
        connection.send_result(
            msg["id"],
            {
                "date": dt_util.now().date().isoformat(),
                "items": chosen,
                "candidateCount": len(candidates),
                "rankedCount": len(scored),
                "catalogErrors": catalog_errors,
                "filters": {
                    "languages": languages,
                    "diet": diet,
                    "mealTypes": meal_types,
                    "onlyHome": only_home,
                    "nutritionGoal": goal,
                    "mealCount": meal_count,
                    "calorieTarget": msg.get("calorie_target"),
                    "calorieTolerancePercent": int(
                        msg.get("calorie_tolerance", 25)
                    ),
                    "maxMissing": max_missing,
                    "preferExpiring": prefer_expiring,
                    "avoidRecentDays": avoid_recent_days,
                    "variety": bool(msg.get("variety", True)),
                    "query": query,
                },
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v19/book_state",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_recipe_book_state(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await recipe_book_store_for_bridge(bridge)
        connection.send_result(
            msg["id"],
            {
                **store.snapshot(),
                "deviceConnected": bridge.available,
                "deviceCanAccept": bridge.can_accept_recipe,
                "loadedRecipe": bridge.loaded_recipe,
                "myRecipes": bridge.recipe_hub.recipes,
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v19/book_toggle",
        vol.Optional("entry_id"): str,
        vol.Required("collection"): vol.In(["favorites", "recipeList"]),
        vol.Required("recipe"): dict,
    }
)
@websocket_api.async_response
async def ws_recipe_book_toggle(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await recipe_book_store_for_bridge(bridge)
        result = await store.async_toggle(str(msg["collection"]), dict(msg["recipe"]))
        connection.send_result(msg["id"], result)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v19/send_or_queue",
        vol.Optional("entry_id"): str,
        vol.Required("recipe"): dict,
    }
)
@websocket_api.async_response
async def ws_send_or_queue(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"])
        variant = str(
            recipe.get("sendVariantId")
            or recipe.get("variantFunctionalId")
            or recipe.get("recipeFunctionalId")
            or ""
        ).strip()
        if not variant or recipe.get("sendable") is False and not recipe.get("groupingFunctionalId"):
            connection.send_result(
                msg["id"],
                {
                    "sent": False,
                    "queued": False,
                    "sendable": False,
                    "reason": "custom_recipe_has_no_official_seb_id",
                },
            )
            return
        if bridge.can_accept_recipe:
            result = await bridge.async_send_variant(variant)
            store = await recipe_book_store_for_bridge(bridge)
            await store.async_clear_queue()
            connection.send_result(
                msg["id"], {"sent": True, "queued": False, "result": result}
            )
            return
        reason = "device_offline" if not bridge.available else "device_busy"
        store = await recipe_book_store_for_bridge(bridge)
        queued = await store.async_queue_send(recipe, reason=reason)
        connection.send_result(
            msg["id"],
            {
                "sent": False,
                "queued": True,
                "sendable": True,
                "reason": reason,
                **queued,
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v19/send_queue_clear",
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_send_queue_clear(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await recipe_book_store_for_bridge(bridge)
        previous = await store.async_clear_queue()
        connection.send_result(msg["id"], {"cleared": bool(previous), "previous": previous})
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


def _find_stock_row(house: Any, ingredient: dict[str, Any]) -> dict[str, Any] | None:
    wanted = inventory_identity(ingredient)
    for row in house if isinstance(house, list) else []:
        if isinstance(row, dict) and inventory_identity(row) == wanted:
            return deepcopy(row)
    return None


def _usage_from_saved(recipes: Any, ingredient: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for recipe in recipes if isinstance(recipes, list) else []:
        if not isinstance(recipe, dict):
            continue
        if any(ingredient_matches(row, ingredient) for row in recipe.get("ingredients") or []):
            out.append(
                {
                    "title": str(recipe.get("title") or "Recipe"),
                    "source": str(recipe.get("source") or "saved"),
                    "recipe": deepcopy(recipe),
                }
            )
    return out[:30]


def _meal_usage(rows: Any, ingredient: dict[str, Any]) -> list[dict[str, Any]]:
    wanted = inventory_identity(ingredient)
    out: list[dict[str, Any]] = []
    for meal in rows if isinstance(rows, list) else []:
        if not isinstance(meal, dict):
            continue
        matched = []
        for row in meal.get("ingredients") or []:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("identity") or "")
            if row_id == wanted or ingredient_matches(row, ingredient):
                matched.append(deepcopy(row))
        if matched:
            out.append(
                {
                    "timestamp": meal.get("timestamp"),
                    "title": meal.get("title"),
                    "ingredients": matched,
                    "nutrition": deepcopy(
                        meal.get("consumedNutrition") or meal.get("nutrition") or {}
                    ),
                }
            )
    return out[:50]


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v19/ingredient_info",
        vol.Optional("entry_id"): str,
        vol.Required("ingredient"): dict,
        vol.Optional("language"): str,
        vol.Optional("include_official_usage", default=True): bool,
    }
)
@websocket_api.async_response
async def ws_ingredient_info(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        ingredient = dict(msg["ingredient"])
        name = ingredient_name(ingredient)
        house = bridge.recipe_hub.profile.get("houseIngredients") or []
        stock = _find_stock_row(house, ingredient)
        identity = inventory_identity(stock or ingredient)
        nutrition_store = await nutrition_store_for_bridge(bridge)
        generic = nutrition_store.get_generic(identity) if identity else None
        exact_lots = (
            nutrition_store.stock_lots.get(identity, []) if identity else []
        )
        history_store = await meal_history_store_for_bridge(bridge)
        history = _meal_usage(history_store.recent(200), stock or ingredient)
        book = await recipe_book_store_for_bridge(bridge)
        book_state = book.snapshot()
        saved = _usage_from_saved(
            bridge.recipe_hub.recipes
            + list(book_state.get("favorites") or [])
            + list(book_state.get("recipeList") or []),
            stock or ingredient,
        )

        official: list[dict[str, Any]] = []
        if name and bool(msg.get("include_official_usage", True)):
            language = str(msg.get("language") or v11._device_language(bridge))
            try:
                search = await v10._search_with_diagnostic(
                    hass,
                    bridge,
                    query=name,
                    page=0,
                    size=12,
                    language=language,
                    strict_language=False,
                    refresh=False,
                )
                if search.get("ok", True):
                    official = [
                        row
                        for row in search.get("items") or []
                        if isinstance(row, dict)
                    ][:12]
            except Exception:
                official = []

        connection.send_result(
            msg["id"],
            {
                "identity": identity,
                "ingredient": {
                    **({"key": stock.get("key")} if stock and stock.get("key") else {}),
                    "name": name or (stock or {}).get("name") or "Ingredient",
                },
                "stock": stock,
                "genericNutrition": generic,
                "exactNutritionLots": exact_lots,
                "history": history,
                "historyCount": len(history),
                "savedRecipeUsage": saved,
                "officialRecipeUsage": official,
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


def _ai_recipe_prompt(
    request: str,
    *,
    language: str,
    profile: dict[str, Any],
    house: list[dict[str, Any]],
) -> str:
    return (
        "Create exactly one Cook4Me-friendly home recipe. "
        f"Write user-facing text in language code {language}. "
        f"User request: {request}\n"
        f"Diet: {profile.get('diet') or 'omnivore'}\n"
        f"Allergies: {', '.join(profile.get('allergies') or []) or 'none'}\n"
        f"Avoid/dislike: {', '.join(profile.get('avoid') or []) or 'none'}\n"
        "Available house ingredients: "
        + (", ".join(str(row.get("name") or "") for row in house[:120]) or "not specified")
        + "\nReturn ONLY JSON with this exact schema: "
        '{"title":"...","servings":4,"ingredients":[{"name":"...","quantity":1,"unit":"g"}],'
        '"steps":[{"instruction":"..."}],"notes":"","tags":["..."]}. '
        "Never include an allergen or avoided ingredient. Use explicit quantities and units where known. "
        "Do not claim the custom recipe can be uploaded as an official SEB recipe."
    )


async def _map_ai_ingredients_to_catalog(
    hass: HomeAssistant,
    bridge,
    recipe: dict[str, Any],
    *,
    language: str,
) -> dict[str, Any]:
    try:
        result = await v11._ingredient_catalog(hass, bridge, language, refresh=False)
        catalog = [row for row in result.get("items") or [] if isinstance(row, dict)]
    except Exception:
        catalog = []
    mapped: list[dict[str, Any]] = []
    for raw in recipe.get("ingredients") or []:
        if isinstance(raw, str):
            item: dict[str, Any] = {"name": raw.strip()}
        elif isinstance(raw, dict):
            item = dict(raw)
        else:
            continue
        name = str(item.get("name") or item.get("foodName") or "").strip()
        if not name:
            continue
        suggestions = suggest_catalog_matches(
            {"genericName": name, "productName": name, "categories": []},
            catalog,
            limit=5,
        ) if catalog else []
        chosen = confident_match(suggestions)
        if chosen:
            ing = chosen["ingredient"]
            item["name"] = str(ing.get("name") or name)
            item["catalogName"] = item["name"]
            if ing.get("key"):
                item["foodKey"] = str(ing["key"])
                item["catalogKey"] = str(ing["key"])
            item["catalogMapped"] = True
        mapped.append(item)
    recipe = dict(recipe)
    recipe["ingredients"] = mapped
    recipe["catalogLanguage"] = language
    return recipe


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v19/ai_generate",
        vol.Optional("entry_id"): str,
        vol.Required("request"): str,
        vol.Optional("language"): str,
        vol.Optional("catalog_language"): str,
    }
)
@websocket_api.async_response
async def ws_ai_generate(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        request = str(msg.get("request") or "").strip()
        if not request:
            raise ValueError("AI recipe request is empty")
        if v5._default_ai_task_entity_id(hass) is None:
            raise ValueError("No default Home Assistant AI Task is configured")
        language = str(msg.get("language") or "en").lower().split("-", 1)[0]
        catalog_language = recipe_languages.normalize_catalog_language(
            msg.get("catalog_language"), v11._device_language(bridge)
        )
        profile = bridge.recipe_hub.profile
        house = profile.get("houseIngredients") or []
        result = await ai_task.async_generate_data(
            hass,
            task_name="Cook4Me recipe generation",
            entity_id=None,
            instructions=_ai_recipe_prompt(
                request, language=language, profile=profile, house=house
            ),
        )
        recipe = v5._parse_ai_json(result.data)
        if not isinstance(recipe, dict):
            raise ValueError("AI Task did not return a valid recipe JSON object")
        recipe = await _map_ai_ingredients_to_catalog(
            hass, bridge, recipe, language=catalog_language
        )
        saved = await bridge.recipe_hub.async_save_recipe(recipe, source="ai")
        annotated = bridge.recipe_hub.annotate(saved)
        connection.send_result(
            msg["id"],
            {
                "recipe": annotated,
                "catalogLanguage": catalog_language,
                "aiTaskEntityId": v5._default_ai_task_entity_id(hass),
            },
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
