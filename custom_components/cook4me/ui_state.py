from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_MAX_TODAY_ITEMS = 8


def _text(value: Any) -> str:
    return str(value or "").strip()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def compact_recipe_card(recipe: Any) -> dict[str, Any]:
    if not isinstance(recipe, dict):
        return {}
    match = recipe.get("match") if isinstance(recipe.get("match"), dict) else {}
    nutrition = recipe.get("nutrition") if isinstance(recipe.get("nutrition"), dict) else {}
    per_serving = nutrition.get("perServing") if isinstance(nutrition.get("perServing"), dict) else {}
    totals = nutrition.get("totals") if isinstance(nutrition.get("totals"), dict) else {}
    ingredients: list[dict[str, Any]] = []
    for raw in recipe.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        row: dict[str, Any] = {}
        for source, target in (("foodKey", "foodKey"),("key", "key"),("foodName", "foodName"),("name", "name"),("quantity", "quantity"),("unit", "unit")):
            if raw.get(source) not in (None, ""):
                row[target] = raw.get(source)
        if row:
            ingredients.append(row)
        if len(ingredients) >= 8:
            break

    out: dict[str, Any] = {}
    for key in ("id","groupingFunctionalId","recipeFunctionalId","variantFunctionalId","searchVariantId","sendVariantId","sendGroupingFunctionalId","sendRecipeFunctionalId","referenceRecipeId","title","cover","language","market","todayCatalogLanguage","officialCatalogLanguage","groupSize","yield","source","sendable","deviceCanAccept"):
        if recipe.get(key) not in (None, ""):
            out[key] = deepcopy(recipe.get(key))
    if ingredients:
        out["ingredients"] = ingredients

    compact_match: dict[str, Any] = {}
    for key in ("score","pantryCoverage","safe","dietary","missingIngredients","calorieTarget","caloriePerServing","calorieDelta","nutritionGoal","nutritionGoalCoverage"):
        if match.get(key) not in (None, ""):
            value = deepcopy(match.get(key))
            if key == "missingIngredients" and isinstance(value, list):
                value = value[:8]
            compact_match[key] = value
    if compact_match:
        out["match"] = compact_match

    if nutrition:
        out["nutrition"] = {
            "perServing": deepcopy(per_serving),
            "totals": deepcopy(totals),
            "servings": nutrition.get("servings"),
            "coverage": nutrition.get("coverage"),
            "fullyCovered": nutrition.get("fullyCovered"),
            "estimated": nutrition.get("estimated"),
            "sourceKinds": deepcopy(nutrition.get("sourceKinds") or []),
        }
    return out


class Cook4MeUiStateStore:
    """Small server-side UI state that is safe to hydrate on first paint."""

    def __init__(self, hass, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.ui_state")
        self._loaded = False
        self._data: dict[str, Any] = {"todayPlan": None}

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            plan = saved.get("todayPlan")
            self._data["todayPlan"] = deepcopy(plan) if isinstance(plan, dict) else None
        self._loaded = True

    @property
    def today_plan(self) -> dict[str, Any] | None:
        value = self._data.get("todayPlan")
        return deepcopy(value) if isinstance(value, dict) else None

    async def async_set_today_plan(self, *, date: str, items: list[dict[str, Any]], filters: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
        plan = {
            "date": _text(date),
            "savedAt": _utcnow(),
            "items": [compact_recipe_card(row) for row in items[:_MAX_TODAY_ITEMS] if isinstance(row, dict)],
            "filters": deepcopy(filters) if isinstance(filters, dict) else {},
            "meta": deepcopy(meta) if isinstance(meta, dict) else {},
            "compact": True,
        }
        self._data["todayPlan"] = plan
        await self._store.async_save(self._data)
        return deepcopy(plan)

    async def async_clear_today_plan(self) -> None:
        self._data["todayPlan"] = None
        await self._store.async_save(self._data)


async def ui_state_store_for_bridge(bridge) -> Cook4MeUiStateStore:
    store = getattr(bridge, "_ui_state_store", None)
    if not isinstance(store, Cook4MeUiStateStore):
        store = Cook4MeUiStateStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._ui_state_store = store
    return store
