"""Persistent recipe blacklist helpers.

Blacklist identity is deliberately based on stable recipe/family identifiers first,
with a normalized title fallback only for recipes that do not expose any stable ID.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
import unicodedata
from typing import Any

_MAX_BLACKLIST = 1000
_ID_FIELDS = (
    "displayFamilyId",
    "groupingFunctionalId",
    "groupingId",
    "recipeFunctionalId",
    "variantFunctionalId",
    "functionalId",
    "id",
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _title_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(ch for ch in text if not unicodedata.category(ch).startswith("M"))
    text = " ".join("".join(ch if ch.isalnum() else " " for ch in text).split())
    return f"title:{text}" if text else ""


def recipe_blacklist_keys(recipe: Any) -> tuple[str, ...]:
    """Return all stable identities carried by one recipe.

    Multiple keys are stored so a recipe remains blocked when the UI later sees a
    different language/variant representation of the same family.
    """
    if not isinstance(recipe, dict):
        return ()
    keys: list[str] = []
    seen: set[str] = set()
    for field in _ID_FIELDS:
        value = _text(recipe.get(field))
        if not value:
            continue
        key = f"{field}:{value}"
        if key not in seen:
            seen.add(key)
            keys.append(key)

    # Only rely on a title when the source gives us no stable recipe identity.
    if not keys:
        key = _title_key(recipe.get("title"))
        if key:
            keys.append(key)
    return tuple(keys)


def normalize_blacklist(value: Any) -> list[dict[str, Any]]:
    """Normalize stored blacklist entries and deduplicate overlapping identities."""
    rows = value if isinstance(value, list) else []
    result: list[dict[str, Any]] = []
    known: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        keys = [
            _text(key)
            for key in raw.get("keys") or []
            if _text(key)
        ]
        if not keys:
            keys = list(recipe_blacklist_keys(raw))
        keys = list(dict.fromkeys(keys))[:16]
        if not keys or known.intersection(keys):
            continue
        title = _text(raw.get("title"))[:300]
        item = {
            "identity": keys[0],
            "identities": keys,
            "keys": keys,
            "title": title or "Recipe",
            "language": _text(raw.get("language") or raw.get("selectedLanguage"))[:24],
            "source": _text(raw.get("source"))[:80],
            "image": _text(raw.get("image") or raw.get("imageUrl") or raw.get("cover"))[:1000],
            "blacklistedAt": _text(raw.get("blacklistedAt"))[:64],
        }
        result.append(item)
        known.update(keys)
        if len(result) >= _MAX_BLACKLIST:
            break
    return result


def blacklist_entry(recipe: dict[str, Any]) -> dict[str, Any]:
    keys = list(recipe_blacklist_keys(recipe))
    if not keys:
        raise ValueError("This recipe does not have a stable identity to blacklist")
    return {
        "identity": keys[0],
        "identities": keys,
        "keys": keys,
        "title": _text(recipe.get("title"))[:300] or "Recipe",
        "language": _text(recipe.get("selectedLanguage") or recipe.get("language"))[:24],
        "source": _text(recipe.get("source"))[:80],
        "image": _text(recipe.get("image") or recipe.get("imageUrl") or recipe.get("cover"))[:1000],
        "blacklistedAt": datetime.now(timezone.utc).isoformat(),
    }


def blacklist_matches(recipe: Any, blacklist: Any) -> bool:
    keys = set(recipe_blacklist_keys(recipe))
    if not keys:
        return False
    for row in normalize_blacklist(blacklist):
        if keys.intersection(row["keys"]):
            return True
    return False


def filter_blacklisted(rows: Any, blacklist: Any) -> list[dict[str, Any]]:
    return [
        row for row in rows if isinstance(row, dict)
        and not blacklist_matches(row, blacklist)
    ]


def add_blacklist(value: Any, recipe: dict[str, Any]) -> list[dict[str, Any]]:
    rows = normalize_blacklist(value)
    entry = blacklist_entry(recipe)
    entry_keys = set(entry["keys"])
    merged: list[dict[str, Any]] = []
    matched = False
    for row in rows:
        if entry_keys.intersection(row["keys"]):
            if not matched:
                combined = deepcopy(entry)
                combined["keys"] = list(dict.fromkeys([*row["keys"], *entry["keys"]]))[:16]
                # Keep the newest visible label/image while preserving the first timestamp.
                combined["blacklistedAt"] = row.get("blacklistedAt") or entry["blacklistedAt"]
                merged.append(combined)
                matched = True
            continue
        merged.append(row)
    if not matched:
        merged.append(entry)
    return normalize_blacklist(merged[-_MAX_BLACKLIST:])


def remove_blacklist(value: Any, keys: Any) -> list[dict[str, Any]]:
    wanted = {_text(key) for key in (keys if isinstance(keys, list) else []) if _text(key)}
    if not wanted:
        return normalize_blacklist(value)
    return [
        row for row in normalize_blacklist(value)
        if not wanted.intersection(row["keys"])
    ]
