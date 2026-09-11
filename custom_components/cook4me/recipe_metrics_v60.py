from __future__ import annotations

from collections import defaultdict
import math
import re
from typing import Any, Iterable

try:
    from .ingredient_identity import canonical_identity, identity_candidates
except ImportError:  # Standalone unit-test import via spec_from_file_location.
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "cook4me_ingredient_identity_metrics_test",
        Path(__file__).with_name("ingredient_identity.py"),
    )
    if spec is None or spec.loader is None:
        raise ImportError("ingredient_identity.py")
    _identity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_identity)
    canonical_identity = _identity.canonical_identity
    identity_candidates = _identity.identity_candidates

NUTRIENT_KEYS: tuple[str, ...] = (
    "energyKcal",
    "energyKJ",
    "protein",
    "carbohydrates",
    "sugars",
    "fat",
    "saturatedFat",
    "fiber",
    "salt",
    "sodium",
)

_UNIT_SCALE: dict[str, tuple[str, float]] = {
    "mg": ("mass", 0.001),
    "g": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "ul": ("volume", 0.001),
    "ml": ("volume", 1.0),
    "cl": ("volume", 10.0),
    "dl": ("volume", 100.0),
    "l": ("volume", 1000.0),
    "pc": ("count", 1.0),
    "pcs": ("count", 1.0),
    "piece": ("count", 1.0),
    "pieces": ("count", 1.0),
    "x": ("count", 1.0),
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
    return number if math.isfinite(number) and number >= 0 else None


def _unit(value: Any) -> str:
    return (
        _text(value)
        .casefold()
        .replace("ℓ", "l")
        .replace("µ", "u")
        .replace("μ", "u")
        .replace(" ", "")
    )


def convert_amount(value: Any, from_unit: Any, to_unit: Any) -> float | None:
    amount = _number(value)
    if amount is None:
        return None
    source = _unit(from_unit)
    target = _unit(to_unit)
    if source == target:
        return amount
    left = _UNIT_SCALE.get(source)
    right = _UNIT_SCALE.get(target)
    if not left or not right or left[0] != right[0]:
        return None
    return amount * left[1] / right[1]


def normalize_nutrition_profile(value: Any) -> dict[str, Any] | None:
    """Normalize an explicit nutrient profile without inferring density/portion mass."""
    if not isinstance(value, dict):
        return None
    basis = _text(value.get("basis")).casefold()
    basis_quantity = _number(value.get("basisQuantity"))
    basis_unit = _unit(value.get("basisUnit"))
    if not basis_quantity and basis == "per100g":
        basis_quantity, basis_unit = 100.0, "g"
    elif not basis_quantity and basis == "per100ml":
        basis_quantity, basis_unit = 100.0, "ml"
    if not basis_quantity or basis_quantity <= 0 or basis_unit not in _UNIT_SCALE:
        return None

    raw_values = value.get("values") if isinstance(value.get("values"), dict) else value
    nutrients: dict[str, float] = {}
    for key in NUTRIENT_KEYS:
        number = _number(raw_values.get(key)) if isinstance(raw_values, dict) else None
        if number is not None:
            nutrients[key] = number
    if not nutrients:
        return None

    out: dict[str, Any] = {
        "basisQuantity": basis_quantity,
        "basisUnit": basis_unit,
        "values": nutrients,
    }
    for field in ("source", "sourceId", "confidence", "evidence", "reviewFile"):
        text = _text(value.get(field))
        if text:
            out[field] = text
    return out


def normalize_price_profile(value: Any) -> dict[str, Any] | None:
    """Normalize one explicit price observation/reference to a quantity basis."""
    if not isinstance(value, dict):
        return None
    amount = _number(value.get("amount") if "amount" in value else value.get("price"))
    basis_quantity = _number(value.get("basisQuantity"))
    basis_unit = _unit(value.get("basisUnit"))
    currency = _text(value.get("currency")).upper()
    if (
        amount is None
        or not basis_quantity
        or basis_quantity <= 0
        or basis_unit not in _UNIT_SCALE
        or not currency
    ):
        return None
    out: dict[str, Any] = {
        "amount": amount,
        "currency": currency,
        "basisQuantity": basis_quantity,
        "basisUnit": basis_unit,
    }
    for field in ("country", "source", "sourceId", "observedAt", "confidence"):
        text = _text(value.get(field))
        if text:
            out[field] = text
    return out


def build_nutrition_index(rows: Iterable[Any]) -> dict[str, dict[str, Any]]:
    """Index only explicit profiles under every compatible identity candidate.

    When multiple rows claim the same identity with different profiles, that
    identity is removed instead of selecting a winner. Conflicting evidence is
    therefore visible as missing coverage rather than silently guessed.
    """
    index: dict[str, dict[str, Any]] = {}
    conflicts: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        profile = normalize_nutrition_profile(raw.get("nutrition"))
        if profile is None:
            continue
        for ident in identity_candidates(raw):
            previous = index.get(ident)
            if previous is not None and previous != profile:
                conflicts.add(ident)
                continue
            index[ident] = profile
    for ident in conflicts:
        index.pop(ident, None)
    return index


def build_price_index(rows: Iterable[Any]) -> dict[str, tuple[dict[str, Any], ...]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        profile = normalize_price_profile(raw)
        if profile is None:
            continue
        target = raw.get("ingredient") if isinstance(raw.get("ingredient"), dict) else raw
        candidates = identity_candidates(target)
        explicit_identity = _text(raw.get("identity"))
        if explicit_identity:
            candidates = tuple(dict.fromkeys((explicit_identity, *candidates)))
        for ident in candidates:
            grouped[ident].append(profile)
    return {
        ident: tuple(rows)
        for ident, rows in grouped.items()
    }


def _lookup(index: dict[str, Any], ingredient: Any) -> Any:
    for ident in identity_candidates(ingredient):
        if ident in index:
            return index[ident]
    return None


def _recipe_amount(item: dict[str, Any]) -> tuple[float | None, str]:
    amount = _number(item.get("quantity"))
    unit = _unit(item.get("unit"))
    if amount is not None:
        return amount, unit
    weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
    return _number(weight.get("quantity")), _unit(weight.get("unit"))


def ingredient_nutrition(
    ingredient: dict[str, Any], nutrition_index: dict[str, dict[str, Any]]
) -> dict[str, float] | None:
    profile = _lookup(nutrition_index, ingredient)
    if not isinstance(profile, dict):
        return None
    quantity, unit = _recipe_amount(ingredient)
    converted = convert_amount(quantity, unit, profile.get("basisUnit"))
    if converted is None:
        return None
    factor = converted / float(profile["basisQuantity"])
    return {
        key: float(value) * factor
        for key, value in profile["values"].items()
        if isinstance(value, (int, float))
    }


def calculate_recipe_nutrition_fast(
    recipe: dict[str, Any],
    nutrition_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    totals: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    ingredients = [row for row in recipe.get("ingredients") or [] if isinstance(row, dict)]
    for ingredient in ingredients:
        values = ingredient_nutrition(ingredient, nutrition_index)
        identity = canonical_identity(ingredient)
        rows.append({"identity": identity, "covered": values is not None})
        if values is None:
            continue
        for key, value in values.items():
            totals[key] = totals.get(key, 0.0) + value

    servings = _number(recipe.get("servings") or recipe.get("groupSize"))
    if servings is None:
        yield_data = recipe.get("yield") if isinstance(recipe.get("yield"), dict) else {}
        servings = _number(yield_data.get("quantity") or yield_data.get("quantityDisplay"))
    covered = sum(bool(row["covered"]) for row in rows)
    rounded = {
        key: round(value, 4)
        for key, value in totals.items()
    }
    return {
        "totals": rounded,
        "perServing": {
            key: round(value / servings, 4)
            for key, value in totals.items()
            if servings and servings > 0
        },
        "servings": servings,
        "coverage": round(covered / len(rows), 4) if rows else 0.0,
        "fullyCovered": bool(rows and covered == len(rows)),
        "ingredientCoverage": rows,
        "calculation": "identity-indexed-vector-sum-v1",
    }


def _price_candidates(
    price_index: dict[str, tuple[dict[str, Any], ...]],
    ingredient: dict[str, Any],
    *,
    currency: str,
    country: str,
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for ident in identity_candidates(ingredient):
        for row in price_index.get(ident, ()):
            if currency and _text(row.get("currency")).upper() != currency:
                continue
            row_country = _text(row.get("country")).upper()
            if country and row_country and row_country != country:
                continue
            signature = (
                row.get("amount"),
                row.get("currency"),
                row.get("basisQuantity"),
                row.get("basisUnit"),
                row.get("sourceId"),
                row.get("observedAt"),
            )
            if signature in seen:
                continue
            seen.add(signature)
            values.append(row)
    # Prefer exact-country evidence, then newest lexical timestamp. The caller's
    # evidence remains visible; there is no currency conversion or price guessing.
    values.sort(
        key=lambda row: (
            1 if country and _text(row.get("country")).upper() == country else 0,
            _text(row.get("observedAt")),
        ),
        reverse=True,
    )
    return values


def ingredient_cost(
    ingredient: dict[str, Any],
    price_index: dict[str, tuple[dict[str, Any], ...]],
    *,
    currency: str = "",
    country: str = "",
) -> dict[str, Any] | None:
    wanted_currency = _text(currency).upper()
    wanted_country = _text(country).upper()
    quantity, unit = _recipe_amount(ingredient)
    if quantity is None or not unit:
        return None
    for profile in _price_candidates(
        price_index,
        ingredient,
        currency=wanted_currency,
        country=wanted_country,
    ):
        converted = convert_amount(quantity, unit, profile.get("basisUnit"))
        if converted is None:
            continue
        amount = float(profile["amount"]) * converted / float(profile["basisQuantity"])
        return {
            "identity": canonical_identity(ingredient),
            "amount": round(amount, 4),
            "currency": profile["currency"],
            "source": _text(profile.get("source")),
            "sourceId": _text(profile.get("sourceId")),
            "observedAt": _text(profile.get("observedAt")),
            "country": _text(profile.get("country")),
        }
    return None


def calculate_recipe_cost_fast(
    recipe: dict[str, Any],
    price_index: dict[str, tuple[dict[str, Any], ...]],
    *,
    currency: str = "",
    country: str = "",
) -> dict[str, Any]:
    totals: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    ingredients = [row for row in recipe.get("ingredients") or [] if isinstance(row, dict)]
    for ingredient in ingredients:
        cost = ingredient_cost(
            ingredient,
            price_index,
            currency=currency,
            country=country,
        )
        rows.append(
            {
                "identity": canonical_identity(ingredient),
                "priced": cost is not None,
                "cost": cost,
            }
        )
        if cost is not None:
            curr = cost["currency"]
            totals[curr] = totals.get(curr, 0.0) + float(cost["amount"])

    servings = _number(recipe.get("servings") or recipe.get("groupSize"))
    covered = sum(bool(row["priced"]) for row in rows)
    return {
        "totalsByCurrency": {
            curr: round(value, 2) for curr, value in totals.items()
        },
        "perServingByCurrency": {
            curr: round(value / servings, 2)
            for curr, value in totals.items()
            if servings and servings > 0
        },
        "servings": servings,
        "coverage": round(covered / len(rows), 4) if rows else 0.0,
        "fullyCovered": bool(rows and covered == len(rows)),
        "ingredients": rows,
        "currencyConversionApplied": False,
        "calculation": "identity-indexed-price-vector-v1",
    }


def compile_recipe_dependency_index(
    recipes: Iterable[Any],
) -> dict[str, tuple[int, ...]]:
    """Map every ingredient identity candidate to affected recipe indexes."""
    dependencies: dict[str, set[int]] = defaultdict(set)
    for recipe_index, recipe in enumerate(recipes):
        if not isinstance(recipe, dict):
            continue
        rows: list[dict[str, Any]] = []
        rows.extend(
            row
            for row in recipe.get("ingredients") or []
            if isinstance(row, dict)
        )
        for variant in recipe.get("variants") or []:
            if isinstance(variant, dict):
                rows.extend(
                    row
                    for row in variant.get("ingredients") or []
                    if isinstance(row, dict)
                )
        for ingredient in rows:
            for ident in identity_candidates(ingredient):
                dependencies[ident].add(recipe_index)
    return {
        ident: tuple(sorted(indices))
        for ident, indices in sorted(dependencies.items())
    }


def affected_recipe_indices(
    dependency_index: dict[str, tuple[int, ...]], ingredient: Any
) -> tuple[int, ...]:
    affected: set[int] = set()
    for ident in identity_candidates(ingredient):
        affected.update(dependency_index.get(ident, ()))
    return tuple(sorted(affected))
