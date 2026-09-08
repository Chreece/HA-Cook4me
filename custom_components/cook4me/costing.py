from __future__ import annotations

from typing import Any
import math

from .costs import (
    Cook4MeCostStore,
    _cost_for_amount,
    _currency,
    _country,
    _number,
    _rounded_currency,
    _text,
    lookup_open_prices,
)
from .inventory import convert_amount, inventory_identity, normalize_inventory


def _add(target: dict[str, float], currency: str, value: float | None) -> None:
    if currency and value is not None and math.isfinite(float(value)):
        target[currency] = target.get(currency, 0.0) + float(value)


def _recipe_amount(item: dict[str, Any]) -> tuple[float | None, str]:
    amount = _number(item.get("quantity"))
    unit = _text(item.get("unit"))
    if amount is not None:
        return amount, unit
    weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
    return _number(weight.get("quantity")), _text(weight.get("unit"))


def _ingredient(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    name = _text(item.get("name") or item.get("foodName"))
    key = _text(item.get("key") or item.get("foodKey"))
    if not name and not key:
        return None
    amount, unit = _recipe_amount(item)
    out: dict[str, Any] = {"name": name or key, "quantity": amount, "unit": unit}
    if key:
        out["key"] = key
    return out


def _stock_row(stock: list[dict[str, Any]], ingredient: dict[str, Any]) -> dict[str, Any] | None:
    wanted = inventory_identity(ingredient)
    return next((row for row in stock if inventory_identity(row) == wanted), None)


def _lot_reference(
    store: Cook4MeCostStore,
    lot: dict[str, Any],
    *,
    currency: str,
    country: str,
) -> tuple[dict[str, Any] | None, str]:
    lot_id = _text(lot.get("id") or lot.get("lotId"))
    if lot_id:
        exact = store.best_reference(f"lot:{lot_id}", currency=currency, country=country)
        if exact is not None:
            return exact, "exact_purchase"
    barcode = _text(lot.get("barcode"))
    if barcode:
        observed = store.best_reference(f"barcode:{barcode}", currency=currency, country=country)
        if observed is not None:
            return observed, "global_barcode_estimate"
    return None, ""


def calculate_recipe_cost(
    recipe: dict[str, Any],
    inventory: Any,
    store: Cook4MeCostStore,
    *,
    currency: str = "",
    country: str = "",
) -> dict[str, Any]:
    """Price a recipe from FEFO stock lots, then generic references.

    Coverage is averaged per ingredient, not across unlike measurement units.
    Currency values are never converted or combined across currencies.
    """
    stock = normalize_inventory(inventory)
    wanted_currency = _currency(currency) or _currency(store.settings.get("currency"))
    wanted_country = _country(country) or _country(store.settings.get("country"))
    totals: dict[str, float] = {}
    rows: list[dict[str, Any]] = []

    for raw in recipe.get("ingredients") or []:
        ingredient = _ingredient(raw)
        if ingredient is None:
            continue
        ident = inventory_identity(ingredient)
        amount = ingredient.get("quantity")
        unit = _text(ingredient.get("unit"))
        if amount is None or not unit:
            rows.append({
                "identity": ident,
                "name": ingredient["name"],
                "quantity": amount,
                "unit": unit,
                "priced": False,
                "coverage": 0.0,
                "exactCoverage": 0.0,
                "costsByCurrency": {},
                "sourceKinds": [],
                "reason": "recipe_amount_unknown",
            })
            continue

        required = float(amount)
        remaining = required
        covered = 0.0
        exact = 0.0
        costs: dict[str, float] = {}
        kinds: list[str] = []
        stock_row = _stock_row(stock, ingredient)
        stock_unit = _text((stock_row or {}).get("unit")) or unit

        if stock_row and not stock_row.get("unlimited"):
            for lot in stock_row.get("lots") or []:
                if remaining <= 1e-9 or not isinstance(lot, dict):
                    break
                available = convert_amount(lot.get("quantity"), stock_unit, unit)
                if available is None or available <= 0:
                    continue
                take = min(remaining, available)
                reference, kind = _lot_reference(
                    store, lot, currency=wanted_currency, country=wanted_country
                )
                if reference is not None:
                    cost = _cost_for_amount(reference, take, unit)
                    curr = _currency(reference.get("currency"))
                    if cost is not None and curr:
                        _add(costs, curr, cost)
                        _add(totals, curr, cost)
                        covered += take
                        if kind == "exact_purchase":
                            exact += take
                        if kind not in kinds:
                            kinds.append(kind)
                remaining -= take

        # Price any quantity not represented by a known stock lot only from an
        # explicit ingredient-level reference. Never infer a barcode/product.
        if remaining > 1e-9:
            reference = store.best_reference(ident, currency=wanted_currency, country=wanted_country)
            if reference is not None:
                cost = _cost_for_amount(reference, remaining, unit)
                curr = _currency(reference.get("currency"))
                if cost is not None and curr:
                    _add(costs, curr, cost)
                    _add(totals, curr, cost)
                    covered += remaining
                    source = _text(reference.get("source"))
                    kind = "manual_reference" if source == "manual" else "ingredient_reference"
                    if kind not in kinds:
                        kinds.append(kind)

        rows.append({
            "identity": ident,
            "name": ingredient["name"],
            "quantity": required,
            "unit": unit,
            "priced": bool(costs),
            "coverage": round(min(1.0, covered / required), 4) if required > 0 else 0.0,
            "exactCoverage": round(min(1.0, exact / required), 4) if required > 0 else 0.0,
            "costsByCurrency": _rounded_currency(costs),
            "sourceKinds": kinds,
        })

    known_rows = [row for row in rows if row.get("quantity") is not None and row.get("unit")]
    coverage = (
        sum(float(row.get("coverage") or 0.0) for row in known_rows) / len(known_rows)
        if known_rows else 0.0
    )
    exact_coverage = (
        sum(float(row.get("exactCoverage") or 0.0) for row in known_rows) / len(known_rows)
        if known_rows else 0.0
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
        "ingredients": rows,
        "coverage": round(coverage, 4),
        "exactPurchaseCoverage": round(exact_coverage, 4),
        "estimated": any(
            any(kind != "exact_purchase" for kind in row.get("sourceKinds") or [])
            for row in rows
        ),
        "targetCurrency": wanted_currency,
        "targetCountry": wanted_country,
        "currencyConversionApplied": False,
    }


def calculate_consumption_cost(
    report: Any,
    store: Cook4MeCostStore,
    *,
    currency: str = "",
    country: str = "",
) -> dict[str, Any]:
    wanted_currency = _currency(currency) or _currency(store.settings.get("currency"))
    wanted_country = _country(country) or _country(store.settings.get("country"))
    totals: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    for raw in report.get("deductedLots") if isinstance(report, dict) else []:
        if not isinstance(raw, dict):
            continue
        quantity = _number(raw.get("quantity"))
        unit = _text(raw.get("unit"))
        reference, kind = _lot_reference(
            store, raw, currency=wanted_currency, country=wanted_country
        )
        cost = _cost_for_amount(reference, quantity, unit) if reference is not None else None
        curr = _currency((reference or {}).get("currency"))
        _add(totals, curr, cost)
        rows.append({
            "identity": _text(raw.get("identity")),
            "lotId": _text(raw.get("lotId") or raw.get("id")),
            "name": _text(raw.get("name") or raw.get("productName")),
            "quantity": quantity,
            "unit": unit,
            "barcode": _text(raw.get("barcode")),
            "cost": round(cost, 2) if cost is not None else None,
            "currency": curr,
            "sourceKind": kind,
        })
    return {
        "totalsByCurrency": _rounded_currency(totals),
        "lots": rows,
        "coverage": round(
            sum(1 for row in rows if row.get("cost") is not None) / len(rows), 4
        ) if rows else 0.0,
        "estimated": any(row.get("sourceKind") == "global_barcode_estimate" for row in rows),
        "currencyConversionApplied": False,
    }


def lookup_open_prices_safe(
    barcode: str,
    *,
    currency: str = "",
    country: str = "",
    timeout: int = 15,
) -> dict[str, Any]:
    """Return Open Prices observations but cost-enable only explicit UNIT/package rows."""
    result = lookup_open_prices(
        barcode, currency=currency, country=country, timeout=timeout
    )
    items = []
    for raw in result.get("items") or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        proven_basis = (
            _text(row.get("pricePer")).upper() == "UNIT"
            and _number(row.get("basisQuantity")) is not None
            and bool(_text(row.get("basisUnit")))
        )
        row["usable"] = bool(proven_basis)
        if not proven_basis:
            row["costExclusionReason"] = "no_explicit_package_basis"
        items.append(row)
    result = dict(result)
    result["items"] = items
    result["usableCount"] = sum(bool(row.get("usable")) for row in items)
    return result


async def store_best_open_price(
    store: Cook4MeCostStore,
    result: dict[str, Any],
    *,
    currency: str = "",
    country: str = "",
) -> dict[str, Any] | None:
    wanted_currency = _currency(currency)
    wanted_country = _country(country)
    candidates = [row for row in result.get("items") or [] if isinstance(row, dict) and row.get("usable")]
    if wanted_currency:
        candidates = [row for row in candidates if _currency(row.get("currency")) == wanted_currency]
    if wanted_country:
        local = [row for row in candidates if _country(row.get("country")) == wanted_country]
        if local:
            candidates = local
    if not candidates:
        return None
    candidates.sort(key=lambda row: _text(row.get("date")), reverse=True)
    chosen = candidates[0]
    return await store.async_set_reference(
        f"barcode:{_text(chosen.get('barcode'))}",
        amount=chosen.get("amount"),
        currency=chosen.get("currency"),
        basis_quantity=chosen.get("basisQuantity"),
        basis_unit=chosen.get("basisUnit"),
        source="open_prices",
        confidence="external_observation",
        country=chosen.get("country") or "",
        location=chosen.get("location") or "",
        date=chosen.get("date") or "",
        barcode=chosen.get("barcode") or "",
        observation_id=chosen.get("id"),
    )
