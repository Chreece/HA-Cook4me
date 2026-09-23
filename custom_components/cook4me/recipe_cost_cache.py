from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
import json
from typing import Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .costing import calculate_recipe_cost
from .inventory import ingredient_identities, inventory_identity, normalize_inventory
from .price_identity import pricing_name
from .store_helpers import store_load_lock

_STORAGE_VERSION = 1
_MAX_ENTRIES = 500


def _text(value: Any) -> str:
    return str(value or "").strip()


def _canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(payload.encode("utf-8")).hexdigest()


def _pricing_identities(raw: Any) -> set[str]:
    """Mirror costing's accepted keys and allocation's explicit aliases."""
    if isinstance(raw, str):
        raw = {"name": raw}
    if not isinstance(raw, dict):
        return set()
    item = dict(raw)
    key = _text(raw.get("key") or raw.get("foodKey") or raw.get("ingredientId"))
    if key:
        item["key"] = key
    identities = ingredient_identities(item)
    if raw.get("identity"):
        identities.add(_text(raw["identity"]))
    return identities


def _recipe_price_shape(recipe: Any) -> dict[str, Any]:
    if not isinstance(recipe, dict):
        return {}
    ingredients = []
    for raw in recipe.get("ingredients") or []:
        if isinstance(raw, str):
            raw = {"name": raw}
        if not isinstance(raw, dict):
            continue
        ingredients.append({
            "identity": inventory_identity(raw),
            "key": _text(raw.get("key") or raw.get("foodKey") or raw.get("ingredientId")),
            "identities": sorted(_pricing_identities(raw)),
            "pricingName": pricing_name(raw),
            "priceQuantityEvidence": deepcopy(raw.get("priceQuantityEvidence")),
            "quantity": raw.get("quantity"),
            "unit": _text(raw.get("unit")),
            "canonicalName": _text(raw.get("canonicalName")),
            "priceCatalogMatched": bool(raw.get("priceCatalogMatched")),
            "priceCategory": _text(raw.get("priceCategory")),
            "unitKey": _text(raw.get("unitKey")),
            "weight": deepcopy(raw.get("weight")) if isinstance(raw.get("weight"), dict) else None,
        })
    return {
        "groupingFunctionalId": _text(recipe.get("groupingFunctionalId")),
        "recipeFunctionalId": _text(recipe.get("recipeFunctionalId")),
        "variantFunctionalId": _text(recipe.get("variantFunctionalId") or recipe.get("searchVariantId")),
        "servings": recipe.get("servings") or recipe.get("groupSize"),
        "yield": deepcopy(recipe.get("yield")) if isinstance(recipe.get("yield"), dict) else None,
        "ingredients": ingredients,
        "quantityEvidenceVersion": 189,
    }


def _relevant_inventory(recipe: dict[str, Any], inventory: Any) -> tuple[list[dict[str, Any]], set[str]]:
    wanted = {
        identity
        for raw in recipe.get("ingredients") or []
        for identity in _pricing_identities(raw)
    }
    rows: list[dict[str, Any]] = []
    reference_identities = set(wanted)
    for row in normalize_inventory(inventory):
        ident = inventory_identity(row)
        row_identities = _pricing_identities(row)
        linked = {
            identity
            for lot in row.get("lots") or [] if isinstance(lot, dict)
            for link in lot.get("ingredientLinks") or []
            for identity in _pricing_identities(link)
        }
        if not (row_identities | linked) & wanted:
            continue
        reference_identities.update(row_identities | linked)
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
                # FEFO sorts lots globally, not just inside their parent row.
                "bestBefore": _text(raw.get("bestBefore")),
                "openedAt": _text(raw.get("openedAt")),
                "useWithinDays": raw.get("useWithinDays"),
                "addedAt": _text(raw.get("addedAt")),
                "ingredientLinks": raw.get("ingredientLinks") or [],
                "barcode": barcode,
                "quantity": raw.get("quantity"),
                "price": raw.get("price"),
                "currency": _text(raw.get("currency")),
                "purchaseQuantity": raw.get("purchaseQuantity"),
                "purchaseUnit": _text(raw.get("purchaseUnit")),
            })
        rows.append({
            "identity": ident,
            "identities": sorted(row_identities),
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
    for raw in (raw_refs.values() if isinstance(raw_refs, dict) else []):
        # Current storage is composite-key -> row, not identity -> list.
        if not isinstance(raw, dict) or raw.get("identity") not in identities:
            continue
        rows.append(deepcopy(raw))
    rows.sort(key=lambda row: json.dumps(row, sort_keys=True, default=str))
    return rows


def pricing_fingerprint(recipe: dict[str, Any], inventory: Any, store: Any) -> str:
    stock, identities = _relevant_inventory(recipe, inventory)
    return _canonical_hash({
        "calculatorVersion": 190,
        "priceDate": datetime.now(timezone.utc).date().isoformat(),
        "settings": {
            "currency": _text(getattr(store, "settings", {}).get("currency")),
            "country": _text(getattr(store, "settings", {}).get("country")),
            "autoGlobalPrices": bool(getattr(store, "settings", {}).get("autoGlobalPrices", True)),
        },
        "stock": stock,
        "references": _reference_shape(store, identities),
    })


def _refresh_display_names(result: dict[str, Any], recipe: dict[str, Any]) -> None:
    """Rebind current labels without recalculating unchanged numeric evidence."""
    names = []
    for raw in recipe.get("ingredients") or []:
        if isinstance(raw, str):
            raw = {"name": raw}
        if not isinstance(raw, dict):
            continue
        name = _text(raw.get("name") or raw.get("foodName"))
        key = _text(raw.get("key") or raw.get("foodKey") or raw.get("ingredientId"))
        if name or key:
            names.append(name or key)
    rows = result.get("ingredients")
    # Only one-to-one calculator rows are rebound; do not guess at mismatches.
    if isinstance(rows, list) and len(rows) == len(names):
        for row, name in zip(rows, names):
            if isinstance(row, dict):
                row["name"] = name


class Cook4MeRecipeCostCache:
    """Persistent derived recipe prices keyed by price-relevant evidence."""

    def __init__(self, bridge: Any) -> None:
        self._hass = bridge.hass
        self._lock = asyncio.Lock()
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
        # The cache is shared per config entry. Serialize cache writes, but run
        # the CPU-heavy calculator in HA's executor so weekly refreshes cannot
        # monopolize the event loop or freeze unrelated browsing requests.
        async with self._lock:
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
                _refresh_display_names(result, recipe)
                result.update({
                    "costCacheHit": True,
                    "pricingFingerprint": price_hash,
                    "recipePriceFingerprint": recipe_hash,
                    "costCacheContract": "price-evidence-fingerprint-v1",
                })
                return result

            cost = await self._hass.async_add_executor_job(
                partial(
                    calculate_recipe_cost,
                    recipe,
                    inventory,
                    cost_store,
                    currency=currency,
                    country=country,
                )
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
    # First access can race across recipe cards, weekly requests and languages.
    # Use the same per-entry store initialization lock as the other stores.
    async with store_load_lock(bridge, "recipe_cost_cache"):
        cache = getattr(bridge, "_recipe_cost_cache_v1", None)
        if not isinstance(cache, Cook4MeRecipeCostCache):
            cache = Cook4MeRecipeCostCache(bridge)
            await cache.async_load()
            bridge._recipe_cost_cache_v1 = cache
        return cache


async def preview_cache_token(bridge: Any) -> str:
    """Validate browser previews without recalculating individual recipes."""
    from .costs import cost_store_for_bridge
    store = await cost_store_for_bridge(bridge)
    return _canonical_hash({
        "evidenceVersion": 190,
        "date": datetime.now(timezone.utc).date().isoformat(),
        "settings": store.settings,
        "inventory": bridge.recipe_hub.profile.get("houseIngredients") or [],
        "references": store._data.get("references", {}),
    })
