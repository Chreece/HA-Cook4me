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
                deepcopy(row) for row in saved["meals"][-_MAX_MEALS:] if isinstance(row, dict)
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
    ) -> dict[str, Any]:
        totals = _nutrition_totals(nutrition)
        servings = recipe.get("servings")
        allocation = allocate_meal_nutrition(totals, servings, allocations)
        row = {
            "id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": str(recipe.get("recipeTitle") or recipe.get("title") or "Cook4Me meal"),
            "groupingFunctionalId": recipe.get("groupingFunctionalId"),
            "variantFunctionalId": recipe.get("variantFunctionalId") or recipe.get("recipeFunctionalId"),
            "servings": _number(servings),
            "nutrition": deepcopy(nutrition),
            "allocations": allocation.get("allocations") or [],
            "assignedServings": allocation.get("assignedServings"),
            "unassignedServings": allocation.get("unassignedServings"),
        }
        self._data["meals"] = (self._data.get("meals", []) + [row])[-_MAX_MEALS:]
        await self._save()
        return deepcopy(row)

    def recent(self, limit: int = 30) -> list[dict[str, Any]]:
        return deepcopy(list(reversed(self._data.get("meals", [])[-max(1, min(int(limit), 200)):])) )

    def summary(self, *, now: datetime | None = None) -> dict[str, Any]:
        reference = now or datetime.now(timezone.utc)
        windows = {"today": timedelta(days=1), "week": timedelta(days=7), "month": timedelta(days=30)}
        result: dict[str, Any] = {}
        meals = self._data.get("meals", [])
        for name, delta in windows.items():
            cutoff = reference - delta
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
                _add(totals, _nutrition_totals(row.get("nutrition")))
                for allocation in row.get("allocations") or []:
                    if not isinstance(allocation, dict):
                        continue
                    person = str(allocation.get("name") or "").strip()
                    if not person:
                        continue
                    person_totals = people.setdefault(person, {})
                    _add(person_totals, _nutrition_totals(allocation.get("nutrition")))
            result[name] = {
                "mealCount": count,
                "totals": {key: round(value, 2) for key, value in totals.items()},
                "people": {
                    person: {key: round(value, 2) for key, value in values.items()}
                    for person, values in people.items()
                },
            }
        return result


async def meal_history_store_for_bridge(bridge: Any) -> Cook4MeMealHistoryStore:
    store = getattr(bridge, "_meal_history_store", None)
    if store is None:
        store = Cook4MeMealHistoryStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._meal_history_store = store
    return store
