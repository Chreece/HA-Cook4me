#!/usr/bin/env python3
"""Generate bounded USDA FDC candidate evidence for manual v60 nutrition review.

This is discovery only. It never selects a candidate, never writes a reviewed
nutrition binding, and never treats search rank as identity proof. The only
artifact that can authorize nutrition resolution remains a separately reviewed
``release_catalog_reviewed_nutrition_sources*.v1.json`` file with an explicit
Cook4Me ingredient ID -> exact FDC ID binding.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any, Callable
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
FDC_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
_ALLOWED_DATA_TYPES = {"Foundation", "SR Legacy"}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return deepcopy(default)


def _validate_queue(queue: dict[str, Any]) -> None:
    if queue.get("kind") != "cook4me-release-catalog-nutrition-queue-v60":
        raise RuntimeError("expected cook4me-release-catalog-nutrition-queue-v60")
    policy = queue.get("identityPolicy") if isinstance(queue.get("identityPolicy"), dict) else {}
    required = {
        "providerIdentityInference": False,
        "ambiguousExcluded": True,
        "reviewedExactFdcProvenanceRequired": True,
        "searchResultAutoAccepted": False,
    }
    bad = [key for key, expected in required.items() if policy.get(key) is not expected]
    if bad:
        raise RuntimeError(
            "nutrition queue is missing fail-closed identity policy: " + ", ".join(bad)
        )


def fetch_fdc_candidates(query: str, api_key: str, *, page_size: int = 8) -> dict[str, Any]:
    body = json.dumps(
        {
            "query": query,
            "pageSize": max(1, min(20, int(page_size))),
            "dataType": sorted(_ALLOWED_DATA_TYPES),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        FDC_SEARCH_URL + "?api_key=" + urllib.parse.quote(api_key),
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "HA-Cook4me-fdc-candidate-review-v60/1",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"FDC search for {query!r}: invalid response")
    return payload


def _candidate(raw: dict[str, Any], *, rank: int) -> dict[str, Any] | None:
    try:
        fdc_id = int(raw.get("fdcId"))
    except (TypeError, ValueError):
        return None
    if fdc_id <= 0:
        return None
    data_type = _text(raw.get("dataType"))
    if data_type not in _ALLOWED_DATA_TYPES:
        return None
    description = _text(raw.get("description"))
    if not description:
        return None

    row: dict[str, Any] = {
        "responseRank": rank,
        "fdcId": fdc_id,
        "description": description,
        "dataType": data_type,
    }
    for field in (
        "foodCategory",
        "scientificName",
        "commonNames",
        "additionalDescriptions",
        "publicationDate",
    ):
        text = _text(raw.get(field))
        if text:
            row[field] = text
    score = _number(raw.get("score"))
    if score is not None:
        row["providerSearchScore"] = score
    return row


def compact_candidates(payload: dict[str, Any], *, max_candidates: int = 8) -> list[dict[str, Any]]:
    foods = payload.get("foods") if isinstance(payload.get("foods"), list) else []
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for rank, raw in enumerate(foods, 1):
        if not isinstance(raw, dict):
            continue
        row = _candidate(raw, rank=rank)
        if not row or int(row["fdcId"]) in seen:
            continue
        seen.add(int(row["fdcId"]))
        out.append(row)
        if len(out) >= max(1, min(20, int(max_candidates))):
            break
    return out


def snapshot(
    queue: dict[str, Any],
    *,
    fetcher: Callable[[str], dict[str, Any]],
    reviewed_ids: set[str] | None = None,
    offset: int = 0,
    limit: int = 100,
    max_candidates: int = 8,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Search one deterministic queue slice and return evidence only."""
    _validate_queue(queue)
    reviewed_ids = {_text(value) for value in (reviewed_ids or set()) if _text(value)}
    tasks = [row for row in queue.get("tasks") or [] if isinstance(row, dict)]
    start = max(0, int(offset))
    size = max(1, min(500, int(limit)))
    stop = min(len(tasks), start + size)

    items: list[dict[str, Any]] = []
    searched = 0
    skipped_reviewed = 0
    zero_candidate = 0

    for queue_index in range(start, stop):
        task = tasks[queue_index]
        ingredient_id = _text(task.get("ingredientId"))
        canonical = _text(task.get("canonicalEnglishName"))
        if not ingredient_id or not canonical:
            raise RuntimeError(f"queue task {queue_index} lacks identity/canonical English")
        if ingredient_id in reviewed_ids:
            skipped_reviewed += 1
            continue

        response = fetcher(canonical)
        candidates = compact_candidates(response, max_candidates=max_candidates)
        searched += 1
        if not candidates:
            zero_candidate += 1
        items.append(
            {
                "queueIndex": queue_index,
                "ingredientId": ingredient_id,
                "canonicalEnglishName": canonical,
                "identityKind": _text(task.get("identityKind")),
                "usageCount": int(task.get("usageCount") or 0),
                "usedByRecipe": bool(task.get("usedByRecipe")),
                "searchQuery": canonical,
                "candidates": candidates,
                "selectionPerformed": False,
                "needsManualExactIdReview": True,
            }
        )

    output = {
        "schemaVersion": 1,
        "kind": "cook4me-fdc-candidate-evidence-v60",
        "catalogVersion": _text(queue.get("catalogVersion")),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "queueSlice": {
            "offset": start,
            "limit": size,
            "endExclusive": stop,
            "queueTaskCount": len(tasks),
        },
        "policy": {
            "candidateSearchIsIdentityProof": False,
            "selectionPerformed": False,
            "searchResultAutoAccepted": False,
            "manualExactIdReviewRequired": True,
            "providerIngredientIdentityInference": False,
            "allowedFdcDataTypes": sorted(_ALLOWED_DATA_TYPES),
            "secretsPersisted": False,
        },
        "items": items,
    }
    summary = {
        "queueTaskCount": len(tasks),
        "sliceStart": start,
        "sliceEndExclusive": stop,
        "sliceTaskCount": max(0, stop - start),
        "searchedTaskCount": searched,
        "alreadyReviewedSkipped": skipped_reviewed,
        "zeroCandidateTaskCount": zero_candidate,
        "candidateCount": sum(len(row["candidates"]) for row in items),
        "selectionCount": 0,
        "secretsPersisted": False,
    }
    return output, summary


def _reviewed_ids(review_root: Path) -> set[str]:
    # Import lazily so this discovery tool cannot weaken the resolver's stricter
    # review-file validation contract.
    import resolve_reviewed_release_catalog_nutrition_v60 as resolver

    return set(resolver.load_reviews(review_root))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
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
        raise SystemExit("FDC candidate evidence requires --fdc-key or FDC_API_KEY")
    queue = _load(Path(args.queue).expanduser(), {})
    if not isinstance(queue, dict):
        raise RuntimeError("nutrition queue must be a JSON object")

    searched = 0

    def fetcher(query: str) -> dict[str, Any]:
        nonlocal searched
        if searched and args.delay:
            time.sleep(max(0.0, float(args.delay)))
        result = fetch_fdc_candidates(
            query,
            api_key,
            page_size=max(1, min(20, int(args.max_candidates))),
        )
        searched += 1
        return result

    output, summary = snapshot(
        queue,
        fetcher=fetcher,
        reviewed_ids=_reviewed_ids(Path(args.review_root).expanduser()),
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
