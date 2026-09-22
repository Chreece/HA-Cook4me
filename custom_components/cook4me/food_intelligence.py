from __future__ import annotations

from copy import deepcopy
import math
import re
import unicodedata
from typing import Any

from .stock_allocation import allocate_stock
from .inventory import stock_for_ingredient, convert_amount, inventory_identity, normalize_inventory
from .price_measurements import price_options

_NUTRITION_GOALS = {
    "balanced",
    "high_protein",
    "lower_calorie",
    "high_fiber",
    "lower_saturated_fat",
}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    out: list[str] = []
    pending_space = False
    for char in text:
        if unicodedata.category(char).startswith("M"):
            continue
        if char.isalnum():
            if pending_space and out:
                out.append(" ")
            out.append(char)
            pending_space = False
        else:
            pending_space = True
    return "".join(out).strip()


def _ingredient_name(item: dict[str, Any]) -> str:
    return _text(item.get("foodName") or item.get("name") or item.get("applicationDescription"))


def _recipe_amount(item: dict[str, Any]) -> tuple[float | None, str]:
    amount = _number(item.get("quantity"))
    unit = _text(item.get("unit"))
    if amount is not None:
        return amount, unit
    weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
    return _number(weight.get("quantity")), _text(weight.get("unit"))


def _find_stock(stock, ingredient, used=None):
    current = stock_for_ingredient(stock, ingredient, used)
    if current is not None:
        return current
    name = _norm(_ingredient_name(ingredient))
    fallback = next((row for row in stock if name and _norm(row.get("name")) == name), None)
    return stock_for_ingredient(stock, fallback, used) if fallback else None


def _availability_status(
    ingredient: dict[str, Any], availability: list[dict[str, Any]]
) -> str:
    key = _text(ingredient.get("foodKey") or ingredient.get("key"))
    name = _norm(_ingredient_name(ingredient))
    for row in availability:
        if not isinstance(row, dict):
            continue
        if key and key == _text(row.get("key")):
            return _text(row.get("status"))
        if name and name == _norm(row.get("name")):
            return _text(row.get("status"))
    return ""


_REVIEWED_PORTION_KINDS = {"food_portion", "reference_portion"}


def _reviewed_portion_requirement(
    ingredient: dict[str, Any],
    current: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a stock-compatible requirement only when reviewed food evidence exists.

    Recipe/source units remain authoritative. Cross-dimension conversion is allowed
    only through an ingredient-specific reviewed portion already bundled with
    Cook4Me (for example USDA garlic: 1 clove = 3 g). Generic spoon, density,
    package or count guesses are intentionally excluded.
    """
    required, required_unit = _recipe_amount(ingredient)
    result = {
        "requiredQuantity": required,
        "requiredUnit": required_unit,
        "allocationQuantity": required,
        "allocationUnit": required_unit,
        "conversion": None,
    }
    if required is None or not isinstance(current, dict) or current.get("unlimited"):
        return result

    stock_amount = _number(current.get("quantity"))
    stock_unit = _text(current.get("unit"))
    if stock_amount is None:
        return result
    if convert_amount(stock_amount, stock_unit, required_unit) is not None:
        return result

    candidate = dict(ingredient)
    if not candidate.get("canonicalName") and candidate.get("foodName"):
        candidate["canonicalName"] = candidate["foodName"]

    for option in price_options(candidate):
        estimate = option.get("estimate") if isinstance(option, dict) else None
        if not isinstance(estimate, dict) or estimate.get("kind") not in _REVIEWED_PORTION_KINDS:
            continue
        quantity = _number(option.get("quantity"))
        unit = _text(option.get("unit"))
        if quantity is None or quantity <= 0 or not unit:
            continue
        if convert_amount(stock_amount, stock_unit, unit) is None:
            continue
        source_unit = required_unit or _text(estimate.get("sourceUnit"))
        result["requiredUnit"] = source_unit
        result["allocationQuantity"] = quantity
        result["allocationUnit"] = unit
        result["conversion"] = {
            "kind": estimate.get("kind"),
            "label": estimate.get("label"),
            "sourceUrl": estimate.get("sourceUrl"),
            "sourceQuantity": required,
            "sourceUnit": source_unit,
            "quantity": quantity,
            "unit": unit,
        }
        return result
    return result


def recipe_quantity_feasibility(
    recipe: dict[str, Any],
    inventory: Any,
    *,
    availability: Any = None,
) -> dict[str, Any]:
    """Compare recipe requirements with actual stock without guessing units.

    Known compatible amounts produce exact shortages. Staples are ignored when the
    caller supplies ingredientAvailability with ``status=staple``. Unknown recipe
    amounts or incompatible units are reported as unknown rather than pretending
    that presence means enough stock exists.
    """
    stock = normalize_inventory(inventory)
    availability_rows = availability if isinstance(availability, list) else []
    rows: list[dict[str, Any]] = []
    known_fractions: list[float] = []
    shortages: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []

    ingredients = [item for item in recipe.get("ingredients") or [] if isinstance(item, dict)]
    requirements: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    for item in ingredients:
        current = _find_stock(stock, item)
        requirement = _reviewed_portion_requirement(item, current)
        requirements.append(requirement)
        requests.append({
            **item,
            "identity": inventory_identity(current or item),
            "quantity": requirement["allocationQuantity"],
            "unit": requirement["allocationUnit"],
            "consume": bool(_ingredient_name(item))
            and _availability_status(item, availability_rows) != "staple",
        })
    for ingredient, current, requirement in zip(
        ingredients, allocate_stock(stock, requests), requirements
    ):
        name = _ingredient_name(ingredient)
        if not name:
            continue
        status = _availability_status(ingredient, availability_rows)
        if status == "staple":
            rows.append({
                "identity": inventory_identity(ingredient),
                "name": name,
                "status": "staple",
                "coverage": 1.0,
                "confidence": "staple",
            })
            continue

        required = requirement["requiredQuantity"]
        required_unit = requirement["requiredUnit"]
        allocation_required = requirement["allocationQuantity"]
        allocation_unit = requirement["allocationUnit"]
        conversion = requirement["conversion"]
        ident = inventory_identity(current or ingredient)
        base: dict[str, Any] = {
            "identity": ident,
            **({"key": _text(ingredient.get("foodKey") or ingredient.get("key"))} if ingredient.get("foodKey") or ingredient.get("key") else {}),
            "name": name,
            "requiredQuantity": required,
            "requiredUnit": required_unit,
        }

        if required is None:
            row = {**base, "status": "unknown_requirement", "coverage": None, "confidence": "unknown"}
            if current is not None:
                row["availableQuantity"] = current.get("quantity")
                row["availableUnit"] = current.get("unit", "")
            rows.append(row)
            unknown.append(deepcopy(row))
            continue

        if current is None:
            row = {
                **base,
                "status": "shortage",
                "availableQuantity": 0.0,
                "availableUnit": required_unit,
                "missingQuantity": required,
                "missingUnit": required_unit,
                "coverage": 0.0,
                "confidence": "exact" if required_unit else "unitless",
            }
            rows.append(row)
            shortages.append(deepcopy(row))
            known_fractions.append(0.0)
            continue

        if current.get("unlimited"):
            row = {
                **base,
                "status": "enough",
                "availableQuantity": None,
                "availableUnit": current.get("unit", ""),
                "unlimited": True,
                "missingQuantity": 0.0,
                "missingUnit": required_unit,
                "coverage": 1.0,
                "confidence": "exact",
            }
            rows.append(row)
            known_fractions.append(1.0)
            continue

        stock_amount = _number(current.get("quantity"))
        stock_unit = _text(current.get("unit"))
        if stock_amount is None:
            row = {
                **base,
                "status": "unknown_stock_amount",
                "availableQuantity": None,
                "availableUnit": stock_unit,
                "coverage": None,
                "confidence": "unknown",
            }
            rows.append(row)
            unknown.append(deepcopy(row))
            continue

        comparison_required = allocation_required if conversion else required
        comparison_unit = allocation_unit if conversion else required_unit

        # If both recipe and stock are truly unitless, compare the values directly.
        if not comparison_unit and not stock_unit:
            available_required = stock_amount
        else:
            available_required = convert_amount(stock_amount, stock_unit, comparison_unit)
        if available_required is None:
            row = {
                **base,
                "status": "incompatible_unit",
                "availableQuantity": stock_amount,
                "availableUnit": stock_unit,
                "coverage": None,
                "confidence": "unknown",
            }
            rows.append(row)
            unknown.append(deepcopy(row))
            continue

        available = max(0.0, float(available_required))
        comparison_missing = max(0.0, comparison_required - available)
        fraction = (
            1.0
            if comparison_required <= 1e-12
            else min(1.0, available / comparison_required)
        )
        if conversion and comparison_required > 1e-12:
            scale = required / comparison_required
            reported_available = min(required, available) * scale
            missing = max(0.0, required - reported_available)
        else:
            reported_available = min(available, required)
            missing = comparison_missing
        row = {
            **base,
            "status": "enough" if missing <= 1e-9 else "shortage",
            "availableQuantity": round(reported_available, 9),
            "availableUnit": required_unit,
            "missingQuantity": round(missing, 9),
            "missingUnit": required_unit,
            "coverage": round(fraction, 3),
            "confidence": "reviewed_portion" if conversion else "exact",
            **({"conversion": deepcopy(conversion)} if conversion else {}),
        }
        rows.append(row)
        known_fractions.append(fraction)
        if missing > 1e-9:
            shortages.append(deepcopy(row))

    known_coverage = sum(known_fractions) / len(known_fractions) if known_fractions else 1.0
    considered = [row for row in rows if row.get("status") != "staple"]
    confidence = (
        1.0
        if not considered
        else sum(1 for row in considered if row.get("coverage") is not None) / len(considered)
    )
    return {
        "items": rows,
        "shortages": shortages,
        "unknown": unknown,
        "quantityCoverage": round(known_coverage, 3),
        "confidence": round(confidence, 3),
        "fullyAvailable": not shortages and not unknown,
        "knownEnough": not shortages,
    }


def shortage_shopping_items(feasibility: Any) -> list[dict[str, Any]]:
    """Return only the known missing amount for native Shopping List actions."""
    if not isinstance(feasibility, dict):
        return []
    out: list[dict[str, Any]] = []
    for row in feasibility.get("shortages") or []:
        if not isinstance(row, dict):
            continue
        amount = _number(row.get("missingQuantity"))
        if amount is None or amount <= 1e-9:
            continue
        item = {
            **({"key": row["key"]} if row.get("key") else {}),
            "name": _text(row.get("name")),
            "quantity": round(amount, 9),
            "unit": _text(row.get("missingUnit")),
            "shortageOnly": True,
        }
        if item["name"]:
            out.append(item)
    return out


def normalize_nutrition_goal(value: Any) -> str:
    goal = _text(value).lower()
    return goal if goal in _NUTRITION_GOALS else "balanced"


def nutrition_goal_bonus(nutrition: Any, goal: Any) -> dict[str, Any]:
    """Return a bounded ranking hint; never override safety or stock feasibility."""
    goal = normalize_nutrition_goal(goal)
    if not isinstance(nutrition, dict):
        return {"goal": goal, "bonus": 0.0, "coverage": 0.0, "reason": "nutrition_unavailable"}
    coverage = _number(nutrition.get("coverage")) or 0.0
    values = nutrition.get("perServing") if isinstance(nutrition.get("perServing"), dict) and nutrition.get("perServing") else nutrition.get("totals")
    if not isinstance(values, dict) or coverage < 0.5:
        return {"goal": goal, "bonus": 0.0, "coverage": round(coverage, 3), "reason": "insufficient_coverage"}

    def val(key: str) -> float | None:
        return _number(values.get(key))

    bonus = 0.0
    metric = None
    if goal == "high_protein":
        metric = val("protein")
        if metric is not None:
            bonus = min(20.0, metric * 0.8)
    elif goal == "high_fiber":
        metric = val("fiber")
        if metric is not None:
            bonus = min(20.0, metric * 2.0)
    elif goal == "lower_calorie":
        metric = val("energyKcal")
        if metric is not None:
            bonus = max(0.0, min(20.0, (700.0 - metric) / 35.0))
    elif goal == "lower_saturated_fat":
        metric = val("saturatedFat")
        if metric is not None:
            bonus = max(0.0, min(20.0, (15.0 - metric) * (20.0 / 15.0)))
    else:
        protein = val("protein") or 0.0
        fiber = val("fiber") or 0.0
        calories = val("energyKcal")
        bonus = min(12.0, protein * 0.25 + fiber * 0.5)
        if calories is not None and calories > 900:
            bonus = max(0.0, bonus - min(6.0, (calories - 900.0) / 100.0))

    # Scale by evidence coverage so partially estimated recipes cannot dominate.
    bonus *= min(1.0, coverage)
    return {
        "goal": goal,
        "bonus": round(max(0.0, min(20.0, bonus)), 1),
        "coverage": round(coverage, 3),
        "metric": metric,
    }


def allocate_meal_nutrition(
    totals: Any,
    servings: Any,
    allocations: Any,
) -> dict[str, Any]:
    """Split confirmed meal nutrition by explicitly assigned serving portions."""
    if not isinstance(totals, dict):
        totals = {}
    recipe_servings = _number(servings)
    clean: list[dict[str, Any]] = []
    assigned = 0.0
    if isinstance(allocations, list):
        for row in allocations:
            if not isinstance(row, dict):
                continue
            name = _text(row.get("name"))
            portion = _number(row.get("servings"))
            if not name or portion is None or portion <= 0:
                continue
            clean.append({"name": name, "servings": portion})
            assigned += portion
    denominator = recipe_servings if recipe_servings and recipe_servings > 0 else assigned
    if denominator is None or denominator <= 0:
        return {"allocations": [], "assignedServings": 0.0, "unassignedServings": recipe_servings}

    result: list[dict[str, Any]] = []
    for row in clean:
        fraction = row["servings"] / denominator
        values = {
            key: round(float(value) * fraction, 2)
            for key, value in totals.items()
            if isinstance(value, (int, float)) and math.isfinite(float(value))
        }
        result.append({**row, "fraction": round(fraction, 4), "nutrition": values})
    unassigned = max(0.0, (recipe_servings or assigned) - assigned)
    return {
        "allocations": result,
        "assignedServings": round(assigned, 3),
        "unassignedServings": round(unassigned, 3),
    }
