#!/usr/bin/env python3
"""Re-probe only release-catalog publications that failed detail hydration.

This is a maintenance/read-only diagnostic. It intentionally reuses the exact
SEB recipe-detail endpoint proven in the mobile app and records only HTTP/result
metadata plus non-secret search-card fields. Provider credentials are read from
the maintainer's local Cook4Me token store and are never written to the report.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
VENDOR = COMPONENT / "vendor"
for path in (ROOT / "tools", COMPONENT, VENDOR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog as release_v1  # type: ignore  # noqa: E402
import cook4me_phonefree as c4m  # type: ignore  # noqa: E402
import cook4me_recipe_catalog as catalog  # type: ignore  # noqa: E402

_CATALOG_RE = re.compile(r"^\[catalog\]\s+([a-z]{2})/GS_([A-Z]{2})\s*$")
_FAILURE_RE = re.compile(r"^\s*!\s+([^:\s]+):\s*(.+?)\s*$")


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _fid(value: Any) -> str:
    return _text(catalog._fid(value))


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_failures(build_log: Path) -> dict[tuple[str, str], list[str]]:
    current: tuple[str, str] | None = None
    failures: dict[tuple[str, str], list[str]] = defaultdict(list)
    for line in build_log.read_text(encoding="utf-8", errors="replace").splitlines():
        if match := _CATALOG_RE.match(line):
            current = (match.group(1), match.group(2))
            continue
        if current and (match := _FAILURE_RE.match(line)):
            failures[current].append(match.group(1))
    return {key: list(dict.fromkeys(values)) for key, values in failures.items() if values}


def _safe_identifier(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {"functionalId": _fid(value)} if _fid(value) else {}
    row = {
        "functionalId": _fid(value),
        "sourceSystem": _text(value.get("sourceSystem")),
        "version": _text(value.get("version")),
    }
    return {key: val for key, val in row.items() if val}


def _search_evidence(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    language: str,
    country: str,
    configured_language: str,
    configured_country: str,
    wanted: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    market = f"GS_{country}"
    url = cfg["platform_base_url"].rstrip("/") + "/common-api/v4/search/recipes"
    page = 0
    total_pages: int | None = None
    found: dict[str, dict[str, Any]] = {}
    pages = 0
    raw_rows = 0
    auth_modes = Counter()
    while total_pages is None or page < total_pages:
        payload, auth_mode = catalog._http_json(
            "POST",
            url,
            headers_iter=release_v1._headers(
                cfg,
                tokens,
                configured_country,
                configured_language,
                url,
                pcfg,
            ),
            params={
                "lang": language,
                "market": market,
                "page": page,
                "size": release_v1.PAGE_SIZE,
                "q": "",
                "groupBy": "",
                "myUniverse": "false",
                "myOwnRecipe": "false",
                "withAutomaticSpellcheck": "true",
            },
            body=release_v1.app_search_body(language, market),
            timeout=30,
        )
        pages += 1
        auth_modes[auth_mode] += 1
        if not isinstance(payload, dict):
            raise RuntimeError(f"{language}/{market}: invalid search response")
        content = payload.get("content") if isinstance(payload.get("content"), list) else []
        raw_rows += len(content)
        for raw in content:
            if not isinstance(raw, dict):
                continue
            variant_id = _fid(raw.get("identifier") or raw.get("fid") or raw.get("functionalId"))
            if variant_id not in wanted:
                continue
            found[variant_id] = {
                "identifier": _safe_identifier(raw.get("identifier") or raw.get("fid") or raw.get("functionalId")),
                "title": catalog._clean_text(raw.get("title") or raw.get("shortTitle") or raw.get("normalizedTitle")),
                "language": catalog._clean_text(raw.get("lang")),
                "market": catalog._clean_text(raw.get("market")),
                "domain": catalog._clean_text(raw.get("domain")),
                "recipeType": catalog._clean_text(raw.get("recipeType")),
                "status": catalog._clean_text(raw.get("status")),
                "groupingFunctionalId": _fid(raw.get("groupingId")),
                "groupSize": raw.get("groupSize"),
                "cover": catalog.extract_recipe_cover(raw),
            }
            found[variant_id] = {
                key: value
                for key, value in found[variant_id].items()
                if value not in (None, "", {}, [])
            }
        page_info = payload.get("page") if isinstance(payload.get("page"), dict) else {}
        try:
            total_pages = int(page_info.get("totalPages"))
        except (TypeError, ValueError):
            total_pages = page + (1 if content else 0)
        page += 1
        if not content:
            break
    return found, {
        "pages": pages,
        "rawRows": raw_rows,
        "found": len(found),
        "wanted": len(wanted),
        "authModes": dict(auth_modes),
    }


def _attempt_get(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    variant_id: str,
    configured_language: str,
    configured_country: str,
    params: dict[str, str] | None,
) -> dict[str, Any]:
    variant = _fid(variant_id)
    url = (
        cfg["platform_base_url"].rstrip("/")
        + "/common-api/v3/recipes/PRO/"
        + urllib.parse.quote(variant, safe="")
        + "/?format=mobile"
    )
    attempts: list[dict[str, Any]] = []
    if c4m.curl_requests is None:
        raise RuntimeError("curl-cffi is not available")
    for auth_mode, headers in release_v1._headers(
        cfg,
        tokens,
        configured_country,
        configured_language,
        url,
        pcfg,
    ):
        try:
            response = c4m.curl_requests.get(
                url,
                params=params or None,
                headers=headers,
                timeout=30,
                allow_redirects=True,
                impersonate="chrome",
            )
        except Exception as exc:
            attempts.append(
                {
                    "authMode": auth_mode,
                    "networkError": type(exc).__name__,
                }
            )
            continue
        status = int(response.status_code)
        row: dict[str, Any] = {
            "authMode": auth_mode,
            "status": status,
            "contentType": _text(response.headers.get("content-type")),
            "bytes": len(response.content or b""),
        }
        if 200 <= status < 300:
            try:
                payload = response.json()
            except Exception as exc:
                row["jsonError"] = type(exc).__name__
            else:
                root = catalog._recipe_root(payload)
                row["detail"] = {
                    "recipeFunctionalId": _fid(root.get("fid") or root.get("identifier")),
                    "groupingFunctionalId": _fid(root.get("groupingId") or root.get("topRecipeId")),
                    "title": catalog._clean_text(root.get("title") or root.get("shortTitle") or root.get("normalizedTitle")),
                    "language": catalog._clean_text(root.get("lang")),
                    "market": catalog._clean_text(root.get("market")),
                    "ingredientCount": len(root.get("ingredients")) if isinstance(root.get("ingredients"), list) else 0,
                }
                row["detail"] = {
                    key: value
                    for key, value in row["detail"].items()
                    if value not in (None, "", {}, [])
                }
        attempts.append(row)
        if 200 <= status < 300:
            break
    return {"attempts": attempts}


def _probe_one(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    variant_id: str,
    configured_language: str,
    configured_country: str,
) -> dict[str, Any]:
    baseline = _attempt_get(
        cfg,
        tokens,
        pcfg,
        variant_id=variant_id,
        configured_language=configured_language,
        configured_country=configured_country,
        params=None,
    )
    baseline_ok = any(
        isinstance(row, dict) and 200 <= int(row.get("status") or 0) < 300
        for row in baseline["attempts"]
    )
    result: dict[str, Any] = {"baseline": baseline}
    if not baseline_ok:
        # The mobile Retrofit contract exposes applianceGroup as an optional
        # query parameter on this exact same v3 detail endpoint. This is the only
        # alternate request shape tried here; no unproven endpoint is invented.
        result["withApplianceGroup"] = _attempt_get(
            cfg,
            tokens,
            pcfg,
            variant_id=variant_id,
            configured_language=configured_language,
            configured_country=configured_country,
            params={"applianceGroup": "APPLIANCE_GROUP_15"},
        )
    return result


def _status_signature(probe: dict[str, Any]) -> str:
    parts: list[str] = []
    for request_name in ("baseline", "withApplianceGroup"):
        request = probe.get(request_name)
        if not isinstance(request, dict):
            continue
        statuses = [
            str(row.get("status"))
            for row in request.get("attempts") or []
            if isinstance(row, dict) and row.get("status") is not None
        ]
        if statuses:
            parts.append(request_name + ":" + ",".join(statuses))
        elif request.get("attempts"):
            parts.append(request_name + ":network")
    return "|".join(parts) or "no-result"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-home", required=True)
    parser.add_argument("--build-log", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    build_log = Path(args.build_log).expanduser().resolve()
    failures = parse_failures(build_log)
    if not failures:
        raise SystemExit("No failed detail IDs were found in the supplied build log")

    cfg = c4m.read_apk_config(None)
    tokens = release_v1._tokens(Path(args.storage_home).expanduser())
    pcfg = catalog._platform_context(
        cfg,
        args.configured_country,
        args.configured_language,
        release_v1.APP_VERSION,
    )

    search_rows: dict[str, dict[str, Any]] = {}
    catalog_stats: list[dict[str, Any]] = []
    for (language, country), ids in failures.items():
        print(f"[search] {language}/GS_{country} failed={len(ids)}", flush=True)
        found, stats = _search_evidence(
            cfg,
            tokens,
            pcfg,
            language=language,
            country=country,
            configured_language=args.configured_language,
            configured_country=args.configured_country,
            wanted=set(ids),
        )
        for variant_id, row in found.items():
            search_rows[variant_id] = {
                "sourceCatalogLanguage": language,
                "sourceCatalogCountry": country,
                **row,
            }
        catalog_stats.append(
            {
                "language": language,
                "country": country,
                "market": f"GS_{country}",
                "failedIds": len(ids),
                **stats,
            }
        )

    all_ids = [variant_id for ids in failures.values() for variant_id in ids]
    probes: dict[str, dict[str, Any]] = {}
    completed = 0
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 8))) as pool:
        futures = {
            pool.submit(
                _probe_one,
                cfg,
                tokens,
                pcfg,
                variant_id=variant_id,
                configured_language=args.configured_language,
                configured_country=args.configured_country,
            ): variant_id
            for variant_id in all_ids
        }
        for future in as_completed(futures):
            variant_id = futures[future]
            completed += 1
            try:
                probes[variant_id] = future.result()
            except Exception as exc:
                probes[variant_id] = {"probeError": type(exc).__name__}
            if completed == 1 or completed % 100 == 0 or completed == len(all_ids):
                print(f"[detail] {completed}/{len(all_ids)}", flush=True)

    signatures = Counter(_status_signature(probe) for probe in probes.values())
    recovered = [
        variant_id
        for variant_id, probe in probes.items()
        if any(
            isinstance(row, dict) and 200 <= int(row.get("status") or 0) < 300
            for request_name in ("baseline", "withApplianceGroup")
            for row in ((probe.get(request_name) or {}).get("attempts") or [])
        )
    ]
    missing_from_search = sorted(set(all_ids) - set(search_rows))

    payload = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "readOnly": True,
        "secretsPersisted": False,
        "detailEndpoint": "/common-api/v3/recipes/PRO/{variantId}/?format=mobile",
        "applianceGroupProbe": "APPLIANCE_GROUP_15",
        "summary": {
            "affectedCatalogs": len(failures),
            "failedVariantIds": len(all_ids),
            "searchRowsRecovered": len(search_rows),
            "missingFromSearch": len(missing_from_search),
            "detailRecovered": len(recovered),
            "detailStillUnavailable": len(all_ids) - len(recovered),
            "statusSignatures": dict(signatures),
        },
        "catalogs": catalog_stats,
        "missingFromSearch": missing_from_search,
        "recoveredDetailIds": sorted(recovered),
        "items": {
            variant_id: {
                "search": search_rows.get(variant_id),
                "detailProbe": probes.get(variant_id),
            }
            for variant_id in sorted(set(all_ids), key=lambda value: (len(value), value))
        },
    }
    _json(Path(args.output).expanduser().resolve(), payload)
    print(json.dumps(payload["summary"], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
