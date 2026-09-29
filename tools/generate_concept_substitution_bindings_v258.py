#!/usr/bin/env python3
"""Generate exact concept-ID dietary substitution bindings from the offline catalog.

This is an offline migration tool only. It may use canonical catalog text to map
rows to already-reviewed source profiles, but runtime decisions consume only the
generated stable concept IDs. Concepts with conflicting signatures are omitted.
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
CONCEPT_ID = re.compile(r"^concept:food:[0-9a-f]+$")


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, COMP / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


subs = load("cook4me_substitutions_concept_bindings_v258", "ingredient_substitutions.py")


def text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def concept_id(row: Any) -> str:
    value = text(row.get("conceptId")) if isinstance(row, dict) else ""
    return value if CONCEPT_ID.fullmatch(value) else ""


def signature(row: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    profile = subs._candidate_source_profile(row)
    profile_id = text(profile.get("id")) if isinstance(profile, dict) else ""
    diets = tuple(subs._source_diets(row))
    return profile_id, diets


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(CATALOG.read_text(encoding="utf-8"))
    by_concept: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in payload.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        ident = concept_id(row)
        if ident:
            by_concept[ident].append(row)

    grouped: dict[tuple[str, tuple[str, ...]], list[str]] = defaultdict(list)
    ambiguous = []
    untouched = 0
    classified_rows = 0
    profile_counts = Counter()

    for concept in sorted(by_concept):
        rows = by_concept[concept]
        claims: set[tuple[str, tuple[str, ...]]] = set()
        conflict_without_profile = False
        samples = []
        for row in rows:
            profile_id, diets = signature(row)
            if diets and not profile_id:
                conflict_without_profile = True
            if profile_id and diets:
                claims.add((profile_id, diets))
                classified_rows += 1
            if len(samples) < 5:
                samples.append({
                    "id": text(row.get("id") or row.get("ingredientId")),
                    "canonicalName": text(row.get("canonicalName") or row.get("name") or row.get("foodName")),
                    "profileId": profile_id,
                    "substitutionDiets": list(diets),
                })

        if conflict_without_profile or len(claims) > 1:
            ambiguous.append({
                "conceptId": concept,
                "reason": (
                    "diet-conflict-without-reviewed-profile"
                    if conflict_without_profile and len(claims) <= 1
                    else "conflicting-reviewed-signatures"
                ),
                "claims": [
                    {"profileId": profile, "substitutionDiets": list(diets)}
                    for profile, diets in sorted(claims)
                ],
                "samples": samples,
            })
            continue
        if not claims:
            untouched += 1
            continue

        claim = next(iter(claims))
        grouped[claim].append(concept)
        profile_counts[claim[0]] += 1

    bindings = []
    for index, ((profile_id, diets), concepts) in enumerate(
        sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1]))
    ):
        bindings.append({
            "id": f"concept_{profile_id}_{index + 1}",
            "profileId": profile_id,
            "substitutionDiets": list(diets),
            "conceptIds": sorted(concepts),
            "ingredientIds": [],
            "evidence": "offline concept-ID migration from unanimous canonical catalog rows",
        })

    result = {
        "schemaVersion": 1,
        "version": "2026.9.29.2",
        "evidence": "Cook4Me reviewed concept ingredient substitution bindings v1",
        "policy": {
            "runtimeUsesLabels": False,
            "stableConceptIdsOnly": True,
            "ambiguousConceptsOmitted": True,
            "generatedFromCurrentOfflineCatalog": True,
            "sourceProfilesRemainReviewedCatalogDefinitions": True,
        },
        "summary": {
            "conceptsSeen": len(by_concept),
            "bindings": len(bindings),
            "boundConcepts": sum(len(row["conceptIds"]) for row in bindings),
            "ambiguousConcepts": len(ambiguous),
            "untouchedConcepts": untouched,
            "classifiedRows": classified_rows,
            "profileCounts": dict(sorted(profile_counts.items())),
        },
        "ingredientBindings": bindings,
        "ambiguous": ambiguous,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("CONCEPT_SUBSTITUTION_BINDINGS_V258=" + json.dumps(result["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
