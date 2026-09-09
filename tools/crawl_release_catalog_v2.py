#!/usr/bin/env python3
"""Resumable Cook4Me provider crawl for release-catalog v2.

This maintenance tool deliberately separates provider acquisition from release
assembly. It re-audits all 28 proven language/market mappings, caches each
successful recipe detail in SQLite, records provider-search-only HTTP-404 rows
separately, and exports a secret-free capture for review/assembly.

No Home Assistant import is required. Account/provider tokens are read only from
the maintainer's local Cook4Me token store and are never written to SQLite or the
exported capture.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
VENDOR = COMPONENT / "vendor"
for path in (COMPONENT, VENDOR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cook4me_phonefree as c4m  # type: ignore  # noqa: E402
import cook4me_recipe_catalog as catalog  # type: ignore  # noqa: E402

APP_VERSION = "36.0.0-RC3"
PAGE_SIZE = 50
APPLIANCE_GROUP = "APPLIANCE_GROUP_15"

AUDITED_CATALOGS: tuple[tuple[str, str], ...] = (
    ("ar", "AE"), ("bg", "BG"), ("cs", "CZ"), ("da", "DK"),
    ("de", "DE"), ("el", "GR"), ("en", "GB"), ("es", "ES"),
    ("fa", "AE"), ("fi", "FI"), ("fr", "FR"), ("hr", "HR"),
    ("hu", "HU"), ("it", "IT"), ("ja", "JP"), ("ko", "KR"),
    ("nl", "NL"), ("no", "NO"), ("pl", "PL"), ("pt", "PT"),
    ("ro", "RO"), ("ru", "RU"), ("sk", "SK"), ("sl", "SI"),
    ("sv", "SE"), ("tr", "TR"), ("uk", "UA"), ("zh", "TW"),
)


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _fid(value: Any) -> str:
    return _text(catalog._fid(value))


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        out = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) and out >= 0 else None


def _tokens(storage_home: Path) -> dict[str, Any]:
    path = storage_home / ".config" / "cook4me" / "tokens.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _identifier(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        fid = _fid(value)
        return {"functionalId": fid} if fid else {}
    out = {
        "functionalId": _fid(value),
        "sourceSystem": _text(value.get("sourceSystem")),
        "version": _text(value.get("version")),
    }
    return {key: val for key, val in out.items() if val not in (None, "")}


def _unit(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out = {
        "key": _text(value.get("key")),
        "name": _text(value.get("name")),
        "abbreviation": _text(value.get("abbreviation")),
        "pluralName": _text(value.get("pluralName")),
    }
    return {key: val for key, val in out.items() if val}


def _media_id(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    media = value.get("media") if isinstance(value.get("media"), dict) else value
    return _text(media.get("_id") or media.get("key") or media.get("id"))


def _cover(root: dict[str, Any]) -> tuple[str, str]:
    url = _text(catalog.extract_recipe_cover(root))
    cover = root.get("cover") if isinstance(root.get("cover"), dict) else {}
    media_id = _media_id(cover)
    if not media_id:
        for row in root.get("resourceMedias") or []:
            if isinstance(row, dict) and row.get("isCover") is True:
                media_id = _media_id(row)
                if media_id:
                    break
    return url, media_id


def _clean_ingredient(item: dict[str, Any]) -> dict[str, Any] | None:
    food = item.get("food") if isinstance(item.get("food"), dict) else {}
    weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
    food_name = _text(food.get("name"))
    appliance = _text(item.get("applianceDescription"))
    application = _text(item.get("applicationDescription"))
    clean_name = food_name or appliance or application
    if not clean_name:
        return None
    out: dict[str, Any] = {
        "lineFunctionalId": _fid(item.get("fid")),
        "foodKey": _text(food.get("key")),
        "foodName": food_name,
        "cleanName": clean_name,
        "applianceDescription": appliance,
        "applicationDescription": application,
        "quantity": _number(item.get("quantity")),
        "unit": _unit(item.get("unit")),
        "weight": {
            "quantity": _number(weight.get("quantity")),
            "unit": _unit(weight.get("unit")),
        },
    }
    if not out["weight"]["unit"] and out["weight"]["quantity"] is None:
        out.pop("weight")
    return {
        key: value
        for key, value in out.items()
        if value not in (None, "", {}, [])
    }


def _detail_payload(root: dict[str, Any], variant_id: str, source_language: str) -> dict[str, Any]:
    cover_url, cover_media_id = _cover(root)
    ingredients = [
        row
        for raw in root.get("ingredients") or []
        if isinstance(raw, dict) and (row := _clean_ingredient(raw))
    ]
    master = root.get("masterRecipe") if isinstance(root.get("masterRecipe"), dict) else {}
    reference = root.get("referenceRecipe") if isinstance(root.get("referenceRecipe"), dict) else {}
    creator = root.get("creator") if isinstance(root.get("creator"), dict) else {}
    owner = root.get("owner") if isinstance(root.get("owner"), dict) else {}
    grouping = _fid(root.get("groupingId")) or _fid(root.get("topRecipeId"))
    recipe_id = _fid(root.get("fid")) or _fid(root.get("identifier")) or _fid(variant_id)
    return {
        "variantId": _fid(variant_id),
        "recipeFunctionalId": recipe_id,
        "groupingFunctionalId": grouping,
        "topRecipeId": _fid(root.get("topRecipeId")),
        "masterRecipeFunctionalId": _fid(master.get("fid")),
        "referenceRecipeFunctionalId": _fid(reference.get("fid") or reference.get("identifier")),
        "title": _text(root.get("title") or root.get("shortTitle") or root.get("normalizedTitle")),
        "normalizedTitle": _text(root.get("normalizedTitle")),
        "language": _text(root.get("lang")).lower() or source_language.lower(),
        "market": _text(root.get("market")).upper(),
        "status": _text(root.get("status")),
        "recipeType": deepcopy(root.get("recipeType")),
        "cover": cover_url,
        "coverMediaId": cover_media_id,
        "servings": (catalog._yield(root) or {}).get("quantity") or root.get("groupSize"),
        "yield": catalog._yield(root),
        "durations": catalog._durations(root),
        "difficulty": root.get("difficulty"),
        "publicationDate": _text(root.get("publicationDate")),
        "recipeModificationDate": _text(root.get("recipeModificationDate")),
        "topRecipeModificationDate": _text(root.get("topRecipeModificationDate")),
        "creator": _identifier(creator.get("fid")),
        "owner": _identifier(owner.get("fid")),
        "ingredients": ingredients,
    }


def _search_body(language: str, market: str) -> dict[str, Any]:
    return {
        "fieldFilters": [
            {"field": "lang.key", "values": [language.lower()]},
            {"field": "market.key", "values": [market.upper()]},
            {"field": "applianceGroups.reference.key", "values": [APPLIANCE_GROUP]},
            {"field": "topRecipe.type.key", "values": ["BRAND"]},
        ]
    }


def _headers(cfg, tokens, country, language, url, pcfg):
    return catalog._request_headers(cfg, tokens, country, language, APP_VERSION, url, pcfg)


def _search_catalog(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    language: str,
    country: str,
    configured_language: str,
    configured_country: str,
) -> list[dict[str, Any]]:
    market = f"GS_{country}"
    url = cfg["platform_base_url"].rstrip("/") + "/common-api/v4/search/recipes"
    rows: list[dict[str, Any]] = []
    page = 0
    total_pages: int | None = None
    while total_pages is None or page < total_pages:
        payload, _auth = catalog._http_json(
            "POST",
            url,
            headers_iter=_headers(cfg, tokens, configured_country, configured_language, url, pcfg),
            params={
                "lang": language,
                "market": market,
                "page": page,
                "size": PAGE_SIZE,
                "q": "",
                "groupBy": "",
                "myUniverse": "false",
                "myOwnRecipe": "false",
                "withAutomaticSpellcheck": "true",
            },
            body=_search_body(language, market),
            timeout=30,
        )
        if not isinstance(payload, dict):
            raise RuntimeError(f"{language}/{market}: invalid search response")
        content = payload.get("content") if isinstance(payload.get("content"), list) else []
        for raw in content:
            if not isinstance(raw, dict):
                continue
            ident = raw.get("identifier") if isinstance(raw.get("identifier"), dict) else {}
            variant = _fid(ident) or _fid(raw.get("fid")) or _fid(raw.get("functionalId"))
            if not variant:
                continue
            cover_url = _text(catalog._search_cover(raw))
            rows.append(
                {
                    "variantId": variant,
                    "sourceSystem": _text(ident.get("sourceSystem")),
                    "version": _text(ident.get("version")),
                    "groupingFunctionalId": _fid(raw.get("groupingId")),
                    "title": _text(raw.get("title") or raw.get("shortTitle") or raw.get("normalizedTitle")),
                    "language": _text(raw.get("lang")).lower() or language.lower(),
                    "market": _text(raw.get("market")).upper() or market,
                    "cover": cover_url,
                    "servings": (catalog._yield(raw) or {}).get("quantity") or raw.get("groupSize"),
                }
            )
        page_info = payload.get("page") if isinstance(payload.get("page"), dict) else {}
        try:
            total_pages = int(page_info.get("totalPages"))
        except (TypeError, ValueError):
            total_pages = page + (1 if content else 0)
        page += 1
        if not content:
            break
    return rows


def _status_codes(exc: Exception) -> list[int]:
    return [int(value) for value in re.findall(r"HTTP(\d{3})", str(exc))]


def _fetch_detail_once(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    variant_id: str,
    source_language: str,
    configured_language: str,
    configured_country: str,
    appliance_group: bool,
) -> tuple[dict[str, Any] | None, list[int], str]:
    suffix = "?format=mobile&applianceGroup=" + APPLIANCE_GROUP if appliance_group else "?format=mobile"
    url = (
        cfg["platform_base_url"].rstrip("/")
        + "/common-api/v3/recipes/PRO/"
        + urllib.parse.quote(_fid(variant_id), safe="")
        + "/"
        + suffix
    )
    try:
        payload, auth = catalog._http_json(
            "GET",
            url,
            headers_iter=_headers(cfg, tokens, configured_country, configured_language, url, pcfg),
            timeout=30,
        )
    except Exception as exc:
        return None, _status_codes(exc), type(exc).__name__ + ": " + str(exc)
    root = catalog._recipe_root(payload)
    return _detail_payload(root, variant_id, source_language), [], auth


def _fetch_detail(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    variant_id: str,
    source_language: str,
    configured_language: str,
    configured_country: str,
) -> tuple[str, dict[str, Any]]:
    detail, codes, evidence = _fetch_detail_once(
        cfg,
        tokens,
        pcfg,
        variant_id=variant_id,
        source_language=source_language,
        configured_language=configured_language,
        configured_country=configured_country,
        appliance_group=False,
    )
    if detail is not None:
        return "detail", detail
    if codes and all(code == 404 for code in codes):
        detail2, codes2, evidence2 = _fetch_detail_once(
            cfg,
            tokens,
            pcfg,
            variant_id=variant_id,
            source_language=source_language,
            configured_language=configured_language,
            configured_country=configured_country,
            appliance_group=True,
        )
        if detail2 is not None:
            return "detail", detail2
        if codes2 and all(code == 404 for code in codes2):
            return "stale404", {
                "variantId": _fid(variant_id),
                "standardStatus": 404,
                "applianceGroupStatus": 404,
            }
        raise RuntimeError(f"{variant_id}: appliance-group retry failed: {evidence2}")
    raise RuntimeError(f"{variant_id}: detail fetch failed: {evidence}")


def _open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS catalog_runs (
            language TEXT NOT NULL,
            country TEXT NOT NULL,
            market TEXT NOT NULL,
            crawled_at TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            PRIMARY KEY(language, country)
        );
        CREATE TABLE IF NOT EXISTS catalog_variants (
            language TEXT NOT NULL,
            country TEXT NOT NULL,
            variant_id TEXT NOT NULL,
            search_json TEXT NOT NULL,
            PRIMARY KEY(language, country, variant_id)
        );
        CREATE INDEX IF NOT EXISTS idx_catalog_variants_variant ON catalog_variants(variant_id);
        CREATE TABLE IF NOT EXISTS variant_details (
            variant_id TEXT PRIMARY KEY,
            detail_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS stale_variants (
            variant_id TEXT PRIMARY KEY,
            evidence_json TEXT NOT NULL,
            verified_at TEXT NOT NULL
        );
        """
    )
    return conn


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dedupe_search_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Collapse repeated search occurrences by exact provider variant ID.

    SEB search pagination can return the same publication more than once within
    one language/market crawl. The SQLite identity is intentionally one row per
    exact variant. Preserve the first occurrence, let later duplicates fill only
    fields that were missing from it, and annotate the representative row with
    the number of extra occurrences so the provider anomaly remains auditable.
    """
    unique: dict[str, dict[str, Any]] = {}
    occurrences: dict[str, int] = {}
    order: list[str] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        variant_id = _text(raw.get("variantId"))
        if not variant_id:
            continue
        occurrences[variant_id] = occurrences.get(variant_id, 0) + 1
        if variant_id not in unique:
            unique[variant_id] = deepcopy(raw)
            order.append(variant_id)
            continue
        current = unique[variant_id]
        for key, value in raw.items():
            if current.get(key) in (None, "", {}, []) and value not in (None, "", {}, []):
                current[key] = deepcopy(value)

    duplicate_count = 0
    output: list[dict[str, Any]] = []
    for variant_id in order:
        row = unique[variant_id]
        extra = occurrences.get(variant_id, 1) - 1
        if extra > 0:
            row["duplicateSearchOccurrences"] = extra
            duplicate_count += extra
        output.append(row)
    return output, duplicate_count


def _replace_catalog(conn: sqlite3.Connection, language: str, country: str, rows: list[dict[str, Any]]) -> None:
    market = f"GS_{country}"
    unique_rows, duplicate_count = _dedupe_search_rows(rows)
    if duplicate_count:
        print(
            f"[search] {language}/{market} collapsed_duplicates={duplicate_count} "
            f"raw={len(rows)} unique={len(unique_rows)}",
            flush=True,
        )
    with conn:
        conn.execute("DELETE FROM catalog_variants WHERE language=? AND country=?", (language, country))
        conn.executemany(
            "INSERT INTO catalog_variants(language,country,variant_id,search_json) VALUES(?,?,?,?)",
            [
                (language, country, row["variantId"], json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                for row in unique_rows
            ],
        )
        conn.execute(
            "INSERT INTO catalog_runs(language,country,market,crawled_at,row_count) VALUES(?,?,?,?,?) "
            "ON CONFLICT(language,country) DO UPDATE SET market=excluded.market,crawled_at=excluded.crawled_at,row_count=excluded.row_count",
            (language, country, market, _iso_now(), len(unique_rows)),
        )


def _cached_state(conn: sqlite3.Connection, variant_id: str) -> str:
    if conn.execute("SELECT 1 FROM variant_details WHERE variant_id=?", (variant_id,)).fetchone():
        return "detail"
    if conn.execute("SELECT 1 FROM stale_variants WHERE variant_id=?", (variant_id,)).fetchone():
        return "stale404"
    return ""


def _store_result(conn: sqlite3.Connection, kind: str, variant_id: str, payload: dict[str, Any]) -> None:
    now = _iso_now()
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    with conn:
        if kind == "detail":
            conn.execute(
                "INSERT INTO variant_details(variant_id,detail_json,fetched_at) VALUES(?,?,?) "
                "ON CONFLICT(variant_id) DO UPDATE SET detail_json=excluded.detail_json,fetched_at=excluded.fetched_at",
                (variant_id, raw, now),
            )
            conn.execute("DELETE FROM stale_variants WHERE variant_id=?", (variant_id,))
        elif kind == "stale404":
            conn.execute(
                "INSERT INTO stale_variants(variant_id,evidence_json,verified_at) VALUES(?,?,?) "
                "ON CONFLICT(variant_id) DO UPDATE SET evidence_json=excluded.evidence_json,verified_at=excluded.verified_at",
                (variant_id, raw, now),
            )


def _export(conn: sqlite3.Connection, output: Path) -> dict[str, Any]:
    catalogs = []
    for language, country, market, crawled_at, row_count in conn.execute(
        "SELECT language,country,market,crawled_at,row_count FROM catalog_runs ORDER BY language,country"
    ):
        stale = conn.execute(
            "SELECT COUNT(*) FROM catalog_variants cv JOIN stale_variants sv ON sv.variant_id=cv.variant_id "
            "WHERE cv.language=? AND cv.country=?",
            (language, country),
        ).fetchone()[0]
        hydrated = conn.execute(
            "SELECT COUNT(*) FROM catalog_variants cv JOIN variant_details vd ON vd.variant_id=cv.variant_id "
            "WHERE cv.language=? AND cv.country=?",
            (language, country),
        ).fetchone()[0]
        catalogs.append(
            {
                "language": language,
                "country": country,
                "market": market,
                "state": "POPULATED" if row_count else "EMPTY",
                "searchRows": row_count,
                "hydratedVariants": hydrated,
                "staleSearchOnlyVariants": stale,
                "unresolvedVariants": max(0, row_count - hydrated - stale),
                "crawledAt": crawled_at,
            }
        )

    details = [json.loads(row[0]) for row in conn.execute("SELECT detail_json FROM variant_details ORDER BY variant_id")]
    stale = []
    for variant_id, evidence_json in conn.execute("SELECT variant_id,evidence_json FROM stale_variants ORDER BY variant_id"):
        search_rows = [
            json.loads(row[0])
            for row in conn.execute(
                "SELECT search_json FROM catalog_variants WHERE variant_id=? ORDER BY language,country",
                (variant_id,),
            )
        ]
        stale.append({"variantId": variant_id, "evidence": json.loads(evidence_json), "searchRows": search_rows})

    payload = {
        "schemaVersion": 2,
        "kind": "cook4me-provider-capture",
        "generatedAt": _iso_now(),
        "readOnly": True,
        "secretsPersisted": False,
        "source": {
            "contract": "standalone-proven-cookeo-brand-v5",
            "applianceGroup": APPLIANCE_GROUP,
            "recipeType": "BRAND",
            "auditedCatalogCount": len(AUDITED_CATALOGS),
            "catalogs": catalogs,
        },
        "details": details,
        "staleSearchOnly": stale,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    return payload


def crawl(args: argparse.Namespace) -> dict[str, Any]:
    cfg = c4m.read_apk_config(None)
    tokens = _tokens(Path(args.storage_home).expanduser())
    pcfg = catalog._platform_context(cfg, args.configured_country, args.configured_language, APP_VERSION)
    conn = _open_db(Path(args.cache_db).expanduser())
    try:
        catalogs = list(AUDITED_CATALOGS)
        if args.max_catalogs:
            catalogs = catalogs[: max(1, int(args.max_catalogs))]
        for language, country in catalogs:
            print(f"[search] {language}/GS_{country}", flush=True)
            rows = _search_catalog(
                cfg,
                tokens,
                pcfg,
                language=language,
                country=country,
                configured_language=args.configured_language,
                configured_country=args.configured_country,
            )
            if args.max_variants_per_catalog:
                rows = rows[: max(1, int(args.max_variants_per_catalog))]
            _replace_catalog(conn, language, country, rows)

        pending: dict[str, str] = {}
        for variant_id, language in conn.execute(
            "SELECT variant_id, MIN(language) FROM catalog_variants GROUP BY variant_id ORDER BY variant_id"
        ):
            if args.refresh_details or not _cached_state(conn, variant_id):
                pending[variant_id] = language

        print(f"[detail] pending={len(pending)} cached={conn.execute('SELECT COUNT(*) FROM variant_details').fetchone()[0]} stale={conn.execute('SELECT COUNT(*) FROM stale_variants').fetchone()[0]}", flush=True)
        failures: list[dict[str, str]] = []
        completed = 0
        workers = max(1, min(int(args.workers), 8))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _fetch_detail,
                    cfg,
                    tokens,
                    pcfg,
                    variant_id=variant_id,
                    source_language=language,
                    configured_language=args.configured_language,
                    configured_country=args.configured_country,
                ): variant_id
                for variant_id, language in pending.items()
            }
            for future in as_completed(futures):
                variant_id = futures[future]
                try:
                    kind, payload = future.result()
                except Exception as exc:
                    failures.append({"variantId": variant_id, "error": type(exc).__name__ + ": " + str(exc)})
                    if args.verbose:
                        print(f"  ! {variant_id}: {type(exc).__name__}", flush=True)
                    continue
                _store_result(conn, kind, variant_id, payload)
                completed += 1
                if completed % 250 == 0:
                    print(f"[detail] {completed}/{len(pending)}", flush=True)

        capture = _export(conn, Path(args.output).expanduser())
        unresolved = sum(int(row["unresolvedVariants"]) for row in capture["source"]["catalogs"])
        summary = {
            "auditedCatalogs": len(capture["source"]["catalogs"]),
            "populatedCatalogs": sum(row["state"] == "POPULATED" for row in capture["source"]["catalogs"]),
            "emptyCatalogs": sum(row["state"] == "EMPTY" for row in capture["source"]["catalogs"]),
            "searchRows": sum(int(row["searchRows"]) for row in capture["source"]["catalogs"]),
            "hydratedDetails": len(capture["details"]),
            "staleSearchOnly": len(capture["staleSearchOnly"]),
            "unresolved": unresolved,
            "fetchFailures": len(failures),
            "output": str(Path(args.output).expanduser()),
            "cacheDb": str(Path(args.cache_db).expanduser()),
        }
        if failures:
            Path(args.failures).expanduser().write_text(json.dumps(failures, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return summary
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-home", required=True)
    parser.add_argument("--cache-db", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--failures", required=True)
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--refresh-details", action="store_true")
    parser.add_argument("--max-catalogs", type=int, default=0)
    parser.add_argument("--max-variants-per-catalog", type=int, default=0)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    summary = crawl(args)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["fetchFailures"] == 0 and summary["unresolved"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
