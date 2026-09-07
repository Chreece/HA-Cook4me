from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .food_intelligence import allocate_meal_nutrition

_STORAGE_VERSION = 1
_MAX_MEALS = 1000


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _nutrition_totals(row: Any) -> dict[str, float]:
    if not isinstance(row, dict):
        return {}
    values = row.get("totals") if isinstance(row.get("totals"), dict) else row
    return {
        str(key): float(value)
        for key, value in values.items()
        if isinstance(value, (int, float))
    }


def _add(target: dict[str, float], values: dict[str, float]) -> None:
    for key, value in values.items():
        target[key] = target.get(key, 0.0) + float(value)


def _scaled_nutrition(nutrition: Any, fraction: float) -> dict[str, Any]:
    out = deepcopy(nutrition) if isinstance(nutrition, dict) else {}
    scale = max(0.0, min(1.0, float(fraction)))
    out["totals"] = {
        key: round(value * scale, 2)
        for key, value in _nutrition_totals(nutrition).items()
    }
    out["consumedFraction"] = round(scale, 4)
    return out


def _actual_consumption(report: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(report, dict):
        return [], []
    ingredients = [
        deepcopy(row)
        for row in report.get("deducted") or []
        if isinstance(row, dict)
    ]
    lots = [
        deepcopy(row)
        for row in report.get("deductedLots") or []
        if isinstance(row, dict)
    ]
    return ingredients, lots


class Cook4MeMealHistoryStore:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.meal_history"
        )
        self._loaded = False
        self._data: dict[str, Any] = {"meals": []}

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict) and isinstance(saved.get("meals"), list):
            self._data["meals"] = [
                deepcopy(row)
                for row in saved["meals"][-_MAX_MEALS:]
                if isinstance(row, dict)
            ]
        self._loaded = True

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    async def async_record(
        self,
        *,
        recipe: dict[str, Any],
        nutrition: dict[str, Any],
        allocations: Any = None,
        consumption: Any = None,
    ) -> dict[str, Any]:
        totals = _nutrition_totals(nutrition)
        servings = _number(recipe.get("servings"))
        allocation = allocate_meal_nutrition(totals, servings, allocations)
        allocation_rows = allocation.get("allocations") or []
        assigned = _number(allocation.get("assignedServings")) or 0.0

        # If the user explicitly allocates servings, only those servings are counted
        # as eaten. The full cooked meal is retained separately for traceability.
        consumed_fraction = 1.0
        if allocation_rows and servings and servings > 0:
            consumed_fraction = min(1.0, assigned / servings)

        ingredients, stock_lots = _actual_consumption(consumption)
        cooked_nutrition = deepcopy(nutrition)
        consumed_nutrition = _scaled_nutrition(nutrition, consumed_fraction)
        remaining = (
            _number(allocation.get("unassignedServings"))
            if allocation_rows
            else (0.0 if servings is not None else None)
        )

        row = {
            "id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": str(
                recipe.get("recipeTitle")
                or recipe.get("title")
                or "Cook4Me meal"
            ),
            "groupingFunctionalId": recipe.get("groupingFunctionalId"),
            "variantFunctionalId": (
                recipe.get("variantFunctionalId")
                or recipe.get("recipeFunctionalId")
            ),
            "servings": servings,
            # Backward compatibility: nutrition remains the full confirmed cooked meal.
            "nutrition": cooked_nutrition,
            "cookedNutrition": cooked_nutrition,
            "consumedNutrition": consumed_nutrition,
            "eatenServings": assigned if allocation_rows else servings,
            "remainingServings": remaining,
            "allocations": allocation_rows,
            "assignedServings": allocation.get("assignedServings"),
            "unassignedServings": allocation.get("unassignedServings"),
            "ingredients": ingredients,
            "stockLots": stock_lots,
        }
        self._data["meals"] = (
            self._data.get("meals", []) + [row]
        )[-_MAX_MEALS:]
        await self._save()
        return deepcopy(row)

    def recent(self, limit: int = 30) -> list[dict[str, Any]]:
        return deepcopy(
            list(
                reversed(
                    self._data.get("meals", [])[
                        -max(1, min(int(limit), 200)):
                    ]
                )
            )
        )

    def summary(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Return local-calendar today plus rolling 7/30-day eaten nutrition totals."""
        reference = now or datetime.now(timezone.utc)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        cutoffs = {
            "today": reference.replace(hour=0, minute=0, second=0, microsecond=0),
            "week": reference - timedelta(days=7),
            "month": reference - timedelta(days=30),
        }
        result: dict[str, Any] = {}
        meals = self._data.get("meals", [])
        for name, cutoff in cutoffs.items():
            totals: dict[str, float] = {}
            people: dict[str, dict[str, float]] = {}
            count = 0
            for row in meals:
                try:
                    stamp = datetime.fromisoformat(str(row.get("timestamp") or ""))
                    if stamp.tzinfo is None:
                        stamp = stamp.replace(tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    continue
                if stamp < cutoff:
                    continue
                count += 1
                # Old records have no consumedNutrition and retain their historical
                # full-meal behavior; new records count only servings marked eaten.
                _add(
                    totals,
                    _nutrition_totals(
                        row.get("consumedNutrition") or row.get("nutrition")
                    ),
                )
                for allocation in row.get("allocations") or []:
                    if not isinstance(allocation, dict):
                        continue
                    person = str(allocation.get("name") or "").strip()
                    if not person:
                        continue
                    person_totals = people.setdefault(person, {})
                    _add(
                        person_totals,
                        _nutrition_totals(allocation.get("nutrition")),
                    )
            result[name] = {
                "mealCount": count,
                "totals": {
                    key: round(value, 2)
                    for key, value in totals.items()
                },
                "people": {
                    person: {
                        key: round(value, 2)
                        for key, value in values.items()
                    }
                    for person, values in people.items()
                },
            }
        return result


async def meal_history_store_for_bridge(bridge: Any) -> Cook4MeMealHistoryStore:
    store = getattr(bridge, "_meal_history_store", None)
    if store is None:
        store = Cook4MeMealHistoryStore(
            bridge.hass, bridge.entry.entry_id
        )
        await store.async_load()
        bridge._meal_history_store = store
    return store
