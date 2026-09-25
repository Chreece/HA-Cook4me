"""Offline seasonal availability and conditional after-opening guidance.

Reviewed canonical-name and provider-ID allowlists are used while loading the
release catalog. Runtime callers resolve an exact ingredient ID through release_catalog;
translated labels, fuzzy matches and display groups never provide evidence.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any

_PATH = Path(__file__).with_name("catalog") / "ingredient_lifecycle.v1.json"
_UNKNOWN = {"seasonality": {"status": "unknown"}, "afterOpening": {"status": "unknown"}}


def _name(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _integer(value: Any, maximum: int) -> bool:
    return type(value) is int and 1 <= value <= maximum


def _gtin(value: Any) -> str:
    """Canonical GTIN for a verified product code; malformed input is unknown."""
    if not isinstance(value, str):
        return ""
    code = value.strip()
    if len(code) not in (8, 12, 13, 14) or not code.isascii() or not code.isdecimal() or not int(code):
        return ""
    total = sum(int(digit) * (3 if i % 2 == 0 else 1) for i, digit in enumerate(code[-2::-1]))
    return code.zfill(14) if (-total) % 10 == int(code[-1]) else ""


def validate_lifecycle_data(data: Any) -> None:
    """Reject malformed bundled evidence rather than guessing dates or months."""
    if not isinstance(data, dict) or data.get("schemaVersion") != 1 or data.get("kind") != "cook4me-ingredient-lifecycle":
        raise ValueError("Invalid ingredient lifecycle schema")
    sources, profiles, names = (data.get(key) for key in ("sources", "profiles", "canonicalNames"))
    if not all(isinstance(value, dict) and value for value in (sources, profiles, names)):
        raise ValueError("Lifecycle sources, profiles and names are required")
    for source in sources.values():
        if not isinstance(source, dict) or not str(source.get("url", "")).startswith("https://") or not source.get("publisher"):
            raise ValueError("Invalid lifecycle source")
        _date(source.get("reviewedOn"))

    def evidence(row):
        ids = row.get("sourceIds")
        if not isinstance(ids, list) or not ids or any(ident not in sources for ident in ids):
            raise ValueError("Unknown or missing lifecycle evidence")

    for profile in profiles.values():
        season, opening = profile.get("seasonality", {}), profile.get("afterOpening", {})
        if season.get("status") not in {"reviewed", "unknown", "not_applicable"}:
            raise ValueError("Invalid seasonality state")
        if season.get("status") == "reviewed" and not season.get("regions"):
            raise ValueError("Reviewed seasons need a region")
        seen = set()
        for region in season.get("regions", []):
            country = region.get("country")
            if not isinstance(country, str) or len(country) != 2 or not country.isalpha() or country != country.upper() or country in seen:
                raise ValueError("Invalid or duplicate season country")
            seen.add(country)
            months = region.get("months")
            if not isinstance(months, list) or not months or any(not _integer(m, 12) for m in months) or months != sorted(set(months)):
                raise ValueError("Invalid season months")
            if region.get("basis") not in {"seasonal_calendar_including_stored_produce", "regional_seasonal_availability", "outdoor_harvest"}:
                raise ValueError("Invalid season basis")
            evidence(region)
        if opening.get("status") not in {"reviewed", "conditional", "label_required", "unknown", "not_applicable"}:
            raise ValueError("Invalid after-opening state")
        if opening.get("status") in {"reviewed", "conditional"} and not opening.get("rules"):
            raise ValueError("Reviewed opening guidance needs a rule")
        if "sourceIds" in opening:
            evidence(opening)
        rule_ids = set()
        for rule in opening.get("rules", []):
            if not rule.get("id") or rule["id"] in rule_ids:
                raise ValueError("Invalid or duplicate opening rule")
            rule_ids.add(rule["id"])
            if not _integer(rule.get("daysMin"), 3650) or not _integer(rule.get("daysMax"), 3650) or rule["daysMin"] > rule["daysMax"]:
                raise ValueError("Invalid opening-day range")
            temperature = rule.get("maxTemperatureC")
            if rule.get("storage") != "fridge" or type(temperature) not in (int, float) or not math.isfinite(temperature) or not 0 < temperature <= 7:
                raise ValueError("Invalid opening storage conditions")
            minimum_temperature = rule.get("minTemperatureC", 0)
            if type(minimum_temperature) not in (int, float) or not math.isfinite(minimum_temperature) or not 0 <= minimum_temperature <= temperature:
                raise ValueError("Invalid opening minimum temperature")
            if not isinstance(rule.get("conditions"), list) or any(not isinstance(c, str) or not c for c in rule["conditions"]):
                raise ValueError("Invalid opening conditions")
            if "productBarcodes" in rule:
                codes = rule["productBarcodes"]
                if not isinstance(codes, list) or not codes or any(not _gtin(code) for code in codes):
                    raise ValueError("Invalid opening product barcode")
                if len({_gtin(code) for code in codes}) != len(codes):
                    raise ValueError("Duplicate opening product barcode")
                if not isinstance(rule.get("brand"), str) or not rule["brand"].strip():
                    raise ValueError("Product-specific guidance needs a brand")
            evidence(rule)
    if any(not key or key != _name(key) or profile_id not in profiles for key, profile_id in names.items()):
        raise ValueError("Invalid lifecycle identity mapping")
    identities = data.get("ingredientIds", {})
    if not isinstance(identities, dict) or any(
        not isinstance(key, str) or not key.strip() or key != key.strip() or profile_id not in profiles
        for key, profile_id in identities.items()
    ):
        raise ValueError("Invalid exact ingredient lifecycle mapping")


@lru_cache(maxsize=1)
def load_lifecycle_data() -> dict[str, Any]:
    # Called by the release-catalog warmup in HA's executor, never per scan.
    data = json.loads(_PATH.read_text(encoding="utf-8"))
    validate_lifecycle_data(data)
    return data


def enrich_catalog_ingredients(payload: dict[str, Any]) -> None:
    data = load_lifecycle_data()
    coverage = {"seasonality": 0, "afterOpening": 0, "labelRequired": 0}
    for ingredient in payload.get("ingredients", []):
        if not isinstance(ingredient, dict) or ingredient.get("needsSemanticConfirmation"):
            continue
        # Reviewed provider IDs distinguish homonyms (vegetable Pepper versus
        # the spice) and cover official rows without a classification field.
        profile_id = data.get("ingredientIds", {}).get(str(ingredient.get("id") or ""))
        classification = ingredient.get("classification")
        if classification not in (None, "food") or (classification != "food" and not profile_id):
            continue
        profile_id = profile_id or data["canonicalNames"].get(_name(ingredient.get("canonicalName")))
        if not profile_id:
            continue
        profile = deepcopy(data["profiles"][profile_id])
        profile.update(schemaVersion=1, version=data["version"], profileId=profile_id)
        ingredient["lifecycle"] = profile
        coverage["seasonality"] += profile["seasonality"]["status"] == "reviewed"
        coverage["afterOpening"] += bool(profile["afterOpening"].get("rules"))
        coverage["labelRequired"] += profile["afterOpening"]["status"] == "label_required"
    payload["_runtimeLifecycleSummary"] = {"version": data["version"], "countryCodes": sorted({r["country"] for p in data["profiles"].values() for r in p["seasonality"].get("regions", [])}), "coverage": coverage, "complete": False}


def lifecycle_profile(ingredient: Any, *, include_sources: bool = True) -> dict[str, Any]:
    """Read a materialized catalog ingredient, returning an independent value."""
    profile = deepcopy(ingredient.get("lifecycle") or _UNKNOWN) if isinstance(ingredient, dict) else deepcopy(_UNKNOWN)
    if include_sources and profile.get("profileId"):
        ids = set(profile.get("afterOpening", {}).get("sourceIds", []))
        for row in profile.get("seasonality", {}).get("regions", []) + profile.get("afterOpening", {}).get("rules", []):
            ids.update(row.get("sourceIds", []))
        profile["sources"] = {key: deepcopy(load_lifecycle_data()["sources"][key]) for key in sorted(ids)}
    return profile


def seasonal_availability(profile: dict[str, Any], *, country: str, month: int) -> dict[str, Any]:
    if not _integer(month, 12):
        raise ValueError("Month must be an integer between 1 and 12")
    season = profile.get("seasonality", {})
    if season.get("status") == "not_applicable":
        return {"status": "not_applicable"}
    country = str(country or "").strip().upper()
    region = next((r for r in season.get("regions", []) if r["country"] == country), None)
    if region is None:
        return {"status": "unknown", "reason": "country_not_reviewed", "country": country}
    # The source lists monthly highlights, not a complete harvest census. An
    # omitted month is unknown, never a ban on buying/using an ingredient.
    status = "year_round" if len(region["months"]) == 12 else "in_season" if month in region["months"] else "unknown"
    return {**deepcopy(region), "month": month, "status": status}


def _date(value: Any) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("Date must use YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError("Date must use YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise ValueError("Date must use YYYY-MM-DD")
    return parsed


def opening_window(profile: dict[str, Any], lot: dict[str, Any], *, temperature_c: float | None = None, confirmed_conditions: tuple[str, ...] = ()) -> dict[str, Any]:
    """Calculate an advisory window without modifying stock or its printed date.

    A saved lot interval is package-specific and takes precedence. Catalog
    ranges require matching storage, temperature, brand and food-form evidence.
    reminders use the shorter end; the window begins immediately on opening.
    """
    if not lot.get("openedAt"):
        return {"status": "unopened"}
    opened = _date(lot["openedAt"])
    printed = _date(lot["bestBefore"]) if lot.get("bestBefore") and not lot.get("noExpiry") else None
    explicit = lot.get("useWithinDays")
    if explicit not in (None, ""):
        # Inventory accepts numeric input strings; never truncate a fraction.
        if isinstance(explicit, str) and explicit.isascii() and explicit.isdecimal():
            explicit = int(explicit)
        if not _integer(explicit, 3650):
            raise ValueError("Use-within days must be an integer between 1 and 3650")
        minimum = maximum = explicit
        evidence = {"kind": "package_value"}
    else:
        opening = profile.get("afterOpening", {})
        rules = opening.get("rules", [])
        barcode = _gtin(lot.get("barcode"))
        # A reviewed product/brand must satisfy its own identity and handling
        # gates. Missing evidence must not select a longer generic interval.
        product_rules = [
            rule for rule in rules if rule.get("productBarcodes") and (
                _name(rule["brand"]) == _name(lot.get("brand"))
                or barcode in {_gtin(code) for code in rule["productBarcodes"]}
            )
        ]
        brand_rules = [
            rule for rule in rules if rule.get("brand")
            and _name(rule["brand"]) == _name(lot.get("brand"))
        ]
        candidates = []
        for rule in product_rules or brand_rules or rules:
            if rule.get("brand") and _name(rule["brand"]) != _name(lot.get("brand")):
                continue
            if "productBarcodes" in rule and barcode not in {_gtin(code) for code in rule["productBarcodes"]}:
                continue
            if lot.get("storage") != rule["storage"]:
                continue
            if type(temperature_c) not in (int, float) or not math.isfinite(temperature_c) or not rule.get("minTemperatureC", 0) <= temperature_c <= rule["maxTemperatureC"]:
                continue
            if not set(rule["conditions"]).issubset(confirmed_conditions):
                continue
            candidates.append(rule)
        if not candidates:
            return {"status": "label_required" if opening.get("rules") else opening.get("status", "unknown"), "openedAt": opened.isoformat(), "reason": "no_applicable_opening_rule"}
        rule = min(candidates, key=lambda r: (r["daysMin"], r["daysMax"], r["id"]))
        minimum, maximum = rule["daysMin"], rule["daysMax"]
        evidence = {"kind": rule["kind"], "ruleId": rule["id"], "sourceIds": deepcopy(rule["sourceIds"])}
    try:
        target, latest = opened + timedelta(days=minimum), opened + timedelta(days=maximum)
    except OverflowError:
        raise ValueError("Opening window exceeds supported calendar range") from None
    if printed:
        target, latest = min(target, printed), min(latest, printed)
    return {"status": "guidance", "openedAt": opened.isoformat(), "consumeFrom": opened.isoformat(), "remindOn": target.isoformat(), "consumeBy": latest.isoformat(), "printedDateBeforeOpening": bool(printed and printed < opened), "daysMin": minimum, "daysMax": maximum, "labelOverrides": True, "safetyGuarantee": False, **evidence}
