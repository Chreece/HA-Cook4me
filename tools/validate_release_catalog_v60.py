#!/usr/bin/env python3
"""Fail-closed offline validator for the immutable Cook4Me v60 catalog."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
if str(COMPONENT) not in sys.path:
    sys.path.insert(0, str(COMPONENT))

import catalog_search_index  # type: ignore  # noqa: E402
import recipe_safety_index_v60  # type: ignore  # noqa: E402


_ALLOWED_SOURCE_LOCAL_CLASSIFICATIONS = {"food", "equipment", "other", "ambiguous"}
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


def _secret_paths(
    value: Any, path: str = "$", out: list[str] | None = None
) -> list[str]:
    out = out if out is not None else []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _SECRET_KEY_PATTERN.search(str(key)):
                out.append(child_path)
            _secret_paths(child, child_path, out)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _secret_paths(child, f"{path}[{index}]", out)
    return out


def _identity(row: dict[str, Any]) -> str:
    return _text(
        row.get("id")
        or row.get("ingredientId")
        or row.get("key")
        or row.get("foodKey")
    )


def _provider_key(row: dict[str, Any]) -> str:
    return _text(row.get("key") or row.get("foodKey") or row.get("providerIngredientId"))


def _nutrition_valid(value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("basis") == "per100g"
        and isinstance(value.get("values"), dict)
        and value["values"]
        and all(
            isinstance(number, (int, float)) and not isinstance(number, bool)
            for number in value["values"].values()
        )
    )


def _index_is_exact(payload: dict[str, Any], field: str, expected: dict[str, Any]) -> bool:
    value = payload.get(field)
    return isinstance(value, dict) and value == expected


def validate(
    payload: dict[str, Any],
    *,
    require_complete: bool = True,
    require_intelligence: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if int(payload.get("schemaVersion") or 0) != 1:
        errors.append("schemaVersion must be 1")
    if not _text(payload.get("catalogVersion")):
        errors.append("catalogVersion is required")
    if require_complete and payload.get("complete") is not True:
        errors.append("catalog is not marked capture-complete")
    runtime_keys = sorted(key for key in payload if str(key).startswith("_runtime"))
    if runtime_keys:
        errors.append(f"runtime-only keys are persisted: {runtime_keys[:10]}")

    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    if int(source.get("auditedCatalogCount") or 0) != 28:
        errors.append("source.auditedCatalogCount must be 28")
    if int(source.get("failedDetailCount") or 0) != 0:
        errors.append("source.failedDetailCount must be zero")
    if source.get("providerIngredientIdentityPreserved") is not True:
        errors.append("providerIngredientIdentityPreserved must be true")
    if source.get("providerIngredientIdentityInferred") is not False:
        errors.append("providerIngredientIdentityInferred must be false")
    if source.get("keylessSourceLocalIdentity") is not True:
        errors.append("keylessSourceLocalIdentity must be true")
    if source.get("semanticConceptProviderIdentity") is not False:
        errors.append("semanticConceptProviderIdentity must be false")
    if source.get("semanticCoverageComplete") is not True:
        errors.append("semanticCoverageComplete must be true")
    if source.get("compiledMultilingualSearchIndex") is not True:
        errors.append("compiledMultilingualSearchIndex must be true")
    if source.get("compiledRecipeSafetyIndex") is not True:
        errors.append("compiledRecipeSafetyIndex must be true")
    if source.get("strictDietAllergyUnknownIsSafe") is not False:
        errors.append("strictDietAllergyUnknownIsSafe must be false")
    if source.get("strictAllergyRequiresExplicitAbsence") is not True:
        errors.append("strictAllergyRequiresExplicitAbsence must be true")
    if source.get("strictDietRequiresExplicitCompatibility") is not True:
        errors.append("strictDietRequiresExplicitCompatibility must be true")
    if source.get("secretsPersisted") is not False:
        errors.append("secretsPersisted must be false")

    for field in (
        "unresolvedCanonicalIngredientNames",
        "unresolvedCanonicalRecipeNames",
        "unresolvedKeylessRecipeLineCount",
    ):
        if int(source.get(field) or 0) != 0:
            errors.append(f"source.{field} must be zero")

    if require_intelligence:
        for field in (
            "foodIntelligenceNutritionComplete",
            "dietAllergyIntelligenceComplete",
            "ingredientIntelligenceComplete",
        ):
            if source.get(field) is not True:
                errors.append(f"source.{field} must be true when intelligence is required")
    elif source.get("ingredientIntelligenceComplete") is not True:
        warnings.append("ingredient intelligence is incomplete; runtime must remain fail-closed")

    ingredients = payload.get("ingredients") if isinstance(payload.get("ingredients"), list) else []
    recipes = payload.get("recipes") if isinstance(payload.get("recipes"), list) else []
    if not ingredients:
        errors.append("global ingredient table is empty")
    if not recipes:
        errors.append("recipe table is empty")

    ingredient_ids: list[str] = []
    provider_ids: set[str] = set()
    source_local_ids: set[str] = set()
    ambiguous_ids: set[str] = set()
    ingredient_by_id: dict[str, dict[str, Any]] = {}

    for index, row in enumerate(ingredients):
        if not isinstance(row, dict):
            errors.append(f"ingredients[{index}] is not an object")
            continue
        ident = _identity(row)
        if not ident:
            errors.append(f"ingredients[{index}] has no identity")
            continue
        ingredient_ids.append(ident)
        ingredient_by_id.setdefault(ident, row)
        provider_key = _provider_key(row)
        source_local = bool(row.get("sourceLocalIdentity")) or ident.startswith("local:")

        if source_local:
            source_local_ids.add(ident)
            if not ident.startswith("local:"):
                errors.append(f"source-local ingredient {ident} must use local: identity")
            if provider_key:
                errors.append(f"source-local ingredient {ident} carries provider identity {provider_key}")
            if row.get("providerIdentityAssigned") is not False:
                errors.append(f"source-local ingredient {ident} must set providerIdentityAssigned=false")
            if not _text(row.get("conceptId")):
                errors.append(f"source-local ingredient {ident} has no reviewed conceptId")
            classification = _text(row.get("classification")).lower()
            if classification not in _ALLOWED_SOURCE_LOCAL_CLASSIFICATIONS:
                errors.append(f"source-local ingredient {ident} has invalid classification {classification!r}")
            if classification == "ambiguous":
                ambiguous_ids.add(ident)
                if row.get("needsSemanticConfirmation") is not True:
                    errors.append(f"ambiguous ingredient {ident} must need semantic confirmation")
                for field in ("nutritionEligible", "dietEligible", "allergenEligible"):
                    if row.get(field) is not False:
                        errors.append(f"ambiguous ingredient {ident} must set {field}=false")
            if classification in {"equipment", "other", "ambiguous"} and row.get("nutrition"):
                errors.append(f"non-food/ambiguous ingredient {ident} must not carry nutrition")
            if row.get("nutrition") and row.get("nutritionEligible") is False:
                errors.append(f"nutrition-ineligible source-local ingredient {ident} carries nutrition")
        else:
            if not provider_key:
                errors.append(f"global ingredient {ident} has neither provider nor source-local identity")
            else:
                provider_ids.add(ident)
                if ident != provider_key:
                    errors.append(f"provider ingredient {ident} must preserve matching provider key")
                if not ident.startswith("M_FOOD_"):
                    errors.append(f"provider ingredient {ident} is not an M_FOOD identity")

        if not _text(row.get("canonicalName")):
            errors.append(f"ingredient {ident} has no canonicalName")
        if row.get("nutrition") and not _nutrition_valid(row.get("nutrition")):
            errors.append(f"ingredient {ident} has invalid nutrition profile")

    duplicates = sorted(key for key, count in Counter(ingredient_ids).items() if count > 1)
    if duplicates:
        errors.append(f"duplicate ingredient ids: {duplicates[:10]}")
    ingredient_id_set = set(ingredient_ids)

    group_ids: list[str] = []
    variant_ids: list[str] = []
    dangling: list[str] = []
    identity_leaks: list[str] = []
    for group_index, group in enumerate(recipes):
        if not isinstance(group, dict):
            errors.append(f"recipes[{group_index}] is not an object")
            continue
        group_id = _text(group.get("groupingFunctionalId"))
        if not group_id:
            errors.append(f"recipes[{group_index}] has no groupingFunctionalId")
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
            variant_id = _text(variant.get("variantId") or variant.get("searchVariantId"))
            if not variant_id:
                errors.append(f"recipe group {group_id} contains variant without identity")
                continue
            variant_ids.append(variant_id)
            variant_group = _text(variant.get("groupingFunctionalId"))
            if variant_group and variant_group != group_id:
                errors.append(f"variant {variant_id} groupingFunctionalId mismatch")
            if not _text(variant.get("originalTitle") or variant.get("title")):
                errors.append(f"variant {variant_id} has no original title")
            if not _text(variant.get("originalLanguage") or variant.get("language")):
                errors.append(f"variant {variant_id} has no original language")
            for line in variant.get("ingredients") or []:
                if not isinstance(line, dict):
                    continue
                ident = _identity(line)
                provider_key = _provider_key(line)
                if not ident:
                    errors.append(f"ingredient line in {variant_id} has no identity")
                    continue
                if ident not in ingredient_id_set:
                    dangling.append(f"{variant_id}:{ident}")
                if ident.startswith("local:") and provider_key:
                    identity_leaks.append(f"{variant_id}:{ident}:{provider_key}")
                if provider_key and (ident != provider_key or not provider_key.startswith("M_FOOD_")):
                    identity_leaks.append(f"{variant_id}:{ident}:{provider_key}")

    duplicate_groups = sorted(key for key, count in Counter(group_ids).items() if count > 1)
    duplicate_variants = sorted(key for key, count in Counter(variant_ids).items() if count > 1)
    if duplicate_groups:
        errors.append(f"duplicate groupingFunctionalIds: {duplicate_groups[:10]}")
    if duplicate_variants:
        errors.append(f"duplicate variant ids: {duplicate_variants[:10]}")
    if dangling:
        errors.append(f"dangling ingredient references: {dangling[:10]}")
    if identity_leaks:
        errors.append(f"ingredient identity leaks: {identity_leaks[:10]}")

    dependencies = payload.get("recipeDependencyIndex")
    if not isinstance(dependencies, dict):
        errors.append("recipeDependencyIndex is missing")
    else:
        for ident, indices in dependencies.items():
            if ident not in ingredient_id_set:
                errors.append(f"recipeDependencyIndex references unknown ingredient {ident}")
                continue
            if not isinstance(indices, list) or any(
                not isinstance(index, int) or index < 0 or index >= len(recipes)
                for index in indices
            ):
                errors.append(f"recipeDependencyIndex has invalid recipe indexes for {ident}")
            elif len(indices) != len(set(indices)):
                errors.append(f"recipeDependencyIndex has duplicate recipe indexes for {ident}")

    expected_search = catalog_search_index.compile_search_index(payload)
    if not _index_is_exact(payload, "searchIndex", expected_search):
        errors.append("precompiled multilingual search index does not match catalog content")

    expected_safety = recipe_safety_index_v60.compile_recipe_safety_index(payload)
    if not _index_is_exact(payload, "recipeSafetyIndex", expected_safety):
        errors.append("precompiled strict recipe safety index does not match catalog content")

    secret_paths = _secret_paths(payload)
    if secret_paths:
        errors.append(f"secret-like keys present: {secret_paths[:10]}")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "ingredientCount": len(ingredients),
            "providerIngredientCount": len(provider_ids),
            "sourceLocalIngredientCount": len(source_local_ids),
            "ambiguousReviewedIngredientCount": len(ambiguous_ids),
            "recipeGroupCount": len(recipes),
            "variantCount": len(variant_ids),
            "ingredientIntelligenceComplete": bool(source.get("ingredientIntelligenceComplete")),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog")
    parser.add_argument("--allow-incomplete", action="store_true")
    parser.add_argument("--require-intelligence", action="store_true")
    args = parser.parse_args()
    result = validate(
        _load(Path(args.catalog).expanduser()),
        require_complete=not args.allow_incomplete,
        require_intelligence=args.require_intelligence,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
