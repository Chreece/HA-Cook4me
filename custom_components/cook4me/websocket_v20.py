from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from functools import partial
import re
from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant.components import ai_task, websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from . import websocket as legacy
from . import websocket_v5 as v5
from . import websocket_v11 as v11
from . import websocket_v12 as v12
from . import websocket_v13 as v13
from . import websocket_v18 as v18
from . import websocket_v19 as v19
from .barcode import confident_match, suggest_catalog_matches
from .costs import cost_store_for_bridge
from .costing import (
    calculate_recipe_cost,
    lookup_open_prices_safe,
    store_best_open_price,
)
from .expiry import update_expiry_notification
from .food_intelligence import nutrition_goal_bonus, normalize_nutrition_goal
from .inventory import inventory_identity
from .meal_history import meal_history_store_for_bridge
from .meal_lifecycle import (
    meal_lifecycle_store_for_bridge,
    reservation_status,
    shopping_delta,
    rolling_week_start,
)
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .nutrition_inventory import async_reconcile_nutrition_inventory
from .today_logic import recipe_identity, recipe_matches_meal_types
from .request_coordinator import EVENT_OPERATION_PROGRESS

_MAX_WEEK_CANDIDATES = 180
_WEEK_NUTRITION_BATCH = 30
_MAX_GLOBAL_PRICE_LOOKUPS = 4
_SHOPPING_RE = re.compile(
    r"^\s*(?P<quantity>\d+(?:[.,]\d+)?)\s*(?P<unit>mg|g|kg|ml|cl|dl|l|pc|pcs|x)\s+(?P<name>.+?)\s*$",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _emit_week_progress(
    hass: HomeAssistant,
    operation_id: str,
    phase: str,
    *,
    completed: int | float | None = None,
    total: int | float | None = None,
    message: str = "",
    done: bool = False,
    error: str = "",
    kind: str = "week_generate",
) -> None:
    """Publish real weekly progress only for validated UI-owned jobs."""
    operation_id = _text(operation_id)[:160]
    if not operation_id:
        return
    completed_number = float(completed) if isinstance(completed, (int, float)) else None
    total_number = float(total) if isinstance(total, (int, float)) else None
    percent = None
    if completed_number is not None and total_number is not None and total_number > 0:
        percent = round(max(0.0, min(100.0, completed_number / total_number * 100.0)))
    hass.bus.async_fire(EVENT_OPERATION_PROGRESS, {
        "operationId": operation_id,
        "kind": str(kind or "week_generate")[:80],
        "title": "Weekly meal plan",
        "phase": str(phase or "starting"),
        "completed": completed_number,
        "total": total_number,
        "percent": percent,
        "message": str(message or "")[:400],
        "waitingCount": 0,
        "done": bool(done),
        "error": str(error or "")[:300],
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })


def _number(value: Any) -> float | None:
    try:
        value = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _currency_map_add(target: dict[str, float], values: Any) -> None:
    if not isinstance(values, dict):
        return
    for currency, amount in values.items():
        if isinstance(amount, (int, float)):
            target[str(currency)] = target.get(str(currency), 0.0) + float(amount)


def _currency_map(values: dict[str, float]) -> dict[str, float]:
    return {key: round(value, 2) for key, value in values.items()}


def _local_date(timestamp: Any) -> str:
    try:
        stamp = datetime.fromisoformat(_text(timestamp))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return dt_util.as_local(stamp).date().isoformat()
    except (TypeError, ValueError):
        return ""


def _nutrition_totals(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    raw = value.get("totals") if isinstance(value.get("totals"), dict) else value
    return {
        str(key): float(number)
        for key, number in raw.items()
        if isinstance(number, (int, float))
    }


def _nutrition_dashboard(
    history_rows: list[dict[str, Any]],
    lifecycle,
    *,
    targets: dict[str, Any],
    days: int = 30,
) -> dict[str, Any]:
    today = dt_util.now().date()
    start = today - timedelta(days=max(1, int(days)) - 1)
    by_day: dict[str, dict[str, Any]] = {}
    totals: dict[str, float] = {}
    costs: dict[str, float] = {}
    for row in reversed(history_rows):
        stamp = _local_date(row.get("timestamp"))
        if not stamp:
            continue
        current = date.fromisoformat(stamp)
        if current < start or current > today:
            continue
        nutrition = _nutrition_totals(
            row.get("consumedNutrition") or row.get("nutrition")
        )
        day = by_day.setdefault(stamp, {"nutrition": {}, "costByCurrency": {}, "mealCount": 0})
        day["mealCount"] += 1
        for key, value in nutrition.items():
            day["nutrition"][key] = day["nutrition"].get(key, 0.0) + value
            totals[key] = totals.get(key, 0.0) + value
        meal_cost = lifecycle.meal_cost(_text(row.get("id")))
        if isinstance(meal_cost, dict):
            _currency_map_add(day["costByCurrency"], meal_cost.get("totalsByCurrency"))
            _currency_map_add(costs, meal_cost.get("totalsByCurrency"))

    series = []
    for offset in range((today - start).days + 1):
        stamp = (start + timedelta(days=offset)).isoformat()
        row = by_day.get(stamp, {"nutrition": {}, "costByCurrency": {}, "mealCount": 0})
        series.append({
            "date": stamp,
            "mealCount": row["mealCount"],
            "nutrition": {key: round(value, 2) for key, value in row["nutrition"].items()},
            "costByCurrency": _currency_map(row["costByCurrency"]),
        })

    today_values = series[-1]["nutrition"] if series else {}
    progress: dict[str, Any] = {}
    for key, raw_target in targets.items() if isinstance(targets, dict) else []:
        target = _number(raw_target)
        if target is None or target <= 0:
            continue
        value = float(today_values.get(key) or 0.0)
        progress[str(key)] = {
            "value": round(value, 2),
            "target": round(target, 2),
            "fraction": round(value / target, 3),
        }
    return {
        "days": len(series),
        "series": series,
        "totals": {key: round(value, 2) for key, value in totals.items()},
        "costByCurrency": _currency_map(costs),
        "todayTargetProgress": progress,
        "targetsAreUserConfigured": True,
    }


def _lot_in_inventory(inventory: Any, lot_id: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    wanted = _text(lot_id)
    for row in inventory if isinstance(inventory, list) else []:
        if not isinstance(row, dict):
            continue
        for lot in row.get("lots") or []:
            if isinstance(lot, dict) and _text(lot.get("id")) == wanted:
                return row, lot
    return None


def _recipe_cost_with_store(bridge, recipe: dict[str, Any], store) -> dict[str, Any]:
    return calculate_recipe_cost(
        recipe,
        bridge.recipe_hub.profile.get("houseIngredients") or [],
        store,
    )


async def _hydrate_global_prices(
    hass: HomeAssistant,
    bridge,
    cost_store,
    recipe: dict[str, Any],
) -> int:
    from .automatic_prices import product_price, price_settings
    import asyncio
    settings = await price_settings(bridge)
    if not settings.get("autoGlobalPrices"):
        return 0
    wanted = {inventory_identity(row) for row in recipe.get("ingredients") or [] if isinstance(row, dict)}
    items = [(row, lot) for row in bridge.recipe_hub.profile.get("houseIngredients") or []
             if inventory_identity(row) in wanted for lot in row.get("lots") or [] if lot.get("barcode")]
    results = await asyncio.gather(*(product_price(bridge, barcode=lot["barcode"], ingredient=row,
        unit=row.get("unit", ""), settings=settings) for row, lot in items[:_MAX_GLOBAL_PRICE_LOOKUPS]), return_exceptions=True)
    return sum(isinstance(result, dict) and bool(result.get("reference")) for result in results)



def _feedback_adjust(lifecycle, recipe: dict[str, Any]) -> dict[str, Any]:
    row = deepcopy(recipe)
    match = row.setdefault("match", {})
    bonus = lifecycle.feedback_bonus(row)
    match["feedbackBonus"] = bonus
    match["score"] = round(float(match.get("score") or 0.0) + bonus, 1)
    return row


def _plan_penalty(
    existing_slots: list[dict[str, Any]],
    candidate_slot: dict[str, Any],
    inventory: Any,
) -> float:
    before = reservation_status(existing_slots, inventory)
    after = reservation_status(existing_slots + [candidate_slot], inventory)
    before_short = len(before.get("shortages") or [])
    after_short = len(after.get("shortages") or [])
    before_unknown = len(before.get("unknown") or [])
    after_unknown = len(after.get("unknown") or [])
    return max(0, after_short - before_short) * 18.0 + max(0, after_unknown - before_unknown) * 2.0


def _week_candidate_nutrition(
    candidates: list[dict[str, Any]],
    inventory: Any,
    nutrition_store,
) -> dict[int, dict[str, Any]]:
    """Calculate invariant candidate nutrition once for reuse across all slots."""
    result: dict[int, dict[str, Any]] = {}
    for candidate in candidates:
        nutrition = calculate_recipe_nutrition_fefo(
            candidate,
            inventory,
            generic=nutrition_store.generic,
            stock_lots=nutrition_store.stock_lots,
        )
        if not nutrition.get("totals"):
            nutrition = deepcopy(
                candidate.get("catalogNutrition") or candidate.get("nutrition") or nutrition
            )
        result[id(candidate)] = nutrition
    return result


def _score_week_pool(
    pool: list[dict[str, Any]],
    *,
    planned: list[dict[str, Any]],
    inventory: Any,
    nutrition_by_id: dict[int, dict[str, Any]],
    cost_store,
    goal: str,
    slot_id: str,
    stamp: str,
    meal_type: str,
    is_selected: bool,
    shared_filters: dict | None,
    profile_target_settings: dict[str, Any],
    profile_daily_targets: dict[str, Any],
    day_total: int,
) -> dict[str, Any] | None:
    """Score one weekly slot off the HA event loop."""
    from .shared_recipe_filters import recipe_target_scope
    from .nutrient_targets import daily_progress_bonus, target_bonus

    before = reservation_status(planned, inventory)
    before_short = len(before.get("shortages") or [])
    before_unknown = len(before.get("unknown") or [])
    day_rows = [
        slot.get("nutrition") or (slot.get("recipe") or {}).get("nutrition") or {}
        for slot in planned
        if slot.get("selected") is not False and _text(slot.get("date")) == stamp
    ]
    day_completed = len(day_rows)

    best: dict[str, Any] | None = None
    best_score = float("-inf")
    best_nutrition: dict[str, Any] = {}
    best_cost: dict[str, Any] = {}
    best_penalty = 0.0
    best_daily_bonus = 0.0
    best_meal_target_bonus = 0.0

    for candidate in pool:
        nutrition = nutrition_by_id.get(id(candidate)) or {}
        nutrition_hint = nutrition_goal_bonus(nutrition, goal)
        candidate_slot = {
            "id": slot_id,
            "selected": is_selected,
            "date": stamp,
            "mealType": meal_type,
            "recipe": candidate,
        }
        after = reservation_status(planned + [candidate_slot], inventory)
        penalty = (
            max(0, len(after.get("shortages") or []) - before_short) * 18.0
            + max(0, len(after.get("unknown") or []) - before_unknown) * 2.0
        )
        meal_target_bonus = 0.0
        if shared_filters is None:
            meal_targets, _meal_scope = recipe_target_scope(
                profile_target_settings, candidate
            )
            meal_target_bonus = float(
                target_bonus(nutrition, meal_targets).get("bonus") or 0.0
            )
        daily_hint = daily_progress_bonus(
            day_rows,
            nutrition,
            profile_daily_targets,
            fraction=min(1.0, (day_completed + 1) / max(1, day_total)),
        )
        score = (
            float((candidate.get("match") or {}).get("score") or 0.0)
            + (
                0.0
                if shared_filters is not None
                else float(nutrition_hint.get("bonus") or 0.0)
            )
            + meal_target_bonus
            + float(daily_hint.get("bonus") or 0.0)
            - penalty
        )
        if score <= best_score:
            continue
        best = candidate
        best_score = score
        best_nutrition = nutrition
        best_penalty = penalty
        best_daily_bonus = float(daily_hint.get("bonus") or 0.0)
        best_meal_target_bonus = meal_target_bonus

    if best is None:
        return None
    # Cost does not influence selection score. Calculate it exactly once for
    # the winning recipe rather than for every temporary "best so far".
    best_cost = calculate_recipe_cost(best, inventory, cost_store)
    return {
        "recipe": best,
        "score": best_score,
        "nutrition": best_nutrition,
        "cost": best_cost,
        "penalty": best_penalty,
        "dailyBonus": best_daily_bonus,
        "mealTargetBonus": best_meal_target_bonus,
    }


async def _week_candidates(
    hass: HomeAssistant,
    bridge,
    lifecycle,
    *,
    languages: list[str],
    diet: str,
    query: str,
    refresh: bool,
    avoid_recent_days: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    page_count = v19._catalog_page_count(bridge, diet=diet, query=query)
    candidates, errors, _fetched = await v19._search_catalogs_paginated(
        hass,
        bridge,
        languages=languages,
        query=query,
        catalog_size=50,
        refresh=refresh,
        page_count=page_count,
    )
    history = await meal_history_store_for_bridge(bridge)
    recent = v18._recent_identities(
        history.recent(200), days=int(lifecycle.settings.get("avoidRecentDays", 7) if avoid_recent_days is None else avoid_recent_days)
    )
    if recent:
        candidates = [row for row in candidates if recipe_identity(row) not in recent]
    ranked = v13._rank_filtered(
        bridge, candidates, diet=diet, limit=_MAX_WEEK_CANDIDATES
    )
    return [_feedback_adjust(lifecycle, row) for row in ranked], errors


async def _generate_week(
    hass: HomeAssistant,
    bridge,
    lifecycle,
    *,
    week_start: str,
    languages: list[str],
    diet: str,
    query: str,
    refresh: bool,
    replace_slot_id: str = "",
    replace_slot_ids: list[str] | None = None,
    shared_filters: dict | None = None,
    ui_language: str = "en",
    progress=None,
) -> dict[str, Any]:
    from . import release_catalog
    from .weekly_variety import signature, already_planned, available_candidates
    from .weekly_plan import MEAL_SLOT_ORDER, meal_slots_for_date
    original_slots = deepcopy(lifecycle.slots)
    replacing = bool(replace_slot_id) or replace_slot_ids is not None
    target_ids = set(replace_slot_ids or ([replace_slot_id] if replace_slot_id else []))
    end = (date.fromisoformat(week_start) + timedelta(days=6)).isoformat()
    eligible_ids = {row["id"] for row in original_slots if week_start <= _text(row.get("date")) <= end}
    if replacing and (not target_ids or not target_ids.issubset(eligible_ids)):
        raise ValueError("The selected meal is no longer in the next seven days")
    if progress:
        progress("catalog_index", completed=0, total=1, message="Preparing weekly candidates")
    if shared_filters is not None and release_catalog.release_catalog_ready():
        from .shared_recipe_runtime import search_filtered
        result = await search_filtered(bridge, query=query, languages=languages, language=ui_language, filters=shared_filters)
        candidates, errors = result["items"], []
    else:
        candidates, errors = await _week_candidates(
            hass, bridge, lifecycle,
            languages=languages, diet=diet, query=query, refresh=refresh,
            avoid_recent_days=int(shared_filters.get("avoidRecentDays") or 0) if shared_filters is not None else None,
        )
        if shared_filters is not None:
            from .shared_recipe_runtime import processor
            process = await processor(bridge, shared_filters, language=ui_language, rank=False)
            candidates = await hass.async_add_executor_job(process, candidates)
    # Release-catalog filtering can return thousands of safe rows. Planning all
    # of them for every slot used to run an unbounded nested scoring loop. Keep
    # a broad ranked window for variety, but bound the expensive planner.
    candidates = list(candidates[:_MAX_WEEK_CANDIDATES])
    if progress:
        progress(
            "catalog_index",
            completed=1,
            total=1,
            message=f"{len(candidates)} weekly candidates ready",
        )
    nutrition_store = await nutrition_store_for_bridge(bridge)
    cost_store = await cost_store_for_bridge(bridge)
    inventory = bridge.recipe_hub.profile.get("houseIngredients") or []
    nutrition_by_id: dict[int, dict[str, Any]] = {}
    total_candidates = max(1, len(candidates))
    if progress:
        progress(
            "nutrition",
            completed=0,
            total=total_candidates,
            message="Preparing candidate nutrition",
        )
    for offset in range(0, len(candidates), _WEEK_NUTRITION_BATCH):
        batch = candidates[offset : offset + _WEEK_NUTRITION_BATCH]
        nutrition_by_id.update(
            await hass.async_add_executor_job(
                _week_candidate_nutrition,
                batch,
                inventory,
                nutrition_store,
            )
        )
        if progress:
            progress(
                "nutrition",
                completed=min(offset + len(batch), len(candidates)),
                total=total_candidates,
                message="Preparing candidate nutrition",
            )
    goal = normalize_nutrition_goal(
        (shared_filters or {}).get("nutritionGoal") or bridge.recipe_hub.ui_preferences.get("nutritionGoal") or "balanced"
    )
    start = date.fromisoformat(week_start)
    settings = lifecycle.settings
    # Each calendar date has its own saved slot pattern. Shared recipe filters
    # still limit which of those slots are eligible.
    from .diet_profiles import resolve_filters
    from .shared_recipe_filters import daily_targets, normalize_filters
    profile_target_settings = resolve_filters(
        bridge.recipe_hub.profile,
        normalize_filters(shared_filters if isinstance(shared_filters, dict) else {"dietProfile": "household"}),
    )
    profile_daily_targets = daily_targets(profile_target_settings)
    targets = [row for row in original_slots if row["id"] in target_ids]
    existing = [row for row in original_slots if row["id"] not in target_ids] if replacing else []

    desired = []
    if replacing:
        desired = [(_text(row.get("date")), _text(row.get("mealType")), row) for row in targets]
    else:
        for offset in range(7):
            stamp = (start + timedelta(days=offset)).isoformat()
            for meal_type in meal_slots_for_date(shared_filters, settings, stamp):
                desired.append((stamp, _text(meal_type), None))

    daily_slot_counts: dict[str, int] = {}
    daily_scope = [*existing, *targets] if replacing else [
        {"date": stamp, "selected": True} for stamp, _meal_type, _target in desired
    ]
    for slot in daily_scope:
        if slot.get("selected") is False:
            continue
        stamp = _text(slot.get("date"))
        if stamp:
            daily_slot_counts[stamp] = daily_slot_counts.get(stamp, 0) + 1

    planned = list(existing)
    end = (start + timedelta(days=6)).isoformat()
    previous_week_recipes = [
        signature(row.get("recipe"))
        for row in original_slots
        if week_start <= _text(row.get("date")) <= end and row.get("recipe")
    ]
    # A full regenerate should actually rotate away from the plan it replaces.
    # If the filtered pool is too small we fall back later, but we first try a
    # genuinely different set of dishes.
    regeneration_avoid = previous_week_recipes if not replacing else []
    used_recipes = [signature(row.get("recipe")) for row in planned
        if week_start <= _text(row.get("date")) <= end and row.get("recipe")]
    used_recipes.extend(signature(row["recipe"]) for row in targets if row.get("recipe"))
    candidate_signatures = {id(row): signature(row) for row in candidates}
    used_leftovers = {_text(row.get("leftoverId")) for row in planned + targets if row.get("leftoverId")}
    leftovers = [row for row in lifecycle.leftovers if _text(row.get("id")) not in used_leftovers]
    if shared_filters is not None:
        history = await meal_history_store_for_bridge(bridge)
        meals = {row.get("id"): row for row in history.recent(200)}
        # A cooked leftover cannot be made vegetarian by replacing raw meat.
        allowed = {recipe_identity(row) for row in candidates if (row.get("match") or {}).get("safe")}
        for leftover in leftovers:
            leftover["recipe"] = _leftover_recipe(leftover, meals)
        leftovers = [row for row in leftovers if recipe_identity(row["recipe"]) in allowed]

    unchanged = []
    regeneration_fallback_slots = []
    total_desired = max(1, len(desired))
    if progress:
        progress(
            "ranking",
            completed=0,
            total=total_desired,
            message="Planning weekly meals",
        )
    for slot_index, (stamp, meal_type, target) in enumerate(desired, start=1):
        slot_id = target["id"] if target else f"{stamp}:{meal_type}"
        is_selected = target.get("selected") is not False if target else True
        if (
            settings.get("leftoversFirst")
            and meal_type != "breakfast"
            and leftovers
        ):
            leftover = leftovers.pop(0)
            planned.append({
                "id": slot_id,
                "selected": is_selected,
                "date": stamp,
                "mealType": meal_type,
                "leftoverId": leftover.get("id"),
                "servings": leftover.get("servings"),
                "nutrition": deepcopy(leftover.get("nutrition") or {}),
                "cost": {"totalsByCurrency": deepcopy(leftover.get("costByCurrency") or {})},
            })
            if leftover.get("recipe"):
                used_recipes.append(signature(leftover["recipe"]))
            if progress:
                progress(
                    "ranking",
                    completed=slot_index,
                    total=total_desired,
                    message=f"{stamp} {meal_type}",
                )
            continue

        wanted_taxonomy = (
            ["breakfast"] if meal_type == "breakfast"
            else ["snack", "dessert"] if meal_type in {"morningSnack", "afternoonSnack", "lateSnack"}
            else ["main", "starter", "salad", "soup", "side"]
        )
        fresh_candidates = available_candidates(
            candidates, candidate_signatures, used_recipes, regeneration_avoid
        )
        pool = [
            row for row in fresh_candidates
            if recipe_matches_meal_types(row, wanted_taxonomy)
        ]
        taxonomy_fallback = False
        regeneration_fallback = False
        if not pool and regeneration_avoid:
            reusable_candidates = available_candidates(
                candidates, candidate_signatures, used_recipes
            )
            pool = [
                row for row in reusable_candidates
                if recipe_matches_meal_types(row, wanted_taxonomy)
            ]
            regeneration_fallback = bool(pool)
        if not pool:
            pool = fresh_candidates
            taxonomy_fallback = bool(pool)
        if not pool and regeneration_avoid:
            pool = available_candidates(candidates, candidate_signatures, used_recipes)
            taxonomy_fallback = bool(pool)
            regeneration_fallback = bool(pool)
        if not pool:
            if target:
                planned.append(target)
                unchanged.append(slot_id)
            if progress:
                progress(
                    "ranking",
                    completed=slot_index,
                    total=total_desired,
                    message=f"{stamp} {meal_type}",
                )
            continue

        day_completed = sum(
            1
            for slot in planned
            if slot.get("selected") is not False and _text(slot.get("date")) == stamp
        )
        day_total = max(daily_slot_counts.get(stamp, 0), day_completed + 1)
        if progress:
            progress(
                "ranking",
                completed=slot_index - 1,
                total=total_desired,
                message=f"Scoring {len(pool)} candidates for {stamp} {meal_type}",
            )
        scored = await hass.async_add_executor_job(
            partial(
                _score_week_pool,
                pool,
                planned=planned,
                inventory=inventory,
                nutrition_by_id=nutrition_by_id,
                cost_store=cost_store,
                goal=goal,
                slot_id=slot_id,
                stamp=stamp,
                meal_type=meal_type,
                is_selected=is_selected,
                shared_filters=shared_filters,
                profile_target_settings=profile_target_settings,
                profile_daily_targets=profile_daily_targets,
                day_total=day_total,
            )
        )
        if scored is None:
            if target:
                planned.append(target)
                unchanged.append(slot_id)
            if progress:
                progress(
                    "ranking",
                    completed=slot_index,
                    total=total_desired,
                    message=f"{stamp} {meal_type}",
                )
            continue

        best = scored["recipe"]
        selected = deepcopy(best)
        selected_match = selected.setdefault("match", {})
        selected_match["weeklySelectionScore"] = round(float(scored["score"]), 1)
        selected_match["plannedStockPenalty"] = round(float(scored["penalty"]), 1)
        selected_match["dailyNutrientTargetBonus"] = round(float(scored["dailyBonus"]), 2)
        if shared_filters is None:
            selected_match["mealNutrientTargetBonus"] = round(float(scored["mealTargetBonus"]), 2)
        selected_match["mealTypeTaxonomyFallback"] = taxonomy_fallback
        selected_match["weeklyRegenerationFallback"] = regeneration_fallback
        selected["nutrition"] = scored["nutrition"]
        selected["cost"] = scored["cost"]
        planned.append({
            "id": slot_id,
            "selected": is_selected,
            "date": stamp,
            "mealType": meal_type,
            "recipe": selected,
            "nutrition": scored["nutrition"],
            "cost": scored["cost"],
        })
        used_recipes.append(candidate_signatures[id(best)])
        if regeneration_fallback:
            regeneration_fallback_slots.append(slot_id)
        if progress:
            progress(
                "ranking",
                completed=slot_index,
                total=total_desired,
                message=f"{stamp} {meal_type}",
            )

    planned.sort(key=lambda row: (
        row.get("date") or "",
        MEAL_SLOT_ORDER.index(row.get("mealType")) if row.get("mealType") in MEAL_SLOT_ORDER else len(MEAL_SLOT_ORDER),
        row.get("id") or "",
    ))
    # Candidate search can take time. Never overwrite a selection or edit made
    # by another client while this generation was in flight.
    if lifecycle.slots != original_slots:
        raise ValueError("The weekly plan changed during generation. Refresh it and try again.")
    if progress:
        progress("persist", completed=0, total=1, message="Saving weekly plan")
    previous_shape = {
        row.get("id"): (
            _text(row.get("leftoverId")),
            recipe_identity(row.get("recipe") or {}),
        )
        for row in original_slots
        if week_start <= _text(row.get("date")) <= end
    }
    planned_shape = {
        row.get("id"): (
            _text(row.get("leftoverId")),
            recipe_identity(row.get("recipe") or {}),
        )
        for row in planned
    }
    changed_slots = sum(
        previous_shape.get(slot_id) != shape
        for slot_id, shape in planned_shape.items()
    )
    await lifecycle.async_replace_week(week_start, planned)
    if progress:
        progress("persist", completed=1, total=1, message="Weekly plan saved")
    return {
        "catalogErrors": errors,
        "slotCount": len(planned),
        "unchangedSlotIds": unchanged,
        "candidateCount": len(candidates),
        "candidateLimit": _MAX_WEEK_CANDIDATES,
        "regeneratedFromExisting": bool(regeneration_avoid),
        "regenerationFallbackSlotIds": regeneration_fallback_slots,
        "changedSlotCount": changed_slots,
    }


def _leftover_recipe(leftover, meals):
    if leftover.get("recipe"):
        return deepcopy(leftover["recipe"])
    meal = meals.get(leftover.get("mealHistoryId")) or {}
    return deepcopy(meal.get("recipe") or {key: meal[key] for key in ("title", "groupingFunctionalId", "variantFunctionalId") if meal.get(key)})


async def _state(hass: HomeAssistant, bridge, *, history_days: int = 30, shared_filters=None, ui_language="en", progress=None) -> dict[str, Any]:
    lifecycle = await meal_lifecycle_store_for_bridge(bridge)
    cost_store = await cost_store_for_bridge(bridge)
    inventory = bridge.recipe_hub.profile.get("houseIngredients") or []
    state = lifecycle.snapshot(inventory, start_date=dt_util.now().date())
    history = await meal_history_store_for_bridge(bridge)
    recent = history.recent(200)
    meals = {row.get("id"): row for row in recent}
    for leftover in state.get("leftovers", []):
        leftover["recipe"] = _leftover_recipe(leftover, meals)
    from .weekly_plan import refresh_plan
    await refresh_plan(bridge, state, filters=shared_filters, language=ui_language, progress=progress)
    state.update({
        "costSettings": cost_store.settings,
        "costReferenceCount": cost_store.snapshot()["referenceCount"],
        "nutritionDashboard": _nutrition_dashboard(
            recent, lifecycle,
            targets=lifecycle.settings.get("nutritionTargets") or {},
            days=history_days,
        ),
        "historySummary": history.summary(now=dt_util.now()),
        "suggestedCountry": _text(getattr(hass.config, "country", "")),
    })
    return state


async def _shopping_add(hass: HomeAssistant, rows: list[dict[str, Any]]) -> dict[str, Any]:
    entity_id = v11._shopping_list_entity(hass)
    if not entity_id or not hass.services.has_service("todo", "add_item"):
        raise ValueError("Home Assistant Shopping List cannot add items")
    snapshot = await v12._shopping_snapshot(hass)
    existing = {
        _text(row.get("summary")).casefold()
        for row in snapshot.get("items") or []
        if isinstance(row, dict) and row.get("status") != "completed"
    }
    added = []
    for row in rows:
        quantity = _number(row.get("quantity"))
        unit = _text(row.get("unit"))
        name = _text(row.get("name"))
        if quantity is None or quantity <= 0 or not unit or not name:
            continue
        shown = str(int(quantity)) if float(quantity).is_integer() else f"{quantity:g}"
        summary = f"{shown} {unit} {name}"
        if summary.casefold() in existing:
            continue
        await hass.services.async_call(
            "todo", "add_item",
            {"entity_id": entity_id, "item": summary},
            blocking=True,
        )
        existing.add(summary.casefold())
        added.append(summary)
    return {"added": added, "shopping": await v12._shopping_snapshot(hass)}


async def _shopping_reconcile_preview(hass: HomeAssistant, bridge) -> dict[str, Any]:
    snapshot = await v12._shopping_snapshot(hass)
    try:
        catalog_result = await v11._ingredient_catalog(
            hass, bridge, v11._device_language(bridge), refresh=False
        )
        catalog = [row for row in catalog_result.get("items") or [] if isinstance(row, dict)]
    except Exception:
        catalog = []
    rows = []
    for item in snapshot.get("items") or []:
        if not isinstance(item, dict) or item.get("status") != "completed":
            continue
        summary = _text(item.get("summary"))
        match = _SHOPPING_RE.match(summary)
        if not match:
            rows.append({
                "uid": item.get("uid"), "summary": summary,
                "status": "needs_quantity_and_unit",
            })
            continue
        quantity = _number(match.group("quantity"))
        unit = match.group("unit").lower()
        name = _text(match.group("name"))
        suggestions = suggest_catalog_matches(
            {"genericName": name, "productName": name, "categories": []},
            catalog,
            limit=5,
        ) if catalog else []
        confident = confident_match(suggestions)
        if confident is None:
            rows.append({
                "uid": item.get("uid"), "summary": summary,
                "quantity": quantity, "unit": unit, "name": name,
                "status": "needs_mapping", "suggestions": suggestions,
            })
            continue
        rows.append({
            "uid": item.get("uid"), "summary": summary,
            "quantity": quantity, "unit": unit, "name": name,
            "ingredient": confident["ingredient"],
            "status": "ready",
        })
    return {"items": rows, "readyCount": sum(row.get("status") == "ready" for row in rows)}


async def _ai_substitutions(hass: HomeAssistant, bridge, ingredient: dict[str, Any]) -> list[dict[str, Any]]:
    if v5._default_ai_task_entity_id(hass) is None:
        return []
    name = _text(ingredient.get("name") or ingredient.get("foodName"))
    if not name:
        return []
    profile = bridge.recipe_hub.profile
    instructions = (
        "Suggest up to 5 culinary substitutes for one ingredient. Suggestions are advisory only. "
        f"Ingredient: {name}. Diet: {profile.get('diet') or 'omnivore'}. "
        f"Allergies: {', '.join(profile.get('allergies') or []) or 'none'}. "
        f"Avoid: {', '.join(profile.get('avoid') or []) or 'none'}. "
        'Return ONLY JSON: {"substitutes":[{"name":"...","note":"..."}]}. '
        "Do not include an allergen, avoided food, medicine, or non-food item."
    )
    result = await ai_task.async_generate_data(
        hass,
        task_name="Cook4Me ingredient substitutions",
        entity_id=None,
        instructions=instructions,
    )
    parsed = v5._parse_ai_json(result.data)
    raw_rows = parsed.get("substitutes") if isinstance(parsed, dict) else []
    try:
        catalog_result = await v11._ingredient_catalog(
            hass, bridge, v11._device_language(bridge), refresh=False
        )
        catalog = [row for row in catalog_result.get("items") or [] if isinstance(row, dict)]
    except Exception:
        catalog = []
    output = []
    for raw in raw_rows if isinstance(raw_rows, list) else []:
        if not isinstance(raw, dict):
            continue
        candidate_name = _text(raw.get("name"))
        if not candidate_name:
            continue
        suggestions = suggest_catalog_matches(
            {"genericName": candidate_name, "productName": candidate_name, "categories": []},
            catalog,
            limit=5,
        ) if catalog else []
        chosen = confident_match(suggestions)
        if chosen is None:
            continue
        candidate = dict(chosen["ingredient"])
        annotated = bridge.recipe_hub.annotate({
            "title": "Cook4Me substitution safety check",
            "ingredients": [candidate],
        })
        if not bool((annotated.get("match") or {}).get("safe", True)):
            continue
        output.append({
            "ingredient": candidate,
            "note": _text(raw.get("note"))[:300],
            "confidence": "ai_advisory",
            "requiresApproval": True,
        })
    return output[:5]


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (
        ws_week_state, ws_week_settings_set, ws_week_generate, ws_week_slot_clear, ws_week_select,
        ws_week_add_shopping, ws_recipe_cost, ws_cost_settings_set,
        ws_lot_cost_set, ws_price_reference_set, ws_global_price_lookup,
        ws_feedback_set, ws_leftover_consume, ws_substitution_suggest,
        ws_substitution_approve, ws_shopping_reconcile_preview,
        ws_shopping_reconcile_apply,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/week_state",
    vol.Optional("shared_filters"): dict,
    vol.Optional("ui_language", default="en"): str,
    vol.Optional("entry_id"): str,
    vol.Optional("history_days", default=30): vol.All(vol.Coerce(int), vol.Range(min=7, max=90)),
})
@websocket_api.async_response
async def ws_week_state(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await _state(hass, bridge, history_days=int(msg.get("history_days", 30)),
                              shared_filters=msg.get("shared_filters"), ui_language=msg.get("ui_language", "en"))
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/week_settings_set",
    vol.Optional("entry_id"): str,
    vol.Optional("meal_types"): [str],
    vol.Optional("leftovers_first"): bool,
    vol.Optional("avoid_recent_days"): vol.All(vol.Coerce(int), vol.Range(min=0, max=90)),
    vol.Optional("nutrition_targets"): dict,
    vol.Optional("weekday_meal_types"): dict,
})
@websocket_api.async_response
async def ws_week_settings_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await meal_lifecycle_store_for_bridge(bridge)
        async with store.weekly_mutation():
            await store.async_set_settings(
                meal_types=msg.get("meal_types") if "meal_types" in msg else None,
                leftovers_first=msg.get("leftovers_first") if "leftovers_first" in msg else None,
                avoid_recent_days=msg.get("avoid_recent_days") if "avoid_recent_days" in msg else None,
                nutrition_targets=msg.get("nutrition_targets") if "nutrition_targets" in msg else None,
                weekday_meal_types=msg.get("weekday_meal_types") if "weekday_meal_types" in msg else None,
            )
            result = await _state(hass, bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/week_generate",
    vol.Optional("shared_filters"): dict,
    vol.Optional("ui_language"): str,
    vol.Optional("entry_id"): str,
    vol.Optional("week_start"): str,
    vol.Optional("languages", default=[]): [str],
    vol.Optional("diet", default="profile"): vol.In(v18._DIET_FILTERS),
    vol.Optional("query", default=""): str,
    vol.Optional("refresh", default=False): bool,
    vol.Optional("replace_slot_id", default=""): str,
    vol.Optional("replace_slot_ids"): vol.All([str], vol.Length(min=1, max=42)),
})
@websocket_api.async_response
async def ws_week_generate(hass, connection, msg) -> None:
    operation_id = _text(msg.get("_cook4me_job_id"))
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        raw_start = _text(msg.get("week_start"))
        week_start = rolling_week_start(raw_start, dt_util.now().date())
        progress = lambda phase, **values: _emit_week_progress(
            hass, operation_id, phase, **values
        )
        if lifecycle.weekly_mutation_busy:
            _emit_week_progress(
                hass,
                operation_id,
                "starting",
                message="Queued behind another weekly plan change",
                kind="week_generate_queued",
            )
        async with lifecycle.weekly_mutation():
            progress("starting", message="Generating weekly plan")
            generation = await _generate_week(
                hass, bridge, lifecycle,
                week_start=week_start,
                languages=v18._languages(bridge, msg.get("languages")),
                diet=_text(msg.get("diet")) or "profile",
                query=_text(msg.get("query")),
                refresh=bool(msg.get("refresh")),
                replace_slot_id=_text(msg.get("replace_slot_id")),
                replace_slot_ids=msg.get("replace_slot_ids"),
                shared_filters=msg.get("shared_filters"),
                ui_language=msg.get("ui_language", "en"),
                progress=progress,
            )
            state = await _state(
                hass,
                bridge,
                shared_filters=msg.get("shared_filters"),
                ui_language=msg.get("ui_language", "en"),
                progress=progress,
            )
            result = {**generation, **state}
        changed = int(generation.get("changedSlotCount") or 0)
        progress(
            "done",
            completed=1,
            total=1,
            message=f"Weekly plan ready · {changed} meal slot(s) changed",
            done=True,
        )
    except Exception as exc:
        _emit_week_progress(
            hass,
            operation_id,
            "failed",
            message=type(exc).__name__,
            done=True,
            error=type(exc).__name__,
        )
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/week_slot_clear",
    vol.Optional("entry_id"): str,
    vol.Required("slot_id"): str,
})
@websocket_api.async_response
async def ws_week_slot_clear(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        async with lifecycle.weekly_mutation():
            cleared = await lifecycle.async_clear_slot(str(msg["slot_id"]))
            result = {"cleared": cleared, **await _state(hass, bridge)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/week_select",
    vol.Optional("entry_id"): str,
    vol.Required("slot_ids"): vol.All([str], vol.Length(min=1, max=42)),
    vol.Required("selected"): bool,
    vol.Optional("shared_filters"): dict,
    vol.Optional("ui_language", default="en"): str,
})
@websocket_api.async_response
async def ws_week_select(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        async with lifecycle.weekly_mutation():
            current = lifecycle.snapshot(start_date=dt_util.now().date())
            if not set(msg["slot_ids"]).issubset({row["id"] for row in current["slots"]}):
                raise ValueError("The selected meals are no longer in the next seven days")
            await lifecycle.async_select_slots(msg["slot_ids"], msg["selected"])
            result = await _state(hass, bridge, shared_filters=msg.get("shared_filters"), ui_language=msg["ui_language"])
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/week_add_shopping",
    vol.Optional("shared_filters"): dict,
    vol.Optional("entry_id"): str,
    vol.Optional("ui_language"): str,
})
@websocket_api.async_response
async def ws_week_add_shopping(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        # Shopping is a plan-derived mutation. Keep its snapshot and writes in
        # the same FIFO lane as generation so it cannot add shortages from a
        # half-replaced week.
        async with lifecycle.weekly_mutation():
            snapshot = lifecycle.snapshot(
                bridge.recipe_hub.profile.get("houseIngredients") or [],
                start_date=dt_util.now().date(),
            )
            if msg.get("shared_filters") is not None:
                snapshot = await _state(
                    hass,
                    bridge,
                    shared_filters=msg["shared_filters"],
                    ui_language=msg.get("ui_language", "en"),
                )
            if any(
                (((slot.get("recipe") or {}).get("match") or {}).get("requiresSubstitutions"))
                for slot in snapshot["slots"]
                if slot.get("selected") is not False
            ):
                raise ValueError(
                    "Some planned recipes still need ingredient replacements. "
                    "Resolve those recipes before adding the week to shopping."
                )
            rows = snapshot["shoppingDelta"]
            from .shopping_presentation import shopping_rows, normalize_supermarket_language
            cost_store = await cost_store_for_bridge(bridge)
            market_settings = cost_store.settings
            shopping_language = normalize_supermarket_language(
                msg.get("ui_language") or market_settings.get("supermarketLanguage"),
                country=market_settings.get("country") or getattr(hass.config, "country", ""),
                fallback="en",
            )
            rows = await hass.async_add_executor_job(
                shopping_rows,
                rows,
                shopping_language,
                market_settings.get("country") or getattr(hass.config, "country", ""),
                [
                    item
                    for slot in snapshot["slots"]
                    if slot.get("selected") is not False
                    for item in (slot.get("recipe") or {}).get("ingredients") or []
                ],
            )
            result = await _shopping_add(hass, rows)
            result["shoppingDelta"] = rows
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)

@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/recipe_cost",
    vol.Optional("entry_id"): str,
    vol.Required("recipe"): dict,
    vol.Optional("refresh_global", default=False): bool,
})
@websocket_api.async_response
async def ws_recipe_cost(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        recipe = dict(msg["recipe"])
        store = await cost_store_for_bridge(bridge)
        global_added = 0
        if bool(msg.get("refresh_global")) or store.settings.get("autoGlobalPrices"):
            global_added = await _hydrate_global_prices(hass, bridge, store, recipe)
        result = _recipe_cost_with_store(bridge, recipe, store)
        result["globalReferencesAdded"] = global_added
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/cost_settings_set",
    vol.Optional("entry_id"): str,
    vol.Optional("currency"): str,
    vol.Optional("country"): str,
    vol.Optional("supermarket_language"): str,
    vol.Optional("auto_global_prices"): bool,
})
@websocket_api.async_response
async def ws_cost_settings_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await cost_store_for_bridge(bridge)
        from .shopping_presentation import normalize_supermarket_language
        country = msg.get("country") if "country" in msg else store.settings.get("country")
        supermarket_language = None
        if "supermarket_language" in msg:
            supermarket_language = normalize_supermarket_language(
                msg.get("supermarket_language"), country=country, fallback="en"
            )
        settings = await store.async_set_settings(
            currency=msg.get("currency") if "currency" in msg else None,
            country=msg.get("country") if "country" in msg else None,
            supermarket_language=supermarket_language,
            auto_global_prices=msg.get("auto_global_prices") if "auto_global_prices" in msg else None,
        )
        result = {"settings": settings, **await _state(hass, bridge)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/lot_cost_set",
    vol.Optional("entry_id"): str,
    vol.Required("lot_id"): str,
    vol.Required("price"): vol.Any(int, float, str),
    vol.Required("currency"): str,
    vol.Required("purchase_quantity"): vol.Any(int, float, str),
    vol.Required("purchase_unit"): str,
    vol.Optional("country", default=""): str,
    vol.Optional("merchant", default=""): str,
    vol.Optional("purchase_date", default=""): str,
})
@websocket_api.async_response
async def ws_lot_cost_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        located = _lot_in_inventory(
            bridge.recipe_hub.profile.get("houseIngredients") or [], str(msg["lot_id"])
        )
        if located is None:
            raise ValueError("Stock lot was not found")
        ingredient, lot = located
        store = await cost_store_for_bridge(bridge)
        reference = await store.async_set_reference(
            f"lot:{_text(msg['lot_id'])}",
            amount=msg.get("price"), currency=msg.get("currency"),
            basis_quantity=msg.get("purchase_quantity"), basis_unit=msg.get("purchase_unit"),
            source="purchase", confidence="exact_purchase",
            country=_text(msg.get("country")), location=_text(msg.get("merchant")),
            date=_text(msg.get("purchase_date")), barcode=_text(lot.get("barcode")),
        )
        result = {
            "reference": reference,
            "ingredientIdentity": inventory_identity(ingredient),
            "lot": deepcopy(lot),
        }
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/price_reference_set",
    vol.Optional("entry_id"): str,
    vol.Required("ingredient"): dict,
    vol.Required("price"): vol.Any(int, float, str),
    vol.Required("currency"): str,
    vol.Required("basis_quantity"): vol.Any(int, float, str),
    vol.Required("basis_unit"): str,
    vol.Optional("country", default=""): str,
    vol.Optional("note", default=""): str,
})
@websocket_api.async_response
async def ws_price_reference_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        identity = inventory_identity(dict(msg["ingredient"]))
        if not identity:
            raise ValueError("Ingredient has no stable identity")
        store = await cost_store_for_bridge(bridge)
        result = await store.async_set_reference(
            identity,
            amount=msg.get("price"), currency=msg.get("currency"),
            basis_quantity=msg.get("basis_quantity"), basis_unit=msg.get("basis_unit"),
            source="manual", confidence="user_entered",
            country=_text(msg.get("country")), location=_text(msg.get("note")),
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/global_price_lookup",
    vol.Optional("entry_id"): str,
    vol.Required("barcode"): str,
    vol.Optional("currency", default=""): str,
    vol.Optional("country", default=""): str,
})
@websocket_api.async_response
async def ws_global_price_lookup(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await cost_store_for_bridge(bridge)
        currency = _text(msg.get("currency")) or _text(store.settings.get("currency"))
        country = _text(msg.get("country")) or _text(store.settings.get("country"))
        result = await hass.async_add_executor_job(
            lambda: lookup_open_prices_safe(
                _text(msg["barcode"]), currency=currency, country=country
            )
        )
        stored = await store_best_open_price(
            store, result, currency=currency, country=country
        ) if result.get("ok") else None
        result["storedReference"] = stored
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/feedback_set",
    vol.Optional("entry_id"): str,
    vol.Required("recipe"): dict,
    vol.Optional("rating"): vol.Any(int, float, str),
    vol.Optional("would_cook_again"): bool,
    vol.Optional("notes", default=""): str,
    vol.Optional("tags", default=[]): [str],
})
@websocket_api.async_response
async def ws_feedback_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        result = await lifecycle.async_set_feedback(
            dict(msg["recipe"]),
            rating=msg.get("rating"),
            would_cook_again=msg.get("would_cook_again") if "would_cook_again" in msg else None,
            notes=msg.get("notes"), tags=msg.get("tags"),
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/leftover_consume",
    vol.Optional("entry_id"): str,
    vol.Required("leftover_id"): str,
    vol.Required("servings"): vol.Any(int, float, str),
})
@websocket_api.async_response
async def ws_leftover_consume(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        async with lifecycle.weekly_mutation():
            consumed = await lifecycle.async_consume_leftover(
                str(msg["leftover_id"]), msg.get("servings")
            )
            history = await meal_history_store_for_bridge(bridge)
            record = await history.async_record(
                recipe={"title": consumed.get("title"), "servings": consumed.get("servings")},
                nutrition=consumed.get("nutrition") or {},
                consumption={},
            )
            await lifecycle.async_record_meal_cost(
                record.get("id"),
                {"totalsByCurrency": consumed.get("costByCurrency") or {}, "source": "leftover"},
            )
            result = {"consumed": consumed, "mealHistoryRecord": record, **await _state(hass, bridge)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/substitution_suggest",
    vol.Optional("entry_id"): str,
    vol.Required("ingredient"): dict,
    vol.Optional("use_ai", default=True): bool,
})
@websocket_api.async_response
async def ws_substitution_suggest(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        ingredient = dict(msg["ingredient"])
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        approved = lifecycle.approved_substitutions(ingredient)
        ai_rows = []
        if bool(msg.get("use_ai")):
            try:
                ai_rows = await _ai_substitutions(hass, bridge, ingredient)
            except Exception:
                ai_rows = []
        result = {"approved": approved, "suggestions": ai_rows, "autoApplied": False}
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/substitution_approve",
    vol.Optional("entry_id"): str,
    vol.Required("ingredient"): dict,
    vol.Required("substitute"): dict,
    vol.Optional("note", default=""): str,
})
@websocket_api.async_response
async def ws_substitution_approve(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        substitute = dict(msg["substitute"])
        annotated = bridge.recipe_hub.annotate({
            "title": "Cook4Me substitution safety check", "ingredients": [substitute]
        })
        if not bool((annotated.get("match") or {}).get("safe", True)):
            raise ValueError("Substitute is blocked by the saved diet/allergy profile")
        result = await lifecycle.async_approve_substitution(
            dict(msg["ingredient"]), substitute, note=str(msg.get("note") or "")
        )
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/shopping_reconcile_preview",
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def ws_shopping_reconcile_preview(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await _shopping_reconcile_preview(hass, bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/shopping_reconcile_apply",
    vol.Optional("entry_id"): str,
    vol.Required("items"): [dict],
    vol.Optional("remove_completed", default=False): bool,
})
@websocket_api.async_response
async def ws_shopping_reconcile_apply(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        cost_store = await cost_store_for_bridge(bridge)
        added = []
        for raw in msg.get("items") or []:
            if not isinstance(raw, dict):
                continue
            ingredient = raw.get("ingredient") if isinstance(raw.get("ingredient"), dict) else {}
            quantity = _number(raw.get("quantity"))
            unit = _text(raw.get("unit"))
            if not inventory_identity(ingredient) or quantity is None or quantity <= 0 or not unit:
                continue
            lot_id = _text(raw.get("lot_id")) or str(uuid4())
            lot_metadata = {
                "id": lot_id,
                "source": "shopping_reconcile",
                "purchaseDate": _text(raw.get("purchase_date")) or dt_util.now().date().isoformat(),
            }
            await bridge.recipe_hub.async_inventory_add(
                dict(ingredient), quantity=quantity, unit=unit, unlimited=False,
                best_before=_text(raw.get("best_before")), lot_metadata=lot_metadata,
            )
            price = _number(raw.get("price"))
            currency = _text(raw.get("currency"))
            purchase_quantity = _number(raw.get("purchase_quantity"))
            purchase_unit = _text(raw.get("purchase_unit"))
            if price is not None and currency and purchase_quantity and purchase_unit:
                await cost_store.async_set_reference(
                    f"lot:{lot_id}", amount=price, currency=currency,
                    basis_quantity=purchase_quantity, basis_unit=purchase_unit,
                    source="purchase", confidence="exact_purchase",
                    country=_text(raw.get("country")), location=_text(raw.get("merchant")),
                    date=_text(raw.get("purchase_date")),
                )
            added.append({"lotId": lot_id, "ingredient": deepcopy(ingredient), "quantity": quantity, "unit": unit})
            if bool(msg.get("remove_completed")) and raw.get("uid"):
                try:
                    await v12._shopping_action(hass, action="remove", uid=_text(raw.get("uid")))
                except Exception:
                    pass
        nutrition_store = await nutrition_store_for_bridge(bridge)
        await async_reconcile_nutrition_inventory(
            nutrition_store, bridge.recipe_hub.profile.get("houseIngredients") or []
        )
        update_expiry_notification(bridge)
        result = {"added": added, "houseIngredients": bridge.recipe_hub.profile.get("houseIngredients") or []}
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)
