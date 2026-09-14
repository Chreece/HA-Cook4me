#!/usr/bin/env python3
"""Capture SEB marketing-food dictionaries using the exact APK request contract.

The RC3 APK constructs ``th0.d(language, market, false)`` for the unfiltered
marketing-food dataset.  That serializes to field filters for ``market.key``
and ``name.lang``, requests ``key/name/mixMedias``, no facets, and an ascending
``name`` sort.  The Retrofit call uses ``size=100000``.

This maintenance capture is read-only. Provider/account credentials and request
headers are never persisted in the result bundle.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
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

_V2_PATH = ROOT / "tools" / "capture_marketing_food_catalogs_v2.py"
_spec = importlib.util.spec_from_file_location("capture_marketing_food_catalogs_v2_shared", _V2_PATH)
assert _spec and _spec.loader
_v2 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _v2
_spec.loader.exec_module(_v2)

APP_VERSION = "36.0.0-RC3"
SIZE = 100000
AUDITED_CATALOGS = _v2.AUDITED_CATALOGS
normalize_marketing_foods = _v2.normalize_marketing_foods


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokens(storage_home: Path) -> dict[str, Any]:
    path = storage_home / ".config" / "cook4me" / "tokens.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def marketing_food_search_body(language: str, market: str) -> dict[str, Any]:
    """Serialize APK ``th0.d(language, market, false)`` exactly in semantics."""
    return {
        "fieldFilters": [
            {"field": "market.key", "values": [market]},
            {"field": "name.lang", "values": [language]},
        ],
        "fieldList": ["key", "name", "mixMedias"],
        "facetList": [],
        "sort": {"name": "name", "direction": "ASC"},
    }


def capture(args: argparse.Namespace) -> dict[str, Any]:
    cfg = c4m.read_apk_config(None)
    tokens = _tokens(Path(args.storage_home).expanduser())
    url = cfg["platform_base_url"].rstrip("/") + "/common-api/datarefs/marketingFoods/search"

    catalogs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    mappings = list(AUDITED_CATALOGS)
    if args.max_catalogs:
        mappings = mappings[: max(1, int(args.max_catalogs))]

    for language, country in mappings:
        market = f"GS_{country}"
        print(f"[marketing-foods] {language}/{market}", flush=True)
        try:
            pcfg = catalog._platform_context(cfg, country, args.configured_language, APP_VERSION)
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
                body=marketing_food_search_body(language, market),
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
                        f"APK request size={SIZE} response returned"
                    ),
                }
            )
        elif stats.get("unparsedRows") or stats.get("missingNameRows"):
            state = "PARTIAL"
            errors.append(
                {
                    "language": language,
                    "country": country,
                    "error": (
                        f"Could not normalize {stats.get('unparsedRows', 0)} structurally unparsed "
                        f"and {stats.get('missingNameRows', 0)} unnamed marketing-food rows"
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
        "schemaVersion": 3,
        "kind": "cook4me-marketing-food-capture-v3",
        "generatedAt": _iso_now(),
        "readOnly": True,
        "secretsPersisted": False,
        "endpoint": "/common-api/datarefs/marketingFoods/search",
        "requestContract": "apk-th0.d-unfiltered",
        "requestSize": SIZE,
        "isMixMainFilter": False,
        "auditedCatalogCount": len(AUDITED_CATALOGS),
        "capturedCatalogCount": len(catalogs),
        "errors": errors,
        "catalogs": catalogs,
    }
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
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
                "partialCatalogs": sum(row["state"] == "PARTIAL" for row in result["catalogs"]),
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
