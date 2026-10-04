"""Common recipe controls for Today, Week and Official; no network/AI calls."""
from copy import deepcopy
import math

from .today_logic import recipe_matches_meal_types, offline_meal_types
from .food_intelligence import nutrition_goal_bonus
from .diet_profiles import exclusions, text_list
from .nutrient_targets import MEAL_TYPES, TARGETS, has_targets, normalize_scoped_targets, target_bonus


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
    if "dietProfile" in data:
        source = str(data.get("dietProfile") or "manual")[:90]
        result["dietProfile"] = source if source in {"manual", "household"} or source.startswith("member:") else "manual"
        result["excludedIngredients"] = exclusions(data.get("excludedIngredients"))
        result["excludedTerms"] = text_list(data.get("excludedTerms"))
    scoped = normalize_scoped_targets(data.get("nutrientTargets"))
    if scoped is not None:
        result["nutrientTargets"] = scoped
    for key, maximum in TARGETS.items():
        result[key] = number(data.get(key), maximum)
    result["diet"] = data.get("diet") if data.get("diet") in {"profile", "omnivore", "pescatarian", "vegetarian", "vegan"} else "profile"
    result["nutritionGoal"] = str(data.get("nutritionGoal") or "balanced")[:40]
    for key, maximum in (("calorieTarget", 10000), ("proteinTarget", 1000), ("fiberTarget", 1000), ("maxCost", 10000), ("maxMissing", 20), ("avoidRecentDays", 90), ("calorieTolerance", 100)):
        result[key] = number(data.get(key), maximum)
    for key in ("onlyHome", "preferExpiring"):
        result[key] = bool(data.get(key, key == "preferExpiring"))
    result["seasonalIngredients"] = data.get("seasonalIngredients") is True
    result["currency"] = str(data.get("currency") or "EUR").upper()[:3]
    return result


def normalize_preferences(value):
    data = value if isinstance(value, dict) else {}
    result = {}
    if "lastTab" in data:
        result["lastTab"] = data["lastTab"] if data["lastTab"] in TABS else "today"
    if "filters" in data:
        result["filters"] = normalize_filters(data["filters"])
    if isinstance(data.get("filtersByView"), dict):
        result["filtersByView"] = {
            tab: normalize_filters(filters)
            for tab, filters in data["filtersByView"].items()
            if tab in TABS and isinstance(filters, dict)
        }
    return result


def merge_preferences(existing, patch):
    """Merge independent view updates without replacing another view's filters."""
    current = deepcopy(existing) if isinstance(existing, dict) else {}
    normalized = normalize_preferences(patch)
    if "filtersByView" in normalized:
        previous = current.get("filtersByView")
        normalized["filtersByView"] = {
            **(previous if isinstance(previous, dict) else {}),
            **normalized["filtersByView"],
        }
    return {**current, **normalized}


def daily_targets(value):
    """Return only explicit full-day targets; legacy per-serving targets never become daily targets."""
    settings = normalize_filters(value)
    scoped = settings.get("nutrientTargets")
    if not isinstance(scoped, dict):
        return {}
    return deepcopy(scoped.get("daily") or {})


def missing_ingredient_count(match):
    """Count genuinely absent ingredient identities, not quantity uncertainty.

    quantityShortages answers whether the amount on hand is sufficient. Max
    missing ingredients is about ingredient presence. A present ingredient with
    an unknown recipe amount, stock amount, or incompatible unit therefore does
    not consume a missing slot.
    """
    if not isinstance(match, dict):
        return 0
    availability = match.get("ingredientAvailability")
    if isinstance(availability, list):
        seen = set()
        for row in availability:
            if not isinstance(row, dict) or row.get("status") != "missing":
                continue
            key = str(row.get("key") or "").strip()
            name = " ".join(str(row.get("name") or "").casefold().split())
            marker = ("k", key) if key else ("n", name)
            if key or name:
                seen.add(marker)
        return len(seen)
    seen = {
        " ".join(str(value or "").casefold().split())
        for value in match.get("missingIngredients") or []
        if str(value or "").strip()
    }
    return len(seen)


def home_missing_filter_allows(match, *, only_home=False, max_missing=None):
    """Apply Home/Max-missing controls with literal ingredient semantics.

    Blank Max missing keeps the historical strict quantity-aware onlyHome
    behavior. Zero is also strict. Positive values allow at most N genuinely
    absent ingredients. Quantity uncertainty for ingredients already present
    does not count as absence.
    """
    if not isinstance(match, dict):
        return not only_home and max_missing is None
    count = missing_ingredient_count(match)
    if max_missing is not None:
        try:
            limit = max(0, int(float(max_missing)))
        except (TypeError, ValueError):
            limit = 0
        if only_home and limit == 0:
            return bool(match.get("fullyAvailableByQuantity"))
        return count <= limit
    if only_home:
        return bool(match.get("fullyAvailableByQuantity"))
    return True


def recipe_target_scope(settings, recipe):
    """Pick the applicable meal-specific target set for one recipe."""
    scoped = settings.get("nutrientTargets")
    if not isinstance(scoped, dict):
        return ({key: settings.get(key) for key in TARGETS}, "legacy")
    meals = scoped.get("mealTypes") if isinstance(scoped.get("mealTypes"), dict) else {}
    preferred = list(settings.get("mealTypes") or [])
    for meal_type in (*preferred, *MEAL_TYPES):
        if meal_type not in MEAL_TYPES:
            continue
        targets = meals.get(meal_type)
        if has_targets(targets) and recipe_matches_meal_types(recipe, [meal_type]):
            return (targets, meal_type)
    return ({}, None)


def seasonal_ingredient_visible(ingredient, country, month):
    """Mirror the opt-in catalog season view for one materialized recipe ingredient."""
    if not isinstance(ingredient, dict) or type(month) is not int or not 1 <= month <= 12:
        return True
    season = (ingredient.get("lifecycle") or {}).get("seasonality") or {}
    if season.get("status") != "reviewed":
        return True
    country = str(country or "").strip().upper()
    region = next((
        row for row in season.get("regions") or []
        if isinstance(row, dict) and row.get("country") == country
    ), None)
    months = region.get("months") if region else None
    if not isinstance(months, list) or not months or any(
            type(value) is not int or not 1 <= value <= 12 for value in months):
        return True
    return month in months


def recipe_seasonally_available(recipe, country, month):
    """A recipe survives when none of its reviewed ingredients is out of season."""
    if not isinstance(recipe, dict):
        return True
    return all(
        seasonal_ingredient_visible(ingredient, country, month)
        for ingredient in recipe.get("ingredients") or []
    )


def apply_filters(rows, filters, *, ingredient_groups=None, cost=None, nutrition=None, recent=(),
                  score_targets=True, progress=None, season_country="", season_month=None):
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
        if settings["seasonalIngredients"] and not recipe_seasonally_available(
                source, season_country, season_month):
            continue
        match = source.get("match") or {}
        if match.get("requiresSubstitutions") and (
                settings["onlyHome"] or settings["maxCost"] is not None):
            # Replacement quantity/price cannot be borrowed from the original.
            # Max-missing alone is not a substitution filter.
            continue
        if not home_missing_filter_allows(
                match,
                only_home=settings["onlyHome"],
                max_missing=settings["maxMissing"],
        ):
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
            targets, target_scope = recipe_target_scope(settings, row)
            target_hint = target_bonus(
                nutrients,
                targets,
                calorie_tolerance_fraction=(settings["calorieTolerance"] or 25) / 100,
            )
            score += float(target_hint.get("bonus") or 0)
            if target_scope:
                match["nutrientTargetScope"] = target_scope
                match["nutrientTargetBonus"] = round(float(target_hint.get("bonus") or 0), 2)
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
