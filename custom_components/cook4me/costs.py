from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import statistics
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .inventory import convert_amount, inventory_identity, normalize_inventory

_STORAGE_VERSION = 1
_MAX_REFERENCES = 5000
_OPEN_PRICES_URL = "https://prices.openfoodfacts.org/api/v1/prices"
_OPEN_PRICES_USER_AGENT = "HA-Cook4me/2026.9.8 (+https://github.com/Chreece/HA-Cook4me)"


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


def _currency(value: Any) -> str:
    token = _text(value).upper()
    return token if len(token) == 3 and token.isalpha() else ""


def _country(value: Any) -> str:
    token = _text(value).upper()
    return token if len(token) == 2 and token.isalpha() else ""


def _recipe_ingredient(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    name = _text(item.get("name") or item.get("foodName"))
    key = _text(item.get("key") or item.get("foodKey"))
    quantity = _number(item.get("quantity"))
    unit = _text(item.get("unit"))
    if quantity is None:
        weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
        quantity = _number(weight.get("quantity"))
        unit = unit or _text(weight.get("unit"))
    if not name and not key:
        return None
    row: dict[str, Any] = {"name": name or key, "quantity": quantity, "unit": unit}
    if key:
        row["key"] = key
    return row


def _price_basis(raw: Any, *, default_unit: str = "") -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    amount = _number(raw.get("purchasePrice") if "purchasePrice" in raw else raw.get("price"))
    currency = _currency(raw.get("currency") or raw.get("purchaseCurrency"))
    basis_quantity = _number(
        raw.get("purchaseQuantity")
        if "purchaseQuantity" in raw
        else raw.get("basisQuantity")
    )
    basis_unit = _text(
        raw.get("purchaseUnit")
        if "purchaseUnit" in raw
        else raw.get("basisUnit") or default_unit
    )
    if amount is None or not currency or basis_quantity is None or basis_quantity <= 0 or not basis_unit:
        return None
    return {
        "amount": amount,
        "currency": currency,
        "basisQuantity": basis_quantity,
        "basisUnit": basis_unit,
        "source": _text(raw.get("priceSource") or raw.get("source") or "purchase") or "purchase",
        "confidence": _text(raw.get("priceConfidence") or raw.get("confidence") or "exact_purchase") or "exact_purchase",
        "date": _text(raw.get("priceDate") or raw.get("purchaseDate") or raw.get("date")),
        "country": _country(raw.get("priceCountry") or raw.get("country")),
        "location": _text(raw.get("priceLocation") or raw.get("merchant") or raw.get("location")),
    }


def _cost_for_amount(reference: dict[str, Any], quantity: Any, unit: Any) -> float | None:
    wanted = _number(quantity)
    basis = _number(reference.get("basisQuantity"))
    if wanted is None or basis is None or basis <= 0:
        return None
    converted = convert_amount(wanted, unit, reference.get("basisUnit"))
    if converted is None:
        return None
    amount = _number(reference.get("amount"))
    if amount is None:
        return None
    return amount * converted / basis


def _add_currency(target: dict[str, float], currency: str, value: float | None) -> None:
    if not currency or value is None or not math.isfinite(float(value)):
        return
    target[currency] = target.get(currency, 0.0) + float(value)


def _rounded_currency(values: dict[str, float]) -> dict[str, float]:
    return {currency: round(value, 2) for currency, value in values.items() if value >= 0}


def _reference_key(identity: str, currency: str, country: str, source: str) -> str:
    return "|".join((identity, _currency(currency), _country(country), _text(source)))


class Cook4MeCostStore:
    """Persistent exact/manual/global price references without implicit FX conversion."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.costs"
        )
        self._loaded = False
        self._data: dict[str, Any] = {
            "settings": {"currency": "", "country": "", "autoGlobalPrices": True},
            "references": {},
        }

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            settings = saved.get("settings") if isinstance(saved.get("settings"), dict) else {}
            self._data["settings"] = {
                "currency": _currency(settings.get("currency")),
                "country": _country(settings.get("country")),
                "autoGlobalPrices": bool(settings.get("autoGlobalPrices", True)),
            }
            refs = saved.get("references") if isinstance(saved.get("references"), dict) else {}
            self._data["references"] = {
                str(key): deepcopy(value)
                for key, value in list(refs.items())[-_MAX_REFERENCES:]
                if isinstance(value, dict)
            }
        self._loaded = True

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    @property
    def settings(self) -> dict[str, Any]:
        return deepcopy(self._data["settings"])

    def snapshot(self) -> dict[str, Any]:
        return {
            "settings": self.settings,
            "referenceCount": len(self._data.get("references") or {}),
            "references": list(deepcopy(self._data.get("references") or {}).values())[-200:],
        }

    async def async_set_settings(
        self, *, currency: Any = None, country: Any = None, auto_global_prices: Any = None
    ) -> dict[str, Any]:
        settings = dict(self._data["settings"])
        if currency is not None:
            settings["currency"] = _currency(currency)
        if country is not None:
            settings["country"] = _country(country)
        if auto_global_prices is not None:
            settings["autoGlobalPrices"] = bool(auto_global_prices)
        self._data["settings"] = settings
        await self._save()
        return self.settings

    async def async_set_reference(
        self,
        identity: str,
        *,
        amount: Any,
        currency: Any,
        basis_quantity: Any,
        basis_unit: Any,
        source: str = "manual",
        confidence: str = "user_entered",
        country: str = "",
        location: str = "",
        date: str = "",
        barcode: str = "",
        observation_id: Any = None,
    ) -> dict[str, Any]:
        identity = _text(identity)
        amount_value = _number(amount)
        basis_value = _number(basis_quantity)
        unit = _text(basis_unit)
        curr = _currency(currency)
        if not identity or amount_value is None or basis_value is None or basis_value <= 0 or not unit or not curr:
            raise ValueError("Price reference requires identity, price, currency, basis quantity and unit")
        row: dict[str, Any] = {
            "identity": identity,
            "amount": amount_value,
            "currency": curr,
            "basisQuantity": basis_value,
            "basisUnit": unit,
            "source": _text(source) or "manual",
            "confidence": _text(confidence) or "user_entered",
            "country": _country(country),
            "location": _text(location)[:300],
            "date": _text(date)[:40],
            "barcode": _text(barcode)[:80],
            "observationId": observation_id,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        key = _reference_key(identity, curr, row["country"], row["source"])
        refs = self._data.setdefault("references", {})
        refs[key] = row
        while len(refs) > _MAX_REFERENCES:
            refs.pop(next(iter(refs)), None)
        await self._save()
        return deepcopy(row)

    def _references_for(self, identity: str, *, currency: str = "") -> list[dict[str, Any]]:
        wanted_currency = _currency(currency)
        out = []
        for row in (self._data.get("references") or {}).values():
            if not isinstance(row, dict) or _text(row.get("identity")) != identity:
                continue
            if wanted_currency and _currency(row.get("currency")) != wanted_currency:
                continue
            out.append(row)
        return out

    def best_reference(
        self,
        identity: str,
        *,
        currency: str = "",
        country: str = "",
    ) -> dict[str, Any] | None:
        rows = self._references_for(identity, currency=currency)
        if not rows:
            return None
        wanted_country = _country(country)

        def rank(row: dict[str, Any]) -> tuple[int, int, str]:
            source = _text(row.get("source"))
            confidence = _text(row.get("confidence"))
            local = bool(wanted_country and _country(row.get("country")) == wanted_country)
            exact = confidence in {"exact_purchase", "user_entered"} or source == "manual"
            return (2 if exact else 1, 1 if local else 0, _text(row.get("date") or row.get("updatedAt")))

        return deepcopy(max(rows, key=rank))

    def barcode_reference(
        self, barcode: str, *, currency: str = "", country: str = ""
    ) -> dict[str, Any] | None:
        code = _text(barcode)
        if not code:
            return None
        return self.best_reference(
            f"barcode:{code}", currency=currency, country=country
        )


async def cost_store_for_bridge(bridge: Any) -> Cook4MeCostStore:
    store = getattr(bridge, "_cost_store", None)
    if store is None:
        store = Cook4MeCostStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._cost_store = store
    return store


def lookup_open_prices(
    barcode: str,
    *,
    currency: str = "",
    country: str = "",
    timeout: int = 15,
) -> dict[str, Any]:
    code = _text(barcode)
    if not code:
        return {"ok": False, "reason": "empty_barcode", "items": []}
    params: dict[str, Any] = {
        "product_code": code,
        "type": "PRODUCT",
        "duplicate_of__isnull": "true",
        "size": 100,
        "order_by": "-date",
    }
    curr = _currency(currency)
    if curr:
        params["currency"] = curr
    url = f"{_OPEN_PRICES_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": _OPEN_PRICES_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "reason": f"http_{exc.code}", "items": []}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "reason": type(exc).__name__, "items": []}

    wanted_country = _country(country)
    normalized: list[dict[str, Any]] = []
    for row in payload.get("items") if isinstance(payload, dict) else []:
        if not isinstance(row, dict) or _text(row.get("product_code")) != code:
            continue
        price = _number(row.get("price"))
        row_currency = _currency(row.get("currency"))
        if price is None or not row_currency:
            continue
        location = row.get("location") if isinstance(row.get("location"), dict) else {}
        row_country = _country(location.get("osm_address_country_code"))
        if wanted_country and row_country and row_country != wanted_country:
            continue
        product = row.get("product") if isinstance(row.get("product"), dict) else {}
        basis_quantity = None
        basis_unit = ""
        price_per = _text(row.get("price_per")).upper()
        if price_per == "UNIT":
            basis_quantity = _number(product.get("product_quantity"))
            basis_unit = _text(product.get("product_quantity_unit"))
        elif price_per == "KG":
            basis_quantity, basis_unit = 1.0, "kg"
        elif price_per in {"L", "LITER", "LITRE"}:
            basis_quantity, basis_unit = 1.0, "l"
        usable = bool(basis_quantity is not None and basis_quantity > 0 and basis_unit)
        normalized.append(
            {
                "id": row.get("id"),
                "barcode": code,
                "amount": price,
                "currency": row_currency,
                "basisQuantity": basis_quantity,
                "basisUnit": basis_unit,
                "pricePer": price_per,
                "usable": usable,
                "date": _text(row.get("date")),
                "country": row_country,
                "location": _text(location.get("osm_name") or location.get("osm_display_name")),
                "productName": _text(row.get("product_name") or product.get("product_name")),
                "source": "open_prices",
                "confidence": "external_observation",
            }
        )

    groups: dict[str, list[float]] = {}
    for row in normalized:
        if row["usable"]:
            groups.setdefault(row["currency"], []).append(float(row["amount"]))
    medians = {key: round(statistics.median(values), 2) for key, values in groups.items() if values}
    return {
        "ok": True,
        "barcode": code,
        "items": normalized,
        "count": len(normalized),
        "usableCount": sum(bool(row["usable"]) for row in normalized),
        "medianObservedPriceByCurrency": medians,
    }


async def async_store_open_price_result(
    store: Cook4MeCostStore,
    result: dict[str, Any],
    *,
    preferred_currency: str = "",
    preferred_country: str = "",
) -> dict[str, Any] | None:
    items = [row for row in result.get("items") or [] if isinstance(row, dict) and row.get("usable")]
    if not items:
        return None
    curr = _currency(preferred_currency)
    country = _country(preferred_country)
    filtered = [row for row in items if not curr or row.get("currency") == curr]
    if country:
        local = [row for row in filtered if row.get("country") == country]
        if local:
            filtered = local
    if not filtered:
        return None
    filtered.sort(key=lambda row: _text(row.get("date")), reverse=True)
    chosen = filtered[0]
    return await store.async_set_reference(
        f"barcode:{chosen['barcode']}",
        amount=chosen["amount"],
        currency=chosen["currency"],
        basis_quantity=chosen["basisQuantity"],
        basis_unit=chosen["basisUnit"],
        source="open_prices",
        confidence="external_observation",
        country=chosen.get("country") or "",
        location=chosen.get("location") or "",
        date=chosen.get("date") or "",
        barcode=chosen["barcode"],
        observation_id=chosen.get("id"),
    )


def _inventory_row(inventory: list[dict[str, Any]], ingredient: dict[str, Any]) -> dict[str, Any] | None:
    ident = inventory_identity(ingredient)
    for row in inventory:
        if inventory_identity(row) == ident:
            return row
    return None


def _reference_for_lot(
    lot: dict[str, Any],
    *,
    row_unit: str,
    store: Cook4MeCostStore,
    currency: str,
    country: str,
) -> tuple[dict[str, Any] | None, str]:
    direct = _price_basis(lot, default_unit=row_unit)
    if direct is not None:
        return direct, "exact_purchase"
    barcode = _text(lot.get("barcode"))
    if barcode:
        external = store.barcode_reference(barcode, currency=currency, country=country)
        if external is not None:
            return external, "global_barcode_estimate"
    return None, ""


def calculate_recipe_cost(
    recipe: dict[str, Any],
    inventory: Any,
    store: Cook4MeCostStore,
    *,
    currency: str = "",
    country: str = "",
) -> dict[str, Any]:
    stock = normalize_inventory(inventory)
    target_currency = _currency(currency) or _currency(store.settings.get("currency"))
    target_country = _country(country) or _country(store.settings.get("country"))
    ingredient_costs: list[dict[str, Any]] = []
    totals: dict[str, float] = {}
    exact_amount = 0.0
    priced_amount = 0.0
    required_amount = 0.0

    for raw in recipe.get("ingredients") or []:
        ingredient = _recipe_ingredient(raw)
        if ingredient is None:
            continue
        quantity = ingredient.get("quantity")
        unit = ingredient.get("unit") or ""
        ident = inventory_identity(ingredient)
        if quantity is None or not unit:
            ingredient_costs.append(
                {
                    "identity": ident,
                    "name": ingredient["name"],
                    "quantity": quantity,
                    "unit": unit,
                    "priced": False,
                    "reason": "recipe_amount_unknown",
                    "costsByCurrency": {},
                }
            )
            continue

        required_amount += float(quantity)
        remaining = float(quantity)
        row = _inventory_row(stock, ingredient)
        row_unit = _text((row or {}).get("unit")) or unit
        costs: dict[str, float] = {}
        sources: list[str] = []
        exact_covered = 0.0
        covered = 0.0

        if row and row.get("unlimited"):
            pass
        elif row:
            for lot in row.get("lots") or []:
                if remaining <= 1e-9 or not isinstance(lot, dict):
                    break
                lot_quantity = _number(lot.get("quantity")) or 0.0
                available_in_recipe_unit = convert_amount(lot_quantity, row_unit, unit)
                if available_in_recipe_unit is None or available_in_recipe_unit <= 0:
                    continue
                take = min(remaining, available_in_recipe_unit)
                reference, source_kind = _reference_for_lot(
                    lot,
                    row_unit=row_unit,
                    store=store,
                    currency=target_currency,
                    country=target_country,
                )
                if reference is not None:
                    value = _cost_for_amount(reference, take, unit)
                    ref_currency = _currency(reference.get("currency"))
                    _add_currency(costs, ref_currency, value)
                    _add_currency(totals, ref_currency, value)
                    if value is not None:
                        covered += take
                        if source_kind == "exact_purchase":
                            exact_covered += take
                        if source_kind and source_kind not in sources:
                            sources.append(source_kind)
                remaining -= take

        if remaining > 1e-9:
            reference = store.best_reference(
                ident, currency=target_currency, country=target_country
            )
            if reference is not None:
                value = _cost_for_amount(reference, remaining, unit)
                ref_currency = _currency(reference.get("currency"))
                _add_currency(costs, ref_currency, value)
                _add_currency(totals, ref_currency, value)
                if value is not None:
                    covered += remaining
                    source = _text(reference.get("source")) or "reference"
                    source_kind = "manual_reference" if source == "manual" else "global_reference"
                    if source_kind not in sources:
                        sources.append(source_kind)

        priced_amount += covered
        exact_amount += exact_covered
        ingredient_costs.append(
            {
                "identity": ident,
                "name": ingredient["name"],
                "quantity": quantity,
                "unit": unit,
                "priced": bool(costs),
                "coverage": round(min(1.0, covered / float(quantity)), 4) if quantity else 0.0,
                "exactCoverage": round(min(1.0, exact_covered / float(quantity)), 4) if quantity else 0.0,
                "costsByCurrency": _rounded_currency(costs),
                "sourceKinds": sources,
            }
        )

    servings = _number(recipe.get("servings") or recipe.get("groupSize"))
    if servings is None:
        yield_data = recipe.get("yield") if isinstance(recipe.get("yield"), dict) else {}
        servings = _number(yield_data.get("quantity") or yield_data.get("quantityDisplay"))
    per_serving = {
        curr: round(value / servings, 2)
        for curr, value in totals.items()
        if servings and servings > 0
    }
    return {
        "totalsByCurrency": _rounded_currency(totals),
        "perServingByCurrency": per_serving,
        "servings": servings,
        "ingredients": ingredient_costs,
        "coverage": round(priced_amount / required_amount, 4) if required_amount > 0 else 0.0,
        "exactPurchaseCoverage": round(exact_amount / required_amount, 4) if required_amount > 0 else 0.0,
        "estimated": any(
            any(kind not in {"exact_purchase"} for kind in row.get("sourceKinds") or [])
            for row in ingredient_costs
        ),
        "targetCurrency": target_currency,
        "targetCountry": target_country,
        "currencyConversionApplied": False,
    }


def calculate_consumption_cost(
    report: Any,
    store: Cook4MeCostStore,
    *,
    currency: str = "",
    country: str = "",
) -> dict[str, Any]:
    target_currency = _currency(currency) or _currency(store.settings.get("currency"))
    target_country = _country(country) or _country(store.settings.get("country"))
    totals: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    for lot in report.get("deductedLots") if isinstance(report, dict) else []:
        if not isinstance(lot, dict):
            continue
        quantity = _number(lot.get("quantity"))
        unit = _text(lot.get("unit"))
        reference = _price_basis(lot, default_unit=unit)
        source_kind = "exact_purchase" if reference else ""
        if reference is None and lot.get("barcode"):
            reference = store.barcode_reference(
                str(lot.get("barcode")), currency=target_currency, country=target_country
            )
            source_kind = "global_barcode_estimate" if reference else ""
        value = _cost_for_amount(reference, quantity, unit) if reference else None
        curr = _currency((reference or {}).get("currency"))
        _add_currency(totals, curr, value)
        rows.append(
            {
                "identity": _text(lot.get("identity")),
                "lotId": _text(lot.get("lotId") or lot.get("id")),
                "name": _text(lot.get("name") or lot.get("productName")),
                "quantity": quantity,
                "unit": unit,
                "barcode": _text(lot.get("barcode")),
                "cost": round(value, 2) if value is not None else None,
                "currency": curr,
                "sourceKind": source_kind,
            }
        )
    return {
        "totalsByCurrency": _rounded_currency(totals),
        "lots": rows,
        "estimated": any(row.get("sourceKind") == "global_barcode_estimate" for row in rows),
        "currencyConversionApplied": False,
    }
