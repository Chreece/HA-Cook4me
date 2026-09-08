from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import math
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .inventory import convert_amount, inventory_identity, normalize_inventory
from .today_logic import recipe_identity

_STORAGE_VERSION = 1
_MAX_SLOTS = 42
_MAX_LEFTOVERS = 250
_MAX_FEEDBACK = 1000
_MAX_SUBSTITUTIONS = 1000
_DEFAULT_MEAL_TYPES = ["breakfast", "lunch", "dinner"]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _day(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return ""


def monday_for(value: date | datetime | None = None) -> str:
    if value is None:
        current = datetime.now(timezone.utc).date()
    elif isinstance(value, datetime):
        current = value.date()
    else:
        current = value
    return (current - timedelta(days=current.weekday())).isoformat()


def _meal_type(value: Any) -> str:
    token = _text(value).lower()
    return token if token in {"breakfast", "lunch", "dinner", "snack"} else "dinner"


def _recipe_snapshot(recipe: Any) -> dict[str, Any]:
    if not isinstance(recipe, dict):
        return {}
    keep = (
        "id", "title", "source", "language", "sourceLanguage", "selectedLanguage",
        "groupingFunctionalId", "recipeFunctionalId", "variantFunctionalId",
        "sendVariantId", "displayVariantId", "searchVariantId", "sendable",
        "servings", "groupSize", "yield", "ingredients", "steps", "cover",
        "image", "imageUrl", "courses", "mealTypes", "meal_types", "nutrition",
        "officialNutrition", "match", "cost",
    )
    return {key: deepcopy(recipe[key]) for key in keep if key in recipe}


def _slot(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    stamp = _day(raw.get("date"))
    if not stamp:
        return None
    meal_type = _meal_type(raw.get("mealType"))
    leftover_id = _text(raw.get("leftoverId"))
    recipe = _recipe_snapshot(raw.get("recipe"))
    if not recipe and not leftover_id:
        return None
    servings = _number(raw.get("servings"))
    out: dict[str, Any] = {
        "id": _text(raw.get("id")) or f"{stamp}:{meal_type}",
        "date": stamp,
        "mealType": meal_type,
        "servings": servings,
        "recipe": recipe,
        "leftoverId": leftover_id,
        "createdAt": _text(raw.get("createdAt")) or datetime.now(timezone.utc).isoformat(),
    }
    if raw.get("cost") is not None:
        out["cost"] = deepcopy(raw.get("cost"))
    if raw.get("nutrition") is not None:
        out["nutrition"] = deepcopy(raw.get("nutrition"))
    return out


def _ingredient_row(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    name = _text(raw.get("name") or raw.get("foodName"))
    key = _text(raw.get("key") or raw.get("foodKey"))
    quantity = _number(raw.get("quantity"))
    unit = _text(raw.get("unit"))
    if quantity is None:
        weight = raw.get("weight") if isinstance(raw.get("weight"), dict) else {}
        quantity = _number(weight.get("quantity"))
        unit = unit or _text(weight.get("unit"))
    if not name and not key:
        return None
    row = {"name": name or key, "quantity": quantity, "unit": unit}
    if key:
        row["key"] = key
    return row


def _requirement_key(identity: str, unit: str) -> str:
    return f"{identity}|{unit.strip().casefold()}"


def planned_requirements(slots: Any) -> list[dict[str, Any]]:
    """Aggregate planned recipe quantities without inventing incompatible conversions."""
    groups: list[dict[str, Any]] = []
    by_identity: dict[str, list[int]] = {}
    for raw_slot in slots if isinstance(slots, list) else []:
        slot = _slot(raw_slot)
        if slot is None or slot.get("leftoverId"):
            continue
        recipe = slot.get("recipe") or {}
        for raw_ingredient in recipe.get("ingredients") or []:
            ingredient = _ingredient_row(raw_ingredient)
            if ingredient is None:
                continue
            ident = inventory_identity(ingredient)
            quantity = ingredient.get("quantity")
            unit = _text(ingredient.get("unit"))
            if not ident or quantity is None or not unit:
                continue
            indexes = by_identity.setdefault(ident, [])
            merged = False
            for index in indexes:
                target = groups[index]
                converted = convert_amount(quantity, unit, target["unit"])
                if converted is None:
                    continue
                target["quantity"] += converted
                target["slots"].append(slot["id"])
                merged = True
                break
            if merged:
                continue
            indexes.append(len(groups))
            groups.append(
                {
                    "key": _requirement_key(ident, unit),
                    "identity": ident,
                    "name": ingredient["name"],
                    "quantity": float(quantity),
                    "unit": unit,
                    "slots": [slot["id"]],
                }
            )
    for row in groups:
        row["quantity"] = round(float(row["quantity"]), 9)
    return groups


def reservation_status(slots: Any, inventory: Any) -> dict[str, Any]:
    stock = normalize_inventory(inventory)
    requirements = planned_requirements(slots)
    result: list[dict[str, Any]] = []
    for requirement in requirements:
        ident = requirement["identity"]
        required = float(requirement["quantity"])
        unit = requirement["unit"]
        row = next((item for item in stock if inventory_identity(item) == ident), None)
        unlimited = bool(row and row.get("unlimited"))
        available = None
        if unlimited:
            available = required
        elif row:
            stock_quantity = _number(row.get("quantity")) or 0.0
            stock_unit = _text(row.get("unit"))
            converted = convert_amount(stock_quantity, stock_unit, unit)
            if converted is not None:
                available = converted
        shortage = None if available is None else max(0.0, required - available)
        result.append(
            {
                **requirement,
                "available": round(available, 9) if available is not None else None,
                "reserved": round(min(required, available), 9) if available is not None else None,
                "shortage": round(shortage, 9) if shortage is not None else None,
                "unlimited": unlimited,
                "confidence": "quantity" if available is not None else "unknown_unit_or_amount",
            }
        )
    known = [row for row in result if row.get("shortage") is not None]
    return {
        "items": result,
        "shortages": [row for row in result if (row.get("shortage") or 0) > 1e-9],
        "unknown": [row for row in result if row.get("shortage") is None],
        "fullyCovered": bool(result) and len(known) == len(result) and all((row.get("shortage") or 0) <= 1e-9 for row in result),
    }


def shopping_delta(slots: Any, inventory: Any) -> list[dict[str, Any]]:
    reservations = reservation_status(slots, inventory)
    return [
        {
            "identity": row["identity"],
            "name": row["name"],
            "quantity": row["shortage"],
            "unit": row["unit"],
            "required": row["quantity"],
            "available": row["available"],
            "slots": row.get("slots") or [],
        }
        for row in reservations["shortages"]
    ]


def _scale_values(values: Any, factor: float) -> dict[str, float]:
    if not isinstance(values, dict):
        return {}
    out: dict[str, float] = {}
    for key, value in values.items():
        number = _number(value)
        if number is not None:
            out[str(key)] = round(number * factor, 2)
    return out


def _nutrition_values(nutrition: Any) -> dict[str, float]:
    if not isinstance(nutrition, dict):
        return {}
    values = nutrition.get("totals") if isinstance(nutrition.get("totals"), dict) else nutrition
    return {str(key): float(value) for key, value in values.items() if isinstance(value, (int, float))}


def _scale_currency(values: Any, factor: float) -> dict[str, float]:
    if not isinstance(values, dict):
        return {}
    return {
        str(currency): round(float(amount) * factor, 2)
        for currency, amount in values.items()
        if isinstance(amount, (int, float))
    }


class Cook4MeMealPlannerStore:
    """Persist weekly planning, leftovers, recipe feedback, and approved substitutions."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.meal_planner"
        )
        self._loaded = False
        self._data: dict[str, Any] = {
            "weekStart": monday_for(),
            "slots": [],
            "leftovers": [],
            "feedback": {},
            "substitutions": {},
            "settings": {
                "mealTypes": list(_DEFAULT_MEAL_TYPES),
                "leftoversFirst": True,
                "avoidRecentDays": 7,
                "nutritionTargets": {},
            },
        }

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            self._data["weekStart"] = _day(saved.get("weekStart")) or monday_for()
            self._data["slots"] = [
                slot for raw in saved.get("slots") or [] if (slot := _slot(raw)) is not None
            ][-_MAX_SLOTS:]
            self._data["leftovers"] = [
                deepcopy(row)
                for row in saved.get("leftovers") or []
                if isinstance(row, dict) and (_number(row.get("servings")) or 0) > 0
            ][-_MAX_LEFTOVERS:]
            feedback = saved.get("feedback") if isinstance(saved.get("feedback"), dict) else {}
            self._data["feedback"] = {
                str(key): deepcopy(value)
                for key, value in list(feedback.items())[-_MAX_FEEDBACK:]
                if isinstance(value, dict)
            }
            substitutions = saved.get("substitutions") if isinstance(saved.get("substitutions"), dict) else {}
            self._data["substitutions"] = {
                str(key): deepcopy(value)
                for key, value in list(substitutions.items())[-_MAX_SUBSTITUTIONS:]
                if isinstance(value, dict)
            }
            settings = saved.get("settings") if isinstance(saved.get("settings"), dict) else {}
            meal_types = [
                _meal_type(value)
                for value in settings.get("mealTypes") or _DEFAULT_MEAL_TYPES
            ]
            meal_types = list(dict.fromkeys(meal_types))[:4] or list(_DEFAULT_MEAL_TYPES)
            targets: dict[str, float] = {}
            for key, value in (settings.get("nutritionTargets") or {}).items() if isinstance(settings.get("nutritionTargets"), dict) else []:
                number = _number(value)
                if number is not None and number > 0:
                    targets[str(key)] = number
            self._data["settings"] = {
                "mealTypes": meal_types,
                "leftoversFirst": bool(settings.get("leftoversFirst", True)),
                "avoidRecentDays": max(0, min(int(settings.get("avoidRecentDays", 7) or 0), 90)),
                "nutritionTargets": targets,
            }
        self._loaded = True

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    @property
    def slots(self) -> list[dict[str, Any]]:
        return deepcopy(self._data["slots"])

    @property
    def leftovers(self) -> list[dict[str, Any]]:
        return deepcopy(self._data["leftovers"])

    @property
    def settings(self) -> dict[str, Any]:
        return deepcopy(self._data["settings"])

    def snapshot(self, inventory: Any = None) -> dict[str, Any]:
        result = {
            "weekStart": self._data["weekStart"],
            "slots": self.slots,
            "leftovers": self.leftovers,
            "feedback": deepcopy(self._data["feedback"]),
            "substitutions": deepcopy(self._data["substitutions"]),
            "settings": self.settings,
        }
        if inventory is not None:
            result["reservations"] = reservation_status(result["slots"], inventory)
            result["shoppingDelta"] = shopping_delta(result["slots"], inventory)
        return result

    async def async_set_settings(
        self,
        *,
        meal_types: Any = None,
        leftovers_first: Any = None,
        avoid_recent_days: Any = None,
        nutrition_targets: Any = None,
    ) -> dict[str, Any]:
        settings = dict(self._data["settings"])
        if meal_types is not None:
            values = [_meal_type(value) for value in meal_types if _text(value)] if isinstance(meal_types, list) else []
            settings["mealTypes"] = list(dict.fromkeys(values))[:4] or list(_DEFAULT_MEAL_TYPES)
        if leftovers_first is not None:
            settings["leftoversFirst"] = bool(leftovers_first)
        if avoid_recent_days is not None:
            settings["avoidRecentDays"] = max(0, min(int(avoid_recent_days), 90))
        if nutrition_targets is not None:
            targets: dict[str, float] = {}
            if isinstance(nutrition_targets, dict):
                for key, value in nutrition_targets.items():
                    number = _number(value)
                    if number is not None and number > 0:
                        targets[str(key)] = number
            settings["nutritionTargets"] = targets
        self._data["settings"] = settings
        await self._save()
        return self.settings

    async def async_replace_week(self, week_start: Any, slots: Any) -> dict[str, Any]:
        start = _day(week_start) or monday_for()
        normalized = [slot for raw in slots if (slot := _slot(raw)) is not None] if isinstance(slots, list) else []
        self._data["weekStart"] = start
        self._data["slots"] = normalized[:_MAX_SLOTS]
        await self._save()
        return self.snapshot()

    async def async_upsert_slot(self, raw: dict[str, Any]) -> dict[str, Any]:
        slot = _slot(raw)
        if slot is None:
            raise ValueError("Meal plan slot requires date plus recipe or leftover")
        slots = [row for row in self._data["slots"] if row.get("id") != slot["id"]]
        slots.append(slot)
        slots.sort(key=lambda row: (row.get("date") or "", row.get("mealType") or ""))
        self._data["slots"] = slots[-_MAX_SLOTS:]
        await self._save()
        return deepcopy(slot)

    async def async_clear_slot(self, slot_id: str) -> bool:
        before = len(self._data["slots"])
        self._data["slots"] = [row for row in self._data["slots"] if row.get("id") != _text(slot_id)]
        changed = len(self._data["slots"]) != before
        if changed:
            await self._save()
        return changed

    def feedback_for(self, recipe: Any) -> dict[str, Any] | None:
        key = recipe_identity(recipe) if isinstance(recipe, dict) else _text(recipe)
        row = self._data["feedback"].get(key)
        return deepcopy(row) if isinstance(row, dict) else None

    def feedback_bonus(self, recipe: dict[str, Any]) -> float:
        row = self.feedback_for(recipe)
        if not row:
            return 0.0
        rating = _number(row.get("rating"))
        bonus = (rating - 3.0) * 7.5 if rating is not None else 0.0
        if row.get("wouldCookAgain") is False:
            bonus -= 50.0
        elif row.get("wouldCookAgain") is True:
            bonus += 5.0
        return round(bonus, 1)

    async def async_set_feedback(
        self,
        recipe: dict[str, Any],
        *,
        rating: Any = None,
        would_cook_again: Any = None,
        notes: Any = "",
        tags: Any = None,
    ) -> dict[str, Any]:
        key = recipe_identity(recipe)
        if not key:
            raise ValueError("Recipe has no stable identity")
        value = _number(rating)
        if value is not None:
            value = max(1.0, min(value, 5.0))
        row = {
            "recipeKey": key,
            "title": _text(recipe.get("title")),
            "rating": value,
            "wouldCookAgain": bool(would_cook_again) if would_cook_again is not None else None,
            "notes": _text(notes)[:1000],
            "tags": list(dict.fromkeys(_text(tag) for tag in tags or [] if _text(tag)))[:30] if isinstance(tags, list) else [],
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        self._data["feedback"][key] = row
        while len(self._data["feedback"]) > _MAX_FEEDBACK:
            self._data["feedback"].pop(next(iter(self._data["feedback"])), None)
        await self._save()
        return deepcopy(row)

    async def async_add_leftover_from_meal(
        self,
        meal: dict[str, Any],
        *,
        cost: Any = None,
        storage: str = "fridge",
        best_before: str = "",
    ) -> dict[str, Any] | None:
        remaining = _number(meal.get("remainingServings"))
        cooked_servings = _number(meal.get("servings"))
        if remaining is None or remaining <= 0 or cooked_servings is None or cooked_servings <= 0:
            return None
        fraction = min(1.0, remaining / cooked_servings)
        cooked_values = _nutrition_values(meal.get("cookedNutrition") or meal.get("nutrition"))
        cost_totals = cost.get("totalsByCurrency") if isinstance(cost, dict) else {}
        row = {
            "id": str(uuid4()),
            "mealHistoryId": _text(meal.get("id")),
            "title": _text(meal.get("title")) or "Cook4Me leftovers",
            "servings": remaining,
            "originalServings": cooked_servings,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "storage": _text(storage).lower() or "fridge",
            "bestBefore": _day(best_before),
            "nutrition": {"totals": _scale_values(cooked_values, fraction)},
            "nutritionPerServing": _scale_values(cooked_values, 1.0 / cooked_servings),
            "costByCurrency": _scale_currency(cost_totals, fraction),
            "costPerServingByCurrency": _scale_currency(cost_totals, 1.0 / cooked_servings),
        }
        self._data["leftovers"] = (self._data["leftovers"] + [row])[-_MAX_LEFTOVERS:]
        await self._save()
        return deepcopy(row)

    async def async_consume_leftover(self, leftover_id: str, servings: Any) -> dict[str, Any]:
        wanted = _text(leftover_id)
        amount = _number(servings)
        if amount is None or amount <= 0:
            raise ValueError("Leftover servings must be greater than zero")
        for index, row in enumerate(self._data["leftovers"]):
            if _text(row.get("id")) != wanted:
                continue
            available = _number(row.get("servings")) or 0.0
            take = min(available, amount)
            factor = take / available if available > 0 else 0.0
            consumed = {
                "id": row.get("id"),
                "title": row.get("title"),
                "servings": take,
                "nutrition": {"totals": _scale_values(_nutrition_values(row.get("nutrition")), factor)},
                "costByCurrency": _scale_currency(row.get("costByCurrency"), factor),
            }
            left = available - take
            if left <= 1e-9:
                self._data["leftovers"].pop(index)
            else:
                row["servings"] = round(left, 3)
                row["nutrition"] = {"totals": _scale_values(_nutrition_values(row.get("nutrition")), left / available)}
                row["costByCurrency"] = _scale_currency(row.get("costByCurrency"), left / available)
            await self._save()
            consumed["remainingServings"] = max(0.0, left)
            return consumed
        raise ValueError("Leftover meal was not found")

    def approved_substitutions(self, ingredient: dict[str, Any]) -> list[dict[str, Any]]:
        ident = inventory_identity(ingredient)
        row = self._data["substitutions"].get(ident)
        values = row.get("items") if isinstance(row, dict) and isinstance(row.get("items"), list) else []
        return deepcopy(values)

    async def async_approve_substitution(
        self,
        ingredient: dict[str, Any],
        substitute: dict[str, Any],
        *,
        note: str = "",
    ) -> dict[str, Any]:
        ident = inventory_identity(ingredient)
        sub_ident = inventory_identity(substitute)
        if not ident or not sub_ident:
            raise ValueError("Both original and substitute require stable identities")
        row = self._data["substitutions"].setdefault(
            ident,
            {"identity": ident, "name": _text(ingredient.get("name") or ingredient.get("foodName")), "items": []},
        )
        items = [item for item in row.get("items") or [] if inventory_identity(item.get("ingredient") or {}) != sub_ident]
        items.append(
            {
                "ingredient": deepcopy(substitute),
                "note": _text(note)[:500],
                "approvedAt": datetime.now(timezone.utc).isoformat(),
                "confidence": "user_approved",
            }
        )
        row["items"] = items[-30:]
        while len(self._data["substitutions"]) > _MAX_SUBSTITUTIONS:
            self._data["substitutions"].pop(next(iter(self._data["substitutions"])), None)
        await self._save()
        return deepcopy(row)


async def meal_planner_store_for_bridge(bridge: Any) -> Cook4MeMealPlannerStore:
    store = getattr(bridge, "_meal_planner_store", None)
    if store is None:
        store = Cook4MeMealPlannerStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._meal_planner_store = store
    return store
