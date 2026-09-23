"""Read-only recipe/stock identity normalization, independent of display language.

The index is prepared alongside the release catalog in HA's executor. No file
reads, translated-name matching, package-size guessing or persistent stock writes
are performed by a coverage request.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .inventory import inventory_identity
from .price_identity import pricing_name
from .price_units import price_ingredient

_STOCK_CATALOG: dict[str, tuple[str, tuple[str, ...]]] = {}


def _key(row: dict[str, Any]) -> str:
    return str(row.get("key") or row.get("foodKey") or row.get("ingredientId") or row.get("id") or "").strip()


def warm_stock_catalog(payload: dict[str, Any] | None = None) -> int:
    """Build immutable lookup evidence off the event loop; publish atomically.

    Exact canonical English food names link provider IDs to their locale-specific
    counterparts. Reviewed preparation aliases come from the existing explicit
    pricing-name table; no substring, translated-label or display-group matching.
    Ambiguous/unconfirmed records never gain inferred links.
    """
    if payload is None:
        from .release_catalog import load_release_catalog
        payload = load_release_catalog()
    sources = [row for row in payload.get("ingredients", []) if isinstance(row, dict)]
    groups: dict[str, set[str]] = defaultdict(set)
    records = []
    for row in sources:
        keys = tuple(dict.fromkeys(str(row.get(field) or "").strip() for field in ("key", "foodKey", "ingredientId", "id") if row.get(field)))
        if not keys:
            continue
        canonical = str(row.get("canonicalName") or row.get("name") or "").strip()
        safe = row.get("classification", "food") == "food" and not row.get("needsSemanticConfirmation", False)
        # pricing_name contains explicit disambiguations (e.g. pepper), rather
        # than collapsing all provider records with the same ambiguous label.
        exact_name = pricing_name({**row, "canonicalName": canonical}) if canonical and safe else ""
        tags = []
        if exact_name:
            tags.append("name:" + " ".join(exact_name.casefold().split()))
        concept = str(row.get("conceptId") or "")
        if safe and concept.startswith("concept:food:"):
            tags.append(concept)
        ids = {"k:" + key for key in keys}
        for tag in tags:
            groups[tag].update(ids)
        records.append((keys, canonical, ids, tags))
    index = {}
    for keys, canonical, ids, tags in records:
        related = set(ids)
        for tag in tags:
            related.update(groups[tag])
        value = (canonical, tuple(sorted(related)))
        for key in keys:
            index[key] = value
    global _STOCK_CATALOG
    _STOCK_CATALOG = index
    return len(index)


def coverage_ingredient(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a calculation copy, preserving the caller's displayed wording."""
    item = dict(raw)
    key = _key(item)
    if key:
        item["key"] = key
        if item.get("foodKey"):
            item["foodKey"] = key
    if not item.get("name") and not item.get("foodName"):
        item["name"] = key
    canonical, identities = _STOCK_CATALOG.get(key, ("", ()))
    if canonical:
        item["canonicalName"] = canonical
    explicit = {str(value) for value in item.get("identities", []) if isinstance(value, str) and value}
    direct = inventory_identity(item)
    item["identities"] = sorted(explicit | set(identities) | ({direct} if direct else set()))
    # Explicit SI unit IDs / reviewed localized symbols only. No inference of
    # grams per bunch, slice or package. Ingredient-specific portions are handled
    # by food_intelligence after stock has been identified.
    return price_ingredient(item)


def coverage_stock(stock: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize stored measurement labels in a copy, never the saved inventory."""
    result = [dict(row) for row in stock]
    for row in result:
        unit = price_ingredient({"quantity": 1, "unit": row.get("unit", "")})["unit"]
        row["unit"] = unit
    return result
