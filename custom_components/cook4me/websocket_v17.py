from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import websocket as legacy
from . import websocket_v10 as v10
from . import websocket_v13 as v13
from .food_intelligence import (
    nutrition_goal_bonus,
    normalize_nutrition_goal,
    recipe_quantity_feasibility,
    shortage_shopping_items,
)
from .inventory import DEFAULT_EXPIRY_WARNING_DAYS, expiring_inventory_items
from .meal_history import meal_history_store_for_bridge
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo

_DIET_FILTERS = ("profile", "omnivore", "pescatarian", "vegetarian", "vegan")


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_recommend, ws_food_state, ws_feasibility):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v17/recommend",
        vol.Optional("entry_id"): str,
        vol.Optional("limit", default=24): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Optional("catalog_size", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Optional("query", default=""): str,
        vol.Optional("diet", default="profile"): vol.In(_DIET_FILTERS),
        vol.Optional("nutrition_goal", default="balanced"): str,
        vol.Required("language"): str,
        vol.Optional("strict_language", default=False): bool,
        vol.Optional("refresh", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_recommend(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        query = str(msg.get("query", "")).strip()
        diet = str(msg.get("diet", "profile"))
        catalog_size = int(msg.get("catalog_size", 50))
        language = str(msg["language"])
        strict_language = bool(msg.get("strict_language"))
        refresh = bool(msg.get("refresh"))
        goal = normalize_nutrition_goal(msg.get("nutrition_goal"))
        search = await v10._search_with_diagnostic(
            hass, bridge, query=query, page=0, size=catalog_size,
            language=language, strict_language=strict_language, refresh=refresh,
        )
        if not search.get("ok", True):
            connection.send_result(msg["id"], search)
            return
        profile = bridge.recipe_hub.profile
        house = profile.get("houseIngredients") or []
        expiring = expiring_inventory_items(
            house, today=dt_util.now().date(),
            within_days=DEFAULT_EXPIRY_WARNING_DAYS, include_past=False,
        )
        candidates = list(search.get("items") or [])
        expiry_candidate_searches = 0
        if not query and expiring:
            for stock in expiring[:3]:
                name = str(stock.get("name") or "").strip()
                if not name:
                    continue
                try:
                    extra = await v10._search_with_diagnostic(
                        hass, bridge, query=name, page=0, size=min(20, catalog_size),
                        language=language, strict_language=strict_language, refresh=refresh,
                    )
                except Exception:
                    continue
                if extra.get("ok", True):
                    candidates.extend(extra.get("items") or [])
                    expiry_candidate_searches += 1
            candidates = v13._dedupe_recipes(candidates)
        ranked = v13._rank_filtered(bridge, candidates, diet=diet, limit=30)
        nutrition_store = await nutrition_store_for_bridge(bridge)
        for item in ranked:
            nutrition = calculate_recipe_nutrition_fefo(
                item, house,
                generic=nutrition_store.generic,
                stock_lots=nutrition_store.stock_lots,
            )
            hint = nutrition_goal_bonus(nutrition, goal)
            match = item.setdefault("match", {})
            base_score = float(match.get("score") or 0.0)
            match["nutritionGoal"] = goal
            match["nutritionGoalBonus"] = hint.get("bonus", 0.0)
            match["nutritionGoalCoverage"] = hint.get("coverage", 0.0)
            match["scoreBeforeNutritionGoal"] = round(base_score, 1)
            match["score"] = round(base_score + float(hint.get("bonus") or 0.0), 1)
            item["nutrition"] = nutrition
            item["deviceCanAccept"] = bridge.can_accept_recipe
        ranked.sort(key=lambda row: row.get("match", {}).get("score", -1000), reverse=True)
        ranked = ranked[: max(1, min(int(msg.get("limit", 24)), 30))]
        connection.send_result(msg["id"], {
            **{key: value for key, value in search.items() if key != "items"},
            "items": ranked,
            "profile": profile,
            "filters": {
                "query": query, "diet": diet, "nutritionGoal": goal,
                "houseIngredientCount": len(house),
                "expiringIngredientCount": len(expiring),
                "expiryWarningDays": DEFAULT_EXPIRY_WARNING_DAYS,
                "expiryCandidateSearches": expiry_candidate_searches,
            },
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v17/food_state",
    vol.Optional("entry_id"): str,
    vol.Optional("history_limit", default=30): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
})
@websocket_api.async_response
async def ws_food_state(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        history = await meal_history_store_for_bridge(bridge)
        profile = bridge.recipe_hub.profile
        connection.send_result(msg["id"], {
            "profile": profile,
            "householdMembers": profile.get("householdMembers") or [],
            "nutritionGoal": bridge.recipe_hub.ui_preferences.get("nutritionGoal") or "balanced",
            "history": history.recent(int(msg.get("history_limit", 30))),
            "summary": history.summary(),
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v17/feasibility",
    vol.Optional("entry_id"): str,
    vol.Required("recipe"): dict,
})
@callback
def ws_feasibility(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        annotated = bridge.recipe_hub.annotate(dict(msg["recipe"]))
        feasibility = recipe_quantity_feasibility(
            annotated,
            bridge.recipe_hub.profile.get("houseIngredients") or [],
            availability=annotated.get("match", {}).get("ingredientAvailability"),
        )
        connection.send_result(msg["id"], {
            "feasibility": feasibility,
            "shoppingShortages": shortage_shopping_items(feasibility),
        })
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
