#!/usr/bin/env python3
"""Generate FDC candidate evidence for all compact review targets offline."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import fdc_reference_data_v60 as reference  # type: ignore  # noqa: E402
import resolve_reviewed_release_catalog_nutrition_targets_v60 as target_resolver  # type: ignore  # noqa: E402


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("nutrition review-target queue must be an object")
    return value


def snapshot(queue: dict[str, Any], index: reference.ReferenceIndex, *, reviewed_ids: set[str] | None = None, max_candidates: int = 8) -> tuple[dict[str, Any], dict[str, Any]]:
    target_resolver._validate_queue(queue)
    reviewed_ids = reviewed_ids or set()
    items: list[dict[str, Any]] = []
    zero = 0
    skipped = 0
    targets = [row for row in queue.get("targets") or [] if isinstance(row, dict)]
    for position, raw in enumerate(targets):
        target_id = _text(raw.get("reviewTargetId"))
        canonical = _text(raw.get("canonicalEnglishName"))
        if not target_id or not canonical:
            raise RuntimeError(f"review target {position} lacks target ID/canonical English")
        if target_id in reviewed_ids:
            skipped += 1
            continue
        candidates = index.search(canonical, max_candidates=max_candidates)
        if not candidates:
            zero += 1
        items.append({
            "queueIndex": position,
            "reviewTargetId": target_id,
            "reviewTargetKind": _text(raw.get("reviewTargetKind")),
            "canonicalEnglishName": canonical,
            "memberCount": int(raw.get("memberCount") or 0),
            "usageCountSum": int(raw.get("usageCountSum") or 0),
            "candidates": candidates,
            "selectionPerformed": False,
            "needsManualExactIdReview": True,
        })
    payload = {
        "schemaVersion": 1,
        "kind": "cook4me-fdc-review-target-candidate-evidence-offline-v60",
        "catalogVersion": _text(queue.get("catalogVersion")),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "referenceManifestSha256": index.manifest_sha256,
        "policy": {
            "candidateSearchIsIdentityProof": False,
            "selectionPerformed": False,
            "searchResultAutoAccepted": False,
            "manualExactIdReviewRequired": True,
            "providerIngredientIdentityInference": False,
            "networkRequestsPerformed": False,
            "secretsPersisted": False,
        },
        "items": items,
    }
    summary = {
        "reviewTargetCount": len(targets),
        "searchedTargetCount": len(items),
        "alreadyReviewedSkipped": skipped,
        "zeroCandidateTargetCount": zero,
        "candidateCount": sum(len(row["candidates"]) for row in items),
        "selectionCount": 0,
        "networkRequestsPerformed": False,
        "secretsPersisted": False,
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True)
    parser.add_argument("--reference-manifest", required=True)
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--max-candidates", type=int, default=8)
    args = parser.parse_args()

    queue = _load(Path(args.targets).expanduser())
    index = reference.ReferenceIndex(Path(args.reference_manifest).expanduser())
    reviewed = set(target_resolver.load_reviews(Path(args.review_root).expanduser()))
    payload, summary = snapshot(queue, index, reviewed_ids=reviewed, max_candidates=args.max_candidates)
    output = Path(args.output).expanduser()
    summary_path = Path(args.summary).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
