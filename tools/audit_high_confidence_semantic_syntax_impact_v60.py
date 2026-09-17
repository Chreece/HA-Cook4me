#!/usr/bin/env python3
"""Report references to high-confidence syntax-only concepts before consolidation."""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
AUDIT_MODULE = TOOLS / "audit_high_confidence_semantic_syntax_v60.py"

spec = importlib.util.spec_from_file_location("cook4me_high_syntax_audit_impact", AUDIT_MODULE)
audit_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit_mod)


def build_impact(review_root: Path) -> dict[str, Any]:
    audit = audit_mod.build_audit(review_root)
    collapse_map: dict[str, str] = {}
    groups: list[dict[str, Any]] = []
    for group in audit.get("candidateGroups") or []:
        if not group.get("hasCleanCanonicalMember"):
            continue
        clean_ids = list(group.get("cleanCanonicalConceptIds") or [])
        if len(clean_ids) != 1:
            raise RuntimeError(
                f"safe-syntax group lacks unique clean target: {group.get('safeEnglish')}"
            )
        target = clean_ids[0]
        old_ids = sorted(
            concept_id
            for concept_id in {
                member["semanticConceptId"] for member in group.get("members") or []
            }
            if concept_id != target
        )
        for old_id in old_ids:
            previous = collapse_map.setdefault(old_id, target)
            if previous != target:
                raise RuntimeError(f"concept has multiple syntax targets: {old_id}")
        groups.append(
            {
                "safeEnglish": group["safeEnglish"],
                "classification": group["classification"],
                "targetConceptId": target,
                "collapsedConceptIds": old_ids,
                "syntaxChangedSourceIngredientIds": sorted(
                    member["sourceIngredientId"]
                    for member in group.get("members") or []
                    if member.get("syntaxChanged") is True
                ),
            }
        )

    path_refs: dict[str, dict[str, int]] = {}
    suffixes = {".json", ".txt", ".md", ".py"}
    excluded_names = {
        "audit_high_confidence_semantic_syntax_v60.py",
        "audit_high_confidence_semantic_syntax_impact_v60.py",
    }
    for path in sorted(review_root.rglob("*")):
        if not path.is_file() or path.suffix not in suffixes or path.name in excluded_names:
            continue
        # Review source files generate the concepts but do not refer to concept IDs.
        if path.name.startswith("release_catalog_reviewed_keyless_ingredients"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        found: dict[str, int] = {}
        for old_id in collapse_map:
            count = text.count(old_id)
            if count:
                found[old_id] = count
        if found:
            path_refs[str(path.relative_to(ROOT))] = found

    semantic_confirmation_refs: list[dict[str, Any]] = []
    confirmation_path = review_root / "release_catalog_semantic_confirmations.v1.json"
    if confirmation_path.exists():
        doc = json.loads(confirmation_path.read_text(encoding="utf-8"))
        for row in doc.get("items") or []:
            if not isinstance(row, dict):
                continue
            old_id = str(row.get("confirmedConceptId") or "")
            if old_id in collapse_map:
                semantic_confirmation_refs.append(
                    {
                        "sourceIngredientId": row.get("sourceIngredientId"),
                        "oldConceptId": old_id,
                        "targetConceptId": collapse_map[old_id],
                        "manualSemanticEquivalence": row.get("manualSemanticEquivalence") is True,
                    }
                )

    nutrition_refs: list[dict[str, Any]] = []
    for path in sorted(review_root.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for row in doc.get("items") or []:
            if not isinstance(row, dict):
                continue
            target_id = str(row.get("reviewTargetId") or "")
            if target_id in collapse_map:
                nutrition_refs.append(
                    {
                        "reviewFile": path.name,
                        "oldReviewTargetId": target_id,
                        "targetConceptId": collapse_map[target_id],
                        "fdcId": row.get("fdcId"),
                        "fdcDescription": row.get("fdcDescription"),
                    }
                )

    target_fdc: dict[str, set[str]] = {}
    for path in sorted(review_root.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for row in doc.get("items") or []:
            if not isinstance(row, dict):
                continue
            rid = str(row.get("reviewTargetId") or "")
            if rid in set(collapse_map.values()) and row.get("fdcId") not in (None, ""):
                target_fdc.setdefault(rid, set()).add(str(row["fdcId"]))

    conflicts: list[dict[str, Any]] = []
    old_fdc_by_target: dict[str, set[str]] = {}
    for row in nutrition_refs:
        if row.get("fdcId") in (None, ""):
            continue
        old_fdc_by_target.setdefault(row["targetConceptId"], set()).add(str(row["fdcId"]))
    for target in sorted(set(old_fdc_by_target) | set(target_fdc)):
        old_values = old_fdc_by_target.get(target, set())
        target_values = target_fdc.get(target, set())
        combined = old_values | target_values
        if len(combined) > 1:
            conflicts.append(
                {
                    "targetConceptId": target,
                    "collapsedFdcIds": sorted(old_values),
                    "existingTargetFdcIds": sorted(target_values),
                    "combinedFdcIds": sorted(combined),
                }
            )

    path_reference_counts = Counter()
    for refs in path_refs.values():
        for concept_id, count in refs.items():
            path_reference_counts[concept_id] += count

    return {
        "schemaVersion": 1,
        "kind": "cook4me-high-confidence-semantic-syntax-impact-audit",
        "policy": {
            "automaticApproval": False,
            "repositoryMutated": False,
            "providerIdentityAssigned": False,
            "nutritionBindingsMutated": False,
        },
        "summary": {
            "candidateGroupCount": len(groups),
            "collapsedConceptCount": len(collapse_map),
            "syntaxChangedSourceIdentityCount": sum(
                len(group["syntaxChangedSourceIngredientIds"]) for group in groups
            ),
            "referencedCollapsedConceptCount": len(path_reference_counts),
            "referencePathCount": len(path_refs),
            "semanticConfirmationReferenceCount": len(semantic_confirmation_refs),
            "nutritionReviewReferenceCount": len(nutrition_refs),
            "nutritionConflictCount": len(conflicts),
        },
        "collapseMap": dict(sorted(collapse_map.items())),
        "groups": groups,
        "pathReferences": path_refs,
        "semanticConfirmationReferences": semantic_confirmation_refs,
        "nutritionReviewReferences": nutrition_refs,
        "nutritionConflicts": conflicts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=TOOLS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_impact(args.review_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
