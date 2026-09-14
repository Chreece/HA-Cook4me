#!/usr/bin/env python3
"""Compact a validated v60 release catalog for immutable runtime shipping.

The maintenance artifact intentionally carries review/debug duplication that is
useful while building but unnecessary at runtime. This compactor preserves every
recipe, variant, global ingredient, provider identity, quantity, unit and send
identity while removing only data that can be recovered deterministically from
the global ingredient table or calculated on demand.

Before repeated recipe-line metadata is removed, only the reviewed clean
``semanticSourceName`` is folded into the matching global ingredient translation
or alias table when it is genuinely missing. Raw ``originalName`` is deliberately
not retained as an alias because some provider catalogs embed quantities/units in
that field.

Reviewed nutrition keeps the exact ingredient/FDC/review identity and nutrient
values required for fail-closed reuse. Large repeated maintenance receipts are
collapsed into one catalog-level USDA reference receipt.

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

# Runtime/future-finalization still has everything is_reviewed_profile() needs,
# plus explicit review-target and USDA data-type identity. The omitted fields are
# maintenance receipts/notes already preserved in versioned review files or in
# the catalog-level reference receipt assembled below.
_RUNTIME_NUTRITION_KEEP_FIELDS = (
    "basis",
    "values",
    "source",
    "sourceId",
    "dataType",
    "ingredientId",
    "reviewedCanonicalEnglishName",
    "reviewFile",
    "nutritionReviewTargetId",
    "nutritionReviewTargetKind",
)


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _language(value: Any) -> str:
    return _text(value).lower().replace("_", "-").split("-", 1)[0]


def _global_lookup(ingredients: list[Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for raw in ingredients:
        if not isinstance(raw, dict):
            continue
        for value in (
            raw.get("id"),
            raw.get("ingredientId"),
            raw.get("key"),
            raw.get("foodKey"),
            raw.get("conceptId"),
        ):
            ident = _text(value)
            if ident:
                lookup.setdefault(ident, raw)
    return lookup


def _line_global(
    line: dict[str, Any], lookup: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    for value in (
        line.get("ingredientId"),
        line.get("id"),
        line.get("key"),
        line.get("foodKey"),
        line.get("conceptId"),
    ):
        ident = _text(value)
        if ident and isinstance(lookup.get(ident), dict):
            return lookup[ident]
    return None


def _preserve_line_semantic_alias(
    line: dict[str, Any], lookup: dict[str, dict[str, Any]]
) -> bool:
    """Preserve only clean reviewed semantic wording, never raw quantity text."""
    name = _text(line.get("semanticSourceName"))
    language = _language(line.get("originalLanguage"))
    if not name or not language:
        return False
    source = _line_global(line, lookup)
    if source is None:
        return False

    translations = source.get("translations")
    if not isinstance(translations, dict):
        translations = {}
        source["translations"] = translations
    translation = _text(translations.get(language))

    aliases = source.get("aliases")
    if not isinstance(aliases, dict):
        aliases = {}
        source["aliases"] = aliases
    values = aliases.get(language)
    if not isinstance(values, list):
        values = []
        aliases[language] = values

    normalized = {_text(value).casefold() for value in values if _text(value)}
    if translation:
        normalized.add(translation.casefold())
    if name.casefold() in normalized:
        return False

    # Prefer one translation over creating a one-item duplicate alias list.
    if not translation:
        translations[language] = name
    else:
        values.append(name)
    return True


def _compact_nutrition_profiles(
    ingredients: list[Any],
) -> dict[str, Any]:
    """Deduplicate maintenance provenance while keeping reviewed-profile proof."""
    manifest_shas: set[str] = set()
    datasets: set[tuple[str, str, str]] = set()
    profile_count = 0
    stripped_fields = 0

    for raw in ingredients:
        if not isinstance(raw, dict):
            continue
        profile = raw.get("nutrition")
        if not isinstance(profile, dict):
            continue
        profile_count += 1

        manifest_sha = _text(profile.get("sourceReferenceManifestSha256"))
        if manifest_sha:
            manifest_shas.add(manifest_sha)
        dataset = _text(profile.get("sourceReferenceDataset"))
        release_date = _text(profile.get("sourceReferenceReleaseDate"))
        json_sha = _text(profile.get("sourceReferenceJsonSha256"))
        if dataset or release_date or json_sha:
            datasets.add((dataset, release_date, json_sha))

        compact = {
            key: profile[key]
            for key in _RUNTIME_NUTRITION_KEEP_FIELDS
            if key in profile and profile[key] not in (None, "", {}, [])
        }
        stripped_fields += max(0, len(profile) - len(compact))
        raw["nutrition"] = compact

    result: dict[str, Any] = {
        "runtimeNutritionProfileCount": profile_count,
        "strippedNutritionMaintenanceFields": stripped_fields,
    }
    if len(manifest_shas) == 1:
        result["reviewedNutritionReferenceManifestSha256"] = next(iter(manifest_shas))
    elif manifest_shas:
        result["reviewedNutritionReferenceManifestSha256s"] = sorted(manifest_shas)
    if datasets:
        result["reviewedNutritionReferenceDatasets"] = [
            {
                "dataType": data_type,
                "releaseDate": release_date,
                "jsonSha256": json_sha,
            }
            for data_type, release_date, json_sha in sorted(datasets)
        ]
    return result


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
    global_lookup = _global_lookup(ingredients)

    stripped_group_fields = 0
    stripped_line_fields = 0
    stripped_variant_vectors = 0
    preserved_unique_aliases = 0

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
                if _preserve_line_semantic_alias(line, global_lookup):
                    preserved_unique_aliases += 1
                for field in _LINE_GLOBAL_DUPLICATE_FIELDS:
                    if field in line:
                        line.pop(field, None)
                        stripped_line_fields += 1

    nutrition_compaction = _compact_nutrition_profiles(ingredients)

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
            "runtimeCatalogRecipeLineSemanticAliasesFoldedToGlobal": True,
            "runtimeCatalogRawRecipeLineNamesNotIndexed": True,
            "runtimeCatalogPrefixPostingsPersisted": False,
            "runtimeNutritionProfilesCompacted": True,
            **nutrition_compaction,
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
        "preservedUniqueRecipeLineAliases": preserved_unique_aliases,
        "strippedGroupFields": stripped_group_fields,
        "strippedRecipeLineDuplicateFields": stripped_line_fields,
        "strippedVariantNutritionVectors": stripped_variant_vectors,
        **nutrition_compaction,
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
