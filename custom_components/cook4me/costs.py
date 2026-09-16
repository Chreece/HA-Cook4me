from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import asyncio
import json
import math
from typing import Any
import urllib.error
import urllib.parse
import urllib.request
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .price_quantities import explicit_product_basis
from .price_food_forms import compatible_food_form, category_unit_basis, compatible_category_basis, consistent_package_basis
from .price_snapshot import country_locations, snapshot_observations
from .const import DOMAIN
from .inventory import convert_amount, inventory_identity, normalize_inventory

_STORAGE_VERSION = 1
_MAX_REFERENCES = 5000
_OPEN_PRICES_URL = "https://prices.openfoodfacts.org/api/v1/prices"
_OPEN_PRICES_USER_AGENT = "HA-Cook4me/2026.9.8 (+https://github.com/Chreece/HA-Cook4me)"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value.replace(",", ".") if isinstance(value, str) else value)
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
        self._lock = asyncio.Lock()
        self._data: dict[str, Any] = {
            "settings": {"currency": "", "country": "", "autoGlobalPrices": True},
            "references": {},
            "priceEvidenceRevision": 90,
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
        # Rebuild external estimates under the stricter food/package rules.
        # User-entered prices and exact purchase history remain untouched.
        if isinstance(saved, dict) and saved.get("priceEvidenceRevision") != 90:
            self._data["references"] = {key: ref for key, ref in self._data["references"].items()
                if not str(ref.get("source", "")).startswith("open_prices") and ref.get("source") not in {"retail_snapshot", "utility_snapshot"}}
            await self._save()
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
        async with self._lock:
            data = deepcopy(self._data)
            settings = data["settings"]
            if currency is not None:
                settings["currency"] = _currency(currency)
            if country is not None:
                settings["country"] = _country(country)
            if auto_global_prices is not None:
                settings["autoGlobalPrices"] = bool(auto_global_prices)
            await self._store.async_save(data)
            self._data = data
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
        source_url: str = "",
        product_name: str = "",
        note: str = "",
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
            "sourceUrl": _text(source_url)[:500],
            "productName": _text(product_name)[:300],
            "note": _text(note)[:600],
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        key = _reference_key(identity, curr, row["country"], row["source"]) + "|" + unit.casefold()
        async with self._lock:
            data = deepcopy(self._data)
            refs = data.setdefault("references", {})
            refs[key] = row
            while len(refs) > _MAX_REFERENCES:
                refs.pop(next(iter(refs)), None)
            await self._store.async_save(data)
            self._data = data
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
        unit: str = "",
    ) -> dict[str, Any] | None:
        rows = self._references_for(identity, currency=currency)
        if unit:
            rows = [row for row in rows if convert_amount(1, unit, row.get("basisUnit")) is not None]
        if not rows:
            return None
        wanted_country = _country(country)
        # Country is a boundary, never a preference that falls back abroad.
        if wanted_country:
            rows = [row for row in rows if _country(row.get("country")) == wanted_country]
        cutoff = (datetime.now(timezone.utc).date() - timedelta(days=180)).isoformat()
        today = datetime.now(timezone.utc).date().isoformat()
        rows = [row for row in rows if (not str(row.get("source", "")).startswith("open_prices") and row.get("source") not in {"retail_snapshot", "utility_snapshot"})
                or cutoff <= _text(row.get("date")) <= today]
        if not rows:
            return None

        def rank(row: dict[str, Any]) -> tuple[int, int, str, str]:
            source = _text(row.get("source"))
            confidence = _text(row.get("confidence"))
            local = bool(wanted_country and _country(row.get("country")) == wanted_country)
            exact = confidence in {"exact_purchase", "user_entered"} or source == "manual"
            return (2 if exact else 1, 1 if local else 0,
                    _text(row.get("date") or row.get("updatedAt")), _text(row.get("updatedAt")))

        return deepcopy(max(rows, key=rank))

    def barcode_reference(
        self, barcode: str, *, currency: str = "", country: str = "", unit: str = ""
    ) -> dict[str, Any] | None:
        code = _text(barcode)
        if not code:
            return None
        return self.best_reference(
            f"barcode:{code}", currency=currency, country=country, unit=unit
        )


async def cost_store_for_bridge(bridge: Any) -> Cook4MeCostStore:
    from .store_helpers import store_load_lock
    async with store_load_lock(bridge, 'costs'):
        store = getattr(bridge, "_cost_store", None)
        if store is None:
            store = Cook4MeCostStore(bridge.hass, bridge.entry.entry_id)
            await store.async_load()
            bridge._cost_store = store
        return store


def lookup_open_prices(
    barcode: str = "", *, currency: str = "", country: str = "", timeout: int = 15,
    category: str = "", category_type: str = "CATEGORY", unit: str = "",
    prefer_snapshot: bool = False,
) -> dict[str, Any]:
    """Bounded, read-only observations, strictly checked against the requested market.

    Use observed offline evidence on first lookup, then country location IDs before
    worldwide pagination. All searches share five requests and one timeout budget.
    An empty result means no usable observation in this sample, not free food.
    PRODUCT rows use the documented package price (price_per may be null).
    CATEGORY rows explicitly use UNIT or KILOGRAM. Never infer a package weight.
    """
    code, curr, market = _text(barcode), _currency(currency), _country(country)
    if not code and not category:
        return {"ok": False, "reason": "empty_barcode", "items": []}
    if prefer_snapshot:
        items = snapshot_observations(barcode=code, category=category, country=market,
                                      currency=curr, unit=unit)
        if items:
            return {"ok": True, "reason": "", "barcode": code, "items": items,
                    "count": len(items), "usableCount": len(items), "pagesChecked": 0,
                    "searchLimited": False, "offlineSnapshot": True}
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=180)
    params = {"type": "PRODUCT" if code else category_type, "duplicate_of__isnull": "true",
              "size": 100, "order_by": "-date", "date__gte": cutoff.isoformat(),
              "date__lte": today.isoformat(), "price_is_discounted": "false"}
    if code:
        params["product_code"] = code
    elif category_type == "PRODUCT":
        params["product__categories_tags__contains"] = category
    else:
        params["category_tag"] = category
    if curr:
        params["currency"] = curr
    normalized, pages_checked, search_limited, error = [], 0, False, ""
    deadline = time.monotonic() + timeout
    # /prices has location_id__in, but no country filter. The bundled index is
    # only a hint: include a worldwide scope for new/missing locations. Rotate
    # scopes before deeper pages so one busy group cannot starve other stores.
    locations = country_locations(market) if market else []
    scopes = [','.join(map(str, locations[i:i + 300])) for i in range(0, len(locations), 300)]
    pending = [(scope, 1) for scope in scopes] + [('', 1)]
    for _ in range(5):
        if not pending:
            break
        scope, page = pending.pop(0)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            search_limited = True
            break
        params["page"] = page
        params.pop("location_id__in", None)
        if scope:
            params["location_id__in"] = scope
        request = urllib.request.Request(f"{_OPEN_PRICES_URL}?{urllib.parse.urlencode(params)}",
            headers={"Accept": "application/json", "User-Agent": _OPEN_PRICES_USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=remaining) as response:
                data = response.read(2_000_001)
            if len(data) > 2_000_000:
                error = "response_too_large"
                break
            payload = json.loads(data.decode("utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
                error = "invalid_response"
                break
        except (OSError, ValueError) as exc:
            error = type(exc).__name__
            break
        pages_checked += 1
        normalized.extend(_normalize_open_prices(payload["items"], code=code, curr=curr,
            market=market, category=category, category_type=category_type, cutoff=cutoff, today=today))
        if any(row["usable"] and (not unit or convert_amount(1, unit, row["basisUnit"]) is not None)
               for row in normalized):
            search_limited = False
            break
        try:
            has_more = page < int(payload.get("pages") or 1)
        except (TypeError, ValueError):
            has_more = False
        if has_more and payload["items"]:
            pending.append((scope, page + 1))
        search_limited = bool(pending)
    return {"ok": not bool(error), "reason": error, "barcode": code, "items": normalized,
            "count": len(normalized), "usableCount": sum(bool(row["usable"]) for row in normalized),
            "pagesChecked": pages_checked, "searchLimited": search_limited or bool(error)}


def _normalize_open_prices(items, *, code, curr, market, category, category_type, cutoff, today):
    normalized = []
    for row in items:
        if not isinstance(row, dict) or row.get("duplicate_of") or row.get("price_is_discounted"):
            continue
        if code and _text(row.get("product_code")) != code:
            continue
        location = row.get("location") if isinstance(row.get("location"), dict) else {}
        product = row.get("product") if isinstance(row.get("product"), dict) else {}
        row_country = _country(location.get("osm_address_country_code"))
        row_currency, amount = _currency(row.get("currency")), _number(row.get("price"))
        if amount is None or not row_currency or (curr and row_currency != curr):
            continue
        if market and row_country != market:
            continue
        try:
            observed = date.fromisoformat(_text(row.get("date")))
        except ValueError:
            continue
        if not cutoff <= observed <= today:
            continue
        if category and not code:
            if category_type == "CATEGORY" and row.get("category_tag") != category:
                continue
            if category_type == "PRODUCT" and category not in (product.get("categories_tags") or []):
                continue
        if category and not code and not compatible_food_form(row, category):
            continue
        price_per = _text(row.get("price_per")).upper()
        basis, unit = None, ""
        if row.get("type") == "PRODUCT" and price_per in {"", "UNIT"}:
            basis, unit = explicit_product_basis(product)
        elif price_per == "KILOGRAM":
            basis, unit = 1.0, "kg"
        elif row.get("type") == "CATEGORY" and price_per == "UNIT":
            basis, unit = category_unit_basis(row)
        if not consistent_package_basis(row, basis, unit):
            basis, unit = None, ""
        if category and not code and not compatible_category_basis(row, category, unit):
            basis, unit = None, ""
        normalized.append({"id": row.get("id"), "barcode": _text(row.get("product_code")),
            "amount": amount, "currency": row_currency, "basisQuantity": basis, "basisUnit": unit,
            "pricePer": price_per, "usable": bool(basis and unit), "date": observed.isoformat(),
            "country": row_country, "location": _text(location.get("osm_name") or location.get("osm_display_name")),
            "productName": _text(row.get("product_name") or product.get("product_name")),
            "source": "open_prices", "confidence": "external_observation", "category": category})
    return normalized


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
        filtered = [row for row in filtered if row.get("country") == country]
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
