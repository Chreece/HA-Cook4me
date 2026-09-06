from __future__ import annotations

from copy import deepcopy
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from . import websocket as legacy
from . import websocket_v10 as v10
from .ingredient_catalog import enrich_match_with_house_keys
from .recipe_logic import score_recipe

_DIET_FILTERS = ("profile", "omnivore", "pescatarian", "vegetarian", "vegan")


def _rank_filtered(
    bridge,
    recipes: list[dict[str, Any]],
    *,
    diet: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Rank recipes against house inventory with an optional transient diet filter."""
    profile = bridge.recipe_hub.profile
    profile["habitTerms"] = bridge.recipe_hub.habit_terms
    if diet != "profile":
        profile["diet"] = diet
    house = profile.get("houseIngredients") or []

    scored: list[dict[str, Any]] = []
    for recipe in recipes:
        if not isinstance(recipe, dict):
            continue
        result = deepcopy(recipe)
        base_match = score_recipe(result, profile)
        result["match"] = enrich_match_with_house_keys(
            result,
            base_match,
            house,
        )
        if result["match"].get("safe"):
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
        search = await v10._search_with_diagnostic(
            hass,
            bridge,
            query=query,
            page=0,
            size=int(msg.get("catalog_size", 50)),
            language=str(msg["language"]),
            strict_language=bool(msg.get("strict_language")),
            refresh=bool(msg.get("refresh")),
        )
        if not search.get("ok", True):
            connection.send_result(msg["id"], search)
            return

        ranked = _rank_filtered(
            bridge,
            search.get("items") or [],
            diet=diet,
            limit=int(msg.get("limit", 24)),
        )
        for item in ranked:
            item["deviceCanAccept"] = bridge.can_accept_recipe

        result = {
            **{key: value for key, value in search.items() if key != "items"},
            "items": ranked,
            "profile": bridge.recipe_hub.profile,
            "filters": {
                "query": query,
                "diet": diet,
                "houseIngredientCount": len(
                    bridge.recipe_hub.profile.get("houseIngredients") or []
                ),
            },
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc)
        return
    connection.send_result(msg["id"], result)
