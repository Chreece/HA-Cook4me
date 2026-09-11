#!/usr/bin/env python3
"""Generate bounded USDA FDC candidate evidence for compact v60 review targets.

Discovery only:
- searches by reviewed canonical English;
- keeps only Foundation and SR Legacy candidates;
- never selects a candidate;
- never writes a reviewed FDC binding;
- never treats search rank or search score as identity proof.

The only artifact that may authorize resolution is a separately reviewed
``release_catalog_reviewed_nutrition_targets*.v1.json`` exact target -> FDC ID
binding.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import snapshot_release_catalog_fdc_candidates_v60 as identity_candidates  # type: ignore  # noqa: E402
import resolve_reviewed_release_catalog_nutrition_targets_v60 as target_resolver  # type: ignore  # noqa: E402


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _validate_targets(queue: dict[str, Any]) -> None:
    if queue.get("kind") != "cook4me-release-catalog-nutrition-review-targets-v60":
        raise RuntimeError(
            "expected cook4me-release-catalog-nutrition-review-targets-v60"
        )
    policy = queue.get("policy") if isinstance(queue.get("policy"), dict) else {}
    required = {
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
        raise RuntimeError(
            "nutrition review-target queue is missing fail-closed policy: "
            + ", ".join(bad)
        )


def snapshot(
    queue: dict[str, Any],
    *,
    fetcher: Callable[[str], dict[str, Any]],
    reviewed_target_ids: set[str] | None = None,
    offset: int = 0,
    limit: int = 100,
    max_candidates: int = 8,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_targets(queue)
    reviewed_target_ids = {
        _text(value) for value in (reviewed_target_ids or set()) if _text(value)
    }
    targets = [row for row in queue.get("targets") or [] if isinstance(row, dict)]
    start = max(0, int(offset))
    size = max(1, min(500, int(limit)))
    stop = min(len(targets), start + size)

    items: list[dict[str, Any]] = []
    searched = 0
    skipped_reviewed = 0
    zero_candidate = 0

    for queue_index in range(start, stop):
        target = targets[queue_index]
        target_id = _text(target.get("reviewTargetId"))
        target_kind = _text(target.get("reviewTargetKind"))
        canonical = _text(target.get("canonicalEnglishName"))
        members = [
            _text(value)
            for value in target.get("memberIngredientIds") or []
            if _text(value)
        ]
        if not target_id or not canonical or not members:
            raise RuntimeError(
                f"review target {queue_index} lacks target ID/canonical English/members"
            )
        if target_id in reviewed_target_ids:
            skipped_reviewed += 1
            continue

        response = fetcher(canonical)
        candidates = identity_candidates.compact_candidates(
            response, max_candidates=max_candidates
        )
        searched += 1
        if not candidates:
            zero_candidate += 1

        item = {
            "queueIndex": queue_index,
            "reviewTargetId": target_id,
            "reviewTargetKind": target_kind,
            "canonicalEnglishName": canonical,
            "memberCount": len(set(members)),
            "usageCountSum": int(target.get("usageCountSum") or 0),
            "searchQuery": canonical,
            "candidates": candidates,
            "selectionPerformed": False,
            "needsManualExactIdReview": True,
        }
        if target_kind == "semantic-concept":
            item["semanticConceptId"] = target_id
            item["sourceLanguages"] = sorted(
                {
                    _text(value)
                    for value in target.get("sourceLanguages") or []
                    if _text(value)
                }
            )
        items.append(item)

    output = {
        "schemaVersion": 1,
        "kind": "cook4me-fdc-review-target-candidate-evidence-v60",
        "catalogVersion": _text(queue.get("catalogVersion")),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "queueSlice": {
            "offset": start,
            "limit": size,
            "endExclusive": stop,
            "reviewTargetCount": len(targets),
        },
        "policy": {
            "candidateSearchIsIdentityProof": False,
            "selectionPerformed": False,
            "searchResultAutoAccepted": False,
            "manualExactIdReviewRequired": True,
            "providerIngredientIdentityInference": False,
            "semanticConceptExpansionOccursOnlyAfterReview": True,
            "allowedFdcDataTypes": sorted(identity_candidates._ALLOWED_DATA_TYPES),
            "secretsPersisted": False,
        },
        "items": items,
    }
    summary = {
        "reviewTargetCount": len(targets),
        "sliceStart": start,
        "sliceEndExclusive": stop,
        "sliceTargetCount": max(0, stop - start),
        "searchedTargetCount": searched,
        "alreadyReviewedSkipped": skipped_reviewed,
        "zeroCandidateTargetCount": zero_candidate,
        "candidateCount": sum(len(row["candidates"]) for row in items),
        "selectionCount": 0,
        "secretsPersisted": False,
    }
    return output, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--fdc-key", default="")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-candidates", type=int, default=8)
    parser.add_argument("--delay", type=float, default=0.15)
    args = parser.parse_args()

    api_key = _text(args.fdc_key or os.environ.get("FDC_API_KEY"))
    if not api_key:
        raise SystemExit(
            "FDC review-target candidate evidence requires --fdc-key or FDC_API_KEY"
        )
    queue = _load(Path(args.targets).expanduser(), {})
    if not isinstance(queue, dict):
        raise RuntimeError("nutrition review-target queue must be a JSON object")

    searched = 0

    def fetcher(query: str) -> dict[str, Any]:
        nonlocal searched
        if searched and args.delay:
            time.sleep(max(0.0, float(args.delay)))
        result = identity_candidates.fetch_fdc_candidates(
            query,
            api_key,
            page_size=max(1, min(20, int(args.max_candidates))),
        )
        searched += 1
        return result

    reviewed_ids = set(
        target_resolver.load_reviews(Path(args.review_root).expanduser())
    )
    output, summary = snapshot(
        queue,
        fetcher=fetcher,
        reviewed_target_ids=reviewed_ids,
        offset=args.offset,
        limit=args.limit,
        max_candidates=args.max_candidates,
    )

    output_path = Path(args.output).expanduser()
    summary_path = Path(args.summary).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
