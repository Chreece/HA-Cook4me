from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from .inventory import inventory_identity, normalize_inventory
from .nutrition import (
    convert_amount,
    ingredient_identity,
    normalize_nutrition,
    nutrition_for_amount,
)


def _number(value: Any) -> float | None:
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _unit(value: Any) -> str:
    return _text(value).lower().replace("µ", "u").replace("μ", "u").replace("ℓ", "l").replace(" ", "")


def _recipe_amount(item: dict[str, Any]) -> tuple[float | None, str]:
    amount = _number(item.get("quantity"))
    unit = _unit(item.get("unit"))
    if amount is not None:
        return amount, unit
    weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
    return _number(weight.get("quantity")), _unit(weight.get("unit"))


def _servings(recipe: dict[str, Any]) -> float | None:
    yield_data = recipe.get("yield") if isinstance(recipe.get("yield"), dict) else {}
    for value in (recipe.get("servings"), recipe.get("groupSize"), yield_data.get("quantity"), yield_data.get("quantityDisplay")):
        number = _number(value)
        if number and number > 0:
            return number
    return None


def _add(target: dict[str, float], values: dict[str, float] | None) -> None:
    if not values:
        return
    for key, value in values.items():
        target[key] = target.get(key, 0.0) + float(value)


def _rounded(values: dict[str, float]) -> dict[str, float]:
    return {
        key: round(float(value), 1 if key in {"energyKcal", "energyKJ"} else 2)
        for key, value in values.items()
        if math.isfinite(float(value))
    }


def _generic_profile(generic: Any, identity: str) -> dict[str, Any] | None:
    row = generic.get(identity) if isinstance(generic, dict) else None
    if isinstance(row, dict) and isinstance(row.get("nutrition"), dict):
        return normalize_nutrition(row["nutrition"])
    return normalize_nutrition(row)


def _find_inventory(stock: list[dict[str, Any]], ingredient: dict[str, Any]) -> dict[str, Any] | None:
    wanted = ingredient_identity(ingredient)
    if wanted:
        for row in stock:
            if inventory_identity(row) == wanted:
                return row
    return None


def _match_score(inventory_lot: dict[str, Any], nutrition_lot: dict[str, Any]) -> int:
    score = 0
    left_id = _text(inventory_lot.get("id"))
    right_id = _text(nutrition_lot.get("inventoryLotId") or nutrition_lot.get("lotId"))
    if left_id and right_id and left_id == right_id:
        return 100
    left_barcode = _text(inventory_lot.get("barcode"))
    right_barcode = _text(nutrition_lot.get("barcode"))
    if left_barcode and right_barcode and left_barcode == right_barcode:
        score += 20
    left_date = _text(inventory_lot.get("bestBefore"))
    right_date = _text(nutrition_lot.get("bestBefore"))
    if left_date == right_date:
        score += 10
    left_product = _text(inventory_lot.get("productName")).casefold()
    right_product = _text(nutrition_lot.get("productName")).casefold()
    if left_product and right_product and left_product == right_product:
        score += 4
    return score


def calculate_recipe_nutrition_fefo(
    recipe: dict[str, Any],
    inventory: Any,
    *,
    generic: Any = None,
    stock_lots: Any = None,
) -> dict[str, Any]:
    """Predict meal nutrition from the same inventory batch order used for FEFO consumption."""
    stock = normalize_inventory(inventory)
    generic = generic or {}
    stock_lots = stock_lots or {}
    totals: dict[str, float] = {}
    details: list[dict[str, Any]] = []
    fractions: list[float] = []
    kinds: set[str] = set()

    for ingredient in recipe.get("ingredients") or []:
        if not isinstance(ingredient, dict):
            continue
        identity = ingredient_identity(ingredient)
        name = _text(ingredient.get("foodName") or ingredient.get("name"))
        amount, unit = _recipe_amount(ingredient)
        detail: dict[str, Any] = {"identity": identity, "name": name, "quantity": amount, "unit": unit, "sources": []}
        if amount is None or not unit:
            detail.update({"coverage": 0.0, "reason": "amount_or_unit_unknown"})
            details.append(detail)
            continue

        current = _find_inventory(stock, ingredient)
        required_remaining = amount
        covered = 0.0
        exact_pool = [deepcopy(row) for row in (stock_lots.get(identity) or []) if isinstance(row, dict)] if isinstance(stock_lots, dict) else []
        generic_profile = _generic_profile(generic, identity)

        if current and not current.get("unlimited"):
            stock_unit = _unit(current.get("unit"))
            required_stock = convert_amount(amount, unit, stock_unit) if stock_unit else None
            if required_stock is not None and required_stock > 0:
                remaining_stock = required_stock
                inventory_lots = current.get("lots") if isinstance(current.get("lots"), list) else []
                for inv_lot in inventory_lots:
                    if remaining_stock <= 1e-12:
                        break
                    available = _number(inv_lot.get("quantity")) or 0.0
                    if available <= 0:
                        continue
                    take_stock = min(available, remaining_stock)
                    take_recipe = convert_amount(take_stock, stock_unit, unit)
                    if take_recipe is None:
                        continue
                    remaining_for_lot = take_stock
                    ranked = sorted(
                        enumerate(exact_pool),
                        key=lambda item: _match_score(inv_lot, item[1]),
                        reverse=True,
                    )
                    for pool_index, record in ranked:
                        if remaining_for_lot <= 1e-12:
                            break
                        if _match_score(inv_lot, record) <= 0:
                            continue
                        record_available = convert_amount(record.get("quantity"), record.get("unit"), stock_unit)
                        if record_available is None or record_available <= 0:
                            continue
                        take_exact = min(record_available, remaining_for_lot)
                        values = nutrition_for_amount(record.get("nutrition"), take_exact, stock_unit)
                        if values is None:
                            continue
                        _add(totals, values)
                        exact_as_recipe = convert_amount(take_exact, stock_unit, unit) or 0.0
                        covered += exact_as_recipe
                        remaining_for_lot -= take_exact
                        record_left = record_available - take_exact
                        if record_left <= 1e-9:
                            exact_pool[pool_index]["quantity"] = 0
                        else:
                            exact_pool[pool_index]["quantity"] = record_left
                            exact_pool[pool_index]["unit"] = stock_unit
                        kinds.add("exact_product")
                        detail["sources"].append({
                            "type": "exact_product",
                            "lotId": inv_lot.get("id"),
                            "barcode": inv_lot.get("barcode") or record.get("barcode"),
                            "productName": inv_lot.get("productName") or record.get("productName"),
                            "quantity": round(exact_as_recipe, 6),
                            "unit": unit,
                            "bestBefore": inv_lot.get("bestBefore"),
                            "effectiveBestBefore": inv_lot.get("effectiveBestBefore"),
                            "storage": inv_lot.get("storage"),
                        })
                    if remaining_for_lot > 1e-12 and generic_profile is not None:
                        generic_as_recipe = convert_amount(remaining_for_lot, stock_unit, unit)
                        if generic_as_recipe is not None:
                            values = nutrition_for_amount(generic_profile, generic_as_recipe, unit)
                            if values is not None:
                                _add(totals, values)
                                covered += generic_as_recipe
                                kinds.add("generic_reference")
                                detail["sources"].append({"type": "generic_reference", "quantity": round(generic_as_recipe, 6), "unit": unit})
                    remaining_stock -= take_stock
                required_remaining = max(0.0, amount - min(amount, covered))

        # Anything not represented by house stock can still be estimated using
        # the generic ingredient catalog, but is explicitly marked estimated.
        if required_remaining > 1e-9 and generic_profile is not None:
            values = nutrition_for_amount(generic_profile, required_remaining, unit)
            if values is not None:
                _add(totals, values)
                covered += required_remaining
                kinds.add("generic_reference")
                detail["sources"].append({"type": "generic_reference", "quantity": round(required_remaining, 6), "unit": unit})

        fraction = min(1.0, covered / amount) if amount > 0 else 1.0
        fractions.append(fraction)
        detail["coverage"] = round(fraction, 3)
        if fraction < 0.999:
            detail["reason"] = "nutrition_reference_missing_or_incompatible_unit"
        details.append(detail)

    coverage = sum(fractions) / len(fractions) if fractions else 0.0
    servings = _servings(recipe)
    return {
        "totals": _rounded(totals),
        "perServing": _rounded({key: value / servings for key, value in totals.items()}) if servings else {},
        "servings": servings,
        "coverage": round(coverage, 3),
        "fullyCovered": bool(fractions) and all(value >= 0.999 for value in fractions),
        "estimated": "generic_reference" in kinds or coverage < 0.999,
        "sourceKinds": sorted(kinds),
        "ingredients": details,
    }
