from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .costing import calculate_recipe_cost
from .costs import cost_store_for_bridge

_STORAGE_VERSION = 1
_MAX_RECIPES = 1000


def _text(value: Any) -> str:
    return str(value or "").strip()


def recipe_identity(recipe: Any) -> str:
    if not isinstance(recipe, dict):
        return ""
    for key in ("referenceRecipeId","groupingFunctionalId","groupingId","recipeFunctionalId","variantFunctionalId","searchVariantId","id"):
        value = _text(recipe.get(key))
        if value:
            return f"{key}:{value}"
    title = _text(recipe.get("title")).casefold()
    return f"title:{title}" if title else ""


def price_revision(cost_store) -> str:
    """Fingerprint every persisted price reference + cost settings.

    Exact/manual/global references remain local. Any price mutation changes this
    fingerprint, which invalidates derived recipe-cost cache rows without
    changing the immutable release catalog.
    """
    data = getattr(cost_store, "_data", {})
    settings = data.get("settings") if isinstance(data, dict) else {}
    references = data.get("references") if isinstance(data, dict) else {}
    payload = {
        "settings": settings if isinstance(settings, dict) else {},
        "references": references if isinstance(references, dict) else {},
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class Cook4MeDerivedRecipeStore:
    def __init__(self, hass, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.derived_recipes")
        self._loaded = False
        self._data: dict[str, Any] = {"costs": {}}

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict) and isinstance(saved.get("costs"), dict):
            self._data["costs"] = deepcopy(saved["costs"])
        self._loaded = True

    async def async_recipe_cost(self, bridge, recipe: dict[str, Any]) -> dict[str, Any]:
        identity = recipe_identity(recipe)
        cost_store = await cost_store_for_bridge(bridge)
        revision = price_revision(cost_store)
        cached = (self._data.get("costs") or {}).get(identity)
        if identity and isinstance(cached, dict) and cached.get("priceRevision") == revision and isinstance(cached.get("cost"), dict):
            result = deepcopy(cached["cost"])
            result["cacheHit"] = True
            result["priceRevision"] = revision
            return result

        result = calculate_recipe_cost(recipe, bridge.recipe_hub.profile.get("houseIngredients") or [], cost_store)
        result = deepcopy(result)
        result["cacheHit"] = False
        result["priceRevision"] = revision
        if identity:
            rows = self._data.setdefault("costs", {})
            rows[identity] = {"priceRevision": revision, "cost": deepcopy(result)}
            while len(rows) > _MAX_RECIPES:
                rows.pop(next(iter(rows)), None)
            await self._store.async_save(self._data)
        return result


async def derived_recipe_store_for_bridge(bridge) -> Cook4MeDerivedRecipeStore:
    store = getattr(bridge, "_derived_recipe_store", None)
    if not isinstance(store, Cook4MeDerivedRecipeStore):
        store = Cook4MeDerivedRecipeStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._derived_recipe_store = store
    return store
