#!/usr/bin/env python3
"""Classify offline FDC candidate evidence into deterministic review lanes.

This classifier never creates or approves a nutrition binding.  It only turns the
bulk offline candidate-evidence artifact into a compact, impact-ranked worklist so
review can proceed in large homogeneous batches without weakening v60 identity
policy.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

EVIDENCE_KIND = "cook4me-fdc-review-target-candidate-evidence-offline-v60"
TRIAGE_KIND = "cook4me-fdc-review-target-candidate-triage-v60"

_LANE_ORDER = {
    "unique-literal-exact": 0,
    "multiple-literal-exact": 1,
    "singleton-nonexact": 2,
    "multi-candidate": 3,
    "zero-candidate": 4,
}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _validate(value: dict[str, Any]) -> None:
    if value.get("kind") != EVIDENCE_KIND or int(value.get("schemaVersion") or 0) != 1:
        raise RuntimeError(f"expected {EVIDENCE_KIND}")
    policy = value.get("policy") if isinstance(value.get("policy"), dict) else {}
    required = {
        "candidateSearchIsIdentityProof": False,
        "selectionPerformed": False,
        "searchResultAutoAccepted": False,
        "providerIngredientIdentityInference": False,
        "reviewedExactFdcBindingRequired": True,
        "literalExactDescriptionIsIdentityProof": False,
        "singletonCandidateIsIdentityProof": False,
        "aliasFallbackIsIdentityProof": False,
        "networkRequestsPerformed": False,
        "apiKeyRequired": False,
        "secretsPersisted": False,
    }
    bad = [key for key, expected in required.items() if policy.get(key) is not expected]
    if bad:
        raise RuntimeError("unsafe candidate-evidence policy: " + ", ".join(bad))


def _lane(row: dict[str, Any]) -> str:
    candidate_count = max(0, int(row.get("candidateCount") or 0))
    exact_count = max(0, int(row.get("literalExactDescriptionMatchCount") or 0))
    if candidate_count == 0:
        return "zero-candidate"
    if exact_count == 1:
        return "unique-literal-exact"
    if exact_count > 1:
        return "multiple-literal-exact"
    if candidate_count == 1:
        return "singleton-nonexact"
    return "multi-candidate"


def classify(value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate(value)
    raw_items = [row for row in value.get("items") or [] if isinstance(row, dict)]
    expected = int(value.get("reviewTargetCount") or 0)
    if len(raw_items) != expected:
        raise RuntimeError(
            f"candidate evidence target count mismatch: declared={expected} actual={len(raw_items)}"
        )

    seen: set[str] = set()
    items: list[dict[str, Any]] = []
    lane_counts: Counter[str] = Counter()
    lane_usage: Counter[str] = Counter()
    lane_members: Counter[str] = Counter()
    lane_used_targets: Counter[str] = Counter()
    alias_counts: Counter[str] = Counter()
    candidate_rows_by_lane: Counter[str] = Counter()

    for raw in raw_items:
        target_id = _text(raw.get("reviewTargetId"))
        if not target_id:
            raise RuntimeError("candidate evidence row lacks reviewTargetId")
        if target_id in seen:
            raise RuntimeError(f"duplicate review target: {target_id}")
        seen.add(target_id)

        lane = _lane(raw)
        usage = max(0, int(raw.get("usageCountSum") or 0))
        members = max(0, int(raw.get("memberCount") or 0))
        candidate_count = max(0, int(raw.get("candidateCount") or 0))
        alias = raw.get("candidateAliasFallbackUsed") is True

        row = deepcopy(raw)
        row["triageLane"] = lane
        row["manualReviewRequired"] = True
        row["bindingCreated"] = False
        items.append(row)

        lane_counts[lane] += 1
        lane_usage[lane] += usage
        lane_members[lane] += members
        lane_used_targets[lane] += int(bool(raw.get("usedByRecipe")))
        candidate_rows_by_lane[lane] += candidate_count
        if alias:
            alias_counts[lane] += 1

    items.sort(
        key=lambda row: (
            _LANE_ORDER[_text(row.get("triageLane"))],
            -int(row.get("usageCountSum") or 0),
            _text(row.get("canonicalEnglishName")).casefold(),
            _text(row.get("reviewTargetId")),
        )
    )

    lane_summaries = []
    for lane in _LANE_ORDER:
        count = lane_counts[lane]
        lane_summaries.append(
            {
                "lane": lane,
                "reviewTargetCount": count,
                "memberIdentityCount": lane_members[lane],
                "usedReviewTargetCount": lane_used_targets[lane],
                "usageCountSum": lane_usage[lane],
                "candidateRowCount": candidate_rows_by_lane[lane],
                "aliasFallbackTargetCount": alias_counts[lane],
                "manualReviewRequired": True,
                "bindingCreatedCount": 0,
            }
        )

    payload = {
        "schemaVersion": 1,
        "kind": TRIAGE_KIND,
        "catalogVersion": _text(value.get("catalogVersion")),
        "referenceManifestSha256": _text(value.get("referenceManifestSha256")),
        "sourceEvidenceKind": EVIDENCE_KIND,
        "reviewTargetCount": len(items),
        "policy": {
            "classificationOnly": True,
            "manualReviewRequired": True,
            "selectionPerformed": False,
            "bindingCreated": False,
            "candidateRankIsIdentityProof": False,
            "literalExactDescriptionIsIdentityProof": False,
            "singletonCandidateIsIdentityProof": False,
            "providerIngredientIdentityInference": False,
            "networkRequestsPerformed": False,
            "secretsPersisted": False,
        },
        "lanes": lane_summaries,
        "items": items,
    }
    summary = {
        "catalogVersion": payload["catalogVersion"],
        "referenceManifestSha256": payload["referenceManifestSha256"],
        "reviewTargetCount": len(items),
        "memberIdentityCount": sum(lane_members.values()),
        "usedReviewTargetCount": sum(lane_used_targets.values()),
        "usageCountSum": sum(lane_usage.values()),
        "reviewTargetsByLane": dict(lane_counts),
        "memberIdentitiesByLane": dict(lane_members),
        "usageByLane": dict(lane_usage),
        "aliasFallbackByLane": dict(alias_counts),
        "selectionCount": 0,
        "bindingCreatedCount": 0,
        "networkRequestsPerformed": False,
        "secretsPersisted": False,
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output", required=True)
    args = parser.parse_args()

    evidence = _load(Path(args.evidence).expanduser())
    payload, summary = classify(evidence)
    output = Path(args.output).expanduser()
    summary_path = Path(args.summary_output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
