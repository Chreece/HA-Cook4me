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
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import catalog_search_index  # type: ignore  # noqa: E402
import provider_identity_v60  # type: ignore  # noqa: E402
import recipe_metrics_v60  # type: ignore  # noqa: E402
import recipe_safety_index_v60  # type: ignore  # noqa: E402
import release_catalog_detail_not_found_v60 as detail_not_found  # type: ignore  # noqa: E402


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
    return provider_identity_v60.provider_key(row)


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


def _safety_complete(index: dict[str, Any]) -> bool:
    recipe_count = max(0, int(index.get("recipeCount") or 0))
    if not recipe_count:
        return False
    diet_compatible = index.get("dietCompatible") or {}
    diet_incompatible = index.get("dietIncompatible") or {}
    allergen_absent = index.get("allergenAbsent") or {}
    allergen_present = index.get("allergenPresent") or {}
    return bool(
        all(
            len(
                set(diet_compatible.get(key) or ())
                | set(diet_incompatible.get(key) or ())
            )
            == recipe_count
            for key in index.get("dietKeys") or ()
        )
        and all(
            len(
                set(allergen_absent.get(key) or ())
                | set(allergen_present.get(key) or ())
            )
            == recipe_count
            for key in index.get("allergenKeys") or ()
        )
    )


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
    errors.extend(detail_not_found.validation_errors(payload))
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
    if source.get("compiledRecipeDependencyIndex") is not True:
        errors.append("compiledRecipeDependencyIndex must be true")
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
    food_intelligence_count = 0
    food_nutrition_resolved = 0

    for index, row in enumerate(ingredients):
        if not isinstance(row, dict):
            errors.append(f"ingredients[{index}] is not an object")
            continue
        ident = _identity(row)
        if not ident:
            errors.append(f"ingredients[{index}] has no identity")
            continue
        ingredient_ids.append(ident)
        provider_key = _provider_key(row)
        source_local = bool(row.get("sourceLocalIdentity")) or ident.startswith("local:")
        food_for_intelligence = False

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
            food_for_intelligence = classification == "food"
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
                food_for_intelligence = True
                if not provider_identity_v60.preserved_provider_identity(row, ident):
                    errors.append(
                        f"provider ingredient {ident} must preserve matching provider key"
                    )

        if not _text(row.get("canonicalName")):
            errors.append(f"ingredient {ident} has no canonicalName")
        nutrition_ok = _nutrition_valid(row.get("nutrition"))
        if row.get("nutrition") and not nutrition_ok:
            errors.append(f"ingredient {ident} has invalid nutrition profile")
        if food_for_intelligence:
            food_intelligence_count += 1
            if nutrition_ok:
                food_nutrition_resolved += 1

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
                elif provider_key and not provider_identity_v60.preserved_provider_identity(
                    line, ident
                ):
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
    expected_dependencies = {
        ident: list(indices)
        for ident, indices in recipe_metrics_v60.compile_recipe_dependency_index(
            recipes
        ).items()
    }
    if not isinstance(dependencies, dict):
        errors.append("recipeDependencyIndex is missing")
    elif dependencies != expected_dependencies:
        errors.append("precompiled recipe dependency index does not match catalog content")
    if int(source.get("recipeDependencyIdentityCount") or 0) != len(expected_dependencies):
        errors.append("recipeDependencyIdentityCount does not match compiled dependency index")

    expected_search = catalog_search_index.compile_search_index(payload)
    if not _index_is_exact(payload, "searchIndex", expected_search):
        errors.append("precompiled multilingual search index does not match catalog content")

    expected_safety = recipe_safety_index_v60.compile_recipe_safety_index(payload)
    if not _index_is_exact(payload, "recipeSafetyIndex", expected_safety):
        errors.append("precompiled strict recipe safety index does not match catalog content")

    derived_food_complete = bool(
        food_intelligence_count
        and food_nutrition_resolved == food_intelligence_count
    )
    declared_food_complete = source.get("foodIntelligenceNutritionComplete") is True
    if declared_food_complete != derived_food_complete:
        errors.append(
            "foodIntelligenceNutritionComplete does not match ingredient nutrition evidence"
        )
    if int(source.get("foodIntelligenceIngredientCount") or 0) != food_intelligence_count:
        errors.append("foodIntelligenceIngredientCount does not match ingredient table")
    if int(source.get("foodIntelligenceNutritionResolvedCount") or 0) != food_nutrition_resolved:
        errors.append("foodIntelligenceNutritionResolvedCount does not match ingredient table")

    derived_safety_complete = _safety_complete(expected_safety)
    if (source.get("dietAllergyIntelligenceComplete") is True) != derived_safety_complete:
        errors.append(
            "dietAllergyIntelligenceComplete does not match strict safety evidence"
        )
    derived_intelligence_complete = bool(
        source.get("semanticCoverageComplete") is True
        and derived_food_complete
        and derived_safety_complete
    )
    if (
        source.get("ingredientIntelligenceComplete") is True
    ) != derived_intelligence_complete:
        errors.append(
            "ingredientIntelligenceComplete does not match semantic, nutrition, and safety evidence"
        )

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
            "recipeDependencyIdentityCount": len(expected_dependencies),
            "foodIntelligenceIngredientCount": food_intelligence_count,
            "foodIntelligenceNutritionResolvedCount": food_nutrition_resolved,
            "foodIntelligenceNutritionComplete": derived_food_complete,
            "dietAllergyIntelligenceComplete": derived_safety_complete,
            "ingredientIntelligenceComplete": derived_intelligence_complete,
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
