from __future__ import annotations

from copy import deepcopy
import re
import unicodedata
from typing import Any


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


def recipe_storage_key(recipe: Any) -> str:
    """Return one stable key for official and local recipes."""
    if not isinstance(recipe, dict):
        return ""
    for key, prefix in (
        ("groupingFunctionalId", "g"),
        ("sendGroupingFunctionalId", "g"),
        ("id", "local"),
        ("recipeFunctionalId", "r"),
        ("variantFunctionalId", "v"),
        ("displayVariantId", "v"),
        ("searchVariantId", "v"),
    ):
        value = _text(recipe.get(key))
        if value:
            return f"{prefix}:{value}"
    title = _norm(recipe.get("title"))
    language = _text(recipe.get("language") or recipe.get("sourceLanguage")).lower()
    return f"title:{language}:{title}" if title else ""


def recipe_snapshot(recipe: Any) -> dict[str, Any]:
    """Keep enough recipe data to render/reopen a favourite without cloning caches."""
    if not isinstance(recipe, dict):
        return {}
    allowed = (
        "id",
        "source",
        "title",
        "cover",
        "language",
        "sourceLanguage",
        "servings",
        "groupSize",
        "yield",
        "groupingFunctionalId",
        "recipeFunctionalId",
        "variantFunctionalId",
        "displayVariantId",
        "searchVariantId",
        "sendVariantId",
        "sendGroupingFunctionalId",
        "sendRecipeFunctionalId",
        "sendable",
        "ingredients",
        "steps",
        "courses",
        "occasions",
        "durations",
        "difficulty",
        "recipeType",
        "notes",
        "tags",
    )
    out = {key: deepcopy(recipe[key]) for key in allowed if key in recipe}
    if recipe.get("match"):
        out["match"] = deepcopy(recipe["match"])
    return out


def ingredient_identity(item: Any) -> str:
    if isinstance(item, dict):
        key = _text(item.get("foodKey") or item.get("key"))
        if key:
            return f"k:{key}"
        name = _norm(
            item.get("foodName")
            or item.get("name")
            or item.get("applicationDescription")
        )
    else:
        name = _norm(item)
    return f"n:{name}" if name else ""


def ingredient_name(item: Any) -> str:
    if isinstance(item, dict):
        return _text(
            item.get("foodName")
            or item.get("name")
            or item.get("applicationDescription")
            or item.get("applianceDescription")
        )
    return _text(item)


def ingredient_matches(left: Any, right: Any) -> bool:
    left_id = ingredient_identity(left)
    right_id = ingredient_identity(right)
    if left_id and right_id and left_id == right_id:
        return True
    return bool(_norm(ingredient_name(left)) and _norm(ingredient_name(left)) == _norm(ingredient_name(right)))


def ingredient_coverage(recipe: Any, ingredient: Any) -> dict[str, Any]:
    """Return stock coverage metadata already proven by quantity feasibility."""
    if not isinstance(recipe, dict):
        return {"percent": None, "status": "unknown", "coverage": None}
    target = ingredient_identity(ingredient)
    target_name = _norm(ingredient_name(ingredient))
    match = recipe.get("match") if isinstance(recipe.get("match"), dict) else {}
    rows = match.get("quantityAvailability") if isinstance(match.get("quantityAvailability"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = ingredient_identity(row)
        row_name = _norm(row.get("name"))
        if (target and row_id == target) or (target_name and row_name == target_name):
            coverage = row.get("coverage")
            try:
                fraction = float(coverage)
            except (TypeError, ValueError):
                fraction = None
            return {
                "percent": None if fraction is None else max(0, min(100, round(fraction * 100))),
                "coverage": fraction,
                "status": _text(row.get("status")) or "unknown",
                "requiredQuantity": row.get("requiredQuantity"),
                "requiredUnit": row.get("requiredUnit"),
                "availableQuantity": row.get("availableQuantity"),
                "availableUnit": row.get("availableUnit"),
                "missingQuantity": row.get("missingQuantity"),
                "missingUnit": row.get("missingUnit"),
                "unlimited": bool(row.get("unlimited")),
            }
    availability = match.get("ingredientAvailability") if isinstance(match.get("ingredientAvailability"), list) else []
    for row in availability:
        if not isinstance(row, dict):
            continue
        if ingredient_matches(row, ingredient):
            status = _text(row.get("status")) or "unknown"
            if status in {"at_home", "staple"}:
                return {"percent": 100, "coverage": 1.0, "status": status}
            if status == "missing":
                return {"percent": 0, "coverage": 0.0, "status": status}
    return {"percent": None, "coverage": None, "status": "unknown"}
