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
_MAX_MEAL_COSTS = 1000
_DEFAULT_MEAL_TYPES = ("breakfast", "lunch", "dinner")
_VALID_MEAL_TYPES = {"breakfast", "lunch", "dinner", "snack"}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _date(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return ""


def week_monday(value: date | datetime | None = None) -> str:
    current = value.date() if isinstance(value, datetime) else value
    current = current or datetime.now(timezone.utc).date()
    return (current - timedelta(days=current.weekday())).isoformat()


def _meal_type(value: Any) -> str:
    token = _text(value).lower()
    return token if token in _VALID_MEAL_TYPES else "dinner"


def _recipe_snapshot(recipe: Any) -> dict[str, Any]:
    if not isinstance(recipe, dict):
        return {}
    keep = (
        "id", "title", "source", "language", "sourceLanguage", "selectedLanguage",
        "groupingFunctionalId", "recipeFunctionalId", "variantFunctionalId",
        "sendVariantId", "displayVariantId", "searchVariantId", "sendable",
        "servings", "groupSize", "yield", "ingredients", "steps", "cover",
        "image", "imageUrl", "courses", "occasions", "mealTypes", "meal_types",
        "nutrition", "officialNutrition", "match", "cost",
    )
    return {key: deepcopy(recipe[key]) for key in keep if key in recipe}


def _slot(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    stamp = _date(raw.get("date"))
    if not stamp:
        return None
    meal_type = _meal_type(raw.get("mealType"))
    recipe = _recipe_snapshot(raw.get("recipe"))
    leftover_id = _text(raw.get("leftoverId"))
    if not recipe and not leftover_id:
        return None
    out: dict[str, Any] = {
        "id": _text(raw.get("id")) or f"{stamp}:{meal_type}",
        "date": stamp,
        "mealType": meal_type,
        "recipe": recipe,
        "leftoverId": leftover_id,
        "createdAt": _text(raw.get("createdAt")) or datetime.now(timezone.utc).isoformat(),
    }
    servings = _number(raw.get("servings"))
    if servings is not None:
        out["servings"] = servings
    for key in ("nutrition", "cost"):
        if isinstance(raw.get(key), dict):
            out[key] = deepcopy(raw[key])
    return out


def _ingredient(raw: Any) -> dict[str, Any] | None:
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
    out = {"name": name or key, "quantity": quantity, "unit": unit}
    if key:
        out["key"] = key
    return out


def planned_requirements(slots: Any) -> list[dict[str, Any]]:
    """Aggregate planned quantities only when unit conversion is explicitly valid."""
    groups: list[dict[str, Any]] = []
    by_identity: dict[str, list[int]] = {}
    for raw_slot in slots if isinstance(slots, list) else []:
        slot = _slot(raw_slot)
        if slot is None or slot.get("leftoverId"):
            continue
        for raw in (slot.get("recipe") or {}).get("ingredients") or []:
            ingredient = _ingredient(raw)
            if ingredient is None:
                continue
            identity = inventory_identity(ingredient)
            quantity = ingredient.get("quantity")
            unit = _text(ingredient.get("unit"))
            if not identity or quantity is None or not unit:
                continue
            merged = False
            indexes = by_identity.setdefault(identity, [])
            for index in indexes:
                target = groups[index]
                converted = convert_amount(quantity, unit, target["unit"])
                if converted is None:
                    continue
                target["quantity"] += converted
                target["slots"].append(slot["id"])
                merged = True
                break
            if not merged:
                indexes.append(len(groups))
                groups.append({
                    "identity": identity,
                    "name": ingredient["name"],
                    "quantity": float(quantity),
                    "unit": unit,
                    "slots": [slot["id"]],
                })
    for row in groups:
        row["quantity"] = round(float(row["quantity"]), 9)
    return groups


def reservation_status(slots: Any, inventory: Any) -> dict[str, Any]:
    stock = normalize_inventory(inventory)
    items: list[dict[str, Any]] = []
    for requirement in planned_requirements(slots):
        row = next(
            (item for item in stock if inventory_identity(item) == requirement["identity"]),
            None,
        )
        required = float(requirement["quantity"])
        unlimited = bool(row and row.get("unlimited"))
        available: float | None = required if unlimited else None
        if row and not unlimited:
            converted = convert_amount(
                row.get("quantity"), row.get("unit", ""), requirement["unit"]
            )
            if converted is not None:
                available = max(0.0, float(converted))
        shortage = None if available is None else max(0.0, required - available)
        items.append({
            **requirement,
            "available": round(available, 9) if available is not None else None,
            "reserved": round(min(required, available), 9) if available is not None else None,
            "shortage": round(shortage, 9) if shortage is not None else None,
            "unlimited": unlimited,
            "confidence": "quantity" if available is not None else "unknown_unit_or_amount",
        })
    known = [row for row in items if row["shortage"] is not None]
    return {
        "items": items,
        "shortages": [row for row in items if (row.get("shortage") or 0.0) > 1e-9],
        "unknown": [row for row in items if row.get("shortage") is None],
        "fullyCovered": len(known) == len(items) and all(
            (row.get("shortage") or 0.0) <= 1e-9 for row in known
        ),
    }


def shopping_delta(slots: Any, inventory: Any) -> list[dict[str, Any]]:
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
        for row in reservation_status(slots, inventory)["shortages"]
    ]


def _nutrition_totals(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    raw = value.get("totals") if isinstance(value.get("totals"), dict) else value
    return {
        str(key): float(number)
        for key, number in raw.items()
        if isinstance(number, (int, float)) and math.isfinite(float(number))
    }


def _scale_numeric_map(values: Any, factor: float) -> dict[str, float]:
    if not isinstance(values, dict):
        return {}
    return {
        str(key): round(float(value) * factor, 2)
        for key, value in values.items()
        if isinstance(value, (int, float)) and math.isfinite(float(value))
    }


class Cook4MeMealLifecycleStore:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.meal_lifecycle"
        )
        self._loaded = False
        self._data: dict[str, Any] = {
            "weekStart": week_monday(),
            "slots": [],
            "leftovers": [],
            "feedback": {},
            "substitutions": {},
            "mealCosts": {},
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
            self._data["weekStart"] = _date(saved.get("weekStart")) or week_monday()
            self._data["slots"] = [
                slot for raw in saved.get("slots") or []
                if (slot := _slot(raw)) is not None
            ][-_MAX_SLOTS:]
            self._data["leftovers"] = [
                deepcopy(row) for row in saved.get("leftovers") or []
                if isinstance(row, dict) and (_number(row.get("servings")) or 0) > 0
            ][-_MAX_LEFTOVERS:]
            for key, maximum in (
                ("feedback", _MAX_FEEDBACK),
                ("substitutions", _MAX_SUBSTITUTIONS),
                ("mealCosts", _MAX_MEAL_COSTS),
            ):
                raw = saved.get(key) if isinstance(saved.get(key), dict) else {}
                self._data[key] = {
                    str(item_key): deepcopy(item_value)
                    for item_key, item_value in list(raw.items())[-maximum:]
                    if isinstance(item_value, dict)
                }
            settings = saved.get("settings") if isinstance(saved.get("settings"), dict) else {}
            raw_types = settings.get("mealTypes") if isinstance(settings.get("mealTypes"), list) else list(_DEFAULT_MEAL_TYPES)
            meal_types = list(dict.fromkeys(_meal_type(value) for value in raw_types))[:4]
            raw_targets = settings.get("nutritionTargets") if isinstance(settings.get("nutritionTargets"), dict) else {}
            targets: dict[str, float] = {}
            for key, value in raw_targets.items():
                number = _number(value)
                if number is not None and number > 0:
                    targets[str(key)] = number
            try:
                avoid_days = int(settings.get("avoidRecentDays", 7))
            except (TypeError, ValueError):
                avoid_days = 7
            self._data["settings"] = {
                "mealTypes": meal_types or list(_DEFAULT_MEAL_TYPES),
                "leftoversFirst": bool(settings.get("leftoversFirst", True)),
                "avoidRecentDays": max(0, min(avoid_days, 90)),
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
            raw = meal_types if isinstance(meal_types, list) else []
            values = list(dict.fromkeys(_meal_type(value) for value in raw if _text(value)))[:4]
            settings["mealTypes"] = values or list(_DEFAULT_MEAL_TYPES)
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
        self._data["weekStart"] = _date(week_start) or week_monday()
        raw_slots = slots if isinstance(slots, list) else []
        self._data["slots"] = [
            slot for raw in raw_slots if (slot := _slot(raw)) is not None
        ][:_MAX_SLOTS]
        await self._save()
        return self.snapshot()

    async def async_upsert_slot(self, raw: dict[str, Any]) -> dict[str, Any]:
        slot = _slot(raw)
        if slot is None:
            raise ValueError("Meal plan slot requires a date plus recipe or leftover")
        rows = [row for row in self._data["slots"] if row.get("id") != slot["id"]]
        rows.append(slot)
        rows.sort(key=lambda row: (row.get("date") or "", row.get("mealType") or ""))
        self._data["slots"] = rows[-_MAX_SLOTS:]
        await self._save()
        return deepcopy(slot)

    async def async_clear_slot(self, slot_id: str) -> bool:
        before = len(self._data["slots"])
        self._data["slots"] = [row for row in self._data["slots"] if row.get("id") != _text(slot_id)]
        changed = before != len(self._data["slots"])
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
        rating_value = _number(rating)
        if rating_value is not None:
            rating_value = max(1.0, min(rating_value, 5.0))
        row = {
            "recipeKey": key,
            "title": _text(recipe.get("title")),
            "rating": rating_value,
            "wouldCookAgain": bool(would_cook_again) if would_cook_again is not None else None,
            "notes": _text(notes)[:1000],
            "tags": list(dict.fromkeys(
                _text(tag) for tag in (tags if isinstance(tags, list) else []) if _text(tag)
            ))[:30],
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        self._data["feedback"][key] = row
        while len(self._data["feedback"]) > _MAX_FEEDBACK:
            self._data["feedback"].pop(next(iter(self._data["feedback"])), None)
        await self._save()
        return deepcopy(row)

    async def async_record_meal_cost(self, meal_id: str, cost: dict[str, Any]) -> None:
        key = _text(meal_id)
        if not key:
            return
        self._data["mealCosts"][key] = {
            "mealId": key,
            "cost": deepcopy(cost),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        while len(self._data["mealCosts"]) > _MAX_MEAL_COSTS:
            self._data["mealCosts"].pop(next(iter(self._data["mealCosts"])), None)
        await self._save()

    def meal_cost(self, meal_id: str) -> dict[str, Any] | None:
        row = self._data["mealCosts"].get(_text(meal_id))
        return deepcopy(row.get("cost")) if isinstance(row, dict) else None

    async def async_add_leftover_from_meal(
        self,
        meal: dict[str, Any],
        *,
        cost: Any = None,
        storage: str = "fridge",
        best_before: str = "",
    ) -> dict[str, Any] | None:
        remaining = _number(meal.get("remainingServings"))
        servings = _number(meal.get("servings"))
        if remaining is None or remaining <= 0 or servings is None or servings <= 0:
            return None
        fraction = min(1.0, remaining / servings)
        nutrition = _nutrition_totals(meal.get("cookedNutrition") or meal.get("nutrition"))
        cost_totals = (
            cost.get("totalsByCurrency") if isinstance(cost, dict)
            and isinstance(cost.get("totalsByCurrency"), dict) else {}
        )
        row = {
            "id": str(uuid4()),
            "mealHistoryId": _text(meal.get("id")),
            "title": _text(meal.get("title")) or "Cook4Me leftovers",
            "servings": remaining,
            "originalServings": servings,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "storage": _text(storage).lower() or "fridge",
            "bestBefore": _date(best_before),
            "nutrition": {"totals": _scale_numeric_map(nutrition, fraction)},
            "nutritionPerServing": _scale_numeric_map(nutrition, 1.0 / servings),
            "costByCurrency": _scale_numeric_map(cost_totals, fraction),
            "costPerServingByCurrency": _scale_numeric_map(cost_totals, 1.0 / servings),
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
            fraction = take / available if available > 0 else 0.0
            consumed = {
                "id": row.get("id"),
                "title": row.get("title"),
                "servings": take,
                "nutrition": {"totals": _scale_numeric_map(
                    _nutrition_totals(row.get("nutrition")), fraction
                )},
                "costByCurrency": _scale_numeric_map(row.get("costByCurrency"), fraction),
            }
            left = available - take
            if left <= 1e-9:
                self._data["leftovers"].pop(index)
            else:
                remaining_fraction = left / available
                row["servings"] = round(left, 3)
                row["nutrition"] = {"totals": _scale_numeric_map(
                    _nutrition_totals(row.get("nutrition")), remaining_fraction
                )}
                row["costByCurrency"] = _scale_numeric_map(
                    row.get("costByCurrency"), remaining_fraction
                )
            await self._save()
            consumed["remainingServings"] = max(0.0, left)
            return consumed
        raise ValueError("Leftover meal was not found")

    def approved_substitutions(self, ingredient: dict[str, Any]) -> list[dict[str, Any]]:
        identity = inventory_identity(ingredient)
        row = self._data["substitutions"].get(identity)
        values = row.get("items") if isinstance(row, dict) and isinstance(row.get("items"), list) else []
        return deepcopy(values)

    async def async_approve_substitution(
        self,
        ingredient: dict[str, Any],
        substitute: dict[str, Any],
        *,
        note: str = "",
    ) -> dict[str, Any]:
        identity = inventory_identity(ingredient)
        substitute_identity = inventory_identity(substitute)
        if not identity or not substitute_identity:
            raise ValueError("Both original and substitute require stable identities")
        row = self._data["substitutions"].setdefault(identity, {
            "identity": identity,
            "name": _text(ingredient.get("name") or ingredient.get("foodName")),
            "items": [],
        })
        items = [
            item for item in row.get("items") or []
            if inventory_identity(item.get("ingredient") or {}) != substitute_identity
        ]
        items.append({
            "ingredient": deepcopy(substitute),
            "note": _text(note)[:500],
            "approvedAt": datetime.now(timezone.utc).isoformat(),
            "confidence": "user_approved",
        })
        row["items"] = items[-30:]
        while len(self._data["substitutions"]) > _MAX_SUBSTITUTIONS:
            self._data["substitutions"].pop(next(iter(self._data["substitutions"])), None)
        await self._save()
        return deepcopy(row)


async def meal_lifecycle_store_for_bridge(bridge: Any) -> Cook4MeMealLifecycleStore:
    store = getattr(bridge, "_meal_lifecycle_store", None)
    if store is None:
        store = Cook4MeMealLifecycleStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._meal_lifecycle_store = store
    return store
