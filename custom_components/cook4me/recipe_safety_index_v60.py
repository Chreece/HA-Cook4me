from __future__ import annotations

from typing import Any, Iterable

try:
    from .ingredient_identity import identity_candidates
    from .ingredient_intelligence import (
        ALLERGEN_KEYS,
        DIET_KEYS,
        compile_recipe_masks,
        evaluate_recipe_masks,
        normalize_ingredient_profile,
    )
except ImportError:  # Standalone unit-test import via spec_from_file_location.
    import importlib.util
    from pathlib import Path

    def _load(name: str, filename: str):
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
        if spec is None or spec.loader is None:
            raise ImportError(filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    _identity = _load("cook4me_identity_safety_test", "ingredient_identity.py")
    _intelligence = _load("cook4me_intelligence_safety_test", "ingredient_intelligence.py")
    identity_candidates = _identity.identity_candidates
    ALLERGEN_KEYS = _intelligence.ALLERGEN_KEYS
    DIET_KEYS = _intelligence.DIET_KEYS
    compile_recipe_masks = _intelligence.compile_recipe_masks
    evaluate_recipe_masks = _intelligence.evaluate_recipe_masks
    normalize_ingredient_profile = _intelligence.normalize_ingredient_profile

SAFETY_INDEX_SCHEMA_VERSION = 1
_NON_FOOD = {"equipment", "other"}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _key(value: Any) -> str:
    return _text(value).casefold().replace("-", "_").replace(" ", "_")


def _global_lookup(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in payload.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        for ident in identity_candidates(row):
            lookup.setdefault(ident, row)
    return lookup


def _profile_for_global(row: dict[str, Any]) -> dict[str, Any] | None:
    classification = _key(row.get("classification"))
    if classification in _NON_FOOD:
        return None
    intelligence = row.get("intelligence") if isinstance(row.get("intelligence"), dict) else {}
    source = {
        "conceptId": row.get("conceptId") or row.get("ingredientId") or row.get("id") or row.get("key"),
        "diets": intelligence.get("diets") if isinstance(intelligence.get("diets"), dict) else row.get("diets"),
        "allergens": intelligence.get("allergens") if isinstance(intelligence.get("allergens"), dict) else row.get("allergens"),
        "evidence": intelligence.get("evidence") if isinstance(intelligence, dict) else [],
        "substitutionClass": intelligence.get("substitutionClass") if isinstance(intelligence, dict) else "",
    }
    return normalize_ingredient_profile(source)


def _profile_for_ingredient(
    ingredient: dict[str, Any],
    lookup: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    for ident in identity_candidates(ingredient):
        source = lookup.get(ident)
        if isinstance(source, dict):
            return _profile_for_global(source)
    # Missing ingredient intelligence must remain unknown, not disappear from
    # recipe safety evaluation. Only proven equipment/other rows are excluded.
    classification = _key(ingredient.get("classification"))
    if classification in _NON_FOOD:
        return None
    return normalize_ingredient_profile(ingredient)


def _recipe_profiles(
    recipe: dict[str, Any],
    lookup: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    direct = [row for row in recipe.get("ingredients") or [] if isinstance(row, dict)]
    variants = [row for row in recipe.get("variants") or [] if isinstance(row, dict)]
    ingredient_groups: list[list[dict[str, Any]]] = [direct] if direct else []
    ingredient_groups.extend(
        [row for row in variant.get("ingredients") or [] if isinstance(row, dict)]
        for variant in variants
    )
    for rows in ingredient_groups:
        for ingredient in rows:
            profile = _profile_for_ingredient(ingredient, lookup)
            if profile is not None:
                profiles.append(profile)
    return profiles


def compile_recipe_safety_index(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile strict recipe safety masks aligned to logical recipe indexes."""
    lookup = _global_lookup(payload)
    masks: list[dict[str, int]] = []
    diet_compatible: dict[str, list[int]] = {key: [] for key in DIET_KEYS}
    diet_incompatible: dict[str, list[int]] = {key: [] for key in DIET_KEYS}
    allergen_absent: dict[str, list[int]] = {key: [] for key in ALLERGEN_KEYS}
    allergen_present: dict[str, list[int]] = {key: [] for key in ALLERGEN_KEYS}
    allergen_unknown: dict[str, list[int]] = {key: [] for key in ALLERGEN_KEYS}

    diet_bits = {key: 1 << index for index, key in enumerate(DIET_KEYS)}
    allergen_bits = {key: 1 << index for index, key in enumerate(ALLERGEN_KEYS)}

    recipes = payload.get("recipes") or []
    for recipe_index, recipe in enumerate(recipes):
        if not isinstance(recipe, dict):
            recipe_masks = compile_recipe_masks([])
        else:
            recipe_masks = compile_recipe_masks(_recipe_profiles(recipe, lookup))
        masks.append(recipe_masks)

        for key, bit in diet_bits.items():
            if recipe_masks["dietCompatibleMask"] & bit:
                diet_compatible[key].append(recipe_index)
            elif recipe_masks["dietIncompatibleMask"] & bit:
                diet_incompatible[key].append(recipe_index)
        for key, bit in allergen_bits.items():
            if recipe_masks["allergenAbsentMask"] & bit:
                allergen_absent[key].append(recipe_index)
            elif recipe_masks["allergenPresentMask"] & bit:
                allergen_present[key].append(recipe_index)
            else:
                allergen_unknown[key].append(recipe_index)

    return {
        "schemaVersion": SAFETY_INDEX_SCHEMA_VERSION,
        "kind": "cook4me-recipe-safety-index",
        "recipeCount": len(recipes),
        "dietKeys": list(DIET_KEYS),
        "allergenKeys": list(ALLERGEN_KEYS),
        "masks": masks,
        "dietCompatible": diet_compatible,
        "dietIncompatible": diet_incompatible,
        "allergenAbsent": allergen_absent,
        "allergenPresent": allergen_present,
        "allergenUnknown": allergen_unknown,
        "policy": {
            "unknownIsSafe": False,
            "strictAllergyRequiresExplicitAbsence": True,
            "strictDietRequiresExplicitCompatibility": True,
            "nonFoodExcludedOnlyWhenReviewed": True,
        },
    }


def prepare_recipe_safety_index(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or int(value.get("schemaVersion") or 0) != SAFETY_INDEX_SCHEMA_VERSION
        or value.get("kind") != "cook4me-recipe-safety-index"
    ):
        return {
            "schemaVersion": SAFETY_INDEX_SCHEMA_VERSION,
            "kind": "cook4me-recipe-safety-index",
            "recipeCount": 0,
            "masks": (),
            "dietCompatible": {},
            "dietIncompatible": {},
            "allergenAbsent": {},
            "allergenPresent": {},
            "allergenUnknown": {},
            "_prepared": True,
        }

    def sets(name: str) -> dict[str, frozenset[int]]:
        source = value.get(name) if isinstance(value.get(name), dict) else {}
        return {
            _key(key): frozenset(index for index in indices if isinstance(index, int) and index >= 0)
            for key, indices in source.items()
            if isinstance(indices, list)
        }

    masks = tuple(
        dict(row) if isinstance(row, dict) else compile_recipe_masks([])
        for row in value.get("masks") or []
    )
    return {
        "schemaVersion": SAFETY_INDEX_SCHEMA_VERSION,
        "kind": "cook4me-recipe-safety-index",
        "recipeCount": max(0, int(value.get("recipeCount") or 0)),
        "masks": masks,
        "dietCompatible": sets("dietCompatible"),
        "dietIncompatible": sets("dietIncompatible"),
        "allergenAbsent": sets("allergenAbsent"),
        "allergenPresent": sets("allergenPresent"),
        "allergenUnknown": sets("allergenUnknown"),
        "policy": dict(value.get("policy") or {}),
        "_prepared": True,
    }


def allowed_recipe_indices(
    prepared: dict[str, Any],
    *,
    diet: Any = "",
    allergies: Iterable[Any] = (),
) -> frozenset[int] | None:
    """Return strict safe recipes using only precompiled set intersections."""
    if not prepared.get("_prepared"):
        prepared = prepare_recipe_safety_index(prepared)
    recipe_count = max(0, int(prepared.get("recipeCount") or 0))
    allowed: set[int] | None = None

    diet_key = _key(diet)
    if diet_key:
        diet_set = set((prepared.get("dietCompatible") or {}).get(diet_key, frozenset()))
        allowed = diet_set

    for raw in allergies:
        allergen = _key(raw)
        if not allergen:
            continue
        safe = set((prepared.get("allergenAbsent") or {}).get(allergen, frozenset()))
        allowed = safe if allowed is None else allowed & safe

    if allowed is None:
        return None
    return frozenset(index for index in allowed if 0 <= index < recipe_count)


def recipe_safety(
    prepared: dict[str, Any],
    recipe_index: int,
    *,
    diet: Any = "omnivore",
    allergies: Iterable[Any] = (),
) -> dict[str, Any]:
    if not prepared.get("_prepared"):
        prepared = prepare_recipe_safety_index(prepared)
    masks = prepared.get("masks") or ()
    if not isinstance(recipe_index, int) or recipe_index < 0 or recipe_index >= len(masks):
        return {
            "state": "unknown",
            "dietState": "unknown",
            "allergyState": "unknown",
            "strictlyAllowed": False,
        }
    return evaluate_recipe_masks(
        masks[recipe_index],
        diet=diet,
        allergies=allergies,
    )
