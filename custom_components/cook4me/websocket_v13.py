from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import websocket as legacy
from . import websocket_v10 as v10
from .food_intelligence import recipe_quantity_feasibility
from .ingredient_catalog import enrich_match_with_house_keys
from .inventory import (
    DEFAULT_EXPIRY_WARNING_DAYS,
    expiring_inventory_items,
    recipe_expiry_priority,
)
from .recipe_logic import score_recipe

_DIET_FILTERS = ("profile", "omnivore", "pescatarian", "vegetarian", "vegan")


def _recipe_identity(row: dict[str, Any]) -> str:
    for key in (
        "groupingFunctionalId",
        "groupingId",
        "recipeFunctionalId",
        "variantFunctionalId",
        "functionalId",
        "id",
    ):
        value = str(row.get(key) or "").strip()
        if value:
            return f"{key}:{value}"
    title = str(row.get("title") or "").strip().casefold()
    language = str(row.get("language") or "").strip().casefold()
    return f"fallback:{language}:{title}" if title else ""


def _dedupe_recipes(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        ident = _recipe_identity(row)
        if ident and ident in seen:
            continue
        if ident:
            seen.add(ident)
        out.append(row)
    return out


def _rank_filtered(
    bridge,
    recipes: list[dict[str, Any]],
    *,
    diet: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Rank recipes against exact stock quantities and soon-expiring batches."""
    profile = bridge.recipe_hub.profile
    profile["habitTerms"] = bridge.recipe_hub.habit_terms
    if diet != "profile":
        profile["diet"] = diet
    house = profile.get("houseIngredients") or []
    today = dt_util.now().date()

    scored: list[dict[str, Any]] = []
    for recipe in recipes:
        if not isinstance(recipe, dict):
            continue
        result = deepcopy(recipe)
        base_match = score_recipe(result, profile)
        result["match"] = enrich_match_with_house_keys(result, base_match, house)
        if not result["match"].get("safe"):
            continue

        quantity = recipe_quantity_feasibility(
            result,
            house,
            availability=result["match"].get("ingredientAvailability"),
        )
        result["match"]["quantityCoverage"] = quantity["quantityCoverage"]
        result["match"]["quantityConfidence"] = quantity["confidence"]
        result["match"]["quantityAvailability"] = quantity["items"]
        result["match"]["quantityShortages"] = quantity["shortages"]
        result["match"]["quantityUnknown"] = quantity["unknown"]
        result["match"]["fullyAvailableByQuantity"] = quantity["fullyAvailable"]

        expiry = recipe_expiry_priority(
            result,
            house,
            today=today,
            within_days=DEFAULT_EXPIRY_WARNING_DAYS,
        )
        base_score = float(result["match"].get("score") or 0.0)
        expiry_priority = float(expiry.get("priority") or 0.0)
        expiry_bonus = min(40.0, expiry_priority * 20.0)
        quantity_adjustment = -25.0 * max(
            0.0, 1.0 - float(quantity.get("quantityCoverage") or 0.0)
        )
        result["match"]["baseScore"] = round(base_score, 1)
        result["match"]["expiryPriority"] = round(expiry_priority, 3)
        result["match"]["expiryBonus"] = round(expiry_bonus, 1)
        result["match"]["expiringIngredients"] = expiry.get("ingredients") or []
        result["match"]["quantityScoreAdjustment"] = round(quantity_adjustment, 1)
        result["match"]["score"] = round(base_score + expiry_bonus + quantity_adjustment, 1)
        scored.append(result)

    scored.sort(
        key=lambda row: row.get("match", {}).get("score", -1000),
        reverse=True,
    )
    return scored[: max(1, min(int(limit), 30))]


@callback
def async_register(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_recommend)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "cook4me/v13/recommend",
        vol.Optional("entry_id"): str,
        vol.Optional("limit", default=24): vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Optional("catalog_size", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=50)),
        vol.Optional("query", default=""): str,
        vol.Optional("diet", default="profile"): vol.In(_DIET_FILTERS),
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
        query = str(msg.get("query", "")).strip()
        diet = str(msg.get("diet", "profile"))
        catalog_size = int(msg.get("catalog_size", 50))
        language = str(msg["language"])
        strict_language = bool(msg.get("strict_language"))
        refresh = bool(msg.get("refresh"))
        search = await v10._search_with_diagnostic(
            hass,
            bridge,
            query=query,
            page=0,
            size=catalog_size,
            language=language,
            strict_language=strict_language,
            refresh=refresh,
        )
        if not search.get("ok", True):
            connection.send_result(msg["id"], search)
            return

        profile = bridge.recipe_hub.profile
        expiring = expiring_inventory_items(
            profile.get("houseIngredients") or [],
            today=dt_util.now().date(),
            within_days=DEFAULT_EXPIRY_WARNING_DAYS,
            include_past=False,
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
                        hass,
                        bridge,
                        query=name,
                        page=0,
                        size=min(20, catalog_size),
                        language=language,
                        strict_language=strict_language,
                        refresh=refresh,
                    )
                except Exception:
                    continue
                if extra.get("ok", True):
                    candidates.extend(extra.get("items") or [])
                    expiry_candidate_searches += 1
            candidates = _dedupe_recipes(candidates)

        ranked = _rank_filtered(
            bridge,
            candidates,
            diet=diet,
            limit=int(msg.get("limit", 24)),
        )
        for item in ranked:
            item["deviceCanAccept"] = bridge.can_accept_recipe

        result = {
            **{key: value for key, value in search.items() if key != "items"},
            "items": ranked,
            "profile": profile,
            "filters": {
                "query": query,
                "diet": diet,
                "houseIngredientCount": len(profile.get("houseIngredients") or []),
                "expiringIngredientCount": len(expiring),
                "expiryWarningDays": DEFAULT_EXPIRY_WARNING_DAYS,
                "expiryCandidateSearches": expiry_candidate_searches,
            },
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
