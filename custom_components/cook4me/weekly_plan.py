"""Current, filtered presentation of saved meals; never rewrite the saved plan."""
from copy import deepcopy


def _inventory_views(slots, inventory):
    from .meal_lifecycle import reservation_status, shopping_delta
    return reservation_status(slots, inventory), shopping_delta(slots, inventory)


async def refresh_plan(bridge, state, *, filters=None, language="en", progress=None):
    from .automatic_prices import offline_recipe_price
    from .release_catalog import async_warm_release_catalog
    from .shared_recipe_runtime import processor
    from .recipe_metrics_v60 import calculate_recipe_nutrition_fast

    catalog = await async_warm_release_catalog(bridge.hass)
    leftovers = {row["id"]: row for row in state.get("leftovers", [])}
    slots = state.get("slots", [])
    rows = []
    total_slots = max(1, len(slots))
    if progress:
        progress("cost", completed=0, total=total_slots, message="Refreshing planned meals")
    for index, slot in enumerate(slots, start=1):
        recipe = slot.get("recipe") or leftovers.get(slot.get("leftoverId"), {}).get("recipe")
        if not recipe:
            if progress:
                progress("cost", completed=index, total=total_slots, message="Refreshing planned meals")
            continue
        recipe = deepcopy(recipe)
        if not slot.get("leftoverId"):
            nutrition = await bridge.hass.async_add_executor_job(
                calculate_recipe_nutrition_fast,
                recipe,
                catalog.get("_runtimeNutritionIndex") or {},
            )
            if nutrition["totals"]:
                nutrition.update(estimated=True, sourceKinds=["reviewed_release_per100g"])
                recipe["catalogNutrition"] = nutrition
            # The same local evidence and budget assumptions used by card prices.
            recipe["cost"] = await offline_recipe_price(bridge, recipe, catalog["ingredients"])
            slot["cost"] = deepcopy(recipe["cost"])
        recipe["_weeklySlotId"] = slot["id"]
        rows.append(recipe)
        if progress:
            progress(
                "cost",
                completed=index,
                total=total_slots,
                message=str(recipe.get("title") or slot.get("mealType") or "Planned meal"),
            )
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
    reservations, shopping = await bridge.hass.async_add_executor_job(
        _inventory_views, visible, inventory
    )
    state["reservations"] = reservations
    state["shoppingDelta"] = shopping
    totals = {}
    selected_slots = [slot for slot in visible if slot.get("selected") is not False]
    state["selectedSlotCount"] = len(selected_slots)
    complete = bool(selected_slots)
    for slot in selected_slots:
        cost = slot.get("cost") or {}
        values = cost.get("budgetTotalsByCurrency", cost.get("totalsByCurrency", {}))
        for currency, value in values.items():
            totals[currency] = totals.get(currency, 0) + value
        complete = complete and bool(cost.get("budgetComplete", cost.get("complete", False)))
    state["weeklyCostByCurrency"] = {key: round(value, 2) for key, value in totals.items()}
    state["weeklyCostComplete"] = complete
    return state


MEAL_SLOT_ORDER = ("breakfast", "morningSnack", "lunch", "afternoonSnack", "dinner", "lateSnack")
WEEKDAY_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
_SLOT_ALIASES = {
    "breakfast": "breakfast",
    "morningsnack": "morningSnack",
    "lunch": "lunch",
    "afternoonsnack": "afternoonSnack",
    "snack": "afternoonSnack",
    "dinner": "dinner",
    "latesnack": "lateSnack",
}


def normalize_meal_slot(value):
    token = str(value or "").strip().replace("_", "").replace("-", "").replace(" ", "").casefold()
    return _SLOT_ALIASES.get(token, "")


def ordered_meal_slots(values):
    selected = {normalize_meal_slot(value) for value in values or []}
    return [meal for meal in MEAL_SLOT_ORDER if meal in selected]


def meal_slots(filters, legacy):
    """Map recipe-course filters onto already-enabled chronological meal slots."""
    fallback = ordered_meal_slots(legacy) or ["breakfast", "lunch", "dinner"]
    if filters is None:
        return fallback
    categories = set(filters.get("mealTypes") or [])
    all_categories = {"breakfast", "starter", "salad", "soup", "main", "side", "dessert", "snack"}
    if not categories or categories == all_categories:
        return fallback
    allowed = set()
    if "breakfast" in categories:
        allowed.add("breakfast")
    if categories & {"starter", "salad", "soup", "main", "side"}:
        allowed.update(("lunch", "dinner"))
    if categories & {"dessert", "snack"}:
        allowed.update(("morningSnack", "afternoonSnack", "lateSnack"))
    return [meal for meal in fallback if meal in allowed]


def meal_slots_for_date(filters, settings, stamp):
    """Apply the saved weekday pattern after shared-filter slot eligibility."""
    allowed = meal_slots(filters, (settings or {}).get("mealTypes"))
    schedule = (settings or {}).get("weekdayMealTypes")
    if not isinstance(schedule, dict):
        return allowed
    from datetime import date
    try:
        weekday = WEEKDAY_KEYS[date.fromisoformat(str(stamp)).weekday()]
    except (ValueError, IndexError):
        return allowed
    raw = schedule.get(weekday)
    if not isinstance(raw, list):
        return allowed
    wanted = set(ordered_meal_slots(raw))
    return [meal for meal in allowed if meal in wanted]
