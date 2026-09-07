from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import recipe_languages
from . import websocket as legacy
from . import websocket_v10 as v10
from . import websocket_v11 as v11
from . import websocket_v13 as v13
from .food_intelligence import nutrition_goal_bonus, normalize_nutrition_goal
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
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
        *(one(language) for language in languages),
        return_exceptions=True,
    )
    candidates: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for response in responses:
        if isinstance(response, Exception):
            errors.append({"language": "", "reason": type(response).__name__})
            continue
        language, result = response
        if not result.get("ok", True):
            errors.append({
                "language": language,
                "reason": str(result.get("reason") or result.get("error") or "catalog_error")[:120],
            })
            continue
        for raw in result.get("items") or []:
            if not isinstance(raw, dict):
                continue
            row = dict(raw)
            row["todayCatalogLanguage"] = language
            candidates.append(row)
    return v13._dedupe_recipes(candidates), errors


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_today_options, ws_today_suggest):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v18/today_options",
    vol.Optional("entry_id"): str,
})
@callback
def ws_today_options(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        connection.send_result(msg["id"], {
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
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v18/today_suggest",
    vol.Optional("entry_id"): str,
    vol.Optional("languages", default=[]): [str],
    vol.Optional("diet", default="profile"): vol.In(_DIET_FILTERS),
    vol.Optional("meal_types", default=[]): [str],
    vol.Optional("only_home", default=False): bool,
    vol.Optional("nutrition_goal", default="balanced"): str,
    vol.Optional("meal_count", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=8)),
    vol.Optional("calorie_target"): vol.Any(int, float, str),
    vol.Optional("calorie_tolerance", default=25): vol.All(vol.Coerce(int), vol.Range(min=5, max=100)),
    vol.Optional("max_missing"): vol.All(vol.Coerce(int), vol.Range(min=0, max=20)),
    vol.Optional("prefer_expiring", default=True): bool,
    vol.Optional("avoid_recent_days", default=7): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
    vol.Optional("variety", default=True): bool,
    vol.Optional("query", default=""): str,
    vol.Optional("catalog_size", default=40): vol.All(vol.Coerce(int), vol.Range(min=10, max=50)),
    vol.Optional("refresh", default=False): bool,
})
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
                row for row in candidates
                if recipe_matches_meal_types(row, meal_types)
            ]

        history_store = await meal_history_store_for_bridge(bridge)
        recent = _recent_identities(history_store.recent(200), days=avoid_recent_days)
        if recent:
            candidates = [
                row for row in candidates
                if recipe_identity(row) not in recent
            ]

        # Diet/allergy gates and stock/expiry scoring remain authoritative.
        ranked = v13._rank_filtered(bridge, candidates, diet=diet, limit=30)
        nutrition_store = await nutrition_store_for_bridge(bridge)
        house = bridge.recipe_hub.profile.get("houseIngredients") or []
        scored: list[dict[str, Any]] = []
        for item in ranked:
            match = item.setdefault("match", {})
            if only_home and not bool(match.get("fullyAvailableByQuantity")):
                continue
            shortages = match.get("quantityShortages") if isinstance(match.get("quantityShortages"), list) else []
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

        scored.sort(key=lambda row: row.get("match", {}).get("score", -1000), reverse=True)
        chosen = select_diverse(
            scored,
            meal_count,
            enabled=bool(msg.get("variety", True)),
        )
        connection.send_result(msg["id"], {
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
                "calorieTolerancePercent": int(msg.get("calorie_tolerance", 25)),
                "maxMissing": max_missing,
                "preferExpiring": prefer_expiring,
                "avoidRecentDays": avoid_recent_days,
                "variety": bool(msg.get("variety", True)),
                "query": query,
            },
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
