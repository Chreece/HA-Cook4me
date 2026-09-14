#!/usr/bin/env python3
"""Resolve reviewed v60 nutrition targets from pinned local USDA FDC data."""
from __future__ import annotations

import argparse
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


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def resolve_offline(
    targets: dict[str, Any],
    cache: dict[str, Any],
    reviews: dict[str, dict[str, Any]],
    index: reference.ReferenceIndex,
) -> tuple[dict[str, Any], dict[str, Any]]:
    output, pending = target_resolver.resolve(
        targets,
        cache,
        reviews,
        fetcher=index.food,
    )
    # Strengthen provenance for profiles produced from this pinned local corpus.
    for value in output.values():
        if not isinstance(value, dict):
            continue
        target_id = value.get("nutritionReviewTargetId")
        if not target_id:
            continue
        try:
            source_id = int(value.get("sourceId"))
        except (TypeError, ValueError):
            continue
        meta = index.metadata(source_id)
        value["sourceReferenceDataset"] = meta["dataType"]
        value["sourceReferenceReleaseDate"] = meta["releaseDate"]
        value["sourceReferenceJsonSha256"] = meta["jsonSha256"]
        value["sourceReferenceManifestSha256"] = index.manifest_sha256
    summary = pending.get("summary") if isinstance(pending.get("summary"), dict) else {}
    summary.update(
        {
            "networkRequestsPerformed": False,
            "apiKeyRequired": False,
            "referenceManifestSha256": index.manifest_sha256,
        }
    )
    pending["summary"] = summary
    return output, pending


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True)
    parser.add_argument("--reference-manifest", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--pending-output", required=True)
    args = parser.parse_args()

    targets = _load(Path(args.targets).expanduser(), {})
    cache_path = Path(args.cache).expanduser()
    cache = _load(cache_path, {})
    if not isinstance(targets, dict):
        raise RuntimeError("nutrition review-target queue must be an object")
    if not isinstance(cache, dict):
        raise RuntimeError("nutrition cache must be an object")
    reviews = target_resolver.load_reviews(Path(args.review_root).expanduser())
    index = reference.ReferenceIndex(Path(args.reference_manifest).expanduser())
    output, pending = resolve_offline(targets, cache, reviews, index)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending_path = Path(args.pending_output).expanduser()
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(pending["summary"], ensure_ascii=False))
    return 0 if pending["summary"]["pendingReviewTargetCount"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
