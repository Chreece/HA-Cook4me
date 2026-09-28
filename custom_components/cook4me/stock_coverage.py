"""Read-only recipe/stock identity normalization, independent of display language.

The index is prepared alongside the release catalog in HA's executor. No file
reads, translated-name matching, package-size guessing or persistent stock writes
are performed by a coverage request.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any
import unicodedata

from .inventory import inventory_identity
from .price_identity import pricing_name
from .price_units import price_ingredient

_STOCK_CATALOG: dict[str, tuple[str, tuple[str, ...]]] = {}
# v249 stored a grouped picker choice as only its representative key/name.
# Keep a read-only compatibility index keyed by exactly that persisted pair so
# existing assignments regain the source IDs the picker originally represented.
_LEGACY_ASSIGNMENT_ALIASES: dict[tuple[str, str], tuple[str, ...]] = {}


def _name_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join(
        "".join(char for char in text if not unicodedata.combining(char)).split()
    )


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

    # Compatibility for assignments created by v249-v254.  The picker choice
    # validated one exact source ID, but resolve_ingredient_links then persisted
    # only the display representative key/name. Rebuild the picker group from
    # immutable catalog data without rewriting the user's inventory.
    from .catalog_presentation import ingredient_choices
    assignment_aliases: dict[tuple[str, str], set[str]] = defaultdict(set)
    for language in ("en", "de", "el"):
        for choice in ingredient_choices(payload, language):
            # websocket_v33._catalog promotes ingredientId/id to "key" before
            # the assignment is persisted; mirror that exact stored identity.
            choice_key = _key(choice)
            primary = f"k:{choice_key}" if choice_key else inventory_identity(choice)
            label = _name_key(choice.get("name"))
            source_ids = {
                f"k:{str(value).strip()}"
                for value in choice.get("sourceIngredientIds") or []
                if str(value).strip()
            }
            if primary and label and len(source_ids) > 1:
                assignment_aliases[(primary, label)].update(source_ids)

    global _STOCK_CATALOG, _LEGACY_ASSIGNMENT_ALIASES
    _STOCK_CATALOG = index
    _LEGACY_ASSIGNMENT_ALIASES = {
        key: tuple(sorted(values)) for key, values in assignment_aliases.items()
    }
    return len(index)


def coverage_identities(
    raw: dict[str, Any], *, legacy_assignment: bool = False
) -> set[str]:
    """Return reviewed stock identities without using display-name equivalence."""
    key = _key(raw)
    _canonical, catalog_identities = _STOCK_CATALOG.get(key, ("", ()))
    identities = {
        str(value)
        for value in raw.get("identities", [])
        if isinstance(value, str) and value
    }
    identities.update(catalog_identities)
    identities.update(
        f"k:{str(value).strip()}"
        for value in raw.get("sourceIngredientIds") or []
        if str(value).strip()
    )
    direct = inventory_identity(raw)
    if direct:
        identities.add(direct)
        if legacy_assignment:
            label = _name_key(raw.get("name") or raw.get("foodName"))
            identities.update(
                _LEGACY_ASSIGNMENT_ALIASES.get((direct, label), ())
            )
    return identities


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
    canonical, _identities = _STOCK_CATALOG.get(key, ("", ()))
    if canonical:
        item["canonicalName"] = canonical
    item["identities"] = sorted(coverage_identities(item))
    # Explicit SI unit IDs / reviewed localized symbols only. No inference of
    # grams per bunch, slice or package. Ingredient-specific portions are handled
    # by food_intelligence after stock has been identified.
    return price_ingredient(item)


def _coverage_link(raw: Any) -> Any:
    if not isinstance(raw, dict):
        return deepcopy(raw)
    link = deepcopy(raw)
    link["identities"] = sorted(coverage_identities(link, legacy_assignment=True))
    return link


def coverage_stock(stock: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize stored measurement labels and reviewed aliases in a copy."""
    result = deepcopy(stock)
    for row in result:
        unit = price_ingredient({"quantity": 1, "unit": row.get("unit", "")})["unit"]
        row["unit"] = unit
        row["identities"] = sorted(
            coverage_identities(row, legacy_assignment=True)
        )
        if row.get("ingredientLinks"):
            row["ingredientLinks"] = [
                _coverage_link(link) for link in row["ingredientLinks"]
            ]
        for lot in row.get("lots") or []:
            if lot.get("ingredientLinks"):
                lot["ingredientLinks"] = [
                    _coverage_link(link) for link in lot["ingredientLinks"]
                ]
    return result
