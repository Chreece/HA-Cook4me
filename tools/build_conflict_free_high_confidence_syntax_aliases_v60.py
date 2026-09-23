#!/usr/bin/env python3
"""Build the conflict-free high-confidence safe-syntax alias overlay.

The source of truth is the reviewed semantic corpus plus the two report-only audits:
- syntax candidates identify high-confidence concepts that collapse under the
  already-approved syntactic normalizer;
- impact analysis identifies canonical targets whose historical nutrition
  bindings conflict.

Only groups with exactly one existing clean canonical high-confidence target are
eligible, and every target with an FDC conflict is excluded. Historical semantic
and nutrition review files are never rewritten here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
SYNTAX_AUDIT = TOOLS / "audit_high_confidence_semantic_syntax_v60.py"
IMPACT_AUDIT = TOOLS / "audit_high_confidence_semantic_syntax_impact_v60.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


syntax_mod = _load_module("cook4me_high_syntax_alias_builder_audit", SYNTAX_AUDIT)
impact_mod = _load_module("cook4me_high_syntax_alias_builder_impact", IMPACT_AUDIT)

EXPECTED_GROUPS = 112
EXPECTED_ALIASES = 128
EXPECTED_SOURCES = 130
EXPECTED_CONFLICT_GROUPS = 11

POLICY = {
    "providerIdentityAssigned": False,
    "sourceLocalIdentityPreserved": True,
    "highConfidenceOnly": True,
    "safeSyntacticNormalizerRequired": True,
    "cleanCanonicalTargetRequired": True,
    "nutritionConflictTargetsExcluded": True,
    "historicalReviewFilesMutated": False,
}

RATIONALE = (
    "High-confidence reviewed meaning differs only by compiler-approved recipe "
    "syntax/measurement metadata and collapses to an existing clean "
    "high-confidence canonical concept."
)


def build_overlay(review_root: Path) -> dict[str, Any]:
    review_root = review_root.resolve()
    syntax = syntax_mod.build_audit(review_root)
    impact = impact_mod.build_impact(review_root)

    conflict_targets = {
        str(row.get("targetConceptId") or "")
        for row in impact.get("nutritionConflicts") or []
        if str(row.get("targetConceptId") or "")
    }

    items: list[dict[str, Any]] = []
    group_count = 0
    source_count = 0
    seen_old: set[str] = set()
    seen_group_targets: set[tuple[str, str]] = set()

    for group in syntax.get("candidateGroups") or []:
        if not isinstance(group, dict) or not group.get("hasCleanCanonicalMember"):
            continue
        clean_targets = [
            str(value) for value in group.get("cleanCanonicalConceptIds") or []
            if str(value)
        ]
        if len(clean_targets) != 1:
            raise RuntimeError(
                "candidate group lacks one clean canonical target: "
                f"{group.get('safeEnglish')!r} -> {clean_targets!r}"
            )
        target_id = clean_targets[0]
        if target_id in conflict_targets:
            continue

        members = [
            row for row in group.get("members") or [] if isinstance(row, dict)
        ]
        clean_members = [
            row for row in members
            if row.get("semanticConceptId") == target_id
            and row.get("syntaxChanged") is not True
        ]
        if not clean_members:
            raise RuntimeError(
                f"clean target lacks clean reviewed member: {target_id}"
            )
        canonical_values = {
            str(row.get("english") or "") for row in clean_members
            if str(row.get("english") or "")
        }
        if len(canonical_values) != 1:
            raise RuntimeError(
                f"clean target has conflicting English values: {target_id}"
            )
        canonical_english = next(iter(canonical_values))
        classification = str(group.get("classification") or "")

        by_old: dict[str, list[dict[str, Any]]] = {}
        for member in members:
            old_id = str(member.get("semanticConceptId") or "")
            if not old_id or old_id == target_id:
                continue
            by_old.setdefault(old_id, []).append(member)

        if not by_old:
            continue
        group_count += 1
        seen_group_targets.add((target_id, classification))

        for old_id, old_members in sorted(by_old.items()):
            if old_id in seen_old:
                raise RuntimeError(f"duplicate old syntax concept: {old_id}")
            seen_old.add(old_id)
            english_values = {
                str(row.get("english") or "") for row in old_members
                if str(row.get("english") or "")
            }
            if len(english_values) != 1:
                raise RuntimeError(
                    f"old syntax concept has conflicting English values: {old_id}"
                )
            source_ids = sorted(
                {
                    str(row.get("sourceIngredientId") or "")
                    for row in old_members
                    if str(row.get("sourceIngredientId") or "")
                }
            )
            if not source_ids:
                raise RuntimeError(f"old syntax concept has no source identities: {old_id}")
            source_count += len(source_ids)
            items.append(
                {
                    "oldConceptId": old_id,
                    "canonicalConceptId": target_id,
                    "oldCanonicalEnglish": next(iter(english_values)),
                    "canonicalEnglish": canonical_english,
                    "classification": classification,
                    "sourceIngredientIds": source_ids,
                    "method": "existing-safe-syntactic-normalizer",
                    "rationale": RATIONALE,
                }
            )

    items.sort(key=lambda row: (row["canonicalConceptId"], row["oldConceptId"]))
    excluded = sorted(conflict_targets)

    actual = {
        "groupCount": group_count,
        "aliasConceptCount": len(items),
        "sourceIdentityCount": source_count,
        "excludedConflictGroupCount": len(excluded),
    }
    expected = {
        "groupCount": EXPECTED_GROUPS,
        "aliasConceptCount": EXPECTED_ALIASES,
        "sourceIdentityCount": EXPECTED_SOURCES,
        "excludedConflictGroupCount": EXPECTED_CONFLICT_GROUPS,
    }
    if actual != expected:
        raise RuntimeError(
            "high-confidence syntax alias corpus changed; explicit re-review required: "
            f"actual={actual} expected={expected}"
        )
    if group_count != len(seen_group_targets):
        raise RuntimeError("duplicate canonical group accounting in alias overlay")
    if set(seen_old) & {row["canonicalConceptId"] for row in items}:
        raise RuntimeError("high-confidence syntax alias overlay contains a chain")
    if set(excluded) & {row["canonicalConceptId"] for row in items}:
        raise RuntimeError("nutrition-conflict target leaked into alias overlay")

    return {
        "schemaVersion": 1,
        "kind": "cook4me-semantic-high-confidence-syntax-aliases",
        "policy": POLICY,
        "summary": {
            "aliasConceptCount": len(items),
            "groupCount": group_count,
            "sourceIdentityCount": source_count,
            "excludedConflictGroupCount": len(excluded),
        },
        "excludedConflictTargetConceptIds": excluded,
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=TOOLS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = build_overlay(args.review_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
