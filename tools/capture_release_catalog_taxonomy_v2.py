#!/usr/bin/env python3
"""Capture only SEB recipe taxonomy omitted from provider-capture v2.

The reviewed v2 provider capture already contains the full usable variant set and
all ingredient/card facts needed by the release catalog. It predates the new
requirement to persist dish/meal type and diet evidence, however, so it did not
retain SEB ``courses``, ``occasions``, exclusions or classifications.

This read-only maintenance pass reuses those exact reviewed variant IDs, calls
the already-proven recipe detail endpoint, and persists only the small taxonomy
subset required for classification. It is resumable in SQLite and deliberately
checks every usable variant instead of assuming serving variants share taxonomy.
Provider/account credentials and full recipe responses are never written to the
cache or export.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
from typing import Any
import urllib.parse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
VENDOR = COMPONENT / "vendor"
for path in (COMPONENT, VENDOR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cook4me_phonefree as c4m  # type: ignore  # noqa: E402
import cook4me_recipe_catalog as catalog  # type: ignore  # noqa: E402

APP_VERSION = "36.0.0-RC3"
APPLIANCE_GROUP = "APPLIANCE_GROUP_15"
PROVIDER_KIND = "cook4me-provider-capture"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _fid(value: Any) -> str:
    return _text(catalog._fid(value))


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_provider(path: Path) -> dict[str, Any]:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith("provider-capture-v2.json.gz"):
                    value = json.loads(gzip.decompress(archive.read(name)))
                    break
            else:
                raise RuntimeError(f"{path}: provider-capture-v2.json.gz not found")
    elif path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("kind") != PROVIDER_KIND:
        raise RuntimeError(f"{path}: expected {PROVIDER_KIND}")
    return value


def _tokens(storage_home: Path) -> dict[str, Any]:
    path = storage_home / ".config" / "cook4me" / "tokens.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _status_codes(exc: Exception) -> list[int]:
    return [int(value) for value in re.findall(r"HTTP(\d{3})", str(exc))]


def _key_name(value: Any) -> dict[str, str] | None:
    if isinstance(value, str):
        text = _text(value)
        return {"key": text} if text else None
    if not isinstance(value, dict):
        return None
    key = _text(value.get("key") or value.get("reference") or value.get("id"))
    name = _text(value.get("name") or value.get("label") or value.get("value"))
    row = {}
    if key:
        row["key"] = key
    if name:
        row["name"] = name
    return row or None


def _key_name_list(value: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in value if isinstance(value, list) else []:
        row = _key_name(raw)
        if not row:
            continue
        ident = (row.get("key", ""), row.get("name", ""))
        if ident in seen:
            continue
        seen.add(ident)
        rows.append(row)
    return rows


def _domain(value: Any) -> dict[str, str] | None:
    return _key_name(value)


def _taxonomy(root: dict[str, Any], variant_id: str) -> dict[str, Any]:
    grouping = _fid(root.get("groupingId")) or _fid(root.get("topRecipeId"))
    out: dict[str, Any] = {
        "variantId": _fid(variant_id),
        "groupingFunctionalId": grouping,
        "recipeFunctionalId": _fid(root.get("fid")) or _fid(variant_id),
        "language": _text(root.get("lang")).lower(),
        "market": _text(root.get("market")).upper(),
        "courses": _key_name_list(root.get("courses")),
        "occasions": _key_name_list(root.get("occasions")),
        "excludedFoods": _key_name_list(root.get("excludedFoods")),
        "detectedExcludedFoods": _key_name_list(root.get("detectedExcludedFoods")),
        "classifications": _key_name_list(root.get("classifications")),
    }
    domain = _domain(root.get("domain"))
    if domain:
        out["domain"] = domain
    return out


def _fetch_once(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    variant_id: str,
    configured_language: str,
    configured_country: str,
    appliance_group: bool,
) -> tuple[dict[str, Any] | None, list[int], str]:
    query = "?format=mobile"
    if appliance_group:
        query += "&applianceGroup=" + APPLIANCE_GROUP
    url = (
        cfg["platform_base_url"].rstrip("/")
        + "/common-api/v3/recipes/PRO/"
        + urllib.parse.quote(_fid(variant_id), safe="")
        + "/"
        + query
    )
    try:
        payload, auth = catalog._http_json(
            "GET",
            url,
            headers_iter=catalog._request_headers(
                cfg,
                tokens,
                configured_country,
                configured_language,
                APP_VERSION,
                url,
                pcfg,
            ),
            timeout=30,
        )
    except Exception as exc:
        return None, _status_codes(exc), type(exc).__name__ + ": " + str(exc)
    return _taxonomy(catalog._recipe_root(payload), variant_id), [], auth


def _fetch_taxonomy(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    variant_id: str,
    configured_language: str,
    configured_country: str,
) -> dict[str, Any]:
    row, codes, evidence = _fetch_once(
        cfg,
        tokens,
        pcfg,
        variant_id=variant_id,
        configured_language=configured_language,
        configured_country=configured_country,
        appliance_group=False,
    )
    if row is not None:
        return row
    if codes and all(code == 404 for code in codes):
        row2, codes2, evidence2 = _fetch_once(
            cfg,
            tokens,
            pcfg,
            variant_id=variant_id,
            configured_language=configured_language,
            configured_country=configured_country,
            appliance_group=True,
        )
        if row2 is not None:
            return row2
        if codes2 and all(code == 404 for code in codes2):
            raise RuntimeError(f"{variant_id}: detail became dual-404 after reviewed provider capture")
        raise RuntimeError(f"{variant_id}: appliance-group taxonomy retry failed: {evidence2}")
    raise RuntimeError(f"{variant_id}: taxonomy detail failed: {evidence}")


def _open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS taxonomy (
            variant_id TEXT PRIMARY KEY,
            taxonomy_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        )
        """
    )
    return conn


def _store(conn: sqlite3.Connection, variant_id: str, row: dict[str, Any]) -> None:
    raw = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
    with conn:
        conn.execute(
            "INSERT INTO taxonomy(variant_id,taxonomy_json,fetched_at) VALUES(?,?,?) "
            "ON CONFLICT(variant_id) DO UPDATE SET taxonomy_json=excluded.taxonomy_json,fetched_at=excluded.fetched_at",
            (variant_id, raw, _iso_now()),
        )


def capture(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, str]]]:
    provider = _load_provider(Path(args.provider_capture).expanduser())
    variants = sorted(
        {
            _text(row.get("variantId"))
            for row in provider.get("details") or []
            if isinstance(row, dict) and _text(row.get("variantId"))
        }
    )
    if args.limit:
        variants = variants[: max(1, int(args.limit))]

    cfg = c4m.read_apk_config(None)
    tokens = _tokens(Path(args.storage_home).expanduser())
    pcfg = catalog._platform_context(
        cfg, args.configured_country, args.configured_language, APP_VERSION
    )
    conn = _open_db(Path(args.cache_db).expanduser())
    failures: list[dict[str, str]] = []
    try:
        cached = {
            row[0]
            for row in conn.execute("SELECT variant_id FROM taxonomy")
        }
        pending = [variant for variant in variants if args.refresh or variant not in cached]
        print(
            f"[taxonomy] variants={len(variants)} cached={len(variants)-len(pending)} pending={len(pending)}",
            flush=True,
        )
        workers = max(1, min(int(args.workers), 8))
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _fetch_taxonomy,
                    cfg,
                    tokens,
                    pcfg,
                    variant_id=variant,
                    configured_language=args.configured_language,
                    configured_country=args.configured_country,
                ): variant
                for variant in pending
            }
            for future in as_completed(futures):
                variant = futures[future]
                try:
                    row = future.result()
                except Exception as exc:
                    failures.append(
                        {"variantId": variant, "error": type(exc).__name__ + ": " + str(exc)}
                    )
                    continue
                _store(conn, variant, row)
                done += 1
                if done % 250 == 0:
                    print(f"[taxonomy] fetched={done}/{len(pending)}", flush=True)

        rows: list[dict[str, Any]] = []
        for variant in variants:
            found = conn.execute(
                "SELECT taxonomy_json FROM taxonomy WHERE variant_id=?", (variant,)
            ).fetchone()
            if found:
                rows.append(json.loads(found[0]))

        payload = {
            "schemaVersion": 1,
            "kind": "cook4me-provider-taxonomy-capture-v2",
            "generatedAt": _iso_now(),
            "readOnly": True,
            "secretsPersisted": False,
            "sourceProviderKind": PROVIDER_KIND,
            "sourceVariantCount": len(variants),
            "capturedVariantCount": len(rows),
            "complete": len(rows) == len(variants) and not failures,
            "taxonomyFields": [
                "courses", "occasions", "excludedFoods", "detectedExcludedFoods",
                "classifications", "domain",
            ],
            "variants": rows,
        }
        output = Path(args.output).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(output, "wt", encoding="utf-8", compresslevel=9) as handle:
            json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        return payload, failures
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-capture", required=True)
    parser.add_argument("--storage-home", required=True)
    parser.add_argument("--cache-db", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--failures", required=True)
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    payload, failures = capture(args)
    Path(args.failures).expanduser().write_text(
        json.dumps(failures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = {
        "sourceVariants": payload["sourceVariantCount"],
        "capturedVariants": payload["capturedVariantCount"],
        "failures": len(failures),
        "complete": payload["complete"],
        "withCourses": sum(bool(row.get("courses")) for row in payload["variants"]),
        "withOccasions": sum(bool(row.get("occasions")) for row in payload["variants"]),
        "withExcludedFoods": sum(bool(row.get("excludedFoods")) for row in payload["variants"]),
        "withDetectedExcludedFoods": sum(bool(row.get("detectedExcludedFoods")) for row in payload["variants"]),
        "withClassifications": sum(bool(row.get("classifications")) for row in payload["variants"]),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if payload["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
