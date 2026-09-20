"""Canonical scoped nutrient-target model and scoring helpers."""
from __future__ import annotations

import math
from typing import Any

MEAL_TYPES = ("breakfast", "starter", "salad", "soup", "main", "side", "dessert", "snack")
TARGETS = {
    "calorieTarget": 10000,
    "proteinTarget": 1000,
    "carbsTarget": 2000,
    "fatTarget": 1000,
    "saturatedFatTarget": 1000,
    "sugarsTarget": 1000,
    "fiberTarget": 1000,
    "saltTarget": 100,
    "sodiumTarget": 100,
}
TARGET_ALIASES = {
    "calorieTarget": ("energyKcal", "calories", "energy"),
    "proteinTarget": ("protein", "proteinG"),
    "carbsTarget": ("carbohydrates", "carbs", "carbohydrateG"),
    "fatTarget": ("fat", "fatG"),
    "saturatedFatTarget": ("saturatedFat", "saturatedFatG"),
    "sugarsTarget": ("sugars", "sugarsG", "sugarG"),
    "fiberTarget": ("fiber", "fiberG"),
    "saltTarget": ("salt", "saltG"),
    "sodiumTarget": ("sodium", "sodiumG"),
}


def _number(value: Any, maximum: float) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and 0 <= number <= maximum else None


def normalize_target_values(value: Any) -> dict[str, float | None]:
    data = value if isinstance(value, dict) else {}
    return {key: _number(data.get(key), maximum) for key, maximum in TARGETS.items()}


def has_targets(value: Any) -> bool:
    return isinstance(value, dict) and any(value.get(key) is not None for key in TARGETS)


def normalize_scoped_targets(value: Any) -> dict[str, Any] | None:
    """Normalize explicit daily and meal-type targets.

    None means the profile still uses the legacy flat per-serving target model.
    An explicit empty mapping means scoped targets are enabled with no target set.
    """
    if not isinstance(value, dict):
        return None
    daily = normalize_target_values(value.get("daily"))
    raw_meals = value.get("mealTypes") if isinstance(value.get("mealTypes"), dict) else {}
    meals: dict[str, dict[str, float | None]] = {}
    for meal_type in MEAL_TYPES:
        targets = normalize_target_values(raw_meals.get(meal_type))
        if has_targets(targets):
            meals[meal_type] = targets
    return {"daily": daily, "mealTypes": meals}


def nutrition_values(nutrition: Any) -> dict[str, float]:
    if not isinstance(nutrition, dict):
        return {}
    raw = nutrition.get("perServing")
    if not isinstance(raw, dict) or not raw:
        raw = nutrition.get("totals")
    if not isinstance(raw, dict) or not raw:
        raw = nutrition
    result: dict[str, float] = {}
    for target_key, aliases in TARGET_ALIASES.items():
        for alias in aliases:
            value = _number(raw.get(alias), 1e9)
            if value is not None:
                result[target_key] = value
                break
    return result


def target_bonus(
    nutrition: Any,
    targets: Any,
    *,
    calorie_tolerance_fraction: float = 0.25,
) -> dict[str, Any]:
    """Score one recipe against one configured target scope."""
    normalized = normalize_target_values(targets)
    values = nutrition_values(nutrition)
    score = 0.0
    applied: dict[str, dict[str, float]] = {}

    calorie_target = normalized["calorieTarget"]
    calories = values.get("calorieTarget")
    coverage = _number(nutrition.get("coverage"), 1.0) if isinstance(nutrition, dict) else None
    if calorie_target is not None and calorie_target > 0 and calories is not None and (coverage is None or coverage >= 0.5):
        tolerance = max(25.0, calorie_target * max(0.05, min(float(calorie_tolerance_fraction), 1.0)))
        delta = calories - calorie_target
        closeness = max(0.0, 1.0 - abs(delta) / tolerance)
        bonus = 25.0 * closeness * (min(1.0, coverage) if coverage is not None else 1.0)
        score += bonus
        applied["calorieTarget"] = {"actual": calories, "target": calorie_target, "bonus": round(bonus, 3)}

    for key in TARGETS:
        if key == "calorieTarget":
            continue
        target = normalized[key]
        actual = values.get(key)
        if target is None or target <= 0 or actual is None:
            continue
        bonus = 10.0 * max(-1.0, 1.0 - abs(actual - target) / max(target, 1.0))
        score += bonus
        applied[key] = {"actual": actual, "target": target, "bonus": round(bonus, 3)}
    return {"bonus": round(score, 3), "applied": applied}


def daily_progress_bonus(
    existing_nutrition: Any,
    candidate_nutrition: Any,
    daily_targets: Any,
    *,
    fraction: float,
) -> dict[str, Any]:
    """Reward a projected day's nutrient totals toward the expected progress point."""
    targets = normalize_target_values(daily_targets)
    rows = existing_nutrition if isinstance(existing_nutrition, (list, tuple)) else []
    projected = {key: 0.0 for key in TARGETS}
    known = {key: False for key in TARGETS}
    for nutrition in [*rows, candidate_nutrition]:
        values = nutrition_values(nutrition)
        for key, value in values.items():
            projected[key] += value
            known[key] = True

    progress = max(0.01, min(float(fraction), 1.0))
    score = 0.0
    applied: dict[str, dict[str, float]] = {}
    for key, target in targets.items():
        if target is None or target <= 0 or not known[key]:
            continue
        expected = target * progress
        actual = projected[key]
        weight = 14.0 if key == "calorieTarget" else 6.0
        bonus = weight * max(-1.0, 1.0 - abs(actual - expected) / max(expected, 1.0))
        score += bonus
        applied[key] = {
            "actual": round(actual, 3),
            "expected": round(expected, 3),
            "dailyTarget": round(target, 3),
            "bonus": round(bonus, 3),
        }
    return {"bonus": round(score, 3), "fraction": round(progress, 4), "applied": applied}
