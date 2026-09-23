#!/usr/bin/env python3
"""Extract a small review-only lane from the unresolved semantic audit.

This never approves a mapping. It only surfaces rows whose best already-reviewed,
high-confidence concept has strong token overlap and is clearly better than the
runner-up. Human semantic review is still required before any source ID can be
added to a confirmation file.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def extract(
    payload: dict[str, Any],
    *,
    minimum_score: float = 0.8,
    minimum_gap: float = 0.15,
) -> dict[str, Any]:
    selected: list[dict[str, Any]] = []
    for row in payload.get("items") or []:
        if not isinstance(row, dict) or row.get("classification") == "ambiguous":
            continue
        candidates = [
            candidate
            for candidate in row.get("candidateTargets") or []
            if isinstance(candidate, dict)
        ]
        if not candidates or any(
            candidate.get("exactLooseText") is True for candidate in candidates
        ):
            continue
        candidates.sort(
            key=lambda candidate: (
                _number(candidate.get("tokenJaccard")),
                str(candidate.get("conceptId") or ""),
            ),
            reverse=True,
        )
        best_score = _number(candidates[0].get("tokenJaccard"))
        second_score = (
            _number(candidates[1].get("tokenJaccard"))
            if len(candidates) > 1
            else 0.0
        )
        gap = best_score - second_score
        if best_score < minimum_score or gap < minimum_gap:
            continue
        selected.append(
            {
                **row,
                "candidateTargets": candidates,
                "reviewLane": {
                    "bestTokenJaccard": round(best_score, 4),
                    "runnerUpTokenJaccard": round(second_score, 4),
                    "scoreGap": round(gap, 4),
                },
            }
        )

    selected.sort(
        key=lambda row: (
            -_number(row.get("reviewLane", {}).get("bestTokenJaccard")),
            str(row.get("classification") or ""),
            str(row.get("english") or "").casefold(),
            str(row.get("sourceIngredientId") or ""),
        )
    )
    return {
        "schemaVersion": 1,
        "kind": "cook4me-remaining-semantic-high-similarity-review-v60",
        "policy": {
            "candidateSearchIsIdentityProof": False,
            "automaticApproval": False,
            "manualSemanticReviewRequired": True,
            "providerIdentityAssigned": False,
            "sourceLocalIdentityPreserved": True,
        },
        "criteria": {
            "minimumTokenJaccard": minimum_score,
            "minimumBestVsRunnerUpGap": minimum_gap,
            "ambiguousClassificationsExcluded": True,
            "exactLooseLaneExcluded": True,
        },
        "summary": {"candidateCount": len(selected)},
        "items": selected,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-score", type=float, default=0.8)
    parser.add_argument("--minimum-gap", type=float, default=0.15)
    args = parser.parse_args()

    payload = json.loads(args.audit.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("kind") != (
        "cook4me-remaining-semantic-ingredient-audit-v60"
    ):
        raise SystemExit("unsupported semantic audit input")
    result = extract(
        payload,
        minimum_score=args.minimum_score,
        minimum_gap=args.minimum_gap,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
