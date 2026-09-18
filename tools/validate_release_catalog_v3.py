#!/usr/bin/env python3
"""Fail-closed validator for the final immutable Cook4Me runtime catalog."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any

_REQUIRED_ZERO_SOURCE_FIELDS = (
    "unresolvedProviderFoods",
    "unresolvedKeylessSemantics",
    "unresolvedRecipeGroups",
    "providerTranslationConflicts",
    "ingredientMappingFailures",
    "missingGroupReviews",
    "unresolvedProviderVariants",
)
_SECRET_KEY_PATTERN = re.compile(
    r"(?:access[_-]?token|refresh[_-]?token|authorization|password|api[_-]?key|client[_-]?secret)",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _secret_paths(value: Any, path: str = "$", out: list[str] | None = None) -> list[str]:
    out = out if out is not None else []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}"
            if _SECRET_KEY_PATTERN.search(key_text):
                out.append(child_path)
            _secret_paths(child, child_path, out)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _secret_paths(child, f"{path}[{index}]", out)
    return out


def validate(payload: dict[str, Any], *, require_complete: bool = True) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if int(payload.get("schemaVersion") or 0) != 1:
        errors.append("schemaVersion must be 1")
    if not _text(payload.get("catalogVersion")):
        errors.append("catalogVersion is required")
    if require_complete and payload.get("complete") is not True:
        errors.append("catalog is not marked complete")

    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    if int(source.get("auditedCatalogCount") or 0) != 28:
        errors.append("auditedCatalogCount must be 28")
    catalogs = source.get("catalogs") if isinstance(source.get("catalogs"), list) else []
    if len(catalogs) != 28:
        errors.append(f"source.catalogs must contain 28 records, got {len(catalogs)}")
    for field in _REQUIRED_ZERO_SOURCE_FIELDS:
        if int(source.get(field) or 0) != 0:
            errors.append(f"source.{field} must be zero")
    if source.get("providerIngredientIdentityAuthoritative") is not True:
        errors.append("providerIngredientIdentityAuthoritative must be true")
    if source.get("keylessFoodIdentityLocalOnly") is not True:
        errors.append("keylessFoodIdentityLocalOnly must be true")
    if source.get("translationNeverMergesRecipeGroups") is not True:
        errors.append("translationNeverMergesRecipeGroups must be true")
    if source.get("secretsPersisted") is not False:
        errors.append("secretsPersisted must be false")
    if source.get("nutritionRequiredForComplete") is not False:
        if int(source.get("nutritionMissingCount") or 0) != 0:
            errors.append("required nutrition is incomplete")

    ingredients = payload.get("ingredients") if isinstance(payload.get("ingredients"), list) else []
    recipes = payload.get("recipes") if isinstance(payload.get("recipes"), list) else []
    if not ingredients:
        errors.append("global ingredient table is empty")
    if not recipes:
        errors.append("recipe table is empty")

    ingredient_ids: list[str] = []
    provider_keys: set[str] = set()
    local_ids: set[str] = set()
    for index, row in enumerate(ingredients):
        if not isinstance(row, dict):
            errors.append(f"ingredients[{index}] is not an object")
            continue
        ident = _text(row.get("id"))
        if not ident:
            errors.append(f"ingredients[{index}] has no id")
            continue
        ingredient_ids.append(ident)
        kind = _text(row.get("identityKind"))
        if kind == "provider":
            if _text(row.get("key")) != ident:
                errors.append(f"provider ingredient {ident} must have matching key")
            if not ident.startswith("M_FOOD_"):
                errors.append(f"provider ingredient {ident} is not an M_FOOD identity")
            provider_keys.add(ident)
        elif kind == "local-keyless":
            if not ident.startswith("local:"):
                errors.append(f"local keyless ingredient {ident} must use local: identity")
            if _text(row.get("key")):
                errors.append(f"local keyless ingredient {ident} must not have provider key")
            if _text(row.get("classification")) != "food":
                errors.append(f"local global ingredient {ident} must be classified food")
            local_ids.add(ident)
        else:
            errors.append(f"ingredient {ident} has unknown identityKind {kind!r}")
        if not _text(row.get("canonicalName")):
            errors.append(f"ingredient {ident} has no canonicalName")
        if source.get("nutritionRequiredForComplete") is not False:
            nutrition = row.get("nutrition") if isinstance(row.get("nutrition"), dict) else {}
            if nutrition.get("basis") != "per100g" or not isinstance(nutrition.get("values"), dict) or not nutrition.get("values"):
                errors.append(f"ingredient {ident} has no required per100g nutrition")

    duplicates = sorted(key for key, count in Counter(ingredient_ids).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate ingredient ids: {duplicates[:10]}")
    ingredient_id_set = set(ingredient_ids)

    group_ids: list[str] = []
    variant_ids: list[str] = []
    dangling: list[str] = []
    local_lines_with_provider_key: list[str] = []
    equipment_global_refs: list[str] = []
    for g_index, group in enumerate(recipes):
        if not isinstance(group, dict):
            errors.append(f"recipes[{g_index}] is not an object")
            continue
        group_id = _text(group.get("groupingFunctionalId"))
        if not group_id:
            errors.append(f"recipes[{g_index}] has no groupingFunctionalId")
            continue
        group_ids.append(group_id)
        if not _text(group.get("canonicalName")):
            errors.append(f"recipe group {group_id} has no canonicalName")
        variants = group.get("variants") if isinstance(group.get("variants"), list) else []
        if not variants:
            errors.append(f"recipe group {group_id} has no variants")
            continue
        for variant in variants:
            if not isinstance(variant, dict):
                errors.append(f"recipe group {group_id} contains non-object variant")
                continue
            variant_id = _text(variant.get("variantId"))
            if not variant_id:
                errors.append(f"recipe group {group_id} contains variant without variantId")
                continue
            variant_ids.append(variant_id)
            if _text(variant.get("groupingFunctionalId")) != group_id:
                errors.append(f"variant {variant_id} groupingFunctionalId mismatch")
            if not _text(variant.get("originalTitle")):
                errors.append(f"variant {variant_id} has no originalTitle")
            if not _text(variant.get("originalLanguage")):
                errors.append(f"variant {variant_id} has no originalLanguage")
            for line in variant.get("ingredients") or []:
                if not isinstance(line, dict):
                    continue
                classification = _text(line.get("classification"))
                ident = _text(line.get("ingredientId"))
                key = _text(line.get("key"))
                if classification in {"equipment", "other"}:
                    if ident:
                        equipment_global_refs.append(f"{variant_id}:{ident}")
                    if key:
                        errors.append(f"non-food line in {variant_id} carries provider key {key}")
                    continue
                if not ident:
                    errors.append(f"food ingredient line in {variant_id} has no ingredientId")
                    continue
                if ident not in ingredient_id_set:
                    dangling.append(f"{variant_id}:{ident}")
                if ident.startswith("local:") and key:
                    local_lines_with_provider_key.append(f"{variant_id}:{ident}:{key}")
                if ident.startswith("M_FOOD_") and key != ident:
                    errors.append(f"provider line {variant_id}:{ident} must preserve matching key")

    duplicate_groups = sorted(key for key, count in Counter(group_ids).items() if count > 1)
    duplicate_variants = sorted(key for key, count in Counter(variant_ids).items() if count > 1)
    if duplicate_groups:
        errors.append(f"duplicate groupingFunctionalIds: {duplicate_groups[:10]}")
    if duplicate_variants:
        errors.append(f"duplicate variantIds: {duplicate_variants[:10]}")
    if dangling:
        errors.append(f"dangling ingredient references: {dangling[:10]}")
    if equipment_global_refs:
        errors.append(f"equipment/other lines reference global ingredients: {equipment_global_refs[:10]}")
    if local_lines_with_provider_key:
        errors.append(f"local ingredient lines carry provider keys: {local_lines_with_provider_key[:10]}")

    secret_paths = _secret_paths(payload)
    if secret_paths:
        errors.append(f"secret-like keys present: {secret_paths[:10]}")

    expected_nutrition = int(source.get("nutritionRequiredCount") or len(ingredients))
    resolved_nutrition = int(source.get("nutritionResolvedCount") or 0)
    if source.get("nutritionRequiredForComplete") is not False:
        if expected_nutrition != len(ingredients):
            errors.append("nutritionRequiredCount must equal global ingredient count")
        if resolved_nutrition != len(ingredients):
            errors.append("nutritionResolvedCount must equal global ingredient count")
    elif resolved_nutrition < len(ingredients):
        warnings.append("catalog uses explicit missing-nutrition maintenance escape hatch")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "ingredientCount": len(ingredients),
            "providerIngredientCount": len(provider_keys),
            "localKeylessFoodCount": len(local_ids),
            "recipeGroupCount": len(recipes),
            "variantCount": len(variant_ids),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog")
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    result = validate(
        _load(Path(args.catalog).expanduser()),
        require_complete=not args.allow_incomplete,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
