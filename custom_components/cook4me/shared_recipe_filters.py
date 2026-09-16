"""Common recipe controls for Today, Week and Official; no network/AI calls."""
from copy import deepcopy
import math

from .today_logic import recipe_matches_meal_types, calorie_target_bonus, offline_meal_types
from .food_intelligence import nutrition_goal_bonus


TABS = {"today", "week", "official", "book", "mine", "profile", "shopping", "ai"}


def number(value, maximum):
    try:
        result = float(value)
        return result if math.isfinite(result) and 0 <= result <= maximum else None
    except (TypeError, ValueError):
        return None


def normalize_filters(value):
    data = value if isinstance(value, dict) else {}
    result = {}
    for key in ("languages", "mealTypes", "ingredients"):
        rows = data.get(key)
        result[key] = list(dict.fromkeys(str(x)[:160] for x in rows if isinstance(x, str)))[:200] if isinstance(rows, list) else []
    result["diet"] = data.get("diet") if data.get("diet") in {"profile", "omnivore", "pescatarian", "vegetarian", "vegan"} else "profile"
    result["nutritionGoal"] = str(data.get("nutritionGoal") or "balanced")[:40]
    for key, maximum in (("calorieTarget", 10000), ("proteinTarget", 1000), ("fiberTarget", 1000), ("maxCost", 10000), ("maxMissing", 20), ("avoidRecentDays", 90), ("calorieTolerance", 100)):
        result[key] = number(data.get(key), maximum)
    for key in ("onlyHome", "preferExpiring"):
        result[key] = bool(data.get(key, key == "preferExpiring"))
    result["currency"] = str(data.get("currency") or "EUR").upper()[:3]
    return result


def normalize_preferences(value):
    data = value if isinstance(value, dict) else {}
    result = {}
    if "lastTab" in data:
        result["lastTab"] = data["lastTab"] if data["lastTab"] in TABS else "today"
    if "filters" in data:
        result["filters"] = normalize_filters(data["filters"])
    return result


def apply_filters(rows, filters, *, ingredient_groups=None, cost=None, nutrition=None, recent=(), score_targets=True, progress=None):
    """Filter before pagination/selection. Unknown costs never count as free."""
    settings = normalize_filters(filters)
    groups = ingredient_groups or {}
    selected = [set(groups.get(key, [key.removeprefix("k:").removeprefix("i:")])) for key in settings["ingredients"]]
    result = []
    for completed, source in enumerate(rows, 1):
        if progress and (completed == 1 or completed % 25 == 0):
            progress("nutrition", completed=completed-1, total=len(rows))
        if settings["mealTypes"] and not recipe_matches_meal_types(source, settings["mealTypes"]):
            continue
        if source.get("displayFamilyId") in recent or source.get("displayVariantId") in recent:
            continue
        match = source.get("match") or {}
        if match.get("requiresSubstitutions") and (settings["onlyHome"] or
                settings["maxCost"] is not None or settings["maxMissing"] is not None):
            # A replacement's quantity/price cannot be borrowed from the original.
            continue
        if settings["onlyHome"] and not match.get("fullyAvailableByQuantity"):
            continue
        if settings["maxMissing"] is not None and len(match.get("quantityShortages") or []) > settings["maxMissing"]:
            continue
        identities = {str(row.get(key) or "") for row in source.get("ingredients", []) if isinstance(row, dict) for key in ("ingredientId", "key", "foodKey", "id")}
        if any(not aliases.intersection(identities) for aliases in selected):
            continue
        row = deepcopy(source)
        if not any(row.get(key) for key in ("mealTypes", "courses", "occasions", "recipeType")):
            row["mealTypes"] = offline_meal_types(row)
            row["mealTypeSource"] = "canonical_title" if row["mealTypes"] else "unknown"
        if settings["maxCost"] is not None:
            estimate = cost(row) if cost else row.get("cost") or {}
            amounts = estimate.get("perServingByCurrency") or {}
            amount = number(amounts.get(settings["currency"]), 1e9)
            if amount is None or estimate.get("coverage", 0) < 1 or any(code != settings["currency"] and val for code, val in amounts.items()) or amount > settings["maxCost"]:
                continue
            row["cost"] = estimate
        match = row.setdefault("match", {})
        score = float(match.get("score") or 0)
        if not settings["preferExpiring"] and not match.get("todayExpiryBonusSuppressed"):
            score -= float(match.get("expiryBonus") or 0)
        nutrients = nutrition(row) if nutrition else row.get("nutrition") or row.get("catalogNutrition") or {}
        if not nutrients.get("totals") and not nutrients.get("perServing"):
            nutrients = row.get("catalogNutrition") or nutrients
        row["nutrition"] = nutrients
        if score_targets:
            score += float(nutrition_goal_bonus(nutrients, settings["nutritionGoal"]).get("bonus") or 0)
            score += float(calorie_target_bonus(nutrients, settings["calorieTarget"], tolerance_fraction=(settings["calorieTolerance"] or 25)/100).get("bonus") or 0)
        for key, target_key in (("protein", "proteinTarget"), ("fiber", "fiberTarget")):
            target = settings[target_key]
            actual = number((nutrients.get("perServing") or {}).get(key), 1e6)
            if target and actual is not None:
                score += 10 * max(-1, 1 - abs(actual-target)/target)
        match["score"] = round(score, 2)
        result.append(row)
    if progress:
        progress("nutrition", completed=len(rows), total=len(rows))
    return sorted(result, key=lambda row: row.get("match", {}).get("score", 0), reverse=True)


def ingredient_aliases(language):
    from .release_catalog import ingredient_choices
    result = {}
    for row in ingredient_choices(language):
        aliases = row.get("sourceIngredientIds") or [row["ingredientId"]]
        for key in (row.get("key"), row.get("foodKey"), row["ingredientId"]):
            if key:
                result["k:"+str(key)] = aliases
                result["i:"+str(key)] = aliases
    return result
