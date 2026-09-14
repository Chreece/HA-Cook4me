#!/usr/bin/env python3
"""Prepare nutrition review targets from the compacted activated v60 catalog.

Pre-activation review artifacts retain the original semantic review filename on
each source-local ingredient. Runtime compaction intentionally removes some
maintenance provenance. The activated catalog still retains the reviewed food
concept, high review confidence, exact source-local identity, and a validated
catalog version.

This adapter keeps the original pre-activation compactor fail-closed. For a
validated runtime-compacted catalog only, it supplies a stable catalog-bound
semantic review receipt when the old build-time filename is absent, then converts
that compatibility shim into an explicit ``semanticReviewReceipts`` field in the
resulting review-target artifact.
"""
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

import snapshot_release_catalog_nutrition_queue_v60 as snapshotter  # type: ignore  # noqa: E402
import compact_release_catalog_nutrition_review_targets_v60 as compactor  # type: ignore  # noqa: E402

_RECEIPT_PREFIX = "runtime-catalog-semantic-review:"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def prepare(catalog: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if int(catalog.get("schemaVersion") or 0) != 1:
        raise RuntimeError("expected release catalog schemaVersion=1")
    if catalog.get("complete") is not True:
        raise RuntimeError("post-activation nutrition enrichment requires complete=true")
    source = catalog.get("source") if isinstance(catalog.get("source"), dict) else {}
    if source.get("runtimeCatalogCompacted") is not True:
        raise RuntimeError("post-activation adapter requires runtimeCatalogCompacted=true")
    if source.get("semanticCoverageComplete") is not True:
        raise RuntimeError("post-activation adapter requires semanticCoverageComplete=true")

    catalog_version = _text(catalog.get("catalogVersion"))
    if not catalog_version:
        raise RuntimeError("activated catalog has no catalogVersion")

    queue, queue_summary = snapshotter.snapshot(catalog)
    receipt_count = 0
    receipt_concepts: set[str] = set()

    for task in queue.get("tasks") or []:
        if not isinstance(task, dict) or _text(task.get("identityKind")) != "source-local":
            continue
        if _text(task.get("semanticReviewFile")):
            continue
        concept_id = _text(task.get("conceptId"))
        confidence = _text(task.get("reviewConfidence")).lower()
        ingredient_id = _text(task.get("ingredientId"))
        if not concept_id.startswith("concept:food:"):
            raise RuntimeError(
                f"runtime-compacted source-local task lacks reviewed food concept: {ingredient_id}"
            )
        if confidence != "high":
            raise RuntimeError(
                f"runtime-compacted source-local task lacks high review confidence: {ingredient_id}"
            )
        receipt = f"{_RECEIPT_PREFIX}{catalog_version}:{concept_id}"
        task["semanticReviewFile"] = receipt
        task["semanticReviewReceipt"] = receipt
        receipt_count += 1
        receipt_concepts.add(concept_id)

    queue.setdefault("identityPolicy", {})["runtimeCompactedSemanticReviewReceiptAllowed"] = True
    queue["postActivationSemanticReviewReceiptCount"] = receipt_count

    targets, target_summary = compactor.compact(queue)
    receipt_target_count = 0
    for target in targets.get("targets") or []:
        if not isinstance(target, dict):
            continue
        files = [
            _text(value)
            for value in target.get("semanticReviewFiles") or []
            if _text(value)
        ]
        receipts = [value for value in files if value.startswith(_RECEIPT_PREFIX)]
        actual_files = [value for value in files if not value.startswith(_RECEIPT_PREFIX)]
        if receipts:
            target["semanticReviewReceipts"] = sorted(set(receipts))
            receipt_target_count += 1
        if actual_files:
            target["semanticReviewFiles"] = sorted(set(actual_files))
        else:
            target.pop("semanticReviewFiles", None)

    policy = targets.setdefault("policy", {})
    policy.update(
        {
            "postActivationRuntimeCompactedCatalog": True,
            "runtimeCompactedSemanticReviewReceiptAllowed": True,
            "runtimeSemanticReviewReceiptIsFdcIdentityProof": False,
            "runtimeSemanticReviewReceiptIsNutritionBinding": False,
        }
    )
    targets["postActivationSemanticReviewReceiptCount"] = receipt_count
    targets["postActivationSemanticReviewReceiptTargetCount"] = receipt_target_count

    queue_summary = dict(queue_summary)
    queue_summary.update(
        {
            "runtimeCatalogCompacted": True,
            "postActivationSemanticReviewReceiptCount": receipt_count,
            "postActivationSemanticReviewReceiptConceptCount": len(receipt_concepts),
        }
    )
    target_summary = dict(target_summary)
    target_summary.update(
        {
            "runtimeCatalogCompacted": True,
            "postActivationSemanticReviewReceiptCount": receipt_count,
            "postActivationSemanticReviewReceiptTargetCount": receipt_target_count,
        }
    )
    return queue, queue_summary, targets, target_summary


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--queue-output", required=True)
    parser.add_argument("--queue-summary", required=True)
    parser.add_argument("--targets-output", required=True)
    parser.add_argument("--targets-summary", required=True)
    args = parser.parse_args()

    catalog = _load(Path(args.catalog).expanduser())
    queue, queue_summary, targets, target_summary = prepare(catalog)
    _write(Path(args.queue_output).expanduser(), queue)
    _write(Path(args.queue_summary).expanduser(), queue_summary)
    _write(Path(args.targets_output).expanduser(), targets)
    _write(Path(args.targets_summary).expanduser(), target_summary)
    print(json.dumps({"queue": queue_summary, "targets": target_summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
