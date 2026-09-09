from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import websocket as legacy
from . import websocket_v13 as v13
from . import websocket_v18 as v18
from . import websocket_v29 as v29
from . import websocket_v30 as v30
from . import websocket_v31 as v31
from .food_intelligence import nutrition_goal_bonus, normalize_nutrition_goal
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .recipe_derived_cache import derived_recipe_store_for_bridge
from .reference_catalog import bundled_reference_catalog
from .request_coordinator import request_coordinator
from .today_logic import calorie_target_bonus, normalize_meal_types, recipe_identity, recipe_matches_meal_types
from .today_multilang import select_catalog_balanced
from .ui_state import ui_state_store_for_bridge


def _text(value: Any) -> str:
    return str(value or "").strip()


async def _candidates(hass, bridge, *, languages, query, ui_language, coordinator):
    reference = bundled_reference_catalog()
    if reference.metadata.get("recipeCount"):
        coordinator.update_progress(phase="catalog", completed=0, total=1, message="Reading bundled recipe catalog")
        rows = v30.reference_recipe_candidates(
            bridge,
            languages=languages,
            query=query,
            ui_language=ui_language,
            limit=500,
        )
        coordinator.update_progress(phase="catalog", completed=1, total=1, message="Bundled recipe catalog ready")
        return rows, [], "bundled_reference_catalog"

    rows: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for index, language in enumerate(languages, 1):
        coordinator.update_progress(
            phase="catalogs",
            completed=index - 1,
            total=len(languages),
            message=f"Loading {language.upper()} catalog",
        )
        part, part_errors = await v29._search_catalogs_preserving_language(
            hass,
            bridge,
            languages=[language],
            query=query,
            catalog_size=40,
            refresh=False,
        )
        rows.extend(part)
        errors.extend(part_errors)
        coordinator.update_progress(
            phase="catalogs",
            completed=index,
            total=len(languages),
            message=f"Loaded {language.upper()} catalog",
        )
    return rows, errors, "persistent_seb_cache"


async def _build_today(hass, bridge, msg: dict[str, Any], coordinator) -> dict[str, Any]:
    languages = v18._languages(bridge, msg.get("languages"))
    diet = str(msg.get("diet") or "profile")
    meal_types = normalize_meal_types(msg.get("meal_types"))
    query = _text(msg.get("query"))
    only_home = bool(msg.get("only_home"))
    prefer_expiring = bool(msg.get("prefer_expiring", True))
    goal = normalize_nutrition_goal(msg.get("nutrition_goal"))
    meal_count = int(msg.get("meal_count", 1))
    max_missing = msg.get("max_missing") if "max_missing" in msg else None
    avoid_recent_days = int(msg.get("avoid_recent_days", 7))
    calorie_tolerance = int(msg.get("calorie_tolerance", 25)) / 100.0
    ui_language = _text(msg.get("ui_language")) or "en"

    candidates, catalog_errors, source = await _candidates(
        hass,
        bridge,
        languages=languages,
        query=query,
        ui_language=ui_language,
        coordinator=coordinator,
    )
    if meal_types:
        candidates = [row for row in candidates if recipe_matches_meal_types(row, meal_types)]

    if avoid_recent_days > 0:
        history_store = await meal_history_store_for_bridge(bridge)
        recent = v18._recent_identities(history_store.recent(200), days=avoid_recent_days)
        if recent:
            candidates = [row for row in candidates if recipe_identity(row) not in recent]

    ranked: list[dict[str, Any]] = []
    for index, language in enumerate(languages, 1):
        coordinator.update_progress(
            phase="ranking",
            completed=index - 1,
            total=len(languages),
            message=f"Ranking {language.upper()}",
        )
        language_rows = [
            row
            for row in candidates
            if _text(row.get("todayCatalogLanguage")).lower() == language
        ]
        if language_rows:
            ranked.extend(v13._rank_filtered(bridge, language_rows, diet=diet, limit=30))
        coordinator.update_progress(
            phase="ranking",
            completed=index,
            total=len(languages),
            message=f"Ranked {language.upper()}",
        )

    nutrition_store = await nutrition_store_for_bridge(bridge)
    house = bridge.recipe_hub.profile.get("houseIngredients") or []
    scored: list[dict[str, Any]] = []
    total = max(1, len(ranked))
    for index, item in enumerate(ranked, 1):
        coordinator.update_progress(
            phase="nutrition",
            completed=index - 1,
            total=total,
            message=f"Calculating nutrition {index}/{len(ranked)}",
        )
        match = item.setdefault("match", {})
        if only_home and not bool(match.get("fullyAvailableByQuantity")):
            coordinator.update_progress(phase="nutrition", completed=index, total=total, message=f"Calculated nutrition {index}/{len(ranked)}")
            continue
        shortages = match.get("quantityShortages") if isinstance(match.get("quantityShortages"), list) else []
        if max_missing is not None and len(shortages) > int(max_missing):
            coordinator.update_progress(phase="nutrition", completed=index, total=total, message=f"Calculated nutrition {index}/{len(ranked)}")
            continue

        local = calculate_recipe_nutrition_fefo(
            item,
            house,
            generic=nutrition_store.generic,
            stock_lots=nutrition_store.stock_lots,
        )
        nutrition = v31._best_nutrition(local, item.get("nutrition"))
        item["nutrition"] = nutrition
        score = float(match.get("score") or 0.0)
        if not prefer_expiring:
            score -= float(match.get("expiryBonus") or 0.0)
        nutrition_hint = nutrition_goal_bonus(nutrition, goal)
        calorie_hint = calorie_target_bonus(
            nutrition,
            msg.get("calorie_target"),
            tolerance_fraction=calorie_tolerance,
        )
        match.update(
            {
                "nutritionGoal": goal,
                "nutritionGoalBonus": nutrition_hint.get("bonus", 0.0),
                "nutritionGoalCoverage": nutrition_hint.get("coverage", 0.0),
                "calorieTarget": calorie_hint.get("target"),
                "caloriePerServing": calorie_hint.get("calories"),
                "calorieDelta": calorie_hint.get("delta"),
                "calorieTargetBonus": calorie_hint.get("bonus", 0.0),
                "score": round(
                    score
                    + float(nutrition_hint.get("bonus") or 0.0)
                    + float(calorie_hint.get("bonus") or 0.0),
                    1,
                ),
            }
        )
        item["deviceCanAccept"] = bridge.can_accept_recipe
        scored.append(item)
        coordinator.update_progress(
            phase="nutrition",
            completed=index,
            total=total,
            message=f"Calculated nutrition {index}/{len(ranked)}",
        )

    scored.sort(key=lambda row: row.get("match", {}).get("score", -1000), reverse=True)
    chosen = select_catalog_balanced(
        scored,
        meal_count,
        languages,
        diversity=bool(msg.get("variety", True)),
    )

    derived = await derived_recipe_store_for_bridge(bridge)
    cost_total = max(1, len(chosen))
    for index, item in enumerate(chosen, 1):
        coordinator.update_progress(
            phase="cost",
            completed=index - 1,
            total=cost_total,
            message=f"Calculating cost {index}/{len(chosen)}",
        )
        item["cost"] = await derived.async_recipe_cost(bridge, item)
        coordinator.update_progress(
            phase="cost",
            completed=index,
            total=cost_total,
            message=f"Calculated cost {index}/{len(chosen)}",
        )

    candidate_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in candidates)
    ranked_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in scored)
    selected_counts = Counter(_text(row.get("todayCatalogLanguage")) for row in chosen)
    filters = {
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
    }
    result = {
        "date": dt_util.now().date().isoformat(),
        "items": chosen,
        "candidateCount": len(candidates),
        "rankedCount": len(scored),
        "catalogErrors": catalog_errors,
        "catalogCandidateCounts": {language: int(candidate_counts.get(language, 0)) for language in languages},
        "catalogRankedCounts": {language: int(ranked_counts.get(language, 0)) for language in languages},
        "catalogSelectedCounts": {language: int(selected_counts.get(language, 0)) for language in languages},
        "catalogLanguagesUsed": [language for language in languages if selected_counts.get(language, 0)],
        "filters": filters,
        "catalogSource": source,
        "referenceCatalog": bundled_reference_catalog().metadata,
    }

    coordinator.update_progress(phase="saving", completed=0, total=1, message="Saving today's plan")
    state_store = await ui_state_store_for_bridge(bridge)
    await state_store.async_set_today_plan(
        date=result["date"],
        items=chosen,
        filters=filters,
        meta={key: deepcopy(value) for key, value in result.items() if key not in {"items", "filters"}},
    )
    coordinator.update_progress(phase="saving", completed=1, total=1, message="Today's plan saved")
    return result


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_today_suggest)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v33/today_suggest",
        vol.Optional("entry_id"): str,
        vol.Optional("languages", default=[]): [str],
        vol.Optional("diet", default="profile"): vol.In(v18._DIET_FILTERS),
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
        vol.Optional("ui_language", default="en"): str,
    }
)
@websocket_api.async_response
async def ws_today_suggest(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        coordinator = await request_coordinator(hass)
        async with coordinator.operation(
            "today_suggestions",
            "Build today's Cook4Me suggestions",
            entry_ids=[bridge.entry.entry_id],
        ):
            result = await _build_today(hass, bridge, msg, coordinator)
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
