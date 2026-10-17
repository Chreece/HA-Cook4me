#!/usr/bin/env python3
"""Read-only, bounded SEB recipe-program audit using HA-Cook4me's proven APIs.

Execute INSIDE the Home Assistant container. No device commands, inventory writes,
credential prints, guessed endpoints, or changes to existing recipe caches.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
from typing import Any

DEFAULT_MARKETS = "DE:de,FR:fr,ES:es,IT:it,PL:pl,CZ:cs,PT:pt,NL:nl,GB:en,TR:tr"
MAX_TOTAL_ACTIONS = 180
LANG_RE = re.compile(r"^[a-z]{2,3}$")
COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
GROUP = "APPLIANCE_GROUP_15"


def display(value: Any, maximum: int = 160) -> str:
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        return ""
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(value)).strip()[:maximum]


def token_doc(config_dir: Path) -> tuple[dict, str, str, str]:
    """Read the token file associated with exactly one active Cook4Me entry.

    Never prints the config entry, device UUID, account or tokens.
    """
    store = config_dir / ".storage" / "core.config_entries"
    if not store.is_file() or store.is_symlink():
        return {}, "DE", "de", "36.0.0-RC3"
    document = json.loads(store.read_text(encoding="utf-8"))
    entries = [e for e in document.get("data", {}).get("entries", [])
               if isinstance(e, dict) and e.get("domain") == "cook4me"
               and not e.get("disabled_by")]
    if len(entries) != 1:
        return {}, "DE", "de", "36.0.0-RC3"
    entry = entries[0]
    cfg = entry.get("data") if isinstance(entry.get("data"), dict) else {}
    country = display(cfg.get("country"), 2).upper() or "DE"
    language = display(cfg.get("language"), 5).lower().split("-")[0] or "de"
    version = display(cfg.get("app_version"), 40) or "36.0.0-RC3"
    ident = str(entry.get("entry_id") or "")
    if not ident or not re.fullmatch(r"[a-zA-Z0-9_-]{6,128}", ident):
        return {}, country, language, version
    key_file = config_dir / ".storage" / "cook4me" / ident / ".config" / "cook4me" / "tokens.json"
    try:
        st = key_file.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_size > 1024 * 1024:
            return {}, country, language, version
        tokens = json.loads(key_file.read_text(encoding="utf-8"))
        if isinstance(tokens, dict):
            return tokens, country, language, version
    except (OSError, ValueError):
        pass
    return {}, country, language, version


def program_rows(detail: dict, *, expected_group: str = GROUP) -> list[tuple[str, str]]:
    """Use normalized SEB step programs; exclude unrelated appliance groups."""
    result = []
    seen = set()
    if not isinstance(detail, dict):
        return result
    for step in detail.get("steps") or []:
        if not isinstance(step, dict):
            continue
        for program in step.get("programs") or []:
            if not isinstance(program, dict):
                continue
            group = program.get("applianceGroup")
            group = group.get("key") if isinstance(group, dict) else group
            if group and display(group) != expected_group:
                continue
            key, name = display(program.get("programKey"), 80), display(program.get("programName"))
            if not key and not name:
                continue
            identity = key + "\0" + name
            if identity in seen:
                continue
            seen.add(identity)
            result.append((key, name))
    return result


def parse_markets(raw: str) -> list[tuple[str, str]]:
    out = []
    for part in raw.split(","):
        if not part.strip():
            continue
        bits = part.strip().split(":")
        if len(bits) != 2:
            raise ValueError("Market format must be COUNTRY:language")
        country, language = bits[0].upper(), bits[1].lower()
        if not COUNTRY_RE.fullmatch(country) or not LANG_RE.fullmatch(language):
            raise ValueError("Invalid COUNTRY:language market pair")
        if (country, language) not in out:
            out.append((country, language))
    if not out or len(out) > 16:
        raise ValueError("Specify between one and 16 markets")
    return out


def parse_page_indices(raw: str) -> list[int]:
    """Explicit, bounded search page sampling; never guess any backend facet."""
    result = []
    for field in str(raw).split(","):
        if not field or not field.strip().isdigit():
            raise ValueError("Page indices must be a comma-separated list of nonnegative integers")
        number = int(field)
        if number > 500:
            raise ValueError("Page index exceeds safe audit bound")
        if number not in result:
            result.append(number)
    if not 1 <= len(result) <= 5:
        raise ValueError("Select 1 to 5 SEB search pages")
    return result


def digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()[:12]


def audited_report() -> dict:
    return {
        "schema": 1,
        "origin": "Groupe SEB /common-api/v4/search/recipes plus /common-api/v3/recipes/PRO/{variantId}/?format=mobile",
        "captureTimeUtc": datetime.now(timezone.utc).isoformat(),
        "scope": "Cook4Me APPLIANCE_GROUP_15; bounded multi-market sample, not all SEB appliances or all recipes",
        "requests": {"configurationContexts": 0, "recipeSearches": 0, "recipeDetails": 0,
                     "successfulSearches": 0, "successfulDetails": 0},
        "marketResults": [],
        "programs": [],
        "warnings": [],
        "completeSeBCatalog": False,
        "sensitiveDataIncluded": False,
    }


def collect_names(rows: list[tuple[str, str]], *, country: str, language: str,
                  inventory: dict[tuple[str, str], dict]) -> None:
    for key, name in rows:
        identity = (key, name)
        if identity not in inventory:
            inventory[identity] = {"programKey": key or None, "programName": name or None,
                                   "observations": 0, "markets": set(), "languages": set()}
        entry = inventory[identity]
        entry["observations"] += 1
        entry["markets"].add(country)
        entry["languages"].add(language)


def offline_self_test() -> None:
    assert parse_markets("DE:de,FR:fr,DE:de") == [("DE", "de"), ("FR", "fr")]
    assert parse_page_indices("0,3,12,3") == [0,3,12]
    fixture = {
        "steps": [
            {"programs": [
                {"programKey": "PROGRAM_200156", "programName": "Cuisson haute pression",
                 "applianceGroup": "APPLIANCE_GROUP_15"},
                {"programKey": "PROGRAM_200161", "programName": "Maintien au chaud"},
                {"programKey": "PROGRAM_5", "programName": "Other oven", "applianceGroup": "APPLIANCE_GROUP_1"},
            ]},
            {"programs": [
                {"programKey": "PROGRAM_200156", "programName": "Cuisson haute pression"},
                {"programKey": "PROGRAM_200159", "programName": "Dorage"},
            ]}
        ]
    }
    got = program_rows(fixture)
    assert len(got) == 3, got
    assert ("PROGRAM_200156", "Cuisson haute pression") in got
    assert ("PROGRAM_200159", "Dorage") in got
    assert all(key != "PROGRAM_5" for key, _ in got)
    d = {}
    collect_names(got, country="FR", language="fr", inventory=d)
    assert len(d) == 3
    assert all(item["observations"] == 1 for item in d.values())
    assert display("ABC\nDEF") == "ABC DEF"
    print("SEB_OFFLINE_SELF_TEST=PASS")


def audit(arguments) -> dict:
    path = Path(arguments.root).resolve()
    vendor = path / "custom_components" / "cook4me" / "vendor"
    if not vendor.is_dir():
        raise RuntimeError("Cook4Me vendor library not found in Home Assistant config")
    sys.path.insert(0, str(vendor))
    import cook4me_phonefree as phone
    import cook4me_recipe_catalog as catalog
    import cook4me_recipe_search_proven as proven

    if phone.curl_requests is None:
        raise RuntimeError("curl-cffi is not installed inside Home Assistant")
    cfg = phone.read_apk_config()
    if not cfg.get("platform_base_url", "").startswith("https://"):
        raise RuntimeError("SEB endpoint is not HTTPS")
    tokens, device_country, device_lang, app_version = token_doc(path)
    markets = parse_markets(arguments.markets)
    pages = parse_page_indices(arguments.page_indices)
    report = audited_report()
    report["parameters"] = {
        "markets": [country+":"+lang for country, lang in markets],
        "pages": pages,
        "maxActions": arguments.max_actions,
        "detailsPerMarket": arguments.details_per_market,
        "pageSize": arguments.page_size,
        "delaySeconds": arguments.delay,
        "accountTokenAvailable": bool(tokens.get("access_token") or tokens.get("id_token")),
    }
    inventory: dict[tuple[str, str], dict] = {}
    requests = report["requests"]
    clock_start = time.monotonic()
    action_count = 0

    def allowed() -> bool:
        return action_count < arguments.max_actions and (
            time.monotonic() - clock_start < arguments.max_seconds)

    def throttle() -> None:
        if arguments.delay:
            time.sleep(arguments.delay)

    for country, language in markets:
        if not allowed():
            report["warnings"].append("BOUNDED_AUDIT_STOPPED")
            break
        info = {"market": country, "language": language, "recipeVariantsDiscovered": 0,
                "detailsLoaded": 0, "programPairsObserved": 0, "result": "unavailable"}
        report["marketResults"].append(info)
        try:
            action_count += 1
            requests["configurationContexts"] += 1
            # Reuses the official config and url-connexion paths with save=False.
            pcfg = catalog._platform_context(
                cfg, country, language, app_version)
            throttle()
        except Exception as exc:
            info["reason"] = "SEB_PLATFORM_CONFIG_" + type(exc).__name__
            continue
        seen_variants: set[str] = set()
        info["pagesScanned"] = []
        for page in pages:
            if not allowed():
                if "BOUNDED_AUDIT_STOPPED" not in report["warnings"]:
                    report["warnings"].append("BOUNDED_AUDIT_STOPPED")
                break
            info["pagesScanned"].append(page)
            search_url = cfg["platform_base_url"].rstrip("/") + "/common-api/v4/search/recipes"
            body = proven.search_body(language, f"GS_{country}")
            params = {
                "lang": language, "market": f"GS_{country}", "page": page,
                "size": arguments.page_size, "q": "",
                "groupBy": "", "myUniverse": "false", "myOwnRecipe": "false",
                "withAutomaticSpellcheck": "true",
            }
            try:
                action_count += 1
                requests["recipeSearches"] += 1
                data, _auth_mode = catalog._http_json(
                    "POST", search_url,
                    headers_iter=catalog._request_headers(
                        cfg, tokens, country, language, app_version, search_url, pcfg),
                    params=params, body=body, timeout=25,
                )
                requests["successfulSearches"] += 1
                throttle()
            except Exception as exc:
                info["reason"] = "SEB_SEARCH_" + type(exc).__name__
                continue

            variants = []
            for row in data.get("content", []) if isinstance(data, dict) else []:
                if isinstance(row, dict):
                    lightweight = catalog._light_search_row(row)
                    variant = lightweight.get("searchVariantId") if isinstance(lightweight, dict) else None
                    if variant and variant not in seen_variants:
                        variants.append(variant)
                        seen_variants.add(variant)
            info["recipeVariantsDiscovered"] += len(variants)
            info["result"] = "search_ok"
            for variant in variants[:arguments.details_per_market]:
                if not allowed():
                    report["warnings"].append("BOUNDED_AUDIT_STOPPED")
                    break
                try:
                    action_count += 1
                    requests["recipeDetails"] += 1
                    detail = catalog.recipe_detail(
                        cfg, tokens, variant, country=country, language=language,
                        configured_language=language, app_version=app_version, pcfg=pcfg)
                    requests["successfulDetails"] += 1
                    info["detailsLoaded"] += 1
                    pairs = program_rows(detail)
                    info["programPairsObserved"] += len(pairs)
                    collect_names(pairs, country=country, language=language, inventory=inventory)
                    throttle()
                except Exception as exc:
                    reason = "SEB_DETAIL_" + type(exc).__name__
                    if reason not in report["warnings"]:
                        report["warnings"].append(reason)
        if info["detailsLoaded"]:
            info["result"] = "details_ok"
    report["programs"] = sorted(
        [
            {"programKey": value["programKey"], "programName": value["programName"],
             "observations": value["observations"],
             "markets": sorted(value["markets"]), "languages": sorted(value["languages"])}
            for value in inventory.values()
        ],
        key=lambda item: (item["programKey"] or "", item["programName"] or ""),
    )
    report["uniqueProgramPairs"] = len(report["programs"])
    report["uniqueKeys"] = sorted({item["programKey"] for item in report["programs"]
                                   if item["programKey"]})
    report["counts"] = {
        "requestsBudgeted": action_count,
        "marketsWithDetails": sum(item["detailsLoaded"] > 0 for item in report["marketResults"]),
        "programKeys": len(report["uniqueKeys"]),
        "programNames": len({item["programName"] for item in report["programs"] if item["programName"]}),
    }
    if not report["programs"]:
        report["warnings"].append("NO_PROGRAM_EVIDENCE: cannot claim coverage")
    if report["counts"]["marketsWithDetails"] < len(markets):
        report["warnings"].append("INCOMPLETE_MARKET_COVERAGE")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Read-only official SEB cooking-program name audit")
    p.add_argument("--root", default="/config")
    p.add_argument("--markets", default=DEFAULT_MARKETS)
    p.add_argument("--page-indices", default="0", help="Page numbers, e.g. 0,3,12")
    p.add_argument("--page-size", type=int, default=12)
    p.add_argument("--details-per-market", type=int, default=4)
    p.add_argument("--max-actions", type=int, default=52)
    p.add_argument("--max-seconds", type=int, default=240)
    p.add_argument("--delay", type=float, default=0.6)
    p.add_argument("--offline-self-test", action="store_true")
    args = p.parse_args()
    if args.offline_self_test:
        offline_self_test()
        return
    if not 1 <= args.page_size <= 30 or not 1 <= args.details_per_market <= 12:
        p.error("page-size or details-per-market outside safe audit limits")
    if not 1 <= args.max_actions <= MAX_TOTAL_ACTIONS or not 15 <= args.max_seconds <= 900:
        p.error("request/time cap outside safe bounds")
    if args.delay < 0.25 or args.delay > 6:
        p.error("delay must be between 0.25 and 6 seconds")
    try:
        result = audit(args)
    except Exception as exc:
        # Never echo raw exception text, which could contain API diagnostics.
        print(json.dumps({"status": "AUDIT_FAILED", "errorClass": type(exc).__name__,
                          "completeSeBCatalog": False}))
        raise SystemExit(3) from None
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    # Code 2 signals partial evidence, not a failed run.
    if result["warnings"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
