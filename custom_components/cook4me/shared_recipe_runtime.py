"""Bind the shared filter contract to stored inventory, costs and history."""
from .shared_recipe_filters import apply_filters, ingredient_aliases, normalize_filters


async def search_filtered(bridge, *, query, languages, language, filters):
    from functools import partial
    from . import release_catalog
    from .websocket_v30 import _device_language, _device_country
    process = await processor(bridge, filters, language=language)
    return await bridge.hass.async_add_executor_job(partial(release_catalog.search_release_recipes,
        query, language=language, configured_language=_device_language(bridge), country=_device_country(bridge),
        catalog_languages=languages, group_families=True, all_results=True, filter_rows=process))


async def processor(bridge, filters, *, language="en", rank=True, score_targets=True):
    from . import websocket_v13 as v13
    from . import websocket_v18 as v18
    from .costs import cost_store_for_bridge
    from .costing import calculate_recipe_cost
    from .meal_history import meal_history_store_for_bridge
    from .nutrition import nutrition_store_for_bridge
    from .nutrition_fefo import calculate_recipe_nutrition_fefo
    from .today_logic import recipe_identity
    settings = normalize_filters(filters)
    house = bridge.recipe_hub.profile.get("houseIngredients") or []
    costs = await cost_store_for_bridge(bridge) if settings["maxCost"] is not None else None
    nutrients = await nutrition_store_for_bridge(bridge)
    history = await meal_history_store_for_bridge(bridge)
    recent = v18._recent_identities(history.recent(200), days=int(settings["avoidRecentDays"] or 0))
    aliases = await bridge.hass.async_add_executor_job(ingredient_aliases, language) if settings["ingredients"] else {}

    def process(rows):
        rows = [row for row in rows if recipe_identity(row) not in recent]
        if rank:
            rows = v13._rank_filtered(bridge, rows, diet=settings["diet"], limit=max(1, len(rows)), unlimited=True)
        return apply_filters(rows, settings, ingredient_groups=aliases,
            cost=(lambda row: calculate_recipe_cost(row, house, costs)) if costs else None,
            nutrition=lambda row: calculate_recipe_nutrition_fefo(row, house, generic=nutrients.generic, stock_lots=nutrients.stock_lots),
            score_targets=score_targets)
    return process
