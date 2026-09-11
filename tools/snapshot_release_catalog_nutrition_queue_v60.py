#!/usr/bin/env python3
"""Create the v60 nutrition-review queue from an immutable release catalog.

Only identities that are already proven food identities are eligible. Provider
identities remain authoritative only when the explicit provider key is preserved
exactly as the ingredient ID. Reviewed source-local concepts are eligible only
when the semantic compiler explicitly marks them nutrition-safe. Equipment,
other, ambiguous, and semantically-unconfirmed source-local rows are never
turned into nutrition tasks.

A structurally valid legacy per-100-g cache entry is not enough to satisfy v60:
resolved nutrition must carry exact-FDC manual-review provenance.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import ingredient_identity  # type: ignore  # noqa: E402
import provider_identity_v60  # type: ignore  # noqa: E402
import reviewed_nutrition_v60 as reviewed_nutrition  # type: ignore  # noqa: E402


_NON_FOOD = {"equipment", "other", "ambiguous"}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value)).casefold()


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _identity(row: dict[str, Any]) -> str:
    return _text(
        row.get("id")
        or row.get("ingredientId")
        or row.get("key")
        or row.get("foodKey")
    )


def _identity_kind(row: dict[str, Any], ident: str) -> str:
    provider_key = provider_identity_v60.provider_key(row)
    source_local = bool(row.get("sourceLocalIdentity")) or ident.startswith("local:")
    if source_local:
        return "unknown" if provider_key else "source-local"
    if provider_identity_v60.preserved_provider_identity(row, ident):
        return "provider"
    return "unknown"


def _nutrition_eligible(row: dict[str, Any], kind: str) -> bool:
    if kind == "provider":
        # The provider key itself is authoritative; no namespace prefix is
        # inferred or required by the v60 release contract.
        return True
    if kind != "source-local":
        return False
    classification = _text(row.get("classification")).lower()
    return bool(
        classification == "food"
        and classification not in _NON_FOOD
        and row.get("nutritionEligible") is True
        and row.get("needsSemanticConfirmation") is not True
        and _text(row.get("conceptId"))
    )


def _usage_count(row: dict[str, Any], dependencies: dict[str, Any]) -> int:
    """Count affected logical recipes across all canonical v60 identity aliases."""
    affected: set[int] = set()
    for candidate in ingredient_identity.identity_candidates(row):
        indices = dependencies.get(candidate)
        if not isinstance(indices, (list, tuple, set)):
            continue
        affected.update(index for index in indices if isinstance(index, int) and index >= 0)
    return len(affected)


def snapshot(
    catalog: dict[str, Any],
    nutrition_cache: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if int(catalog.get("schemaVersion") or 0) != 1:
        raise RuntimeError("expected release catalog schemaVersion=1")
    source = catalog.get("source") if isinstance(catalog.get("source"), dict) else {}
    if source.get("semanticCoverageComplete") is not True:
        raise RuntimeError("v60 semantic coverage must be complete before nutrition review")

    nutrition_cache = nutrition_cache or {}
    dependencies = (
        catalog.get("recipeDependencyIndex")
        if isinstance(catalog.get("recipeDependencyIndex"), dict)
        else {}
    )

    tasks: list[dict[str, Any]] = []
    resolved = 0
    food_identities = 0
    excluded_by_classification = Counter()
    invalid_food_rows: list[str] = []
    rejected_unreviewed_cache = 0
    rejected_unreviewed_embedded = 0

    for raw in catalog.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        ident = _identity(raw)
        if not ident:
            continue
        kind = _identity_kind(raw, ident)
        classification = _text(raw.get("classification")).lower()
        if not _nutrition_eligible(raw, kind):
            if kind == "source-local":
                excluded_by_classification[classification or "unclassified"] += 1
            continue

        canonical = _text(raw.get("canonicalName"))
        if not canonical:
            invalid_food_rows.append(ident)
            continue
        food_identities += 1

        cached = nutrition_cache.get(ident)
        embedded = raw.get("nutrition")
        cached_reviewed = reviewed_nutrition.is_reviewed_profile(
            cached,
            ingredient_id=ident,
            canonical_name=canonical,
        )
        embedded_reviewed = reviewed_nutrition.is_reviewed_profile(
            embedded,
            ingredient_id=ident,
            canonical_name=canonical,
        )
        if cached_reviewed or embedded_reviewed:
            resolved += 1
            continue
        if isinstance(cached, dict) and cached:
            rejected_unreviewed_cache += 1
        if isinstance(embedded, dict) and embedded:
            rejected_unreviewed_embedded += 1

        usage_count = _usage_count(raw, dependencies)
        task: dict[str, Any] = {
            "ingredientId": ident,
            "canonicalEnglishName": canonical,
            "identityKind": kind,
            "usageCount": usage_count,
            "usedByRecipe": bool(usage_count),
        }
        if kind == "source-local":
            task.update(
                {
                    "conceptId": _text(raw.get("conceptId")),
                    "sourceLanguage": _text(
                        raw.get("sourceLanguage") or raw.get("originalLanguage")
                    ).lower(),
                    "reviewConfidence": _text(raw.get("reviewConfidence")),
                    "semanticReviewFile": _text(raw.get("semanticReviewFile")),
                }
            )
        tasks.append(
            {key: value for key, value in task.items() if value not in ("", None)}
        )

    if invalid_food_rows:
        raise RuntimeError(
            "nutrition-eligible ingredients missing canonical names: "
            + ", ".join(sorted(invalid_food_rows)[:20])
        )

    tasks.sort(
        key=lambda row: (
            -int(row.get("usageCount") or 0),
            0 if row.get("identityKind") == "provider" else 1,
            _norm(row.get("canonicalEnglishName")),
            _text(row.get("ingredientId")),
        )
    )
    kinds = Counter(_text(row.get("identityKind")) for row in tasks)
    payload = {
        "schemaVersion": 1,
        "kind": "cook4me-release-catalog-nutrition-queue-v60",
        "nutritionBasisRequired": "per100g",
        "identityPolicy": {
            "providerIngredientIdsPreserved": True,
            "providerKeyMustMatchIngredientId": True,
            "providerIdentityInference": False,
            "sourceLocalFoodRequiresReviewedNutritionEligibility": True,
            "reviewedExactFdcProvenanceRequired": True,
            "legacyStructuralNutritionAccepted": False,
            "ambiguousExcluded": True,
            "equipmentAndOtherExcluded": True,
            "searchResultAutoAccepted": False,
        },
        "catalogVersion": _text(catalog.get("catalogVersion")),
        "taskCount": len(tasks),
        "tasks": tasks,
    }
    summary = {
        "foodIdentityCount": food_identities,
        "resolvedNutritionCount": resolved,
        "pendingNutritionCount": len(tasks),
        "pendingByIdentityKind": dict(sorted(kinds.items())),
        "usedPendingCount": sum(bool(row.get("usedByRecipe")) for row in tasks),
        "excludedSourceLocalByClassification": dict(
            sorted(excluded_by_classification.items())
        ),
        "rejectedUnreviewedCacheCount": rejected_unreviewed_cache,
        "rejectedUnreviewedEmbeddedCount": rejected_unreviewed_embedded,
        "semanticCoverageComplete": True,
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--nutrition-cache", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    catalog = _load(Path(args.catalog).expanduser(), {})
    cache = (
        _load(Path(args.nutrition_cache).expanduser(), {})
        if args.nutrition_cache
        else {}
    )
    if not isinstance(catalog, dict):
        raise RuntimeError("catalog must be a JSON object")
    if not isinstance(cache, dict):
        raise RuntimeError("nutrition cache must be a JSON object")
    payload, summary = snapshot(catalog, cache)
    Path(args.output).expanduser().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    Path(args.summary).expanduser().write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())