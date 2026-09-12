#!/usr/bin/env python3
"""Create a deterministic nutrition-resolution queue from reviewed catalog prep."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
import unicodedata
from typing import Any


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value)).casefold()


def _load(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _resolved_profile(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and value.get("basis") == "per100g"
        and isinstance(value.get("values"), dict)
        and bool(value["values"])
    )


def snapshot(
    prep: dict[str, Any],
    nutrition: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if prep.get("kind") != "cook4me-release-assembly-prep":
        raise RuntimeError("expected cook4me-release-assembly-prep")
    nutrition = nutrition or {}

    tasks: list[dict[str, Any]] = []
    total_food_identities = 0
    resolved = 0
    unresolved_semantics = 0

    for row in prep.get("providerFoods") or []:
        if not isinstance(row, dict):
            continue
        ident = _text(row.get("key"))
        canonical = _text(row.get("canonicalEnglishName"))
        if not ident:
            continue
        total_food_identities += 1
        if not canonical or _text(row.get("translationTaskId")):
            unresolved_semantics += 1
            continue
        if _resolved_profile(nutrition.get(ident)):
            resolved += 1
            continue
        tasks.append(
            {
                "ingredientId": ident,
                "canonicalEnglishName": canonical,
                "identityKind": "provider",
                "usageCount": int(row.get("usageCount") or 0),
                "usedByRecipe": bool(row.get("usedByRecipe")),
            }
        )

    for row in prep.get("unkeyedIngredients") or []:
        if not isinstance(row, dict):
            continue
        if _text(row.get("classification")).lower() != "food":
            continue
        ident = _text(row.get("localSyntheticIngredientId"))
        canonical = _text(row.get("canonicalEnglishName"))
        total_food_identities += 1
        if not ident or not canonical or _text(row.get("translationTaskId")):
            unresolved_semantics += 1
            continue
        if _resolved_profile(nutrition.get(ident)):
            resolved += 1
            continue
        tasks.append(
            {
                "ingredientId": ident,
                "canonicalEnglishName": canonical,
                "identityKind": "local-keyless",
                "sourceLanguage": _text(row.get("sourceLanguage")).lower(),
                "sourceName": _text(row.get("sourceName")),
                "usageCount": int(row.get("occurrenceCount") or 0),
                "usedByRecipe": bool(int(row.get("occurrenceCount") or 0)),
            }
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
        "kind": "cook4me-release-catalog-nutrition-queue-v59",
        "nutritionBasisRequired": "per100g",
        "identityPolicy": {
            "providerIngredientIdsPreserved": True,
            "keylessFoodIdsRemainLocal": True,
            "equipmentAndOtherExcluded": True,
        },
        "taskCount": len(tasks),
        "tasks": tasks,
    }
    summary = {
        "foodIdentityCount": total_food_identities,
        "resolvedNutritionCount": resolved,
        "pendingNutritionCount": len(tasks),
        "unresolvedSemanticFoodCount": unresolved_semantics,
        "pendingByIdentityKind": dict(sorted(kinds.items())),
        "usedPendingCount": sum(bool(row.get("usedByRecipe")) for row in tasks),
        "unusedProviderPendingCount": sum(
            row.get("identityKind") == "provider" and not row.get("usedByRecipe")
            for row in tasks
        ),
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviewed-prep", required=True)
    parser.add_argument("--nutrition-cache", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    prep = _load(Path(args.reviewed_prep).expanduser())
    nutrition = _load(Path(args.nutrition_cache).expanduser()) if args.nutrition_cache else {}
    payload, summary = snapshot(prep, nutrition)
    Path(args.output).expanduser().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    Path(args.summary).expanduser().write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["unresolvedSemanticFoodCount"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
