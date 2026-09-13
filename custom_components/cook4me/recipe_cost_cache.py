from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .costing import calculate_recipe_cost
from .inventory import inventory_identity, normalize_inventory

_STORAGE_VERSION = 1
_MAX_ENTRIES = 500


def _text(value: Any) -> str:
    return str(value or "").strip()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _recipe_price_shape(recipe: Any) -> dict[str, Any]:
    if not isinstance(recipe, dict):
        return {}
    ingredients = []
    for raw in recipe.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        ingredients.append({
            "identity": inventory_identity(raw),
            "key": _text(raw.get("key") or raw.get("foodKey")),
            "quantity": raw.get("quantity"),
            "unit": _text(raw.get("unit")),
            "weight": deepcopy(raw.get("weight")) if isinstance(raw.get("weight"), dict) else None,
        })
    return {
        "groupingFunctionalId": _text(recipe.get("groupingFunctionalId")),
        "recipeFunctionalId": _text(recipe.get("recipeFunctionalId")),
        "variantFunctionalId": _text(recipe.get("variantFunctionalId") or recipe.get("searchVariantId")),
        "servings": recipe.get("servings") or recipe.get("groupSize"),
        "yield": deepcopy(recipe.get("yield")) if isinstance(recipe.get("yield"), dict) else None,
        "ingredients": ingredients,
    }


def _relevant_inventory(recipe: dict[str, Any], inventory: Any) -> tuple[list[dict[str, Any]], set[str]]:
    wanted = {
        inventory_identity(raw)
        for raw in recipe.get("ingredients") or []
        if isinstance(raw, dict) and inventory_identity(raw)
    }
    rows: list[dict[str, Any]] = []
    reference_identities = set(wanted)
    for row in normalize_inventory(inventory):
        ident = inventory_identity(row)
        if not ident or ident not in wanted:
            continue
        lots = []
        for raw in row.get("lots") or []:
            if not isinstance(raw, dict):
                continue
            lot_id = _text(raw.get("id") or raw.get("lotId"))
            barcode = _text(raw.get("barcode"))
            if lot_id:
                reference_identities.add(f"lot:{lot_id}")
            if barcode:
                reference_identities.add(f"barcode:{barcode}")
            lots.append({
                "id": lot_id,
                "barcode": barcode,
                "quantity": raw.get("quantity"),
                "price": raw.get("price"),
                "currency": _text(raw.get("currency")),
                "purchaseQuantity": raw.get("purchaseQuantity"),
                "purchaseUnit": _text(raw.get("purchaseUnit")),
            })
        rows.append({
            "identity": ident,
            "unit": _text(row.get("unit")),
            "unlimited": bool(row.get("unlimited")),
            "quantity": row.get("quantity"),
            "lots": lots,
        })
    rows.sort(key=lambda row: row["identity"])
    return rows, reference_identities


def _reference_shape(store: Any, identities: set[str]) -> list[dict[str, Any]]:
    data = getattr(store, "_data", {})
    raw_refs = data.get("references") if isinstance(data, dict) else {}
    rows: list[dict[str, Any]] = []
    for ident in sorted(identities):
        for raw in (raw_refs.get(ident) if isinstance(raw_refs, dict) else []) or []:
            if not isinstance(raw, dict):
                continue
            rows.append({
                "identity": ident,
                "amount": raw.get("amount"),
                "currency": _text(raw.get("currency")),
                "basisQuantity": raw.get("basisQuantity"),
                "basisUnit": _text(raw.get("basisUnit")),
                "source": _text(raw.get("source")),
                "confidence": _text(raw.get("confidence")),
                "country": _text(raw.get("country")),
                "barcode": _text(raw.get("barcode")),
                "observationId": _text(raw.get("observationId")),
                "date": _text(raw.get("date")),
            })
    rows.sort(key=lambda row: json.dumps(row, sort_keys=True, default=str))
    return rows


def pricing_fingerprint(recipe: dict[str, Any], inventory: Any, store: Any) -> str:
    stock, identities = _relevant_inventory(recipe, inventory)
    return _canonical_hash({
        "settings": {
            "currency": _text(getattr(store, "settings", {}).get("currency")),
            "country": _text(getattr(store, "settings", {}).get("country")),
        },
        "stock": stock,
        "references": _reference_shape(store, identities),
    })


class Cook4MeRecipeCostCache:
    """Persistent derived recipe prices keyed by price-relevant evidence."""

    def __init__(self, bridge: Any) -> None:
        self._store: Store[dict[str, Any]] = Store(
            bridge.hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{bridge.entry.entry_id}.recipe_cost_cache",
        )
        self._loaded = False
        self._data: dict[str, Any] = {"entries": {}}

    async def async_load(self) -> None:
        if self._loaded:
            return
        raw = await self._store.async_load()
        entries = raw.get("entries") if isinstance(raw, dict) else {}
        self._data = {"entries": dict(entries) if isinstance(entries, dict) else {}}
        self._loaded = True

    async def async_cost(
        self,
        recipe: dict[str, Any],
        inventory: Any,
        cost_store: Any,
        *,
        currency: str = "",
        country: str = "",
        force: bool = False,
    ) -> dict[str, Any]:
        await self.async_load()
        recipe_hash = _canonical_hash(_recipe_price_shape(recipe))
        price_hash = pricing_fingerprint(recipe, inventory, cost_store)
        key = _canonical_hash({
            "recipe": recipe_hash,
            "pricing": price_hash,
            "currency": _text(currency).upper(),
            "country": _text(country).upper(),
        })
        entries = self._data["entries"]
        cached = entries.get(key)
        if not force and isinstance(cached, dict) and isinstance(cached.get("cost"), dict):
            result = deepcopy(cached["cost"])
            result.update({
                "costCacheHit": True,
                "pricingFingerprint": price_hash,
                "recipePriceFingerprint": recipe_hash,
                "costCacheContract": "price-evidence-fingerprint-v1",
            })
            return result

        cost = calculate_recipe_cost(
            recipe, inventory, cost_store, currency=currency, country=country
        )
        entries[key] = {
            "cost": deepcopy(cost),
            "pricingFingerprint": price_hash,
            "recipePriceFingerprint": recipe_hash,
        }
        while len(entries) > _MAX_ENTRIES:
            entries.pop(next(iter(entries)))
        await self._store.async_save(deepcopy(self._data))
        result = deepcopy(cost)
        result.update({
            "costCacheHit": False,
            "pricingFingerprint": price_hash,
            "recipePriceFingerprint": recipe_hash,
            "costCacheContract": "price-evidence-fingerprint-v1",
        })
        return result


async def recipe_cost_cache_for_bridge(bridge: Any) -> Cook4MeRecipeCostCache:
    cache = getattr(bridge, "_recipe_cost_cache_v1", None)
    if not isinstance(cache, Cook4MeRecipeCostCache):
        cache = Cook4MeRecipeCostCache(bridge)
        await cache.async_load()
        bridge._recipe_cost_cache_v1 = cache
    return cache
