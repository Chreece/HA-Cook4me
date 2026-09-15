"""Choose varied weekly meals without merging catalog or device identities."""
import re

from .catalog_presentation import clean_name, name_key
from .today_logic import recipe_identity

_TITLE_FILLERS = {"a", "an", "the", "and", "with", "in", "of", "on", "to", "for"}


def signature(recipe):
    recipe = recipe if isinstance(recipe, dict) else {}
    title = recipe.get("canonicalName") or recipe.get("originalTitle") or recipe.get("title") or ""
    words = frozenset(re.findall(r"\w+", name_key(title))) - _TITLE_FILLERS
    foods = set()
    for item in recipe.get("ingredients") or []:
        if not isinstance(item, dict):
            continue
        canonical = item.get("canonicalName")
        key = item.get("ingredientId") or item.get("foodKey") or item.get("key")
        if canonical:
            foods.add("food:" + name_key(clean_name(canonical)))
        elif key:
            foods.add("id:" + str(key))
        elif item.get("name") or item.get("foodName"):
            foods.add("name:" + name_key(clean_name(item.get("name") or item.get("foodName"))))
    return {
        "family": str(recipe.get("displayFamilyId") or ""),
        "identity": recipe_identity(recipe),
        "title": words,
        "foods": frozenset(foods),
        "cover": str(recipe.get("cover") or "").split("?", 1)[0],
    }


def similar(left, right):
    if left["family"] and left["family"] == right["family"]:
        return True
    if left["identity"] and left["identity"] == right["identity"]:
        return True
    a, b = left["foods"], right["foods"]
    if a and a == b and left["title"] and left["title"] == right["title"]:
        return True  # Also covers simple one/two-ingredient dishes.
    # At least three matching foods and 80% of the smaller ingredient set.
    # Regional additions and serving amounts do not create weekly variety.
    overlap = len(a & b)
    if overlap < 3 or overlap / min(len(a), len(b)) < 0.8:
        return False
    titles = left["title"] | right["title"]
    title_overlap = len(left["title"] & right["title"]) / len(titles) if titles else 0
    return title_overlap >= 0.5 or bool(left["cover"] and left["cover"] == right["cover"])


def already_planned(candidate, selected):
    return any(similar(candidate, other) for other in selected)
