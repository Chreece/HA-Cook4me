from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import websocket as legacy
from . import websocket_v10 as v10
from . import websocket_v13 as v13
from . import websocket_v18 as v18
from .food_intelligence import nutrition_goal_bonus, normalize_nutrition_goal
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .today_logic import (
    calorie_target_bonus,
    normalize_meal_types,
    recipe_identity,
    recipe_matches_meal_types,
    select_diverse,
)


_RESTRICTED_DIETS = {"vegetarian", "vegan", "pescatarian"}


def _effective_diet(bridge, selected: str) -> str:
    value = str(selected or "profile").strip().lower()
    if value == "profile":
        value = str(bridge.recipe_hub.profile.get("diet") or "omnivore").strip().lower()
    return value or "omnivore"


def _catalog_page_count(bridge, *, diet: str, query: str) -> int:
    """Use a substantially broader corpus for restrictive diets.

    The old Today path only inspected page 0 (50 publications). For vegetarian/
    vegan/pescatarian profiles that frequently left only one or two eligible
    recipes after safety/taxonomy filtering, so the frontend rotation had
    nothing meaningful to rotate through.
    """

    restricted = _effective_diet(bridge, diet) in _RESTRICTED_DIETS
    if str(query or "").strip():
        return 5 if restricted else 3
    return 8 if restricted else 4


async def _search_catalogs_paginated(
    hass: HomeAssistant,
    bridge,
    *,
    languages: list[str],
    query: str,
    catalog_size: int,
    refresh: bool,
    page_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    """Read several official search pages per language, then de-duplicate them."""

    async def one(language: str):
        rows: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        fetched = 0
        for page in range(max(1, int(page_count))):
            try:
                result = await v10._search_with_diagnostic(
                    hass,
                    bridge,
                    query=query,
                    page=page,
                    size=catalog_size,
                    language=language,
                    strict_language=True,
                    refresh=refresh,
                )
            except Exception as exc:
                errors.append({"language": language, "reason": type(exc).__name__})
                break
            if not result.get("ok", True):
                errors.append(
                    {
                        "language": language,
                        "reason": str(
                            result.get("reason")
                            or result.get("error")
                            or "catalog_error"
                        )[:120],
                    }
                )
                break
            items = [row for row in result.get("items") or [] if isinstance(row, dict)]
            if not items:
                break
            fetched += 1
            for raw in items:
                row = deepcopy(raw)
                row["todayCatalogLanguage"] = language
                rows.append(row)
            if len(items) < catalog_size:
                break
        return rows, errors, fetched

    responses = await asyncio.gather(*(one(language) for language in languages))
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    fetched_pages = 0
    for rows, language_errors, fetched in responses:
        candidates.extend(rows)
        errors.extend(language_errors)
        fetched_pages += fetched
    return v13._dedupe_recipes(candidates), errors, fetched_pages


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_today_suggest)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v19/today_suggest",
        vol.Optional("entry_id"): str,
        vol.Optional("languages", default=[]): [str],
        vol.Optional("diet", default="profile"): vol.In(v18._DIET_FILTERS),
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
        vol.Optional("catalog_size", default=50): vol.All(
            vol.Coerce(int), vol.Range(min=10, max=50)
        ),
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_today_suggest(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        languages = v18._languages(bridge, msg.get("languages"))
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
        page_count = _catalog_page_count(bridge, diet=diet, query=query)

        candidates, catalog_errors, fetched_pages = await _search_catalogs_paginated(
            hass,
            bridge,
            languages=languages,
            query=query,
            catalog_size=int(msg.get("catalog_size", 50)),
            refresh=bool(msg.get("refresh")),
            page_count=page_count,
        )
        if meal_types:
            candidates = [
                row
                for row in candidates
                if recipe_matches_meal_types(row, meal_types)
            ]

        history_store = await meal_history_store_for_bridge(bridge)
        recent = v18._recent_identities(
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
                "catalogPagesRequested": page_count,
                "catalogPagesFetched": fetched_pages,
                "effectiveDiet": _effective_diet(bridge, diet),
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
