#!/usr/bin/env python3
"""One-capture, fail-closed Cook4Me v60 release-build and activation pipeline.

Flow:
1. Capture/build the provider catalog exactly once with an intentionally empty
   nutrition cache and missing nutrition allowed for capture completeness.
2. Validate the captured semantic artifact offline.
3. Create the impact-ranked reviewed-nutrition queue.
4. Resolve only manually reviewed exact USDA FDC IDs.
5. Attach reviewed nutrition offline and regenerate every derived v60 index.
6. Validate the final candidate independently.
7. Activate only when no reviewed nutrition task remains and all requested gates
   pass. Activation is explicit and atomically copies the exact validated bytes.

No API key, provider credential, or account secret is written to artifacts or the
pipeline manifest.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"

import build_release_catalog_v60 as builder
import resolve_reviewed_release_catalog_nutrition_v60 as nutrition_resolver
import snapshot_release_catalog_nutrition_queue_v60 as nutrition_queue
import validate_release_catalog_v60 as validator


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def _save_json(path: Path, payload: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":") if compact else None,
        indent=None if compact else 2,
    )
    path.write_text(text + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_copy_bytes(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(
        f".{destination.name}.tmp-{os.getpid()}-{source.stat().st_size}"
    )
    try:
        temporary.write_bytes(source.read_bytes())
        os.replace(temporary, destination)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _capture_args(args: Any, *, output: Path, empty_nutrition_cache: Path) -> Any:
    return SimpleNamespace(
        storage_home=str(Path(getattr(args, "storage_home", Path.home())).expanduser()),
        configured_language=_text(getattr(args, "configured_language", "de")) or "de",
        configured_country=(_text(getattr(args, "configured_country", "DE")) or "DE").upper(),
        catalog_version=_text(getattr(args, "catalog_version", "")),
        output=str(output),
        nutrition_cache=str(empty_nutrition_cache),
        english_overrides=_text(getattr(args, "english_overrides", "")),
        resolve_nutrition=False,
        allow_missing_nutrition=True,
        fdc_key="",
        fdc_delay=0.0,
        workers=max(1, int(getattr(args, "workers", 4) or 4)),
        verbose=bool(getattr(args, "verbose", False)),
    )


def _validation_snapshot(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "valid": bool(result.get("valid")),
        "errors": list(result.get("errors") or []),
        "warnings": list(result.get("warnings") or []),
        "stats": dict(result.get("stats") or {}),
    }


def _pending_without_fetch(queue: dict[str, Any], reviewed_fetch_count: int) -> dict[str, Any]:
    tasks = [dict(row) for row in queue.get("tasks") or [] if isinstance(row, dict)]
    return {
        "summary": {
            "queueTaskCount": len(tasks),
            "alreadyResolved": 0,
            "resolvedNow": 0,
            "missingReview": len(tasks) - reviewed_fetch_count,
            "pendingCount": len(tasks),
            "reviewedFetchBlockedByMissingKey": reviewed_fetch_count,
            "searchResultsAutoAccepted": False,
            "secretsPersisted": False,
        },
        "pending": tasks,
    }


def run_pipeline(
    args: Any,
    *,
    build_func: Callable[[Any], dict[str, Any]] | None = None,
    validate_func: Callable[..., dict[str, Any]] | None = None,
    queue_func: Callable[[dict[str, Any], dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]] | None = None,
    review_loader: Callable[[Path], dict[str, dict[str, Any]]] | None = None,
    resolve_func: Callable[..., tuple[dict[str, Any], dict[str, Any]]] | None = None,
    fdc_fetcher: Callable[[int, str], dict[str, Any]] | None = None,
    finalize_func: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    build_func = build_func or builder.build
    validate_func = validate_func or validator.validate
    queue_func = queue_func or nutrition_queue.snapshot
    review_loader = review_loader or nutrition_resolver.load_reviews
    resolve_func = resolve_func or nutrition_resolver.resolve
    fdc_fetcher = fdc_fetcher or nutrition_resolver.fetch_fdc_detail
    finalize_func = finalize_func or builder.apply_reviewed_nutrition

    catalog_version = _text(getattr(args, "catalog_version", ""))
    if not catalog_version:
        raise RuntimeError("catalog_version is required")

    build_dir = Path(getattr(args, "build_dir", ROOT / ".catalog-build" / "v60-release")).expanduser()
    nutrition_cache_path = Path(
        getattr(
            args,
            "nutrition_cache",
            ROOT / ".catalog-build" / "fdc-nutrition-reviewed-v60.json",
        )
    ).expanduser()
    review_root = Path(getattr(args, "review_root", TOOLS)).expanduser()
    live_path = Path(
        getattr(
            args,
            "live_path",
            COMPONENT / "catalog" / "merged_catalog.v1.json",
        )
    ).expanduser()
    activate_requested = bool(getattr(args, "activate", False))
    require_intelligence = bool(getattr(args, "require_intelligence", False))
    fdc_key = _text(getattr(args, "fdc_key", "") or os.environ.get("FDC_API_KEY"))

    build_dir.mkdir(parents=True, exist_ok=True)
    stage_path = build_dir / "captured-semantic-catalog.v60.json"
    empty_cache_path = build_dir / "capture-empty-nutrition.json"
    queue_path = build_dir / "nutrition-queue.v60.json"
    queue_summary_path = build_dir / "nutrition-queue-summary.v60.json"
    pending_path = build_dir / "nutrition-pending.v60.json"
    candidate_path = build_dir / "candidate-catalog.v60.json"
    manifest_path = build_dir / "release-manifest.v60.json"

    _save_json(empty_cache_path, {}, compact=True)
    capture_args = _capture_args(
        args,
        output=stage_path,
        empty_nutrition_cache=empty_cache_path,
    )
    captured = build_func(capture_args)
    if not isinstance(captured, dict):
        raise RuntimeError("v60 capture builder did not return a catalog object")
    _save_json(stage_path, captured, compact=True)

    capture_validation = validate_func(
        captured,
        require_complete=True,
        require_intelligence=False,
    )
    if not bool(capture_validation.get("valid")):
        manifest = {
            "schemaVersion": 1,
            "kind": "cook4me-v60-release-pipeline-manifest",
            "catalogVersion": catalog_version,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "status": "capture-validation-failed",
            "providerCaptureCount": 1,
            "activationRequested": activate_requested,
            "activated": False,
            "captureValidation": _validation_snapshot(capture_validation),
            "secretsPersisted": False,
        }
        _save_json(manifest_path, manifest)
        return manifest

    cache = _load_json(nutrition_cache_path, {})
    if not isinstance(cache, dict):
        raise RuntimeError("reviewed nutrition cache must be a JSON object")
    queue, queue_summary = queue_func(captured, cache)
    _save_json(queue_path, queue)
    _save_json(queue_summary_path, queue_summary)

    reviews = review_loader(review_root)
    queued_ids = [
        _text(row.get("ingredientId"))
        for row in queue.get("tasks") or []
        if isinstance(row, dict) and _text(row.get("ingredientId"))
    ]
    reviewed_fetch_ids = [ident for ident in queued_ids if ident in reviews]
    blocked_by_missing_key = bool(reviewed_fetch_ids and not fdc_key)

    if blocked_by_missing_key:
        resolved_cache = dict(cache)
        pending = _pending_without_fetch(queue, len(reviewed_fetch_ids))
    else:
        resolved_cache, pending = resolve_func(
            queue,
            cache,
            reviews,
            fetcher=lambda fdc_id: fdc_fetcher(fdc_id, fdc_key),
        )
        nutrition_cache_path.parent.mkdir(parents=True, exist_ok=True)
        _save_json(nutrition_cache_path, resolved_cache)
    _save_json(pending_path, pending)

    candidate = finalize_func(captured, resolved_cache)
    _save_json(candidate_path, candidate, compact=True)
    final_queue, final_queue_summary = queue_func(candidate, resolved_cache)
    final_validation = validate_func(
        candidate,
        require_complete=True,
        require_intelligence=require_intelligence,
    )

    pending_count = int(final_queue_summary.get("pendingNutritionCount") or 0)
    reviewed_complete = bool(
        isinstance(candidate.get("source"), dict)
        and candidate["source"].get("reviewedNutritionComplete") is True
    )
    ready_for_activation = bool(
        final_validation.get("valid")
        and candidate.get("complete") is True
        and pending_count == 0
        and reviewed_complete
        and not blocked_by_missing_key
    )

    activated = False
    candidate_sha = _sha256(candidate_path)
    activated_sha = ""
    if activate_requested and ready_for_activation:
        _atomic_copy_bytes(candidate_path, live_path)
        activated_sha = _sha256(live_path)
        if activated_sha != candidate_sha:
            raise RuntimeError("activated catalog checksum differs from validated candidate")
        activated = True

    if activated:
        status = "activated"
    elif blocked_by_missing_key:
        status = "awaiting-fdc-key"
    elif pending_count:
        status = "nutrition-review-pending"
    elif not bool(final_validation.get("valid")):
        status = "final-validation-failed"
    elif activate_requested and not ready_for_activation:
        status = "activation-refused"
    else:
        status = "ready-for-activation"

    manifest = {
        "schemaVersion": 1,
        "kind": "cook4me-v60-release-pipeline-manifest",
        "catalogVersion": catalog_version,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "providerCaptureCount": 1,
        "captureNutritionCacheIntentionallyEmpty": True,
        "captureValidation": _validation_snapshot(capture_validation),
        "initialNutritionQueue": dict(queue_summary),
        "nutritionResolution": dict(pending.get("summary") or {}),
        "finalNutritionQueue": dict(final_queue_summary),
        "finalValidation": _validation_snapshot(final_validation),
        "requireIntelligence": require_intelligence,
        "fdcKeyProvided": bool(fdc_key),
        "reviewedTasksAwaitingFetch": len(reviewed_fetch_ids) if blocked_by_missing_key else 0,
        "readyForActivation": ready_for_activation,
        "activationRequested": activate_requested,
        "activated": activated,
        "candidateSha256": candidate_sha,
        "activatedSha256": activated_sha,
        "paths": {
            "capturedSemanticCatalog": str(stage_path),
            "nutritionQueue": str(queue_path),
            "nutritionPending": str(pending_path),
            "candidateCatalog": str(candidate_path),
            "liveCatalog": str(live_path),
        },
        "secretsPersisted": False,
    }
    _save_json(manifest_path, manifest)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-version", required=True)
    parser.add_argument("--storage-home", default=str(Path.home()))
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--english-overrides", default="")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--build-dir",
        default=str(ROOT / ".catalog-build" / "v60-release"),
    )
    parser.add_argument(
        "--nutrition-cache",
        default=str(ROOT / ".catalog-build" / "fdc-nutrition-reviewed-v60.json"),
    )
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--fdc-key", default="")
    parser.add_argument(
        "--live-path",
        default=str(COMPONENT / "catalog" / "merged_catalog.v1.json"),
    )
    parser.add_argument("--require-intelligence", action="store_true")
    parser.add_argument("--activate", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    manifest = run_pipeline(args)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest.get("readyForActivation") else 2


if __name__ == "__main__":
    raise SystemExit(main())
