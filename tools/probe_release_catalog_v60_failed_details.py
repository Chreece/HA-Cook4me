#!/usr/bin/env python3
"""Probe only unresolved Cook4Me v60 recipe-detail identities.

This diagnostic is intentionally separate from release assembly.  It reads an
already captured v60 catalog, re-queries only catalogs that reported failed
detail hydration, and probes only provider search IDs that are absent from the
captured recipe table.

The historical capture did not persist failed variant IDs, so this tool never
claims that a current absent ID is the exact historical failed ID.  It reports
count reconciliation explicitly and keeps all provider identities unchanged.
No catalog, token, response body, URL, header, or raw exception is persisted.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60_reviewed as reviewed  # type: ignore  # noqa: E402

v59 = reviewed.base._core.v59


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _save(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _captured_variant_ids(catalog: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for group in catalog.get("recipes") or []:
        if not isinstance(group, dict):
            continue
        for variant in group.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            ident = _text(variant.get("variantId") or variant.get("searchVariantId"))
            if ident:
                out.add(ident)
    return out


def _failed_catalog_rows(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    source = catalog.get("source") if isinstance(catalog.get("source"), dict) else {}
    rows = source.get("catalogs") if isinstance(source.get("catalogs"), list) else []
    failed: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        unique = int(raw.get("uniqueVariants") or 0)
        hydrated = int(raw.get("hydratedVariants") or 0)
        failed_count = int(raw.get("failedDetails") or 0)
        if failed_count or hydrated != unique:
            failed.append(deepcopy(raw))
    return failed


_HTTP_RE = re.compile(r"=HTTP(\d{3})(?:\b|$)")
_NETWORK_RE = re.compile(r"=network:([^| ]+)")


def classify_failure(exc: BaseException) -> dict[str, Any]:
    """Return a secret-free, bounded failure category."""
    catalog_module = v59.catalog
    if isinstance(exc, catalog_module.CatalogAuthError):
        return {"outcome": "auth"}
    if not isinstance(exc, catalog_module.CatalogError):
        return {"outcome": "unexpected"}

    message = str(exc)
    if "returned invalid JSON" in message:
        return {"outcome": "invalid-json"}

    marker = "SEB recipe request failed:"
    if marker not in message:
        return {"outcome": "catalog-error"}

    details = message.split(marker, 1)[1]
    statuses = sorted({int(value) for value in _HTTP_RE.findall(details)})
    network_kinds = _NETWORK_RE.findall(details)

    if statuses and not network_kinds:
        if statuses == [404]:
            return {"outcome": "http-404", "httpStatuses": statuses}
        return {"outcome": "http-other", "httpStatuses": statuses}

    if network_kinds and not statuses:
        if all(kind == "Timeout" for kind in network_kinds):
            return {"outcome": "network-timeout-exhausted"}
        return {"outcome": "network-other"}

    if statuses or network_kinds:
        row: dict[str, Any] = {"outcome": "mixed-provider-failure"}
        if statuses:
            row["httpStatuses"] = statuses
        return row

    return {"outcome": "catalog-error"}


def _probe_candidate(
    *,
    variant_id: str,
    language: str,
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    configured_language: str,
    configured_country: str,
    detail_func: Callable[..., dict[str, Any]],
    detail_retry: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    try:
        detail_retry(
            detail_func,
            cfg,
            tokens,
            pcfg,
            variant_id=variant_id,
            source_language=language,
            configured_language=configured_language,
            configured_country=configured_country,
        )
    except Exception as exc:
        result = classify_failure(exc)
    else:
        result = {"outcome": "success-now"}
    return {"variantId": variant_id, **result}


def probe(
    catalog: dict[str, Any],
    *,
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    configured_language: str,
    configured_country: str,
    workers: int = 4,
    search_func: Callable[..., list[dict[str, Any]]] | None = None,
    detail_func: Callable[..., dict[str, Any]] | None = None,
    search_retry: Callable[..., list[dict[str, Any]]] | None = None,
    detail_retry: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate current-state evidence without mutating release artifacts."""
    search_func = search_func or v59._all_search_rows
    detail_func = detail_func or v59._detail
    search_retry = search_retry or reviewed._retry_search_rows
    detail_retry = detail_retry or reviewed._retry_detail

    captured_ids = _captured_variant_ids(catalog)
    failed_rows = _failed_catalog_rows(catalog)
    catalog_results: list[dict[str, Any]] = []
    total_outcomes: Counter[str] = Counter()
    declared_failed_total = 0
    current_candidate_total = 0
    probed_total = 0
    search_failures = 0

    for raw in failed_rows:
        language = _text(raw.get("language")).lower()
        country = _text(raw.get("country")).upper()
        market = _text(raw.get("market")) or (f"GS_{country}" if country else "")
        declared_unique = int(raw.get("uniqueVariants") or 0)
        declared_hydrated = int(raw.get("hydratedVariants") or 0)
        declared_failed = int(raw.get("failedDetails") or 0)
        declared_failed_total += declared_failed

        row: dict[str, Any] = {
            "language": language,
            "country": country,
            "market": market,
            "declaredUniqueVariants": declared_unique,
            "declaredHydratedVariants": declared_hydrated,
            "declaredFailedDetails": declared_failed,
        }

        if not language or not country:
            row.update(
                {
                    "state": "invalid-catalog-identity",
                    "currentSearchCount": 0,
                    "currentCandidateCount": 0,
                    "probedCount": 0,
                }
            )
            catalog_results.append(row)
            search_failures += 1
            continue

        try:
            search_rows = search_retry(
                search_func,
                cfg,
                tokens,
                pcfg,
                language=language,
                country=country,
                configured_language=configured_language,
                configured_country=configured_country,
            )
        except Exception as exc:
            row.update(
                {
                    "state": "search-failed",
                    "searchFailure": classify_failure(exc),
                    "currentSearchCount": 0,
                    "currentCandidateCount": 0,
                    "probedCount": 0,
                }
            )
            catalog_results.append(row)
            search_failures += 1
            continue

        current_ids = {
            ident
            for item in search_rows
            if isinstance(item, dict)
            and (ident := _text(item.get("searchVariantId")))
        }
        candidates = sorted(current_ids - captured_ids)
        manifest_count_stable = len(current_ids) == declared_unique
        candidate_count_matches = bool(
            manifest_count_stable and len(candidates) == declared_failed
        )
        current_candidate_total += len(candidates)

        evidence: list[dict[str, Any]] = []
        if candidates:
            with ThreadPoolExecutor(max_workers=max(1, min(int(workers), 8))) as pool:
                futures = {
                    pool.submit(
                        _probe_candidate,
                        variant_id=variant_id,
                        language=language,
                        cfg=cfg,
                        tokens=tokens,
                        pcfg=pcfg,
                        configured_language=configured_language,
                        configured_country=configured_country,
                        detail_func=detail_func,
                        detail_retry=detail_retry,
                    ): variant_id
                    for variant_id in candidates
                }
                for future in as_completed(futures):
                    evidence.append(future.result())

        evidence.sort(key=lambda item: _text(item.get("variantId")))
        outcomes = Counter(_text(item.get("outcome")) for item in evidence)
        total_outcomes.update(outcomes)
        probed_total += len(evidence)

        row.update(
            {
                "state": "probed",
                "currentSearchCount": len(current_ids),
                "searchManifestCountStable": manifest_count_stable,
                "currentCandidateCount": len(candidates),
                "candidateCountMatchesDeclaredFailures": candidate_count_matches,
                # The old capture did not persist failed IDs.  Equality by count
                # is useful evidence, but it is not historical identity proof.
                "historicalFailedIdsKnown": False,
                "presentInCapturedCatalogCount": len(current_ids & captured_ids),
                "unattributedDeclaredFailureCount": max(
                    0, declared_failed - len(candidates)
                ),
                "probedCount": len(evidence),
                "outcomes": dict(sorted(outcomes.items())),
                "evidence": evidence,
            }
        )
        catalog_results.append(row)

    result = {
        "schemaVersion": 1,
        "kind": "cook4me-v60-failed-detail-evidence",
        "catalogVersion": _text(catalog.get("catalogVersion")),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "readOnly": True,
            "failedCatalogsOnly": True,
            "currentSearchIdsOnly": True,
            "providerVariantIdentityPreserved": True,
            "providerVariantIdentityInferred": False,
            "historicalFailedIdsPersistedByCapture": False,
            "countEqualityIsHistoricalIdentityProof": False,
            "rawExceptionsPersisted": False,
            "responseBodiesPersisted": False,
            "requestHeadersPersisted": False,
            "requestUrlsPersisted": False,
            "tokensPersisted": False,
        },
        "summary": {
            "failedCatalogCount": len(failed_rows),
            "declaredFailedDetailCount": declared_failed_total,
            "capturedVariantCount": len(captured_ids),
            "currentCandidateCount": current_candidate_total,
            "probedCount": probed_total,
            "searchFailureCount": search_failures,
            "outcomes": dict(sorted(total_outcomes.items())),
        },
        "catalogs": catalog_results,
        "secretsPersisted": False,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--storage-home", default=str(Path.home()))
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--output",
        default=str(
            ROOT
            / ".catalog-build"
            / "v60-release"
            / "failed-detail-evidence.v60.json"
        ),
    )
    args = parser.parse_args()

    catalog_path = Path(args.catalog).expanduser()
    output_path = Path(args.output).expanduser()
    catalog = _load(catalog_path)

    cfg = v59.c4m.read_apk_config(None)
    tokens = v59._tokens(Path(args.storage_home).expanduser())
    if not tokens:
        raise RuntimeError("Cook4Me token store is empty")
    pcfg = v59.catalog._platform_context(
        cfg,
        args.configured_country,
        args.configured_language,
        v59.APP_VERSION,
    )

    result = probe(
        catalog,
        cfg=cfg,
        tokens=tokens,
        pcfg=pcfg,
        configured_language=args.configured_language,
        configured_country=args.configured_country,
        workers=args.workers,
    )
    _save(output_path, result)
    print(
        json.dumps(
            {
                **result["summary"],
                "output": str(output_path),
            },
            ensure_ascii=False,
        )
    )
    # This is diagnostic evidence only.  Exit zero means the evidence artifact
    # was generated, never that a release is capture-complete or activatable.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
