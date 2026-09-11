#!/usr/bin/env python3
"""Cook4Me v60 release builder facade with strict recipe safety indexing.

The proven semantic/nutrition/search implementation lives in
``build_release_catalog_v60_core``. This facade adds the immutable diet/allergy
safety index without changing provider identity, semantic review, nutrition, or
search assembly behavior.

Provider capture happens once. Reviewed exact-FDC nutrition can then be attached
offline and every derived v60 vector/index is deterministically regenerated.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60_core as _core
import provider_identity_v60
import recipe_safety_index_v60 as safety
import release_catalog_phase3_identity_v60 as phase3_identity
import reviewed_nutrition_v60 as reviewed_nutrition


def _reject_unreviewed_nutrition_search(args: Any) -> None:
    """Never let v60 turn a fuzzy FDC search result into release evidence."""
    if bool(getattr(args, "resolve_nutrition", False)):
        raise RuntimeError(
            "v60 automatic USDA/FDC search resolution is disabled; build with "
            "--allow-missing-nutrition, create the reviewed v60 nutrition queue, "
            "bind exact FDC IDs in release_catalog_reviewed_nutrition_sources*.v1.json, "
            "resolve them with resolve_reviewed_release_catalog_nutrition_v60.py, "
            "then finalize that captured artifact offline"
        )


def _safety_completeness(index: dict[str, Any]) -> bool:
    recipe_count = max(0, int(index.get("recipeCount") or 0))
    if not recipe_count:
        return False
    diet_compatible = index.get("dietCompatible") or {}
    diet_incompatible = index.get("dietIncompatible") or {}
    allergen_absent = index.get("allergenAbsent") or {}
    allergen_present = index.get("allergenPresent") or {}
    diet_complete = all(
        len(set(diet_compatible.get(key) or ()) | set(diet_incompatible.get(key) or ()))
        == recipe_count
        for key in index.get("dietKeys") or ()
    )
    allergen_complete = all(
        len(set(allergen_absent.get(key) or ()) | set(allergen_present.get(key) or ()))
        == recipe_count
        for key in index.get("allergenKeys") or ()
    )
    return bool(diet_complete and allergen_complete)


def _refresh_safety(result: dict[str, Any]) -> dict[str, Any]:
    safety_index = safety.compile_recipe_safety_index(result)
    result["recipeSafetyIndex"] = safety_index
    source = result.setdefault("source", {})
    if not isinstance(source, dict):
        source = {}
        result["source"] = source
    safety_complete = _safety_completeness(safety_index)
    source.update(
        {
            "compiledRecipeSafetyIndex": True,
            "recipeSafetyIndexSchemaVersion": int(
                safety_index.get("schemaVersion") or 0
            ),
            "recipeSafetyIndexedRecipeCount": int(
                safety_index.get("recipeCount") or 0
            ),
            "strictDietAllergyUnknownIsSafe": False,
            "strictAllergyRequiresExplicitAbsence": True,
            "strictDietRequiresExplicitCompatibility": True,
            "dietAllergyIntelligenceComplete": safety_complete,
            "ingredientIntelligenceComplete": bool(
                source.get("ingredientIntelligenceComplete") and safety_complete
            ),
        }
    )
    return result


def enrich_payload(
    payload: dict[str, Any], semantic_payload: dict[str, Any]
) -> dict[str, Any]:
    """Run the proven v60 core then append strict precompiled safety sets.

    Source-local identity must be computed from the exact semantic label that
    Phase 3 reviewed.  During live capture that label is retained explicitly as
    ``semanticSourceName`` before the v59 compactor discards raw descriptions.
    """
    original_source_name = _core._source_name

    def reviewed_source_name(item: dict[str, Any]) -> str:
        return (
            phase3_identity.compact_semantic_source_name(item)
            or original_source_name(item)
        )

    _core._source_name = reviewed_source_name
    try:
        return _refresh_safety(_core.enrich_payload(payload, semantic_payload))
    finally:
        _core._source_name = original_source_name


def _identity(row: dict[str, Any]) -> str:
    return _core._text(
        row.get("id")
        or row.get("ingredientId")
        or row.get("key")
        or row.get("foodKey")
    )


def _reviewed_nutrition_eligible(row: dict[str, Any], ident: str) -> bool:
    source_local = bool(row.get("sourceLocalIdentity")) or ident.startswith("local:")
    if not source_local:
        return provider_identity_v60.preserved_provider_identity(row, ident)
    return bool(
        _core._text(row.get("classification")).lower() == "food"
        and row.get("nutritionEligible") is True
        and row.get("needsSemanticConfirmation") is not True
        and _core._text(row.get("conceptId"))
    )


def apply_reviewed_nutrition(
    payload: dict[str, Any],
    nutrition_cache: dict[str, Any],
) -> dict[str, Any]:
    """Attach only reviewed exact-FDC profiles and rebuild every derived index.

    This function is deliberately network-free. It never performs provider or
    USDA requests and never changes recipe/provider identity. Legacy fuzzy cache
    entries are ignored and any pre-existing unreviewed nutrition is stripped.
    """
    result = deepcopy(payload)
    ingredients = [
        row for row in result.get("ingredients") or [] if isinstance(row, dict)
    ]
    required = 0
    resolved = 0
    rejected_unreviewed_cache = 0
    rejected_unreviewed_embedded = 0

    for row in ingredients:
        ident = _identity(row)
        canonical = _core._text(row.get("canonicalName"))
        embedded = row.pop("nutrition", None)
        eligible = bool(ident and canonical and _reviewed_nutrition_eligible(row, ident))
        if not eligible:
            continue
        required += 1

        cached = nutrition_cache.get(ident)
        if reviewed_nutrition.is_reviewed_profile(
            cached,
            ingredient_id=ident,
            canonical_name=canonical,
        ):
            row["nutrition"] = deepcopy(cached)
            resolved += 1
            continue
        if isinstance(cached, dict) and cached:
            rejected_unreviewed_cache += 1

        if reviewed_nutrition.is_reviewed_profile(
            embedded,
            ingredient_id=ident,
            canonical_name=canonical,
        ):
            row["nutrition"] = deepcopy(embedded)
            resolved += 1
            continue
        if isinstance(embedded, dict) and embedded:
            rejected_unreviewed_embedded += 1

    # The v59 capture layer may have emitted a generic recipe nutrition summary.
    # It is not v60 reviewed evidence and must never survive finalization.
    for recipe in result.get("recipes") or []:
        if not isinstance(recipe, dict):
            continue
        recipe.pop("nutrition", None)
        for variant in recipe.get("variants") or []:
            if isinstance(variant, dict):
                variant.pop("nutrition", None)
                variant.pop("calculatedNutritionV60", None)

    metric_stats = _core._compile_recipe_vectors(result, ingredients)
    result["searchIndex"] = _core.search_index.compile_search_index(result)

    source = result.setdefault("source", {})
    if not isinstance(source, dict):
        source = {}
        result["source"] = source
    complete = bool(required and resolved == required)
    source.update(
        {
            **metric_stats,
            "compiledMultilingualSearchIndex": True,
            "compiledMultilingualSearchIndexSchemaVersion": int(
                (result.get("searchIndex") or {}).get("schemaVersion") or 0
            ),
            "compiledRecipeDependencyIndex": True,
            "precomputedRecipeNutritionVectors": True,
            "nutritionResolvedCount": resolved,
            "reviewedNutritionIdentityOnly": True,
            "reviewedNutritionRequiredForActivation": True,
            "reviewedNutritionRequiredCount": required,
            "reviewedNutritionResolvedCount": resolved,
            "reviewedNutritionComplete": complete,
            "legacyFuzzyNutritionAccepted": False,
            "reviewedNutritionRejectedLegacyCacheCount": rejected_unreviewed_cache,
            "reviewedNutritionRejectedEmbeddedCount": rejected_unreviewed_embedded,
            "foodIntelligenceIngredientCount": required,
            "foodIntelligenceNutritionResolvedCount": resolved,
            "foodIntelligenceNutritionComplete": complete,
            "ingredientIntelligenceComplete": bool(
                source.get("semanticCoverageComplete") and complete
            ),
        }
    )
    return _refresh_safety(result)


def build(args: Any) -> dict[str, Any]:
    _reject_unreviewed_nutrition_search(args)
    payload = phase3_identity.build_with_phase3_identity(_core.v59, args)
    semantic_payload = _core.semantics.compile_from_paths(
        _core.semantics._review_paths(_core.TOOLS)
    )
    payload = enrich_payload(payload, semantic_payload)
    _core._save_compact(Path(args.output), payload)
    return payload


def main() -> int:
    args = _core._parser().parse_args()
    payload = build(args)
    source = payload.get("source") or {}
    output = Path(args.output)
    print(
        json.dumps(
            {
                "catalogVersion": payload.get("catalogVersion"),
                "catalogComplete": bool(payload.get("complete")),
                "semanticCoverageComplete": bool(
                    source.get("semanticCoverageComplete")
                ),
                "dietAllergyIntelligenceComplete": bool(
                    source.get("dietAllergyIntelligenceComplete")
                ),
                "ingredientIntelligenceComplete": bool(
                    source.get("ingredientIntelligenceComplete")
                ),
                "recipes": len(payload.get("recipes") or []),
                "ingredients": len(payload.get("ingredients") or []),
                "sourceLocalIngredients": int(
                    source.get("sourceLocalIngredientCount") or 0
                ),
                "nutritionVectors": int(
                    source.get("recipeVariantNutritionVectorCount") or 0
                ),
                "dependencyIdentities": int(
                    source.get("recipeDependencyIdentityCount") or 0
                ),
                "safetyIndexedRecipes": int(
                    source.get("recipeSafetyIndexedRecipeCount") or 0
                ),
                "searchIndexStats": (payload.get("searchIndex") or {}).get(
                    "stats", {}
                ),
                "outputBytes": output.stat().st_size if output.exists() else 0,
                "output": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload.get("complete") else 2


def __getattr__(name: str):
    """Keep the established v60 builder API available to existing tests/tools."""
    return getattr(_core, name)


if __name__ == "__main__":
    raise SystemExit(main())