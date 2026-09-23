"""Keep basic ingredient-cooking guides out of automatic meal suggestions.

Presentation/selection policy only: never a dietary-safety or inventory rule.
No catalog I/O, AI calls, title substring blacklist or ingredient-ID rewrites.
"""
from __future__ import annotations

from functools import lru_cache
import math
import re
import unicodedata
from typing import Any


@lru_cache(maxsize=4096)
def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(char for char in text if not unicodedata.category(char).startswith("M"))
    return " ".join(re.findall(r"[^\W_]+", text, re.UNICODE))


def _strings(row: dict, keys: tuple[str, ...]) -> list[str]:
    return [row[key].strip() for key in keys if isinstance(row.get(key), str) and row[key].strip()]


# Full names only. Coconut water, stock, sauces, milk, garlic and onions are
# ingredients, not cooking aids. Canonical names take precedence over UI labels.
_AIDS = frozenset(_norm(name) for name in (
    "water", "water for cooking", "water (for water bath)", "water for steaming",
    "tap water", "boiling water", "cold water", "hot water", "eau", "wasser",
    "νερό", "agua", "água", "acqua", "salt", "table salt", "sea salt",
    "sel", "salz", "αλάτι", "sal", "sale", "black pepper", "ground black pepper",
    "white pepper", "poivre", "schwarzer pfeffer", "μαύρο πιπέρι", "πιπέρι",
    "salt and pepper", "salt & pepper", "sel et poivre", "salz und pfeffer",
    "αλάτι και πιπέρι", "olive oil", "extra virgin olive oil", "vegetable oil",
    "sunflower oil", "rapeseed oil", "huile d'olive", "olivenöl", "ελαιόλαδο",
))
_GUIDE_TYPES = frozenset(_norm(name) for name in (
    "cooking guide", "ingredient cooking guide", "basic ingredient",
    "ingredient preset", "ingredient cooking", "guide de cuisson",
    "οδηγός μαγειρέματος υλικού",
))
# These are the existing provider's ingredient-yield units, not servings.
_PRESET_UNITS = {"UNIT_27", "UNIT_35", "UNIT_41", "UNIT_48"}
_PRESET_LABELS = {"g", "kg", "ml", "l", "pcs", "piece", "pieces", "unit", "units", "cup", "cups"}
_BASIC_PREFIX = re.compile(r"^(?:how to cook|how to steam|how to boil|plain|steamed|boiled|cooked) ")


def _aid_name(text: str) -> str:
    value = _norm(text)
    # Some source labels embed the cooking-water amount in the name itself.
    # Strip only an explicit measure; never match substrings such as coconut water.
    measure = r"(?:ml|milliliters?|millilitres?|g|grams?)"
    value = re.sub(r"^\d+(?: \d+)? " + measure + r" (?:of )?", "", value)
    return re.sub(r" \d+(?: \d+)? " + measure + r"$", "", value)


def _food_name(text: str) -> str:
    value = _norm(text)
    value = _BASIC_PREFIX.sub("", value)
    # Small plural normalization, not fuzzy food matching. Preserve compounds:
    # rice flour, rice pudding and a rice recipe remain different from rice.
    if value.endswith("s") and not value.endswith(("ss", "us")):
        value = value[:-1]
    return value


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        result = float(str(value).replace(",", "."))
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def _preset_yield(recipe: dict, ingredient: dict) -> bool:
    """Recognize compact ingredient presets even when titles are mistranslated.

    A zero-preparation Cook4Me preset yields the ingredient's own measured
    quantity, not a number of diners. Count alone is never enough evidence.
    """
    if recipe.get("source") != "cook4me_release_catalog":
        return False
    output, times = recipe.get("yield"), recipe.get("durations")
    if not isinstance(output, dict) or not isinstance(times, dict):
        return False
    if _number(times.get("prepTime")) != 0 or not _number(times.get("cookingTime")):
        return False
    key, unit = output.get("unitKey"), output.get("unit")
    if key:
        same_unit = isinstance(key, str) and key in _PRESET_UNITS and key == ingredient.get("unitKey")
    else:
        label = _norm(unit) if isinstance(unit, str) else ""
        same_unit = label in _PRESET_LABELS and label == _norm(str(ingredient.get("unit") or ""))
    quantity = _number(output.get("quantity"))
    return bool(same_unit and quantity and quantity == _number(ingredient.get("quantity")))


def is_cooking_guide(recipe: Any) -> bool:
    """Return True only for positive evidence of a basic ingredient guide.

    Missing/sparse data stays undecided (False); the normal safety, missing-data
    and meal filters still run. Genuine simple dishes are not excluded merely
    for having few ingredients. A guide never becomes eligible as a fallback.
    """
    if not isinstance(recipe, dict):
        return False
    for field in ("recipeType", "recipeKind"):
        kind = recipe.get(field)
        names = _strings(kind, ("name", "key")) if isinstance(kind, dict) else [kind] if isinstance(kind, str) else []
        if any(_norm(name) in _GUIDE_TYPES for name in names):
            return True
    ingredients = recipe.get("ingredients")
    if not isinstance(ingredients, list) or not ingredients:
        return False
    foods: list[dict] = []
    for item in ingredients:
        if not isinstance(item, dict):
            return False
        canonical = _strings(item, ("canonicalName",))
        names = canonical or _strings(item, ("foodName", "name", "originalName"))
        if not names:
            return False  # An unresolved row could be another real ingredient.
        if _aid_name(names[0]) in _AIDS:
            continue
        identities = set(_strings(item, ("ingredientId", "foodKey", "key", "id")))
        labels = {_food_name(name) for name in names} - {""}
        if not labels:
            return False
        prior = next((food for food in foods if identities & food["ids"] or labels & food["names"]), None)
        if prior is None:
            foods.append({"ids": identities, "names": labels, "row": item})
        else:
            prior["ids"].update(identities)
            prior["names"].update(labels)
    if len(foods) != 1:
        return False
    titles = _strings(recipe, ("canonicalName", "originalTitle", "title"))
    if any(_food_name(title) in foods[0]["names"] for title in titles):
        return True
    return _preset_yield(recipe, foods[0]["row"])


def meal_candidates(rows: Any) -> list[dict]:
    """Filter without cloning, mutating, reordering or changing source identity."""
    return [row for row in rows if isinstance(row, dict) and not is_cooking_guide(row)] if isinstance(rows, (list, tuple)) else []
