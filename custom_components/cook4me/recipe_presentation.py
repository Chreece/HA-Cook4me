"""Display metadata without changing recipe identity or ingredient evidence."""
from copy import deepcopy

from . import release_catalog
from .recipe_logic import dietary_flags
from .today_logic import offline_meal_types


def present_recipe(recipe, language):
    row = deepcopy(recipe)
    for item in row.get("ingredients") or []:
        if not isinstance(item, dict):
            continue
        item["originalName"] = item.get("originalName") or item.get("name") or item.get("foodName") or ""
        item["displayName"] = release_catalog.ingredient_display_name(item, language) or item["originalName"]
        item["displayLanguage"] = language
    row["dietary"] = dietary_flags(row)
    row["mealTypes"] = row.get("mealTypes") or offline_meal_types(row)
    row["presentationLanguage"] = language
    return row
