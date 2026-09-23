#!/usr/bin/env python3
"""Snapshot unresolved v60 semantics into conservative source-local dispositions.

This tool never merges identities and never grants nutrition/diet/allergen safety
eligibility. It converts an already reviewed unresolved audit into an explicit,
pinned disposition ledger so genuinely source-local or fragmentary labels do not
remain indefinitely marked as awaiting semantic review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

AUDIT_KIND = "cook4me-remaining-semantic-ingredient-audit-v60"
OUTPUT_KIND = "cook4me-semantic-ingredient-standalone-dispositions"
MERGEABLE = {"food", "equipment", "other"}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def snapshot(audit: dict[str, Any]) -> dict[str, Any]:
    if audit.get("schemaVersion") != 1 or audit.get("kind") != AUDIT_KIND:
        raise RuntimeError("unsupported unresolved semantic audit")
    policy = audit.get("policy")
    if not isinstance(policy, dict):
        raise RuntimeError("missing unresolved audit policy")
    if policy.get("automaticApproval") is not False:
        raise RuntimeError("unresolved audit unexpectedly allows automatic approval")
    if policy.get("providerIdentityAssigned") is not False:
        raise RuntimeError("unresolved audit unexpectedly assigns provider identity")

    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(audit.get("items") or [], 1):
        if not isinstance(raw, dict):
            raise RuntimeError(f"audit item {index}: expected object")
        source_id = _text(raw.get("sourceIngredientId"))
        english = _text(raw.get("english"))
        classification = _text(raw.get("classification")).lower()
        language = _text(raw.get("language")).lower()
        source = _text(raw.get("source"))
        if not source_id.startswith("local:") or not english or not classification:
            raise RuntimeError(f"audit item {index}: incomplete reviewed identity")
        if source_id in seen:
            raise RuntimeError(f"duplicate source identity in audit: {source_id}")
        seen.add(source_id)

        if classification == "ambiguous":
            disposition = "reviewed-ambiguous-source-fragment"
            rationale = (
                "The retained source label is incomplete, fragmentary, or otherwise "
                "insufficient to identify a safer food/equipment concept. Preserve the "
                "exact source-local identity as reviewed ambiguous without safety eligibility."
            )
        elif classification in MERGEABLE:
            disposition = "reviewed-source-local-standalone"
            rationale = (
                "The reviewed label has a usable classification and English meaning but "
                "does not have evidence for a safe cross-identity merge. Preserve it as "
                "its own reviewed source-local concept without safety eligibility."
            )
        else:
            raise RuntimeError(
                f"audit item {index}: unsupported classification {classification!r}"
            )

        items.append(
            {
                "sourceIngredientId": source_id,
                "language": language,
                "source": source,
                "sourceReviewedEnglish": english,
                "classification": classification,
                "disposition": disposition,
                "rationale": rationale,
            }
        )

    items.sort(key=lambda row: row["sourceIngredientId"])
    ambiguous_count = sum(
        row["disposition"] == "reviewed-ambiguous-source-fragment"
        for row in items
    )
    return {
        "schemaVersion": 1,
        "kind": OUTPUT_KIND,
        "policy": {
            "providerIdentityAssigned": False,
            "sourceLocalIdentityPreserved": True,
            "crossIdentityMergeAllowed": False,
            "reviewDispositionOnly": True,
            "exactReviewedEnglishAndClassificationRequired": True,
            "safetyEligibilityGranted": False,
        },
        "summary": {
            "standaloneDispositionCount": len(items),
            "reviewedAmbiguousCount": ambiguous_count,
            "reviewedSourceLocalStandaloneCount": len(items) - ambiguous_count,
        },
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    result = snapshot(audit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
