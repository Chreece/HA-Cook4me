#!/usr/bin/env python3
"""Run one fresh v60 provider capture without activation or FDC resolution.

A successful first capture is expected to stop at the nutrition-review gate. This
wrapper therefore treats ``nutrition-review-pending`` (or ``awaiting-fdc-key`` if
review bindings already exist) as a successful capture result while still
returning failure for capture/final validation errors. Activation is forced off.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"

import run_release_catalog_v60_reviewed_pipeline as reviewed_pipeline

_OK_CAPTURE_STATUSES = {
    "nutrition-review-pending",
    "awaiting-fdc-key",
    "ready-for-activation",
}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def capture_once(
    args: Any,
    *,
    run_func: Callable[[Any], dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    """Force a non-activating, no-FDC-key first capture and summarize artifacts."""
    run_func = run_func or reviewed_pipeline.run_pipeline
    safe_args = SimpleNamespace(
        catalog_version=_text(getattr(args, "catalog_version", "")),
        storage_home=str(Path(getattr(args, "storage_home", Path.home())).expanduser()),
        configured_language=_text(getattr(args, "configured_language", "de")) or "de",
        configured_country=(_text(getattr(args, "configured_country", "DE")) or "DE").upper(),
        english_overrides=_text(getattr(args, "english_overrides", "")),
        workers=max(1, int(getattr(args, "workers", 4) or 4)),
        verbose=bool(getattr(args, "verbose", False)),
        build_dir=str(
            Path(
                getattr(
                    args,
                    "build_dir",
                    ROOT / ".catalog-build" / "v60-release",
                )
            ).expanduser()
        ),
        nutrition_cache=str(
            Path(
                getattr(
                    args,
                    "nutrition_cache",
                    ROOT / ".catalog-build" / "fdc-nutrition-reviewed-v60.json",
                )
            ).expanduser()
        ),
        review_root=str(Path(getattr(args, "review_root", TOOLS)).expanduser()),
        fdc_key="",
        live_path=str(
            Path(
                getattr(
                    args,
                    "live_path",
                    COMPONENT / "catalog" / "merged_catalog.v1.json",
                )
            ).expanduser()
        ),
        require_intelligence=False,
        activate=False,
    )
    if not safe_args.catalog_version:
        raise RuntimeError("catalog_version is required")

    manifest = run_func(safe_args)
    if not isinstance(manifest, dict):
        raise RuntimeError("reviewed v60 pipeline did not return a manifest")
    status = _text(manifest.get("status"))
    paths = manifest.get("paths") if isinstance(manifest.get("paths"), dict) else {}
    build_dir = Path(safe_args.build_dir)
    summary = {
        "status": status,
        "providerCaptureCount": int(manifest.get("providerCaptureCount") or 0),
        "captureValidationValid": bool(
            (manifest.get("captureValidation") or {}).get("valid")
            if isinstance(manifest.get("captureValidation"), dict)
            else False
        ),
        "nutritionPending": int(
            (manifest.get("finalNutritionQueue") or {}).get("pendingNutritionCount") or 0
            if isinstance(manifest.get("finalNutritionQueue"), dict)
            else 0
        ),
        "activated": bool(manifest.get("activated")),
        "nutritionQueue": str(paths.get("nutritionQueue") or ""),
        "nutritionPendingFile": str(paths.get("nutritionPending") or ""),
        "capturedCatalog": str(paths.get("capturedSemanticCatalog") or ""),
        "candidateCatalog": str(paths.get("candidateCatalog") or ""),
        "manifest": str(build_dir / "release-manifest.v60.json"),
    }
    if summary["activated"]:
        raise RuntimeError("capture-only command must never activate a catalog")

    ok = bool(
        status in _OK_CAPTURE_STATUSES
        and summary["providerCaptureCount"] == 1
        and summary["captureValidationValid"]
    )
    return manifest, summary, 0 if ok else 2


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
    parser.add_argument(
        "--live-path",
        default=str(COMPONENT / "catalog" / "merged_catalog.v1.json"),
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    _manifest, summary, code = capture_once(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
