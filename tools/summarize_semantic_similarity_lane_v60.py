#!/usr/bin/env python3
"""Create a compact human-review view of a semantic similarity lane."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def compact(payload: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for row in payload.get("items") or []:
        if not isinstance(row, dict):
            continue
        candidates = [
            item for item in row.get("candidateTargets") or [] if isinstance(item, dict)
        ]
        best = candidates[0] if candidates else {}
        lane = row.get("reviewLane") if isinstance(row.get("reviewLane"), dict) else {}
        items.append(
            {
                "sourceIngredientId": row.get("sourceIngredientId"),
                "language": row.get("language"),
                "source": row.get("source"),
                "english": row.get("english"),
                "classification": row.get("classification"),
                "bestConceptId": best.get("conceptId"),
                "bestCanonicalEnglish": best.get("canonicalEnglish"),
                "bestTokenJaccard": lane.get("bestTokenJaccard"),
                "runnerUpTokenJaccard": lane.get("runnerUpTokenJaccard"),
                "scoreGap": lane.get("scoreGap"),
            }
        )
    return {
        "schemaVersion": 1,
        "kind": "cook4me-semantic-similarity-compact-review-v60",
        "policy": {
            "automaticApproval": False,
            "manualSemanticReviewRequired": True,
            "candidateSearchIsIdentityProof": False,
        },
        "summary": {"candidateCount": len(items)},
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = compact(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
