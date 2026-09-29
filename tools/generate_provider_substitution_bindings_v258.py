#!/usr/bin/env python3
"""Generate a reviewed-input proposal for provider-ID substitution bindings.

This is an offline migration/audit tool. Runtime substitution decisions never use
these labels: the generated catalog binds stable M_FOOD IDs to reviewed profile
IDs and diet conflicts. Ambiguous provider IDs are intentionally omitted.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "cook4me"
CATALOG = COMP / "catalog" / "merged_catalog.v1.json"
PROVIDER_ID = re.compile(r"^M_FOOD_\d+$")


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, COMP / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


logic = load("cook4me_recipe_logic_provider_bindings_v258", "recipe_logic.py")
subs = load("cook4me_substitutions_provider_bindings_v258", "ingredient_substitutions.py")


def text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def provider_id(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    for key in ("ingredientId", "id", "key", "foodKey"):
        value = text(row.get(key))
        if PROVIDER_ID.fullmatch(value):
            return value
    return ""


def label(row: dict[str, Any]) -> str:
    return text(
        row.get("canonicalName")
        or row.get("foodName")
        or row.get("name")
        or row.get("originalName")
        or row.get("applicationDescription")
        or row.get("applianceDescription")
    )


def profile_id(row: dict[str, Any]) -> str:
    profile = subs._candidate_source_profile(row)
    return text(profile.get("id")) if isinstance(profile, dict) else ""


def binding_signature(row: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    return profile_id(row), tuple(subs._source_diets(row))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for recipe in payload.get("recipes") or []:
        if not isinstance(recipe, dict):
            continue
        for variant in recipe.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            for row in variant.get("ingredients") or []:
                ident = provider_id(row)
                if ident:
                    occurrences[ident].append(row)

    bindings = []
    ambiguous = []
    untouched = 0
    covered_occurrences = 0
    profile_counts = Counter()

    for ident in sorted(occurrences, key=lambda value: int(value.rsplit("_", 1)[1])):
        rows = occurrences[ident]
        signatures = Counter(binding_signature(row) for row in rows)
        relevant = {
            signature: count
            for signature, count in signatures.items()
            if signature[0] or signature[1]
        }
        if not relevant:
            untouched += 1
            continue
        if len(relevant) != 1 or sum(relevant.values()) != len(rows):
            ambiguous.append({
                "ingredientId": ident,
                "occurrences": len(rows),
                "signatures": [
                    {
                        "profileId": signature[0],
                        "substitutionDiets": list(signature[1]),
                        "count": count,
                    }
                    for signature, count in signatures.most_common()
                ],
                "labels": sorted({label(row) for row in rows if label(row)})[:12],
            })
            continue

        (profile, diets), count = next(iter(relevant.items()))
        if not profile:
            ambiguous.append({
                "ingredientId": ident,
                "occurrences": len(rows),
                "reason": "diet-conflict-without-reviewed-profile",
                "substitutionDiets": list(diets),
                "labels": sorted({label(row) for row in rows if label(row)})[:12],
            })
            continue

        bindings.append({
            "id": "provider_" + ident.lower(),
            "ingredientIds": [ident],
            "profileId": profile,
            "substitutionDiets": list(diets),
            "evidence": "offline provider-ID migration from stable catalog occurrences",
        })
        profile_counts[profile] += 1
        covered_occurrences += count

    result = {
        "schemaVersion": 1,
        "kind": "cook4me-provider-substitution-bindings-proposal",
        "policy": {
            "runtimeUsesLabels": False,
            "stableProviderIdsOnly": True,
            "ambiguousProviderIdsOmitted": True,
            "profileDefinitionsRemainIngredientSubstitutionCatalog": True,
        },
        "summary": {
            "providerIdsSeen": len(occurrences),
            "bindings": len(bindings),
            "ambiguousProviderIds": len(ambiguous),
            "untouchedProviderIds": untouched,
            "boundOccurrences": covered_occurrences,
            "profileCounts": dict(sorted(profile_counts.items())),
        },
        "ingredientBindings": bindings,
        "ambiguous": ambiguous,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PROVIDER_SUBSTITUTION_BINDINGS_V258=" + json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
