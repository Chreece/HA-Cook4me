#!/usr/bin/env python3
"""Capture pinned offline USDA/FDC candidate evidence for every v60 review target.

This is review evidence only. It performs no identity selection, writes no
reviewed binding, and never treats candidate rank as identity proof. Each target
is searched independently against the pinned local FDC reference corpus and the
result retains the exact review-target identity and usage impact.

Bulk discovery uses a candidate-only reference index so the hosted runner does
not retain the full raw nutrient payload for every USDA food while reviewing
1,000+ unresolved Cook4Me targets. Exact reviewed-FDC nutrition resolution keeps
using the full reference index elsewhere.
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
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import fdc_reference_data_v60 as reference  # type: ignore  # noqa: E402
import fdc_candidate_reference_data_v60 as candidate_reference  # type: ignore  # noqa: E402

TARGET_KIND = "cook4me-release-catalog-nutrition-review-targets-v60"
EVIDENCE_KIND = "cook4me-fdc-review-target-candidate-evidence-offline-v60"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _validate_targets(value: dict[str, Any]) -> None:
    if value.get("kind") != TARGET_KIND or int(value.get("schemaVersion") or 0) != 1:
        raise RuntimeError(f"expected {TARGET_KIND}")
    policy = value.get("policy") if isinstance(value.get("policy"), dict) else {}
    required = {
        "exactIngredientIdentityCompletenessPreserved": True,
        "providerIdentityInference": False,
        "providerIdentityReviewGrouped": False,
        "sourceLocalGroupingRequiresSemanticConcept": True,
        "sourceLocalGroupingRequiresHighConfidence": True,
        "sourceLocalGroupingRequiresExactCanonicalEnglish": True,
        "reviewedExactFdcProvenanceRequired": True,
        "searchResultAutoAccepted": False,
        "candidateSearchIsIdentityProof": False,
    }
    bad = [key for key, expected in required.items() if policy.get(key) is not expected]
    if bad:
        raise RuntimeError("unsafe review-target policy: " + ", ".join(bad))


def capture(
    targets: dict[str, Any],
    index: Any,
    *,
    max_candidates: int = 12,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_targets(targets)
    maximum = max(1, int(max_candidates))
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    with_candidates = 0
    zero_candidates = 0
    singleton_candidates = 0
    total_candidates = 0
    literal_exact_targets = 0
    unique_literal_exact_targets = 0
    multiple_literal_exact_targets = 0
    alias_fallback_targets = 0
    used_targets = 0
    used_zero_candidates = 0

    raw_targets = [row for row in targets.get("targets") or [] if isinstance(row, dict)]
    for raw in raw_targets:
        target_id = _text(raw.get("reviewTargetId"))
        canonical = _text(raw.get("canonicalEnglishName"))
        if not target_id or not canonical:
            raise RuntimeError("review target lacks identity or canonical English")
        if target_id in seen:
            raise RuntimeError(f"duplicate review target: {target_id}")
        seen.add(target_id)

        candidates = [
            dict(row)
            for row in index.search(canonical, max_candidates=maximum)
            if isinstance(row, dict)
        ]
        total_candidates += len(candidates)
        if candidates:
            with_candidates += 1
        else:
            zero_candidates += 1
        if len(candidates) == 1:
            singleton_candidates += 1

        exact = [
            row
            for row in candidates
            if reference.norm(row.get("description")) == reference.norm(canonical)
        ]
        if exact:
            literal_exact_targets += 1
        if len(exact) == 1:
            unique_literal_exact_targets += 1
        elif len(exact) > 1:
            multiple_literal_exact_targets += 1

        alias_fallback = any(row.get("localEvidenceQueryAlias") is True for row in candidates)
        if alias_fallback:
            alias_fallback_targets += 1
        used = bool(raw.get("usedByRecipe"))
        if used:
            used_targets += 1
            if not candidates:
                used_zero_candidates += 1

        item = deepcopy(raw)
        item["candidateCount"] = len(candidates)
        item["literalExactDescriptionMatchCount"] = len(exact)
        item["literalExactDescriptionFdcIds"] = sorted(
            int(row.get("fdcId") or 0) for row in exact if int(row.get("fdcId") or 0) > 0
        )
        item["candidateAliasFallbackUsed"] = alias_fallback
        item["candidates"] = candidates
        items.append(item)

    if len(items) != int(targets.get("reviewTargetCount") or 0):
        raise RuntimeError(
            "review-target evidence count mismatch: "
            f"targets={targets.get('reviewTargetCount')} evidence={len(items)}"
        )

    manifest_sha = _text(getattr(index, "manifest_sha256", ""))
    if not manifest_sha:
        raise RuntimeError("reference index did not expose manifest SHA256")

    candidate_only = bool(getattr(index, "candidate_only", False))
    indexed_fdc_ids = max(0, int(getattr(index, "indexed_fdc_id_count", 0) or 0))
    payload = {
        "schemaVersion": 1,
        "kind": EVIDENCE_KIND,
        "catalogVersion": _text(targets.get("catalogVersion")),
        "referenceManifestSha256": manifest_sha,
        "sourceTargetKind": TARGET_KIND,
        "maxCandidatesPerTarget": maximum,
        "candidateOnlyReferenceIndex": candidate_only,
        "indexedReferenceFdcIdCount": indexed_fdc_ids,
        "policy": {
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
        },
        "reviewTargetCount": len(items),
        "items": items,
    }
    summary = {
        "catalogVersion": payload["catalogVersion"],
        "referenceManifestSha256": manifest_sha,
        "candidateOnlyReferenceIndex": candidate_only,
        "indexedReferenceFdcIdCount": indexed_fdc_ids,
        "reviewTargetCount": len(items),
        "usedReviewTargetCount": used_targets,
        "withCandidateCount": with_candidates,
        "zeroCandidateCount": zero_candidates,
        "usedZeroCandidateCount": used_zero_candidates,
        "singletonCandidateCount": singleton_candidates,
        "totalCandidateRows": total_candidates,
        "literalExactDescriptionMatchTargetCount": literal_exact_targets,
        "uniqueLiteralExactDescriptionMatchTargetCount": unique_literal_exact_targets,
        "multipleLiteralExactDescriptionMatchTargetCount": multiple_literal_exact_targets,
        "aliasFallbackTargetCount": alias_fallback_targets,
        "selectionCount": 0,
        "networkRequestsPerformed": False,
        "apiKeyRequired": False,
        "secretsPersisted": False,
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True)
    parser.add_argument("--reference-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--max-candidates", type=int, default=12)
    args = parser.parse_args()

    targets = _load(Path(args.targets).expanduser())
    index = candidate_reference.CandidateReferenceIndex(
        Path(args.reference_manifest).expanduser()
    )
    payload, summary = capture(targets, index, max_candidates=args.max_candidates)

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
