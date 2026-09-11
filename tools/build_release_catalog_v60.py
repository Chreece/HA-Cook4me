#!/usr/bin/env python3
"""Build the v60 Cook4Me release catalog with semantic ingredient identities.

The v59 builder remains the provider-capture authority. This layer enriches its
compact output with reviewed source-local keyless identity, conservative semantic
concepts and a precompiled multilingual search index.

Provider M_FOOD identity is never inferred from labels or translations.
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

import build_release_catalog as v59  # type: ignore  # noqa: E402
import catalog_search_index as search_index  # type: ignore  # noqa: E402
import compile_release_catalog_semantics_v60 as semantics  # type: ignore  # noqa: E402


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _language(value: Any) -> str:
    return _text(value).lower().replace("_", "-").split("-", 1)[0]


def _provider_identity(item: dict[str, Any]) -> str:
    """Return only provider-backed identity; never synthesize it from a label."""
    return _text(
        item.get("foodKey")
        or item.get("key")
        or item.get("providerIngredientId")
    )


def _source_name(item: dict[str, Any]) -> str:
    return _text(
        item.get("originalName")
        or item.get("foodName")
        or item.get("name")
        or item.get("cleanName")
    )


def _semantic_maps(
    semantic_payload: dict[str, Any],
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    source_to_concept = {
        _text(source_id): _text(concept_id)
        for source_id, concept_id in (
            semantic_payload.get("sourceIdentityToConcept") or {}
        ).items()
        if _text(source_id) and _text(concept_id)
    }
    concepts = {
        _text(row.get("conceptId")): row
        for row in semantic_payload.get("concepts") or []
        if isinstance(row, dict) and _text(row.get("conceptId"))
    }
    return source_to_concept, concepts


def _concept_source_identity(
    concept: dict[str, Any], source_id: str
) -> dict[str, Any] | None:
    for row in concept.get("sourceIdentities") or []:
        if isinstance(row, dict) and _text(row.get("ingredientId")) == source_id:
            return row
    return None


def _source_local_global_row(
    *,
    source_id: str,
    source_name: str,
    source_language: str,
    concept: dict[str, Any] | None,
) -> dict[str, Any]:
    """Create a global source-local row without fabricating provider identity."""
    if concept is None:
        return {
            "id": source_id,
            "canonicalName": source_name,
            "translations": {source_language: source_name},
            "aliases": {source_language: [source_name]},
            "classification": "ambiguous",
            "sourceLocalIdentity": True,
            "providerIdentityAssigned": False,
            "canonicalEnglishNeedsReview": True,
            "nutritionEligible": False,
            "dietEligible": False,
            "allergenEligible": False,
            "needsSemanticConfirmation": True,
        }

    aliases = deepcopy(concept.get("aliases") or {})
    translations = {
        language: values[0]
        for language, values in aliases.items()
        if isinstance(values, list) and values
    }
    identity = _concept_source_identity(concept, source_id) or {}
    row = {
        "id": source_id,
        "conceptId": _text(concept.get("conceptId")),
        "canonicalName": _text(concept.get("canonicalEnglish")) or source_name,
        "translations": translations,
        "aliases": aliases,
        "classification": _text(concept.get("classification")) or "ambiguous",
        "sourceLocalIdentity": True,
        "providerIdentityAssigned": False,
        "semanticMergePolicy": _text(concept.get("mergePolicy")),
        "reviewConfidence": _text(identity.get("confidence")) or "reviewed",
        "semanticReviewFile": _text(identity.get("reviewFile")),
        "nutritionEligible": bool(concept.get("nutritionEligible")),
        "dietEligible": bool(concept.get("dietEligible")),
        "allergenEligible": bool(concept.get("allergenEligible")),
        "needsSemanticConfirmation": bool(
            concept.get("needsSemanticConfirmation")
        ),
    }
    if source_language and source_name:
        row.setdefault("translations", {}).setdefault(source_language, source_name)
        row.setdefault("aliases", {}).setdefault(source_language, [])
        if source_name not in row["aliases"][source_language]:
            row["aliases"][source_language].append(source_name)
    return {
        key: value
        for key, value in row.items()
        if value not in ("", None, {}, [])
    }


def _annotate_keyless_ingredient(
    item: dict[str, Any],
    *,
    source_to_concept: dict[str, str],
    concepts: dict[str, dict[str, Any]],
    globals_by_id: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    row = deepcopy(item)
    if _provider_identity(row):
        # Provider-backed rows remain provider-backed. Concept association for
        # provider foods requires its own reviewed mapping and is not guessed here.
        return row, True

    source_name = _source_name(row)
    source_language = _language(
        row.get("originalLanguage") or row.get("language")
    )
    if not source_name or not source_language:
        row["semanticIdentityState"] = "missing-source-evidence"
        return row, False

    source_id = semantics.source_local_ingredient_id(
        source_language, source_name
    )
    concept_id = source_to_concept.get(source_id, "")
    concept = concepts.get(concept_id) if concept_id else None

    row["ingredientId"] = source_id
    row["sourceLocalIdentity"] = True
    row["providerIdentityAssigned"] = False
    if concept is not None:
        row["conceptId"] = concept_id
        row["canonicalName"] = (
            _text(concept.get("canonicalEnglish")) or source_name
        )
        row["classification"] = (
            _text(concept.get("classification")) or "ambiguous"
        )
        row["semanticIdentityState"] = "reviewed"
    else:
        row["classification"] = "ambiguous"
        row["semanticIdentityState"] = "unreviewed-source-local"

    globals_by_id.setdefault(
        source_id,
        _source_local_global_row(
            source_id=source_id,
            source_name=source_name,
            source_language=source_language,
            concept=concept,
        ),
    )
    return row, concept is not None


def enrich_payload(
    payload: dict[str, Any], semantic_payload: dict[str, Any]
) -> dict[str, Any]:
    """Attach safe semantic keyless identity and compiled multilingual search."""
    result = deepcopy(payload)
    source_to_concept, concepts = _semantic_maps(semantic_payload)
    globals_by_id: dict[str, dict[str, Any]] = {
        _text(row.get("id") or row.get("ingredientId") or row.get("key")): deepcopy(row)
        for row in result.get("ingredients") or []
        if isinstance(row, dict)
        and _text(row.get("id") or row.get("ingredientId") or row.get("key"))
    }

    reviewed_keyless_lines = 0
    unresolved_keyless_lines = 0
    source_local_ids: set[str] = set()
    semantic_concepts_used: set[str] = set()

    for recipe in result.get("recipes") or []:
        if not isinstance(recipe, dict):
            continue
        for variant in recipe.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            annotated: list[Any] = []
            for raw in variant.get("ingredients") or []:
                if not isinstance(raw, dict):
                    annotated.append(deepcopy(raw))
                    continue
                if _provider_identity(raw):
                    annotated.append(deepcopy(raw))
                    continue
                row, reviewed = _annotate_keyless_ingredient(
                    raw,
                    source_to_concept=source_to_concept,
                    concepts=concepts,
                    globals_by_id=globals_by_id,
                )
                annotated.append(row)
                source_id = _text(row.get("ingredientId"))
                if source_id:
                    source_local_ids.add(source_id)
                concept_id = _text(row.get("conceptId"))
                if concept_id:
                    semantic_concepts_used.add(concept_id)
                if reviewed:
                    reviewed_keyless_lines += 1
                else:
                    unresolved_keyless_lines += 1
            variant["ingredients"] = annotated

    ingredient_rows = list(globals_by_id.values())
    ingredient_rows.sort(
        key=lambda row: (
            _text(row.get("canonicalName")).casefold(),
            _text(row.get("id") or row.get("key")),
        )
    )
    result["ingredients"] = ingredient_rows

    search = search_index.compile_search_index(result)
    result["searchIndex"] = search

    source = result.setdefault("source", {})
    if not isinstance(source, dict):
        source = {}
        result["source"] = source
    source.update(
        {
            "format": "normalized-ingredient-references-v2-semantic",
            "providerIngredientIdentityPreserved": True,
            "providerIngredientIdentityInferred": False,
            "keylessSourceLocalIdentity": True,
            "semanticIngredientConcepts": True,
            "semanticConceptProviderIdentity": False,
            "compiledMultilingualSearchIndex": True,
            "compiledMultilingualSearchIndexSchemaVersion": int(
                search.get("schemaVersion") or 0
            ),
            "reviewedSemanticConceptCount": len(concepts),
            "semanticConceptsUsedByRecipes": len(semantic_concepts_used),
            "sourceLocalIngredientCount": len(source_local_ids),
            "reviewedKeylessRecipeLineCount": reviewed_keyless_lines,
            "unresolvedKeylessRecipeLineCount": unresolved_keyless_lines,
            "semanticCoverageComplete": unresolved_keyless_lines == 0,
        }
    )

    food_rows = [
        row
        for row in ingredient_rows
        if not row.get("sourceLocalIdentity")
        or row.get("classification") == "food"
    ]
    food_with_nutrition = sum(
        isinstance(row.get("nutrition"), dict)
        and isinstance((row.get("nutrition") or {}).get("values"), dict)
        for row in food_rows
    )
    source["foodIntelligenceIngredientCount"] = len(food_rows)
    source["foodIntelligenceNutritionResolvedCount"] = food_with_nutrition
    source["foodIntelligenceNutritionComplete"] = bool(
        food_rows and food_with_nutrition == len(food_rows)
    )
    source["ingredientIntelligenceComplete"] = bool(
        source.get("semanticCoverageComplete")
        and source.get("foodIntelligenceNutritionComplete")
    )
    return result


def _save_compact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def build(args: argparse.Namespace) -> dict[str, Any]:
    payload = v59.build(args)
    semantic_payload = semantics.compile_from_paths(semantics._review_paths(TOOLS))
    payload = enrich_payload(payload, semantic_payload)
    _save_compact(Path(args.output), payload)
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-home", default=str(Path.home()))
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--catalog-version", required=True)
    parser.add_argument(
        "--output",
        default=str(COMPONENT / "catalog" / "merged_catalog.v1.json"),
    )
    parser.add_argument(
        "--nutrition-cache",
        default=str(ROOT / ".catalog-build" / "fdc-nutrition-cache.json"),
    )
    parser.add_argument("--english-overrides", default="")
    parser.add_argument("--resolve-nutrition", action="store_true")
    parser.add_argument("--allow-missing-nutrition", action="store_true")
    parser.add_argument("--fdc-key", default="")
    parser.add_argument("--fdc-delay", type=float, default=0.15)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--verbose", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
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
                "ingredientIntelligenceComplete": bool(
                    source.get("ingredientIntelligenceComplete")
                ),
                "recipes": len(payload.get("recipes") or []),
                "ingredients": len(payload.get("ingredients") or []),
                "sourceLocalIngredients": int(
                    source.get("sourceLocalIngredientCount") or 0
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
    # Capture completeness remains the release command's exit gate. Food
    # intelligence has its own explicit gate and may be completed independently.
    return 0 if payload.get("complete") else 2


if __name__ == "__main__":
    raise SystemExit(main())
