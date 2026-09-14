#!/usr/bin/env python3
"""Compact a validated v60 candidate into the runtime release representation.

The release catalog intentionally keeps one rich global ingredient table. Recipe
ingredient lines therefore only need identity plus quantity/unit facts. Review
file paths, duplicate per-line labels, and per-variant nutrition coverage vectors
are build evidence rather than runtime data.

This compactor never drops a recipe, variant, ingredient identity, nutrient
profile, quantity, unit, title, market, send identity, or safety/search fact.
After compaction it deterministically regenerates dependency, multilingual
search, and strict safety indexes from the compact payload.
"""
from __future__ import annotations

import argparse
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

import catalog_search_index  # type: ignore  # noqa: E402
import recipe_metrics_v60  # type: ignore  # noqa: E402
import recipe_safety_index_v60  # type: ignore  # noqa: E402

_INGREDIENT_BUILD_ONLY_FIELDS = {
    "semanticReviewFile",
    "canonicalEnglishReviewFile",
    "canonicalEnglishSource",
    "canonicalEnglishConfidence",
}
_RECIPE_BUILD_ONLY_FIELDS = {
    "canonicalEnglishReviewFile",
    "canonicalEnglishSource",
    "canonicalEnglishConfidence",
}
_LINE_RUNTIME_FIELDS = (
    "ingredientId",
    "quantity",
    "unit",
    "unitKey",
    "weight",
    "functionalId",
)


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _identity(row: dict[str, Any]) -> str:
    return _text(
        row.get("ingredientId")
        or row.get("id")
        or row.get("key")
        or row.get("foodKey")
    )


def _compact_line(raw: dict[str, Any]) -> dict[str, Any]:
    ident = _identity(raw)
    if not ident:
        raise RuntimeError("runtime ingredient line has no stable identity")
    out: dict[str, Any] = {"ingredientId": ident}
    for field in _LINE_RUNTIME_FIELDS[1:]:
        value = raw.get(field)
        if value not in (None, "", {}, []):
            out[field] = deepcopy(value)
    return out


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
            len(set(diet_compatible.get(key) or ()) | set(diet_incompatible.get(key) or ()))
            == recipe_count
            for key in index.get("dietKeys") or ()
        )
        and all(
            len(set(allergen_absent.get(key) or ()) | set(allergen_present.get(key) or ()))
            == recipe_count
            for key in index.get("allergenKeys") or ()
        )
    )


def compact(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    result = deepcopy(payload)
    ingredients = [
        row for row in result.get("ingredients") or [] if isinstance(row, dict)
    ]
    recipes = [row for row in result.get("recipes") or [] if isinstance(row, dict)]
    if not ingredients or not recipes:
        raise RuntimeError("cannot compact an empty release catalog")

    ingredient_ids = {_identity(row) for row in ingredients if _identity(row)}
    if len(ingredient_ids) != len(ingredients):
        raise RuntimeError("ingredient table contains empty or duplicate identities")

    removed_line_fields = 0
    removed_vectors = 0
    for row in ingredients:
        for field in _INGREDIENT_BUILD_ONLY_FIELDS:
            row.pop(field, None)

    for recipe in recipes:
        for field in _RECIPE_BUILD_ONLY_FIELDS:
            recipe.pop(field, None)
        for variant in recipe.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            if variant.pop("calculatedNutritionV60", None) is not None:
                removed_vectors += 1
            variant.pop("nutrition", None)
            compacted: list[dict[str, Any]] = []
            for raw in variant.get("ingredients") or []:
                if not isinstance(raw, dict):
                    continue
                before = len(raw)
                line = _compact_line(raw)
                if line["ingredientId"] not in ingredient_ids:
                    raise RuntimeError(
                        f"runtime ingredient line references unknown identity {line['ingredientId']}"
                    )
                removed_line_fields += max(0, before - len(line))
                compacted.append(line)
            variant["ingredients"] = compacted

    result["ingredients"] = ingredients
    result["recipes"] = recipes

    dependencies = recipe_metrics_v60.compile_recipe_dependency_index(recipes)
    result["recipeDependencyIndex"] = {
        ident: list(indices) for ident, indices in dependencies.items()
    }
    search_index = catalog_search_index.compile_search_index(result)
    result["searchIndex"] = search_index
    safety_index = recipe_safety_index_v60.compile_recipe_safety_index(result)
    result["recipeSafetyIndex"] = safety_index

    source = result.setdefault("source", {})
    if not isinstance(source, dict):
        source = {}
        result["source"] = source
    safety_complete = _safety_complete(safety_index)
    source.update(
        {
            "compiledRecipeDependencyIndex": True,
            "recipeDependencyIdentityCount": len(dependencies),
            "compiledMultilingualSearchIndex": True,
            "compiledMultilingualSearchIndexSchemaVersion": int(
                search_index.get("schemaVersion") or 0
            ),
            "compiledRecipeSafetyIndex": True,
            "recipeSafetyIndexSchemaVersion": int(safety_index.get("schemaVersion") or 0),
            "recipeSafetyIndexedRecipeCount": int(safety_index.get("recipeCount") or 0),
            "dietAllergyIntelligenceComplete": safety_complete,
            "precomputedRecipeNutritionVectors": False,
            "recipeNutritionComputedOnDemand": True,
            "recipeVariantNutritionVectorsPersisted": False,
            "runtimeCatalogCompacted": True,
            "runtimeCatalogGlobalIngredientLabels": True,
        }
    )
    # Nutrition completeness is still derived from the global ingredient table.
    source["ingredientIntelligenceComplete"] = bool(
        source.get("semanticCoverageComplete")
        and source.get("foodIntelligenceNutritionComplete")
        and safety_complete
    )

    report = {
        "catalogVersion": _text(result.get("catalogVersion")),
        "recipeGroupCount": len(recipes),
        "variantCount": sum(
            len(row.get("variants") or []) for row in recipes if isinstance(row, dict)
        ),
        "ingredientCount": len(ingredients),
        "removedPerVariantNutritionVectors": removed_vectors,
        "removedDuplicateIngredientLineFields": removed_line_fields,
        "searchTokenCount": int((search_index.get("stats") or {}).get("tokens") or 0),
        "searchPrefixCount": int((search_index.get("stats") or {}).get("prefixes") or 0),
        "searchPrefixPostingsPersisted": bool(
            (search_index.get("stats") or {}).get("prefixPostingsPersisted", True)
        ),
        "dependencyIdentityCount": len(dependencies),
        "safetyRecipeCount": int(safety_index.get("recipeCount") or 0),
        "recipeContentDropped": False,
        "ingredientNutritionDropped": False,
        "networkRequestsPerformed": False,
    }
    return result, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    result, report = compact(_load(Path(args.catalog).expanduser()))
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    report_path = Path(args.report).expanduser()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**report, "outputBytes": output.stat().st_size}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
