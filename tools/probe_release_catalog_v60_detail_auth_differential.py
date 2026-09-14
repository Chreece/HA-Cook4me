#!/usr/bin/env python3
"""Generate bounded, secret-free detail-auth evidence for failed v60 catalogs.

This probe is intentionally diagnostic only. It reuses the current failed-catalog
search path, selects a deterministic handful of unresolved provider IDs plus
known-present controls from each failed catalog, and records only bounded
per-auth-mode HTTP/network outcomes from the existing detail request.

No token, header, URL, response body, title, ingredient payload, or raw exception
is persisted. The release catalog is never modified or activated.
"""
from __future__ import annotations

import argparse
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
import probe_release_catalog_v60_failed_details as failed_probe  # type: ignore  # noqa: E402

v59 = reviewed.base._core.v59

_ALLOWED_PROVIDER_MODES = {
    "app",
    "access_rcu",
    "access_rcu_remote",
    "id_rcu",
    "id_rcu_remote",
    "access_bearer",
    "id_bearer",
}
_RESULT_RE = re.compile(
    r"^([a-z0-9_]+)=(HTTP\d{3}|network:[A-Za-z0-9_.-]+)$",
    re.IGNORECASE,
)
_IDENTITY_FIELDS = (
    "searchVariantId",
    "variantId",
    "recipeFunctionalId",
    "groupingFunctionalId",
    "functionalId",
    "fid",
    "identifier",
)


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except PermissionError:
        raise RuntimeError(f"not readable by current user: {path}") from None
    except FileNotFoundError:
        raise RuntimeError(f"file does not exist: {path}") from None
    except json.JSONDecodeError:
        raise RuntimeError(f"invalid JSON: {path}") from None
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {type(exc).__name__}") from None
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _load_tokens(storage_home: Path) -> dict[str, Any]:
    path = storage_home / ".config" / "cook4me" / "tokens.json"
    value = _load_json(path)
    if not value:
        raise RuntimeError("Cook4Me token store is an empty JSON object")
    return value


def _safe_provider_results(exc: BaseException) -> dict[str, str]:
    """Extract only allow-listed auth-mode result classes from a provider error."""
    message = str(exc)
    markers = (
        "SEB recipe authentication failed (tokens redacted):",
        "SEB recipe request failed:",
    )
    details = ""
    for marker in markers:
        if marker in message:
            details = message.split(marker, 1)[1].strip()
            break
    if not details:
        return {}

    results: dict[str, str] = {}
    for part in details.split("|"):
        match = _RESULT_RE.fullmatch(part.strip())
        if not match:
            continue
        mode = match.group(1).lower()
        if mode not in _ALLOWED_PROVIDER_MODES:
            continue
        result = match.group(2)
        if result.upper().startswith("HTTP"):
            result = "HTTP" + result[4:]
        elif result.lower().startswith("network:"):
            kind = result.split(":", 1)[1]
            result = "network:" + kind
        results[mode] = result
    return dict(sorted(results.items()))


def classify_detail_failure(exc: BaseException) -> dict[str, Any]:
    """Classify a detail failure without collapsing 404+401 into generic auth."""
    matrix = _safe_provider_results(exc)
    statuses = sorted(
        {
            int(result[4:])
            for result in matrix.values()
            if result.startswith("HTTP") and result[4:].isdigit()
        }
    )
    networks = sorted(
        {
            result.split(":", 1)[1]
            for result in matrix.values()
            if result.startswith("network:")
        }
    )

    catalog_module = v59.catalog
    if isinstance(exc, catalog_module.CatalogAuthError):
        if matrix and not networks and statuses and set(statuses) <= {401, 403}:
            outcome = "auth"
        elif (
            matrix
            and matrix.get("app") == "HTTP404"
            and not networks
            and statuses
            and set(statuses) <= {401, 403, 404}
        ):
            outcome = "app-404-auth-fallbacks"
        else:
            outcome = "mixed-auth-provider-failure"
    elif isinstance(exc, catalog_module.CatalogError):
        outcome = failed_probe.classify_failure(exc).get("outcome") or "catalog-error"
    else:
        outcome = "unexpected"

    result: dict[str, Any] = {"outcome": outcome}
    if matrix:
        result["providerResults"] = matrix
    if statuses:
        result["httpStatuses"] = statuses
    if networks:
        result["networkKinds"] = networks
    return result


def _sample_ids(values: list[str], count: int) -> list[str]:
    """Return deterministic spread samples: edges first, then interior points."""
    ordered = sorted(dict.fromkeys(_text(value) for value in values if _text(value)))
    count = max(0, int(count))
    if count <= 0 or not ordered:
        return []
    if count >= len(ordered):
        return ordered
    if count == 1:
        return [ordered[0]]
    indexes = {
        round(position * (len(ordered) - 1) / (count - 1))
        for position in range(count)
    }
    return [ordered[index] for index in sorted(indexes)]


def _identity_snapshot(row: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in _IDENTITY_FIELDS:
        value = row.get(key)
        if isinstance(value, (str, int, float)) and (text := _text(value)):
            out[key] = text
    return out


def _probe_one(
    *,
    variant_id: str,
    role: str,
    language: str,
    search_row: dict[str, Any],
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    configured_language: str,
    configured_country: str,
    detail_func: Callable[..., dict[str, Any]],
    detail_retry: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "variantId": variant_id,
        "role": role,
        "searchIdentity": _identity_snapshot(search_row),
        "searchRowKeys": sorted(_text(key) for key in search_row.keys() if _text(key)),
    }
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
        row.update(classify_detail_failure(exc))
    else:
        row["outcome"] = "success-now"
    return row


def probe(
    catalog: dict[str, Any],
    *,
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    configured_language: str,
    configured_country: str,
    candidate_samples: int = 3,
    control_samples: int = 1,
    search_func: Callable[..., list[dict[str, Any]]] | None = None,
    detail_func: Callable[..., dict[str, Any]] | None = None,
    search_retry: Callable[..., list[dict[str, Any]]] | None = None,
    detail_retry: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare a bounded sample of unresolved IDs with known-present controls."""
    if not 1 <= int(candidate_samples) <= 9:
        raise ValueError("candidate_samples must be between 1 and 9")
    if not 1 <= int(control_samples) <= 3:
        raise ValueError("control_samples must be between 1 and 3")

    search_func = search_func or v59._all_search_rows
    detail_func = detail_func or v59._detail
    search_retry = search_retry or reviewed._retry_search_rows
    detail_retry = detail_retry or reviewed._retry_detail

    captured_ids = failed_probe._captured_variant_ids(catalog)
    failed_catalogs = failed_probe._failed_catalog_rows(catalog)
    results: list[dict[str, Any]] = []

    for failed in failed_catalogs:
        language = _text(failed.get("language")).lower()
        country = _text(failed.get("country")).upper()
        market = _text(failed.get("market")) or f"GS_{country}"
        if not language or not country:
            results.append(
                {
                    "language": language,
                    "country": country,
                    "market": market,
                    "state": "invalid-catalog-identity",
                    "samples": [],
                }
            )
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
            results.append(
                {
                    "language": language,
                    "country": country,
                    "market": market,
                    "state": "search-failed",
                    "searchFailure": classify_detail_failure(exc),
                    "samples": [],
                }
            )
            continue

        by_id = {
            ident: row
            for row in search_rows
            if isinstance(row, dict)
            and (ident := _text(row.get("searchVariantId")))
        }
        current_ids = set(by_id)
        candidates = sorted(current_ids - captured_ids)
        controls = sorted(current_ids & captured_ids)
        candidate_ids = _sample_ids(candidates, candidate_samples)
        control_ids = _sample_ids(controls, control_samples)

        samples: list[dict[str, Any]] = []
        for role, sample_ids in (
            ("unresolved-current-id", candidate_ids),
            ("captured-control", control_ids),
        ):
            for variant_id in sample_ids:
                samples.append(
                    _probe_one(
                        variant_id=variant_id,
                        role=role,
                        language=language,
                        search_row=by_id[variant_id],
                        cfg=cfg,
                        tokens=tokens,
                        pcfg=pcfg,
                        configured_language=configured_language,
                        configured_country=configured_country,
                        detail_func=detail_func,
                        detail_retry=detail_retry,
                    )
                )

        results.append(
            {
                "language": language,
                "country": country,
                "market": market,
                "state": "probed",
                "declaredFailedDetails": int(failed.get("failedDetails") or 0),
                "currentSearchCount": len(current_ids),
                "currentCandidateCount": len(candidates),
                "currentControlCount": len(controls),
                "candidateSamples": candidate_ids,
                "controlSamples": control_ids,
                "samples": samples,
            }
        )

    sample_rows = [
        sample
        for catalog_row in results
        for sample in catalog_row.get("samples") or []
        if isinstance(sample, dict)
    ]
    outcomes: dict[str, int] = {}
    for sample in sample_rows:
        outcome = _text(sample.get("outcome")) or "unknown"
        outcomes[outcome] = outcomes.get(outcome, 0) + 1

    return {
        "schemaVersion": 1,
        "kind": "cook4me-v60-detail-auth-differential",
        "catalogVersion": _text(catalog.get("catalogVersion")),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "policy": {
            "readOnly": True,
            "failedCatalogsOnly": True,
            "boundedSampling": True,
            "candidateSampleLimit": 9,
            "controlSampleLimit": 3,
            "rawExceptionsPersisted": False,
            "responseBodiesPersisted": False,
            "requestHeadersPersisted": False,
            "requestUrlsPersisted": False,
            "tokensPersisted": False,
            "providerResultModesAllowlisted": True,
        },
        "summary": {
            "failedCatalogCount": len(failed_catalogs),
            "sampleCount": len(sample_rows),
            "outcomes": dict(sorted(outcomes.items())),
        },
        "catalogs": results,
        "secretsPersisted": False,
    }


def _save(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--storage-home", default=str(Path.home()))
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--candidate-samples", type=int, default=3)
    parser.add_argument("--control-samples", type=int, default=1)
    parser.add_argument(
        "--output",
        default=str(
            ROOT
            / ".catalog-build"
            / "v60-release"
            / "detail-auth-differential.v60.json"
        ),
    )
    args = parser.parse_args()

    catalog = _load_json(Path(args.catalog).expanduser())
    tokens = _load_tokens(Path(args.storage_home).expanduser())
    cfg = v59.c4m.read_apk_config(None)
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
        candidate_samples=args.candidate_samples,
        control_samples=args.control_samples,
    )
    output = Path(args.output).expanduser()
    _save(output, result)
    print(
        json.dumps(
            {
                **result["summary"],
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
