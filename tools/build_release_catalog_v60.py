#!/usr/bin/env python3
"""Cook4Me v60 release builder facade with strict recipe safety indexing.

The proven semantic/nutrition/search implementation lives in
``build_release_catalog_v60_core``. This facade adds the immutable diet/allergy
safety index without changing provider identity, semantic review, nutrition, or
search assembly behavior.
"""
from __future__ import annotations

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
import recipe_safety_index_v60 as safety


def _reject_unreviewed_nutrition_search(args: Any) -> None:
    """Never let v60 turn a fuzzy FDC search result into release evidence."""
    if bool(getattr(args, "resolve_nutrition", False)):
        raise RuntimeError(
            "v60 automatic USDA/FDC search resolution is disabled; build with "
            "--allow-missing-nutrition, create the reviewed v60 nutrition queue, "
            "bind exact FDC IDs in release_catalog_reviewed_nutrition_sources*.v1.json, "
            "resolve them with resolve_reviewed_release_catalog_nutrition_v60.py, "
            "then rebuild from that reviewed cache"
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


def enrich_payload(
    payload: dict[str, Any], semantic_payload: dict[str, Any]
) -> dict[str, Any]:
    """Run the proven v60 core then append strict precompiled safety sets."""
    result = _core.enrich_payload(payload, semantic_payload)
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


def build(args: Any) -> dict[str, Any]:
    _reject_unreviewed_nutrition_search(args)
    payload = _core.v59.build(args)
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
