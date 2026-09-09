from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .inventory import inventory_identity, normalize_inventory
from .recipe_cache import stable_cache_key
from .today_logic import recipe_identity

_STORAGE_VERSION = 1
_MAX_ROWS = 500
_DIRECT_PRICE_FIELDS = (
    "purchasePrice",
    "price",
    "currency",
    "purchaseCurrency",
    "purchaseQuantity",
    "basisQuantity",
    "purchaseUnit",
    "basisUnit",
    "priceSource",
    "source",
    "priceConfidence",
    "confidence",
    "priceDate",
    "purchaseDate",
    "date",
    "priceCountry",
    "country",
    "priceLocation",
    "merchant",
    "location",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _reference_view(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return {
        key: deepcopy(value.get(key))
        for key in (
            "identity",
            "amount",
            "currency",
            "basisQuantity",
            "basisUnit",
            "source",
            "confidence",
            "country",
            "date",
            "barcode",
            "observationId",
            "updatedAt",
        )
        if value.get(key) not in (None, "")
    }


def _direct_price_view(lot: dict[str, Any]) -> dict[str, Any]:
    return {
        key: deepcopy(lot.get(key))
        for key in _DIRECT_PRICE_FIELDS
        if key in lot and lot.get(key) not in (None, "")
    }


def _recipe_key(recipe: dict[str, Any]) -> str:
    identity = recipe_identity(recipe)
    if identity:
        return identity
    return stable_cache_key(
        "recipe-cost",
        recipe.get("title"),
        recipe.get("ingredients") or [],
        recipe.get("servings") or recipe.get("groupSize"),
    )


def pricing_fingerprint(recipe: dict[str, Any], inventory: Any, cost_store: Any) -> str:
    """Hash only cost evidence that can affect this recipe.

    Changing an unrelated ingredient price leaves the fingerprint stable. A
    matching ingredient, stock lot, exact lot reference, barcode reference,
    quantity or generic price change produces a new fingerprint and therefore
    invalidates only affected recipes.
    """
    settings = cost_store.settings
    currency = _text(settings.get("currency"))
    country = _text(settings.get("country"))
    stock = normalize_inventory(inventory)
    ingredients: list[dict[str, Any]] = []

    for raw in recipe.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        identity = inventory_identity(raw)
        if not identity:
            continue
        ingredient: dict[str, Any] = {
            "identity": identity,
            "quantity": raw.get("quantity"),
            "unit": raw.get("unit"),
            "reference": _reference_view(
                cost_store.best_reference(identity, currency=currency, country=country)
            ),
            "lots": [],
        }
        stock_row = next(
            (row for row in stock if isinstance(row, dict) and inventory_identity(row) == identity),
            None,
        )
        if stock_row is not None:
            ingredient["stockUnit"] = stock_row.get("unit")
            ingredient["unlimited"] = bool(stock_row.get("unlimited"))
            for lot in stock_row.get("lots") or []:
                if not isinstance(lot, dict):
                    continue
                lot_id = _text(lot.get("id") or lot.get("lotId"))
                barcode = _text(lot.get("barcode"))
                ingredient["lots"].append(
                    {
                        "id": lot_id,
                        "quantity": lot.get("quantity"),
                        "unit": stock_row.get("unit") or lot.get("unit"),
                        "barcode": barcode,
                        "directPrice": _direct_price_view(lot),
                        "lotReference": _reference_view(
                            cost_store.best_reference(f"lot:{lot_id}") if lot_id else None
                        ),
                        "barcodeReference": _reference_view(
                            cost_store.best_reference(
                                f"barcode:{barcode}",
                                currency=currency,
                                country=country,
                            ) if barcode else None
                        ),
                    }
                )
        ingredients.append(ingredient)

    payload = {
        "settings": {
            "currency": currency,
            "country": country,
            "autoGlobalPrices": bool(settings.get("autoGlobalPrices")),
        },
        "ingredients": ingredients,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class Cook4MeRecipeCostCache:
    def __init__(self, bridge: Any) -> None:
        self._store: Store[dict[str, Any]] = Store(
            bridge.hass,
            _STORAGE_VERSION,
            f"{DOMAIN}.{bridge.entry.entry_id}.recipe_cost_cache",
        )
        self._loaded = False
        self._rows: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        rows = saved.get("rows") if isinstance(saved, dict) and isinstance(saved.get("rows"), dict) else {}
        self._rows = {
            str(key): deepcopy(row)
            for key, row in rows.items()
            if isinstance(row, dict) and isinstance(row.get("value"), dict)
        }
        while len(self._rows) > _MAX_ROWS:
            self._rows.pop(next(iter(self._rows)), None)
        self._loaded = True

    def get(self, recipe: dict[str, Any], inventory: Any, cost_store: Any) -> dict[str, Any] | None:
        key = _recipe_key(recipe)
        row = self._rows.get(key)
        if not isinstance(row, dict):
            return None
        fingerprint = pricing_fingerprint(recipe, inventory, cost_store)
        if row.get("priceFingerprint") != fingerprint:
            return None
        result = deepcopy(row["value"])
        result["cacheHit"] = True
        result["priceFingerprint"] = fingerprint
        result["costCacheContract"] = "relevant-price-fingerprint-v1"
        return result

    async def async_set(
        self,
        recipe: dict[str, Any],
        inventory: Any,
        cost_store: Any,
        value: dict[str, Any],
    ) -> dict[str, Any]:
        key = _recipe_key(recipe)
        fingerprint = pricing_fingerprint(recipe, inventory, cost_store)
        result = deepcopy(value)
        result["cacheHit"] = False
        result["priceFingerprint"] = fingerprint
        result["costCacheContract"] = "relevant-price-fingerprint-v1"
        self._rows[key] = {
            "priceFingerprint": fingerprint,
            "value": deepcopy(result),
        }
        while len(self._rows) > _MAX_ROWS:
            self._rows.pop(next(iter(self._rows)), None)
        await self._store.async_save({"rows": deepcopy(self._rows)})
        return result


async def recipe_cost_cache_for_bridge(bridge: Any) -> Cook4MeRecipeCostCache:
    cache = getattr(bridge, "_cook4me_recipe_cost_cache", None)
    if not isinstance(cache, Cook4MeRecipeCostCache):
        cache = Cook4MeRecipeCostCache(bridge)
        await cache.async_load()
        bridge._cook4me_recipe_cost_cache = cache
    return cache
