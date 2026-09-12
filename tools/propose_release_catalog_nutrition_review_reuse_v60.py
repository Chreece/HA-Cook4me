#!/usr/bin/env python3
"""Build a fail-closed exact-canonical nutrition decision reuse proposal.

This is an offline review aid only. It never writes a reviewed binding and never
accepts a candidate because of search rank. A target is proposed only when:

1. previously reviewed rows with the exact normalized canonical English all
   agree on one FDC ID; and
2. that exact FDC ID is present in the target's own pinned candidate evidence.

The resulting proposal still requires explicit review before any binding is
committed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402

CANDIDATE_KIND = "cook4me-fdc-review-target-candidate-evidence-offline-v60"
PROPOSAL_KIND = "cook4me-nutrition-exact-canonical-reuse-proposal-v60"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", _text(value)).casefold().split()
    )


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _validate_candidates(value: dict[str, Any]) -> None:
    if value.get("kind") != CANDIDATE_KIND:
        raise RuntimeError(f"expected {CANDIDATE_KIND}")
    if not _text(value.get("catalogVersion")):
        raise RuntimeError("candidate evidence catalogVersion is required")
    if not _text(value.get("referenceManifestSha256")):
        raise RuntimeError("candidate evidence referenceManifestSha256 is required")
    policy = value.get("policy") if isinstance(value.get("policy"), dict) else {}
    required = {
        "candidateSearchIsIdentityProof": False,
        "selectionPerformed": False,
        "searchResultAutoAccepted": False,
        "providerIngredientIdentityInference": False,
        "networkRequestsPerformed": False,
        "secretsPersisted": False,
    }
    bad = [
        key
        for key, expected in required.items()
        if policy.get(key) is not expected
    ]
    if bad:
        raise RuntimeError(
            "candidate evidence has unsafe policy: " + ", ".join(bad)
        )


def propose(
    candidates: dict[str, Any],
    reviews: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_candidates(candidates)

    reviewed_ids = set(reviews)
    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    held_history_excluded = 0
    for row in reviews.values():
        if resolver.reviewed_nutrition.holds.profile_hold(row) is not None:
            held_history_excluded += 1
            continue
        canonical = _norm(row.get("canonicalEnglishName"))
        if canonical:
            history[canonical].append(row)

    proposals: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    already_reviewed_skipped = 0
    exact_canonical_history_targets = 0
    missing_own_candidate = 0

    for raw in candidates.get("items") or []:
        if not isinstance(raw, dict):
            continue
        target_id = _text(raw.get("reviewTargetId"))
        canonical_name = _text(raw.get("canonicalEnglishName"))
        if not target_id or not canonical_name:
            continue
        if target_id in reviewed_ids:
            already_reviewed_skipped += 1
            continue

        matching = history.get(_norm(canonical_name), [])
        if not matching:
            continue
        exact_canonical_history_targets += 1

        fdc_ids = sorted(
            {
                int(row["fdcId"])
                for row in matching
                if int(row.get("fdcId") or 0) > 0
            }
        )
        if len(fdc_ids) != 1:
            conflicts.append(
                {
                    "reviewTargetId": target_id,
                    "reviewTargetKind": _text(raw.get("reviewTargetKind")),
                    "canonicalEnglishName": canonical_name,
                    "historicalFdcIds": fdc_ids,
                    "historicalReviewTargetIds": sorted(
                        _text(row.get("reviewTargetId"))
                        for row in matching
                        if _text(row.get("reviewTargetId"))
                    ),
                    "usageCount": int(raw.get("usageCountSum") or 0),
                }
            )
            continue

        fdc_id = fdc_ids[0]
        own_candidates = [
            row
            for row in raw.get("candidates") or []
            if isinstance(row, dict)
        ]
        evidence = next(
            (
                row
                for row in own_candidates
                if int(row.get("fdcId") or 0) == fdc_id
            ),
            None,
        )
        if evidence is None:
            missing_own_candidate += 1
            continue

        proposals.append(
            {
                "reviewTargetId": target_id,
                "reviewTargetKind": _text(raw.get("reviewTargetKind")),
                "canonicalEnglishName": canonical_name,
                "proposedFdcId": fdc_id,
                "confidence": "proposal-only",
                "fdcDescription": _text(evidence.get("description")),
                "fdcDataType": _text(evidence.get("dataType")),
                "candidateEvidenceRank": int(
                    evidence.get("localEvidenceRank") or 0
                ),
                "usageCountAtReview": int(raw.get("usageCountSum") or 0),
                "historicalReviewCount": len(matching),
                "historicalReviewTargetIds": sorted(
                    _text(row.get("reviewTargetId"))
                    for row in matching
                    if _text(row.get("reviewTargetId"))
                ),
                "selectionPerformed": False,
                "needsManualExactIdReview": True,
            }
        )

    proposals.sort(
        key=lambda row: (
            -int(row["usageCountAtReview"]),
            str(row["reviewTargetId"]),
        )
    )
    conflicts.sort(
        key=lambda row: (
            -int(row["usageCount"]),
            str(row["reviewTargetId"]),
        )
    )

    manifest_sha = _text(candidates.get("referenceManifestSha256"))
    payload = {
        "schemaVersion": 1,
        "kind": PROPOSAL_KIND,
        "catalogVersion": _text(candidates.get("catalogVersion")),
        "referenceManifestSha256": manifest_sha,
        "sourceEvidenceKind": CANDIDATE_KIND,
        "policy": {
            "selectionPerformed": False,
            "searchResultAutoAccepted": False,
            "candidateSearchIsIdentityProof": False,
            "providerIdentityInference": False,
            "manualExactIdReviewRequired": True,
            "exactCanonicalHistoryRequired": True,
            "unambiguousHistoricalFdcIdRequired": True,
            "targetOwnCandidateEvidenceRequired": True,
            "networkRequestsPerformed": False,
            "secretsPersisted": False,
        },
        "reviewCorpusCount": len(reviews),
        "heldHistoricalReviewsExcluded": held_history_excluded,
        "proposalCount": len(proposals),
        "conflictCount": len(conflicts),
        "proposals": proposals,
        "conflicts": conflicts,
    }
    summary = {
        "catalogVersion": payload["catalogVersion"],
        "referenceManifestSha256": manifest_sha,
        "reviewCorpusCount": len(reviews),
        "heldHistoricalReviewsExcluded": held_history_excluded,
        "candidateEvidenceTargetCount": len(candidates.get("items") or []),
        "alreadyReviewedTargetSkipped": already_reviewed_skipped,
        "exactCanonicalHistoryTargetCount": exact_canonical_history_targets,
        "proposalCount": len(proposals),
        "proposalUsageCount": sum(
            int(row["usageCountAtReview"]) for row in proposals
        ),
        "conflictCount": len(conflicts),
        "missingTargetOwnCandidateCount": missing_own_candidate,
        "selectionCount": 0,
        "networkRequestsPerformed": False,
        "secretsPersisted": False,
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    args = parser.parse_args()

    candidate_path = Path(args.candidates).expanduser()
    review_root = Path(args.review_root).expanduser()
    output = Path(args.output).expanduser()
    summary_output = (
        Path(args.summary_output).expanduser()
        if args.summary_output
        else None
    )

    candidates = _load(candidate_path)
    reviews = resolver.load_reviews(review_root)
    payload, summary = propose(candidates, reviews)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
