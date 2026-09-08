from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
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
    week_monday,
)
from .nutrition import nutrition_store_for_bridge
from .nutrition_fefo import calculate_recipe_nutrition_fefo
from .nutrition_inventory import async_reconcile_nutrition_inventory
from .today_logic import recipe_identity, recipe_matches_meal_types

_MAX_WEEK_CANDIDATES = 30
_MAX_GLOBAL_PRICE_LOOKUPS = 4
_SHOPPING_RE = re.compile(
    r"^\s*(?P<quantity>\d+(?:[.,]\d+)?)\s*(?P<unit>mg|g|kg|ml|cl|dl|l|pc|pcs|x)\s+(?P<name>.+?)\s*$",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return str(value or "").strip()


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
    settings = cost_store.settings
    if not settings.get("autoGlobalPrices"):
        return 0
    inventory = bridge.recipe_hub.profile.get("houseIngredients") or []
    wanted = {
        inventory_identity(row)
        for row in recipe.get("ingredients") or []
        if isinstance(row, dict)
    }
    barcodes: list[str] = []
    for row in inventory:
        if not isinstance(row, dict) or inventory_identity(row) not in wanted:
            continue
        for lot in row.get("lots") or []:
            if not isinstance(lot, dict):
                continue
            barcode = _text(lot.get("barcode"))
            if not barcode or barcode in barcodes:
                continue
            if cost_store.best_reference(
                f"barcode:{barcode}",
                currency=settings.get("currency", ""),
                country=settings.get("country", ""),
            ) is not None:
                continue
            barcodes.append(barcode)
            if len(barcodes) >= _MAX_GLOBAL_PRICE_LOOKUPS:
                break
        if len(barcodes) >= _MAX_GLOBAL_PRICE_LOOKUPS:
            break

    stored = 0
    for barcode in barcodes:
        result = await hass.async_add_executor_job(
            lambda code=barcode: lookup_open_prices_safe(
                code,
                currency=settings.get("currency", ""),
                country=settings.get("country", ""),
            )
        )
        if result.get("ok") and await store_best_open_price(
            cost_store,
            result,
            currency=settings.get("currency", ""),
            country=settings.get("country", ""),
        ):
            stored += 1
    return stored


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


async def _week_candidates(
    hass: HomeAssistant,
    bridge,
    lifecycle,
    *,
    languages: list[str],
    diet: str,
    query: str,
    refresh: bool,
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
        history.recent(200), days=int(lifecycle.settings.get("avoidRecentDays", 7))
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
) -> dict[str, Any]:
    candidates, errors = await _week_candidates(
        hass, bridge, lifecycle,
        languages=languages, diet=diet, query=query, refresh=refresh,
    )
    nutrition_store = await nutrition_store_for_bridge(bridge)
    cost_store = await cost_store_for_bridge(bridge)
    inventory = bridge.recipe_hub.profile.get("houseIngredients") or []
    goal = normalize_nutrition_goal(
        bridge.recipe_hub.ui_preferences.get("nutritionGoal") or "balanced"
    )
    start = date.fromisoformat(week_start)
    settings = lifecycle.settings
    meal_types = settings.get("mealTypes") or ["breakfast", "lunch", "dinner"]
    existing = lifecycle.slots if replace_slot_id else []
    replace_target = next((row for row in existing if row.get("id") == replace_slot_id), None)
    if replace_slot_id:
        existing = [row for row in existing if row.get("id") != replace_slot_id]

    desired: list[tuple[str, str]] = []
    if replace_target:
        desired = [(_text(replace_target.get("date")), _text(replace_target.get("mealType")))]
    else:
        for offset in range(7):
            stamp = (start + timedelta(days=offset)).isoformat()
            for meal_type in meal_types:
                desired.append((stamp, _text(meal_type)))

    planned = list(existing)
    used_recipes = {recipe_identity(row.get("recipe") or {}) for row in planned}
    used_leftovers = {_text(row.get("leftoverId")) for row in planned if row.get("leftoverId")}
    leftovers = [row for row in lifecycle.leftovers if _text(row.get("id")) not in used_leftovers]

    for stamp, meal_type in desired:
        if (
            settings.get("leftoversFirst")
            and meal_type != "breakfast"
            and leftovers
        ):
            leftover = leftovers.pop(0)
            planned.append({
                "id": f"{stamp}:{meal_type}",
                "date": stamp,
                "mealType": meal_type,
                "leftoverId": leftover.get("id"),
                "servings": leftover.get("servings"),
                "nutrition": deepcopy(leftover.get("nutrition") or {}),
                "cost": {"totalsByCurrency": deepcopy(leftover.get("costByCurrency") or {})},
            })
            continue

        wanted_taxonomy = ["breakfast"] if meal_type == "breakfast" else ["main"]
        pool = [
            row for row in candidates
            if recipe_identity(row) not in used_recipes
            and recipe_matches_meal_types(row, wanted_taxonomy)
        ]
        taxonomy_fallback = False
        if not pool:
            pool = [row for row in candidates if recipe_identity(row) not in used_recipes]
            taxonomy_fallback = True
        if not pool:
            continue

        best: dict[str, Any] | None = None
        best_score = float("-inf")
        best_nutrition: dict[str, Any] = {}
        best_cost: dict[str, Any] = {}
        best_penalty = 0.0
        for candidate in pool:
            nutrition = calculate_recipe_nutrition_fefo(
                candidate,
                inventory,
                generic=nutrition_store.generic,
                stock_lots=nutrition_store.stock_lots,
            )
            nutrition_hint = nutrition_goal_bonus(nutrition, goal)
            candidate_slot = {
                "id": f"{stamp}:{meal_type}",
                "date": stamp,
                "mealType": meal_type,
                "recipe": candidate,
            }
            penalty = _plan_penalty(planned, candidate_slot, inventory)
            score = (
                float((candidate.get("match") or {}).get("score") or 0.0)
                + float(nutrition_hint.get("bonus") or 0.0)
                - penalty
            )
            if score <= best_score:
                continue
            best = candidate
            best_score = score
            best_nutrition = nutrition
            best_cost = _recipe_cost_with_store(bridge, candidate, cost_store)
            best_penalty = penalty
        if best is None:
            continue
        selected = deepcopy(best)
        selected_match = selected.setdefault("match", {})
        selected_match["weeklySelectionScore"] = round(best_score, 1)
        selected_match["plannedStockPenalty"] = round(best_penalty, 1)
        selected_match["mealTypeTaxonomyFallback"] = taxonomy_fallback
        selected["nutrition"] = best_nutrition
        selected["cost"] = best_cost
        planned.append({
            "id": f"{stamp}:{meal_type}",
            "date": stamp,
            "mealType": meal_type,
            "recipe": selected,
            "nutrition": best_nutrition,
            "cost": best_cost,
        })
        used_recipes.add(recipe_identity(selected))

    planned.sort(key=lambda row: (row.get("date") or "", row.get("mealType") or ""))
    if replace_slot_id:
        await lifecycle.async_replace_week(week_start, planned)
    else:
        await lifecycle.async_replace_week(week_start, planned)
    return {"catalogErrors": errors, "slotCount": len(planned)}


async def _state(hass: HomeAssistant, bridge, *, history_days: int = 30) -> dict[str, Any]:
    lifecycle = await meal_lifecycle_store_for_bridge(bridge)
    cost_store = await cost_store_for_bridge(bridge)
    inventory = bridge.recipe_hub.profile.get("houseIngredients") or []
    state = lifecycle.snapshot(inventory)
    weekly_cost: dict[str, float] = {}
    for slot in state["slots"]:
        cost = slot.get("cost") if isinstance(slot.get("cost"), dict) else {}
        if not cost and slot.get("recipe"):
            cost = _recipe_cost_with_store(bridge, slot["recipe"], cost_store)
            slot["cost"] = cost
        _currency_map_add(weekly_cost, cost.get("totalsByCurrency"))
    history = await meal_history_store_for_bridge(bridge)
    recent = history.recent(200)
    state.update({
        "weeklyCostByCurrency": _currency_map(weekly_cost),
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
        ws_week_state, ws_week_settings_set, ws_week_generate, ws_week_slot_clear,
        ws_week_add_shopping, ws_recipe_cost, ws_cost_settings_set,
        ws_lot_cost_set, ws_price_reference_set, ws_global_price_lookup,
        ws_feedback_set, ws_leftover_consume, ws_substitution_suggest,
        ws_substitution_approve, ws_shopping_reconcile_preview,
        ws_shopping_reconcile_apply,
    ):
        websocket_api.async_register_command(hass, command)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/week_state",
    vol.Optional("entry_id"): str,
    vol.Optional("history_days", default=30): vol.All(vol.Coerce(int), vol.Range(min=7, max=90)),
})
@websocket_api.async_response
async def ws_week_state(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        result = await _state(hass, bridge, history_days=int(msg.get("history_days", 30)))
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
})
@websocket_api.async_response
async def ws_week_settings_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await meal_lifecycle_store_for_bridge(bridge)
        await store.async_set_settings(
            meal_types=msg.get("meal_types") if "meal_types" in msg else None,
            leftovers_first=msg.get("leftovers_first") if "leftovers_first" in msg else None,
            avoid_recent_days=msg.get("avoid_recent_days") if "avoid_recent_days" in msg else None,
            nutrition_targets=msg.get("nutrition_targets") if "nutrition_targets" in msg else None,
        )
        result = await _state(hass, bridge)
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/week_generate",
    vol.Optional("entry_id"): str,
    vol.Optional("week_start"): str,
    vol.Optional("languages", default=[]): [str],
    vol.Optional("diet", default="profile"): vol.In(v18._DIET_FILTERS),
    vol.Optional("query", default=""): str,
    vol.Optional("refresh", default=False): bool,
    vol.Optional("replace_slot_id", default=""): str,
})
@websocket_api.async_response
async def ws_week_generate(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        raw_start = _text(msg.get("week_start"))
        week_start = week_monday()
        if raw_start:
            week_start = week_monday(date.fromisoformat(raw_start))
        generation = await _generate_week(
            hass, bridge, lifecycle,
            week_start=week_start,
            languages=v18._languages(bridge, msg.get("languages")),
            diet=_text(msg.get("diet")) or "profile",
            query=_text(msg.get("query")),
            refresh=bool(msg.get("refresh")),
            replace_slot_id=_text(msg.get("replace_slot_id")),
        )
        result = {**generation, **await _state(hass, bridge)}
    except Exception as exc:
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
        cleared = await lifecycle.async_clear_slot(str(msg["slot_id"]))
        result = {"cleared": cleared, **await _state(hass, bridge)}
    except Exception as exc:
        legacy._send_error(connection, msg, exc); return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "cook4me/v20/week_add_shopping",
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def ws_week_add_shopping(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        lifecycle = await meal_lifecycle_store_for_bridge(bridge)
        rows = shopping_delta(
            lifecycle.slots, bridge.recipe_hub.profile.get("houseIngredients") or []
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
    vol.Optional("auto_global_prices"): bool,
})
@websocket_api.async_response
async def ws_cost_settings_set(hass, connection, msg) -> None:
    try:
        bridge = legacy._bridge(hass, msg.get("entry_id"))
        store = await cost_store_for_bridge(bridge)
        settings = await store.async_set_settings(
            currency=msg.get("currency") if "currency" in msg else None,
            country=msg.get("country") if "country" in msg else None,
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
