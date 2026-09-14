#!/usr/bin/env python3
"""Compact a validated v60 release catalog for immutable runtime shipping.

The maintenance artifact intentionally carries review/debug duplication that is
useful while building but unnecessary at runtime. This compactor preserves every
recipe, variant, global ingredient, provider identity, quantity, unit and send
identity while removing only data that can be recovered deterministically from
the global ingredient table or calculated on demand.

All derived search/dependency/safety indexes are rebuilt after compaction. No
network access is performed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (ROOT / "tools", COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import catalog_search_index  # type: ignore  # noqa: E402
import recipe_metrics_v60  # type: ignore  # noqa: E402
import recipe_safety_index_v60  # type: ignore  # noqa: E402

_POLICY = "global-ingredient-dedup-runtime-index-v1"

_GROUP_BUILD_ONLY_FIELDS = {
    "canonicalEnglishReviewFile",
    "canonicalEnglishSource",
    "canonicalEnglishConfidence",
    "canonicalEnglishNeedsReview",
}

# These fields already live on the globally indexed ingredient row and are
# reattached by release_catalog_v60_core when a recipe is materialized. Keep
# ingredientId/key plus quantity/unit evidence on every recipe line.
_LINE_GLOBAL_DUPLICATE_FIELDS = {
    "conceptId",
    "semanticSourceName",
    "canonicalName",
    "semanticIdentityState",
    "classification",
    "providerIdentityAssigned",
    "sourceLocalIdentity",
    "semanticMergePolicy",
    "reviewConfidence",
    "nutritionEligible",
    "dietEligible",
    "allergenEligible",
    "needsSemanticConfirmation",
    "semanticReviewFile",
    "originalName",
    "originalLanguage",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def compact(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    recipes = payload.get("recipes") if isinstance(payload.get("recipes"), list) else []
    ingredients = payload.get("ingredients") if isinstance(payload.get("ingredients"), list) else []
    before_groups = len(recipes)
    before_variants = sum(
        len(row.get("variants") or [])
        for row in recipes
        if isinstance(row, dict)
    )
    before_ingredients = len(ingredients)

    stripped_group_fields = 0
    stripped_line_fields = 0
    stripped_variant_vectors = 0

    for group in recipes:
        if not isinstance(group, dict):
            continue
        for field in _GROUP_BUILD_ONLY_FIELDS:
            if field in group:
                group.pop(field, None)
                stripped_group_fields += 1
        for variant in group.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            # Legacy capture nutrition and the large per-variant v60 vector are
            # derivable from the authoritative global reviewed profiles.
            for field in ("nutrition", "calculatedNutritionV60"):
                if field in variant:
                    variant.pop(field, None)
                    stripped_variant_vectors += 1
            for line in variant.get("ingredients") or []:
                if not isinstance(line, dict):
                    continue
                for field in _LINE_GLOBAL_DUPLICATE_FIELDS:
                    if field in line:
                        line.pop(field, None)
                        stripped_line_fields += 1

    # Rebuild every derived structure from the compact recipe representation so
    # the independent validator can prove byte-for-structure consistency.
    payload["searchIndex"] = catalog_search_index.compile_search_index(payload)
    dependencies = recipe_metrics_v60.compile_recipe_dependency_index(recipes)
    payload["recipeDependencyIndex"] = {
        ident: list(indices) for ident, indices in dependencies.items()
    }
    safety = recipe_safety_index_v60.compile_recipe_safety_index(payload)
    payload["recipeSafetyIndex"] = safety

    source = payload.setdefault("source", {})
    if not isinstance(source, dict):
        source = {}
        payload["source"] = source
    source.update(
        {
            "compiledMultilingualSearchIndex": True,
            "compiledMultilingualSearchIndexSchemaVersion": int(
                (payload.get("searchIndex") or {}).get("schemaVersion") or 0
            ),
            "compiledRecipeDependencyIndex": True,
            "recipeDependencyIdentityCount": len(dependencies),
            "compiledRecipeSafetyIndex": True,
            "recipeSafetyIndexSchemaVersion": int(safety.get("schemaVersion") or 0),
            "recipeSafetyIndexedRecipeCount": int(safety.get("recipeCount") or 0),
            "precomputedRecipeNutritionVectors": False,
            "recipeVariantNutritionVectorCount": 0,
            "recipeVariantNutritionFullyCoveredCount": 0,
            "runtimeRecipeNutritionOnDemand": True,
            "runtimeNutritionIndexFromGlobalIngredients": True,
            "runtimeCatalogCompacted": True,
            "runtimeCatalogCompactionPolicy": _POLICY,
            "runtimeCatalogRecipeLineGlobalMetadataDeduplicated": True,
            "runtimeCatalogPrefixPostingsPersisted": False,
        }
    )

    after_variants = sum(
        len(row.get("variants") or [])
        for row in recipes
        if isinstance(row, dict)
    )
    if len(recipes) != before_groups or after_variants != before_variants:
        raise RuntimeError("runtime compaction changed recipe/variant counts")
    if len(ingredients) != before_ingredients:
        raise RuntimeError("runtime compaction changed global ingredient count")

    summary = {
        "policy": _POLICY,
        "recipeGroups": before_groups,
        "variants": before_variants,
        "ingredients": before_ingredients,
        "strippedGroupFields": stripped_group_fields,
        "strippedRecipeLineDuplicateFields": stripped_line_fields,
        "strippedVariantNutritionVectors": stripped_variant_vectors,
        "searchTokenCount": int((payload.get("searchIndex") or {}).get("stats", {}).get("tokens") or 0),
        "searchPrefixCount": int((payload.get("searchIndex") or {}).get("stats", {}).get("prefixes") or 0),
        "prefixPostingsPersisted": bool((payload.get("searchIndex") or {}).get("prefixPostings")),
        "runtimeRecipeNutritionOnDemand": True,
        "networkRequestsPerformed": False,
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", default="")
    args = parser.parse_args()

    result, summary = compact(_load(Path(args.catalog).expanduser()))
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    summary["outputBytes"] = output.stat().st_size
    if args.summary:
        summary_path = Path(args.summary).expanduser()
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
