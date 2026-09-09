#!/usr/bin/env python3
"""Capture SEB marketing-food dictionaries for release-catalog v2.

This read-only maintenance tool calls the APK-proven
``/common-api/datarefs/marketingFoods/search`` endpoint for every one of the 28
Cook4Me language/market mappings used by the release catalog. It exports only
provider food keys and localized labels; account tokens and request headers are
never persisted.
"""
from __future__ import annotations

import argparse
from collections import OrderedDict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
VENDOR = COMPONENT / "vendor"
for path in (COMPONENT, VENDOR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import cook4me_phonefree as c4m  # type: ignore  # noqa: E402
import cook4me_recipe_catalog as catalog  # type: ignore  # noqa: E402

APP_VERSION = "36.0.0-RC3"
SIZE = 5000

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


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(storage_home: Path) -> dict[str, Any]:
    path = storage_home / ".config" / "cook4me" / "tokens.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _localized_name(value: Any, language: str) -> str:
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, dict):
        return _text(value.get("value") or value.get("name") or value.get("label"))
    if not isinstance(value, list):
        return ""
    language = _text(language).lower().replace("_", "-").split("-", 1)[0]
    fallback = ""
    for row in value:
        if isinstance(row, str):
            fallback = fallback or _text(row)
            continue
        if not isinstance(row, dict):
            continue
        name = _text(row.get("value") or row.get("name") or row.get("label"))
        if not name:
            continue
        fallback = fallback or name
        row_language = _text(
            row.get("lang") or row.get("language") or row.get("languageKey")
        ).lower().replace("_", "-").split("-", 1)[0]
        if row_language == language:
            return name
    return fallback


def _candidates(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    values: list[Any] = []
    for key in ("content", "marketingFoods", "items", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            values.extend(value)
        elif isinstance(value, dict):
            nested = value.get("content") or value.get("items") or value.get("marketingFoods")
            if isinstance(nested, list):
                values.extend(nested)
    if not values and payload.get("key"):
        values = [payload]
    return [row for row in values if isinstance(row, dict)]


def _reported_total(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    candidates: list[Any] = [payload.get("totalElements"), payload.get("total")]
    page = payload.get("page")
    if isinstance(page, dict):
        candidates.extend((page.get("totalElements"), page.get("total")))
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend((data.get("totalElements"), data.get("total")))
        data_page = data.get("page")
        if isinstance(data_page, dict):
            candidates.extend((data_page.get("totalElements"), data_page.get("total")))
    for value in candidates:
        try:
            total = int(value)
        except (TypeError, ValueError):
            continue
        if total >= 0:
            return total
    return None


def normalize_marketing_foods(payload: Any, language: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normalize one localized provider dictionary without hiding duplicates."""
    candidates = _candidates(payload)
    by_key: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    missing_key = 0
    duplicate_rows = 0
    conflicting_labels = 0
    for raw in candidates:
        key = _text(raw.get("key") or raw.get("id") or raw.get("reference"))
        name = _localized_name(raw.get("name"), language)
        if not name:
            name = _text(raw.get("label") or raw.get("title"))
        if not name:
            continue
        if not key:
            missing_key += 1
            continue
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = {"key": key, "name": name}
            continue
        duplicate_rows += 1
        aliases = existing.setdefault("aliases", [])
        if name != existing["name"] and name not in aliases:
            aliases.append(name)
            conflicting_labels += 1

    rows = list(by_key.values())
    for row in rows:
        if row.get("aliases"):
            row["aliases"] = sorted(row["aliases"], key=lambda value: value.casefold())
    rows.sort(key=lambda row: row["key"])
    reported_total = _reported_total(payload)
    truncated = bool(reported_total is not None and reported_total > len(candidates))
    return rows, {
        "candidateRows": len(candidates),
        "reportedTotalElements": reported_total,
        "truncated": truncated,
        "uniqueKeys": len(rows),
        "missingKeyRows": missing_key,
        "duplicateRows": duplicate_rows,
        "conflictingLabels": conflicting_labels,
    }


def capture(args: argparse.Namespace) -> dict[str, Any]:
    cfg = c4m.read_apk_config(None)
    tokens = _tokens(Path(args.storage_home).expanduser())
    base = cfg["platform_base_url"].rstrip("/")
    url = base + "/common-api/datarefs/marketingFoods/search"

    catalogs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    mappings = list(AUDITED_CATALOGS)
    if args.max_catalogs:
        mappings = mappings[: max(1, int(args.max_catalogs))]

    for language, country in mappings:
        market = f"GS_{country}"
        print(f"[marketing-foods] {language}/{market}", flush=True)
        try:
            # Match the proven Home Assistant runtime path exactly: RCU and
            # request-header country follow the target catalog's market, while
            # the account/device language remains the configured language.
            pcfg = catalog._platform_context(
                cfg, country, args.configured_language, APP_VERSION
            )
            payload, auth_mode = catalog._http_json(
                "POST",
                url,
                headers_iter=catalog._request_headers(
                    cfg,
                    tokens,
                    country,
                    args.configured_language,
                    APP_VERSION,
                    url,
                    pcfg,
                ),
                params={"lang": language, "market": market, "size": SIZE},
                body={},
                timeout=30,
            )
            items, stats = normalize_marketing_foods(payload, language)
        except Exception as exc:
            errors.append(
                {
                    "language": language,
                    "country": country,
                    "error": type(exc).__name__ + ": " + str(exc),
                }
            )
            catalogs.append(
                {
                    "language": language,
                    "country": country,
                    "market": market,
                    "state": "ERROR",
                    "items": [],
                }
            )
            continue

        state = "POPULATED" if items else "EMPTY"
        if stats.get("truncated"):
            state = "TRUNCATED"
            errors.append(
                {
                    "language": language,
                    "country": country,
                    "error": (
                        "Provider reported more marketing-food rows than the "
                        f"APK-supported size={SIZE} response returned"
                    ),
                }
            )
        catalogs.append(
            {
                "language": language,
                "country": country,
                "market": market,
                "state": state,
                "authMode": auth_mode,
                **stats,
                "items": items,
            }
        )

    result = {
        "schemaVersion": 1,
        "kind": "cook4me-marketing-food-capture-v2",
        "generatedAt": _iso_now(),
        "readOnly": True,
        "secretsPersisted": False,
        "endpoint": "/common-api/datarefs/marketingFoods/search",
        "requestSize": SIZE,
        "auditedCatalogCount": len(AUDITED_CATALOGS),
        "capturedCatalogCount": len(catalogs),
        "errors": errors,
        "catalogs": catalogs,
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-home", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--configured-language", default="de")
    parser.add_argument("--configured-country", default="DE")
    parser.add_argument("--max-catalogs", type=int, default=0)
    args = parser.parse_args()
    result = capture(args)
    print(
        json.dumps(
            {
                "capturedCatalogs": len(result["catalogs"]),
                "populatedCatalogs": sum(row["state"] == "POPULATED" for row in result["catalogs"]),
                "emptyCatalogs": sum(row["state"] == "EMPTY" for row in result["catalogs"]),
                "truncatedCatalogs": sum(row["state"] == "TRUNCATED" for row in result["catalogs"]),
                "errors": len(result["errors"]),
                "uniqueLocalizedFoodRows": sum(len(row["items"]) for row in result["catalogs"]),
            },
            ensure_ascii=False,
        )
    )
    return 0 if not result["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
