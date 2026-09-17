"""Current, filtered presentation of saved meals; never rewrite the saved plan."""
from copy import deepcopy


async def refresh_plan(bridge, state, *, filters=None, language="en"):
    from .automatic_prices import offline_recipe_price
    from .release_catalog import async_warm_release_catalog
    from .shared_recipe_runtime import processor
    from .recipe_metrics_v60 import calculate_recipe_nutrition_fast
    from .meal_lifecycle import reservation_status, shopping_delta

    catalog = await async_warm_release_catalog(bridge.hass)
    leftovers = {row["id"]: row for row in state.get("leftovers", [])}
    slots = state.get("slots", [])
    rows = []
    for slot in slots:
        recipe = slot.get("recipe") or leftovers.get(slot.get("leftoverId"), {}).get("recipe")
        if not recipe:
            continue
        recipe = deepcopy(recipe)
        if not slot.get("leftoverId"):
            nutrition = calculate_recipe_nutrition_fast(recipe, catalog.get("_runtimeNutritionIndex") or {})
            if nutrition["totals"]:
                nutrition.update(estimated=True, sourceKinds=["reviewed_release_per100g"])
                recipe["catalogNutrition"] = nutrition
            # The same local evidence and budget assumptions used by card prices.
            recipe["cost"] = await offline_recipe_price(bridge, recipe, catalog["ingredients"])
            slot["cost"] = deepcopy(recipe["cost"])
        recipe["_weeklySlotId"] = slot["id"]
        rows.append(recipe)
    if filters is not None:
        selected = filters.get("languages")
        if isinstance(selected, list):
            rows = [row for row in rows if row.get("language") in selected]
        process = await processor(bridge, filters, language=language, rank=True,
                                  score_targets=False, cost_calculator=lambda row: row.get("cost") or {})
        rows = await bridge.hass.async_add_executor_job(process, rows)
    by_slot = {row.pop("_weeklySlotId"): row for row in rows}
    visible = []
    for slot in slots:
        if slot["id"] not in by_slot:
            continue
        if filters is not None and slot.get("leftoverId") and not (by_slot[slot["id"]].get("match") or {}).get("safe"):
            continue
        slot["recipe"] = by_slot[slot["id"]]
        if not slot.get("leftoverId"):
            slot["nutrition"] = deepcopy(slot["recipe"].get("catalogNutrition") or slot["recipe"].get("nutrition") or {})
        visible.append(slot)
    state["slots"] = visible
    state["filteredSlotCount"] = len(slots) - len(visible)
    inventory = bridge.recipe_hub.profile.get("houseIngredients") or []
    state["reservations"] = reservation_status(visible, inventory)
    state["shoppingDelta"] = shopping_delta(visible, inventory)
    totals = {}
    complete = bool(visible)
    for slot in visible:
        cost = slot.get("cost") or {}
        values = cost.get("budgetTotalsByCurrency", cost.get("totalsByCurrency", {}))
        for currency, value in values.items():
            totals[currency] = totals.get(currency, 0) + value
        complete = complete and bool(cost.get("budgetComplete", cost.get("complete", False)))
    state["weeklyCostByCurrency"] = {key: round(value, 2) for key, value in totals.items()}
    state["weeklyCostComplete"] = complete
    return state


def meal_slots(filters, legacy):
    """Shared recipe categories determine meal times when that UI is in use."""
    if filters is None:
        return legacy or ["breakfast", "lunch", "dinner"]
    categories = set(filters.get("mealTypes") or [])
    if not categories or categories == {"breakfast", "starter", "salad", "soup", "main", "side", "dessert", "snack"}:
        return ["breakfast", "lunch", "dinner"]
    result = ["breakfast"] if "breakfast" in categories else []
    if categories & {"starter", "salad", "soup", "main", "side"}:
        result += ["lunch", "dinner"]
    if categories & {"dessert", "snack"}:
        result.append("snack")
    return result
