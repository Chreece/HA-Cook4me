from __future__ import annotations

from copy import deepcopy
import math
import re
import unicodedata
from typing import Any

MEAL_TYPES = (
    "breakfast",
    "starter",
    "salad",
    "soup",
    "main",
    "side",
    "dessert",
    "snack",
)

_ALIASES = {
    "breakfast": (
        "BREAKFAST", "BRUNCH", "FRUHSTUCK", "FRUEHSTUECK", "PETIT DEJEUNER",
        "DESAYUNO", "COLAZIONE", "CAFE DA MANHA", "PROINO", "ΠΡΩΙΝΟ",
    ),
    "starter": (
        "STARTER", "APPETIZER", "APPETISER", "ENTREE", "VORSPEISE", "ENTRADA",
        "ANTIPASTO", "OREKTIKO", "ΟΡΕΚΤΙΚΟ",
    ),
    "salad": (
        "SALAD", "SALAT", "SALADE", "ENSALADA", "INSALATA", "SALATA", "ΣΑΛΑΤΑ",
    ),
    "soup": (
        "SOUP", "SUPPE", "SOUPE", "SOPA", "ZUPPA", "SOUPA", "ΣΟΥΠΑ",
    ),
    "main": (
        "MAIN", "MAIN COURSE", "MAIN_DISH", "HAUPTGERICHT", "PLAT PRINCIPAL",
        "PLATO PRINCIPAL", "SECONDO", "KYRIOS", "ΚΥΡΙΩΣ", "ΚΥΡΙΟ",
    ),
    "side": (
        "SIDE", "SIDE DISH", "BEILAGE", "ACCOMPANIMENT", "GUARNICION", "CONTORNO",
        "SYNODEFTIKO", "ΣΥΝΟΔΕΥΤΙΚΟ",
    ),
    "dessert": (
        "DESSERT", "NACHSPEISE", "POSTRE", "DOLCE", "EPIDORPIO", "ΓΛΥΚΟ", "ΕΠΙΔΟΡΠΙΟ",
    ),
    "snack": (
        "SNACK", "COLLATION", "MERIENDA", "SPUNTINO", "SNAK", "ΣΝΑΚ",
    ),
}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


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


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def normalize_meal_types(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for raw in value:
        item = _text(raw).lower().replace("-", "_")
        if item in MEAL_TYPES and item not in out:
            out.append(item)
    return out


def _taxonomy_values(recipe: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field in ("courses", "occasions"):
        rows = recipe.get(field)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict):
                for key in ("key", "name"):
                    if row.get(key):
                        values.append(_text(row[key]))
            elif row:
                values.append(_text(row))
    recipe_type = recipe.get("recipeType")
    if isinstance(recipe_type, dict):
        for key in ("key", "name"):
            if recipe_type.get(key):
                values.append(_text(recipe_type[key]))
    elif recipe_type:
        values.append(_text(recipe_type))
    return values


def recipe_matches_meal_types(recipe: dict[str, Any], selected: Any) -> bool:
    wanted = normalize_meal_types(selected)
    if not wanted:
        return True
    haystack = " | ".join(_taxonomy_values(recipe))
    if not haystack:
        return False
    normalized = _norm(haystack)
    compact = normalized.replace(" ", "")
    for meal_type in wanted:
        for alias in _ALIASES.get(meal_type, (meal_type,)):
            token = _norm(alias)
            if token and (token in normalized or token.replace(" ", "") in compact):
                return True
    return False


def calorie_target_bonus(
    nutrition: Any,
    target: Any,
    *,
    tolerance_fraction: float = 0.25,
) -> dict[str, Any]:
    target_value = _number(target)
    if target_value is None or target_value <= 0:
        return {"bonus": 0.0, "target": None, "calories": None, "delta": None}
    if not isinstance(nutrition, dict):
        return {"bonus": 0.0, "target": target_value, "calories": None, "delta": None}
    coverage = _number(nutrition.get("coverage")) or 0.0
    values = nutrition.get("perServing") if isinstance(nutrition.get("perServing"), dict) and nutrition.get("perServing") else nutrition.get("totals")
    calories = _number(values.get("energyKcal")) if isinstance(values, dict) else None
    if calories is None or coverage < 0.5:
        return {"bonus": 0.0, "target": target_value, "calories": calories, "delta": None, "coverage": round(coverage, 3)}
    delta = calories - target_value
    tolerance = max(25.0, target_value * max(0.05, min(float(tolerance_fraction), 1.0)))
    closeness = max(0.0, 1.0 - abs(delta) / tolerance)
    bonus = min(25.0, 25.0 * closeness * min(1.0, coverage))
    return {
        "bonus": round(bonus, 1),
        "target": round(target_value, 1),
        "calories": round(calories, 1),
        "delta": round(delta, 1),
        "coverage": round(coverage, 3),
    }


def recipe_identity(recipe: Any) -> str:
    if not isinstance(recipe, dict):
        return ""
    for key in (
        "groupingFunctionalId",
        "groupingId",
        "recipeFunctionalId",
        "variantFunctionalId",
        "functionalId",
        "id",
    ):
        value = _text(recipe.get(key))
        if value:
            return f"{key}:{value}"
    title = _norm(recipe.get("title"))
    return f"title:{title}" if title else ""


def ingredient_identities(recipe: Any) -> set[str]:
    if not isinstance(recipe, dict):
        return set()
    out: set[str] = set()
    for row in recipe.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        key = _text(row.get("foodKey") or row.get("key"))
        name = _norm(row.get("foodName") or row.get("name"))
        if key:
            out.add(f"k:{key}")
        elif name:
            out.add(f"n:{name}")
    return out


def select_diverse(rows: Any, count: int, *, enabled: bool = True) -> list[dict[str, Any]]:
    candidates = [deepcopy(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    target = max(1, min(int(count), 8))
    if not enabled:
        return candidates[:target]
    chosen: list[dict[str, Any]] = []
    while candidates and len(chosen) < target:
        best_index = 0
        best_score = float("-inf")
        best_penalty = 0.0
        for index, row in enumerate(candidates):
            base = _number((row.get("match") or {}).get("score")) or 0.0
            ingredients = ingredient_identities(row)
            max_overlap = 0.0
            if ingredients:
                for prior in chosen:
                    previous = ingredient_identities(prior)
                    if not previous:
                        continue
                    overlap = len(ingredients & previous) / max(1, min(len(ingredients), len(previous)))
                    max_overlap = max(max_overlap, overlap)
            penalty = 14.0 * max_overlap
            score = base - penalty
            if score > best_score:
                best_score = score
                best_index = index
                best_penalty = penalty
        picked = candidates.pop(best_index)
        match = picked.setdefault("match", {})
        match["todayDiversityPenalty"] = round(best_penalty, 1)
        match["todaySelectionScore"] = round(best_score, 1)
        chosen.append(picked)
    return chosen
