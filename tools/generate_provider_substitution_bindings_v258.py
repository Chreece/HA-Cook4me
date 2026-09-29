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
    global_rows: dict[str, dict[str, Any]] = {}
    for row in payload.get("ingredients") or []:
        ident = provider_id(row)
        if ident:
            global_rows[ident] = row

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

    # Build reviewed concept-level bindings offline. Runtime never classifies by
    # these labels; it consumes only the emitted stable concept IDs. A concept is
    # emitted only when every informative catalog row agrees on one
    # (profileId, substitutionDiets) signature.
    concept_signatures: dict[str, set[tuple[str, tuple[str, ...]]]] = defaultdict(set)
    concept_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        concept = text(row.get("conceptId"))
        if not concept:
            continue
        concept_rows[concept].append(row)
        signature = binding_signature(row)
        if signature[0] or signature[1]:
            concept_signatures[concept].add(signature)

    for ident in sorted(occurrences, key=lambda value: int(value.rsplit("_", 1)[1])):
        rows = occurrences[ident]
        source = global_rows.get(ident)
        if not isinstance(source, dict):
            untouched += 1
            continue
        profile, diets = binding_signature(source)
        if not profile and not diets:
            untouched += 1
            continue
        if diets and not profile:
            ambiguous.append({
                "ingredientId": ident,
                "occurrences": len(rows),
                "reason": "diet-conflict-without-reviewed-profile",
                "substitutionDiets": list(diets),
                "labels": [label(source)] if label(source) else [],
            })
            continue
        count = len(rows)

        bindings.append({
            "id": "provider_" + ident.lower(),
            "ingredientIds": [ident],
            "profileId": profile,
            "substitutionDiets": list(diets),
            "evidence": "offline provider-ID migration from stable catalog occurrences",
        })
        profile_counts[profile] += 1
        covered_occurrences += count

    concept_groups: dict[tuple[str, tuple[str, ...]], list[str]] = defaultdict(list)
    ambiguous_concepts = []
    untouched_concepts = 0
    for concept in sorted(concept_rows):
        signatures = concept_signatures.get(concept) or set()
        if not signatures:
            untouched_concepts += 1
            continue
        if len(signatures) != 1:
            ambiguous_concepts.append({
                "conceptId": concept,
                "reason": "conflicting-reviewed-signatures",
                "signatures": [
                    {"profileId": profile, "substitutionDiets": list(diets)}
                    for profile, diets in sorted(signatures)
                ],
                "labels": list(dict.fromkeys(
                    label(row) for row in concept_rows[concept] if label(row)
                ))[:12],
            })
            continue
        profile, diets = next(iter(signatures))
        if diets and not profile:
            ambiguous_concepts.append({
                "conceptId": concept,
                "reason": "diet-conflict-without-reviewed-profile",
                "substitutionDiets": list(diets),
                "labels": list(dict.fromkeys(
                    label(row) for row in concept_rows[concept] if label(row)
                ))[:12],
            })
            continue
        if not profile:
            untouched_concepts += 1
            continue
        concept_groups[(profile, diets)].append(concept)

    for (profile, diets), concept_ids in sorted(
        concept_groups.items(), key=lambda item: (item[0][0], item[0][1])
    ):
        suffix = "_".join(diets) if diets else "allergy"
        bindings.append({
            "id": f"concept_{profile}_{suffix}",
            "conceptIds": sorted(concept_ids),
            "profileId": profile,
            "substitutionDiets": list(diets),
            "evidence": "offline unanimous concept-ID migration from current catalog",
        })

    top_provider_ids = sorted(
        occurrences,
        key=lambda ident: (-len(occurrences[ident]), ident),
    )[:30]
    diagnostics = []
    for ident in top_provider_ids:
        sample = global_rows.get(ident) or occurrences[ident][0]
        diagnostics.append({
            "ingredientId": ident,
            "occurrences": len(occurrences[ident]),
            "row": sample,
            "ingredientText": logic._ingredient_text(sample),
            "sourceDiets": list(subs._source_diets(sample)),
            "candidateProfileId": profile_id(sample),
        })

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
            "providerGlobalRows": len(global_rows),
            "bindings": len(bindings),
            "providerBindings": len([
                row for row in bindings if row.get("ingredientIds")
            ]),
            "conceptBindings": len([
                row for row in bindings if row.get("conceptIds")
            ]),
            "conceptIds": sum(
                len(row.get("conceptIds") or []) for row in bindings
            ),
            "ambiguousProviderIds": len(ambiguous),
            "ambiguousConcepts": len(ambiguous_concepts),
            "untouchedProviderIds": untouched,
            "untouchedConcepts": untouched_concepts,
            "boundOccurrences": covered_occurrences,
            "profileCounts": dict(sorted(profile_counts.items())),
        },
        "ingredientBindings": bindings,
        "ambiguous": ambiguous,
        "ambiguousConcepts": ambiguous_concepts,
        "diagnostics": diagnostics,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PROVIDER_SUBSTITUTION_BINDINGS_V258=" + json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
