from __future__ import annotations

from copy import deepcopy
from typing import Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_MAX_ITEMS = 16


def _text(value: Any) -> str:
    return str(value or "").strip()


def _compact_nutrition(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    result: dict[str, Any] = {}
    for key in ("totals", "perServing"):
        raw = value.get(key)
        if isinstance(raw, dict):
            result[key] = {
                str(name): number
                for name, number in raw.items()
                if isinstance(number, (int, float))
            }
    for key in ("servings", "coverage", "fullyCovered", "estimated"):
        if key in value:
            result[key] = deepcopy(value[key])
    source_kinds = value.get("sourceKinds")
    if isinstance(source_kinds, list):
        result["sourceKinds"] = [str(item) for item in source_kinds[:8] if str(item)]
    return result or None


def _compact_match(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    keys = (
        "score", "baseScore", "pantryCoverage", "quantityCoverage",
        "quantityConfidence", "fullyAvailableByQuantity", "expiryPriority",
        "expiryBonus", "nutritionGoal", "nutritionGoalBonus",
        "nutritionGoalCoverage", "calorieTarget", "caloriePerServing",
        "calorieDelta", "calorieTargetBonus", "todayBaseScore",
    )
    out = {key: deepcopy(value[key]) for key in keys if key in value}
    shortages = value.get("quantityShortages")
    if isinstance(shortages, list):
        out["quantityShortageCount"] = len(shortages)
    missing = value.get("missingIngredients")
    if isinstance(missing, list):
        out["missingIngredientCount"] = len(missing)
    return out or None


def compact_today_recipe(value: Any) -> dict[str, Any] | None:
    """Persist only data needed to paint a Today card without recipe detail."""
    if not isinstance(value, dict):
        return None
    out: dict[str, Any] = {}
    scalar_keys = (
        "groupingFunctionalId", "recipeFunctionalId", "variantFunctionalId",
        "searchVariantId", "displayVariantId", "sendVariantId",
        "sendGroupingFunctionalId", "sendRecipeFunctionalId", "title",
        "canonicalName", "cover", "language", "market", "groupSize",
        "todayCatalogLanguage", "source", "releaseCatalogVersion",
        "deviceCanAccept", "sendable",
    )
    for key in scalar_keys:
        if key in value and value[key] not in (None, ""):
            out[key] = deepcopy(value[key])
    if isinstance(value.get("yield"), dict):
        out["yield"] = {
            key: deepcopy(raw)
            for key, raw in value["yield"].items()
            if key in {"quantity", "quantityDisplay", "unit", "unitKey"}
            and raw not in (None, "")
        }
    nutrition = _compact_nutrition(value.get("nutrition"))
    if nutrition:
        out["nutrition"] = nutrition
    match = _compact_match(value.get("match"))
    if match:
        out["match"] = match
    return out if _text(out.get("title")) or _text(out.get("searchVariantId")) else None


def compact_today_result(result: Any) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    items = [
        compact
        for raw in (result.get("items") or [])[:_MAX_ITEMS]
        if (compact := compact_today_recipe(raw)) is not None
    ]
    if not items:
        return None
    out: dict[str, Any] = {"date": _text(result.get("date")), "items": items}
    for key in (
        "candidateCount", "rankedCount", "catalogCandidateCounts",
        "catalogRankedCounts", "catalogSelectedCounts", "catalogLanguagesUsed",
        "filters", "catalogMode", "catalogVersion",
    ):
        if key in result:
            out[key] = deepcopy(result[key])
    return out


class Cook4MeTodayPlanStore:
    """HA-side compact Today cache, independent from browser localStorage."""

    def __init__(self, bridge: Any) -> None:
        self._store: Store[dict[str, Any]] = Store(
            bridge.hass, _STORAGE_VERSION, f"{DOMAIN}.{bridge.entry.entry_id}.today_plan"
        )
        self._loaded = False
        self._data: dict[str, Any] | None = None

    async def async_load(self) -> None:
        if self._loaded:
            return
        raw = await self._store.async_load()
        self._data = compact_today_result(raw)
        self._loaded = True

    @property
    def snapshot(self) -> dict[str, Any] | None:
        return deepcopy(self._data)

    async def async_set(self, result: Any) -> dict[str, Any] | None:
        compact = compact_today_result(result)
        self._data = compact
        self._loaded = True
        if compact is None:
            await self._store.async_remove()
            return None
        await self._store.async_save(deepcopy(compact))
        return deepcopy(compact)

    async def async_clear(self) -> None:
        self._data = None
        self._loaded = True
        await self._store.async_remove()


async def today_plan_store_for_bridge(bridge: Any) -> Cook4MeTodayPlanStore:
    store = getattr(bridge, "_today_plan_store", None)
    if not isinstance(store, Cook4MeTodayPlanStore):
        store = Cook4MeTodayPlanStore(bridge)
        await store.async_load()
        bridge._today_plan_store = store
    return store
