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

Post-activation review work can advance after the activated catalog snapshot. To
avoid searching USDA again for work that is already explicitly reviewed, this
adapter may also subtract exact reviewTargetIds present in the trusted review
corpus. Subtraction is ID-only: canonical names, candidate rank, aliases, FDC IDs,
and similarity never remove a target. Both the activated pending counts and the
remaining review counts are retained in the output summaries.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import snapshot_release_catalog_nutrition_queue_v60 as snapshotter  # type: ignore  # noqa: E402
import compact_release_catalog_nutrition_review_targets_v60 as compactor  # type: ignore  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as review_checkpoint  # type: ignore  # noqa: E402

_RECEIPT_PREFIX = "runtime-catalog-semantic-review:"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _task_review_target_id(task: dict[str, Any]) -> str:
    kind = _text(task.get("identityKind"))
    if kind == "provider":
        target = _text(task.get("ingredientId"))
    elif kind == "source-local":
        target = _text(task.get("conceptId"))
    else:
        raise RuntimeError(f"unsupported post-activation identity kind: {kind!r}")
    if not target:
        raise RuntimeError("post-activation nutrition task lacks review target identity")
    return target


def _reviewed_ids(review_root: Path) -> set[str]:
    checkpoint = review_checkpoint.build_checkpoint(review_root)
    ids = {
        _text(row.get("reviewTargetId"))
        for row in checkpoint.get("recordedBindings") or []
        if isinstance(row, dict) and _text(row.get("reviewTargetId"))
    }
    if len(ids) != int(checkpoint.get("summary", {}).get("recordedReviewTargetCount") or 0):
        raise RuntimeError("review checkpoint target count is not unique")
    return ids


def prepare(
    catalog: dict[str, Any],
    reviewed_target_ids: Iterable[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
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
    activated_pending_identity_count = len(queue.get("tasks") or [])
    activated_used_pending_count = sum(
        bool(row.get("usedByRecipe"))
        for row in queue.get("tasks") or []
        if isinstance(row, dict)
    )

    activated_receipt_count = 0
    activated_receipt_concepts: set[str] = set()
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
        activated_receipt_count += 1
        activated_receipt_concepts.add(concept_id)

    queue.setdefault("identityPolicy", {})["runtimeCompactedSemanticReviewReceiptAllowed"] = True
    queue["postActivationSemanticReviewReceiptCount"] = activated_receipt_count

    # Compact once before subtraction so the exact activated review-target
    # baseline remains provable even when newer review files exist.
    activated_targets, activated_target_summary = compactor.compact(queue)
    activated_review_target_count = int(activated_target_summary.get("reviewTargetCount") or 0)

    reviewed_ids = {_text(value) for value in (reviewed_target_ids or []) if _text(value)}
    reviewed_rows = [
        row
        for row in activated_targets.get("targets") or []
        if isinstance(row, dict) and _text(row.get("reviewTargetId")) in reviewed_ids
    ]
    reviewed_ids_present = {
        _text(row.get("reviewTargetId")) for row in reviewed_rows if _text(row.get("reviewTargetId"))
    }

    original_tasks = [row for row in queue.get("tasks") or [] if isinstance(row, dict)]
    remaining_tasks: list[dict[str, Any]] = []
    removed_tasks: list[dict[str, Any]] = []
    for task in original_tasks:
        if _task_review_target_id(task) in reviewed_ids_present:
            removed_tasks.append(task)
        else:
            remaining_tasks.append(task)

    queue["tasks"] = remaining_tasks
    queue["taskCount"] = len(remaining_tasks)
    queue["activatedPendingIdentityCount"] = activated_pending_identity_count
    queue["reviewedAfterActivationIdentityCount"] = len(removed_tasks)
    queue["reviewedAfterActivationTargetCount"] = len(reviewed_rows)
    queue["reviewedAfterActivationTargetIds"] = sorted(reviewed_ids_present)
    queue["reviewCorpusTargetCount"] = len(reviewed_ids)
    queue["identityPolicy"].update(
        {
            "reviewedAfterActivationExactTargetIdSubtraction": True,
            "reviewedAfterActivationCanonicalNameInference": False,
            "reviewedAfterActivationFdcInference": False,
        }
    )

    pending_kinds = Counter(_text(row.get("identityKind")) for row in remaining_tasks)
    queue_summary = dict(queue_summary)
    queue_summary.update(
        {
            "activatedPendingNutritionCount": activated_pending_identity_count,
            "activatedUsedPendingCount": activated_used_pending_count,
            "pendingNutritionCount": len(remaining_tasks),
            "pendingByIdentityKind": dict(sorted(pending_kinds.items())),
            "usedPendingCount": sum(bool(row.get("usedByRecipe")) for row in remaining_tasks),
            "reviewCorpusTargetCount": len(reviewed_ids),
            "reviewedAfterActivationTargetCount": len(reviewed_rows),
            "reviewedAfterActivationIdentityCount": len(removed_tasks),
            "reviewedAfterActivationUsedTargetCount": sum(
                bool(row.get("usedByRecipe")) for row in reviewed_rows
            ),
            "reviewedAfterActivationUsageCountSum": sum(
                max(0, int(row.get("usageCountSum") or 0)) for row in reviewed_rows
            ),
            "runtimeCatalogCompacted": True,
            "activatedPostActivationSemanticReviewReceiptCount": activated_receipt_count,
            "activatedPostActivationSemanticReviewReceiptConceptCount": len(activated_receipt_concepts),
        }
    )

    remaining_receipt_count = sum(
        bool(_text(task.get("semanticReviewReceipt"))) for task in remaining_tasks
    )
    remaining_receipt_concepts = {
        _text(task.get("conceptId"))
        for task in remaining_tasks
        if _text(task.get("semanticReviewReceipt")) and _text(task.get("conceptId"))
    }
    queue["postActivationSemanticReviewReceiptCount"] = remaining_receipt_count
    queue_summary["postActivationSemanticReviewReceiptCount"] = remaining_receipt_count
    queue_summary["postActivationSemanticReviewReceiptConceptCount"] = len(remaining_receipt_concepts)

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

    reviewed_target_summaries = [
        {
            "reviewTargetId": _text(row.get("reviewTargetId")),
            "reviewTargetKind": _text(row.get("reviewTargetKind")),
            "canonicalEnglishName": _text(row.get("canonicalEnglishName")),
            "memberCount": max(0, int(row.get("memberCount") or 0)),
            "usageCountSum": max(0, int(row.get("usageCountSum") or 0)),
            "usedByRecipe": bool(row.get("usedByRecipe")),
        }
        for row in reviewed_rows
    ]

    policy = targets.setdefault("policy", {})
    policy.update(
        {
            "postActivationRuntimeCompactedCatalog": True,
            "runtimeCompactedSemanticReviewReceiptAllowed": True,
            "runtimeSemanticReviewReceiptIsFdcIdentityProof": False,
            "runtimeSemanticReviewReceiptIsNutritionBinding": False,
            "reviewedAfterActivationExactTargetIdSubtraction": True,
            "reviewedAfterActivationCanonicalNameInference": False,
            "reviewedAfterActivationFdcInference": False,
        }
    )
    targets["activatedPendingIdentityCount"] = activated_pending_identity_count
    targets["activatedReviewTargetCount"] = activated_review_target_count
    targets["reviewCorpusTargetCount"] = len(reviewed_ids)
    targets["reviewedAfterActivationTargetCount"] = len(reviewed_rows)
    targets["reviewedAfterActivationIdentityCount"] = len(removed_tasks)
    targets["reviewedAfterActivationTargets"] = reviewed_target_summaries
    targets["postActivationSemanticReviewReceiptCount"] = remaining_receipt_count
    targets["postActivationSemanticReviewReceiptTargetCount"] = receipt_target_count

    target_summary = dict(target_summary)
    target_summary.update(
        {
            "activatedPendingIdentityCount": activated_pending_identity_count,
            "activatedReviewTargetCount": activated_review_target_count,
            "reviewCorpusTargetCount": len(reviewed_ids),
            "reviewedAfterActivationTargetCount": len(reviewed_rows),
            "reviewedAfterActivationIdentityCount": len(removed_tasks),
            "reviewedAfterActivationUsedTargetCount": sum(
                bool(row.get("usedByRecipe")) for row in reviewed_rows
            ),
            "reviewedAfterActivationUsageCountSum": sum(
                max(0, int(row.get("usageCountSum") or 0)) for row in reviewed_rows
            ),
            "runtimeCatalogCompacted": True,
            "postActivationSemanticReviewReceiptCount": remaining_receipt_count,
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
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--queue-output", required=True)
    parser.add_argument("--queue-summary", required=True)
    parser.add_argument("--targets-output", required=True)
    parser.add_argument("--targets-summary", required=True)
    args = parser.parse_args()

    catalog = _load(Path(args.catalog).expanduser())
    reviewed_ids = _reviewed_ids(Path(args.review_root).expanduser())
    queue, queue_summary, targets, target_summary = prepare(catalog, reviewed_ids)
    _write(Path(args.queue_output).expanduser(), queue)
    _write(Path(args.queue_summary).expanduser(), queue_summary)
    _write(Path(args.targets_output).expanduser(), targets)
    _write(Path(args.targets_summary).expanduser(), target_summary)
    print(json.dumps({"queue": queue_summary, "targets": target_summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
