from __future__ import annotations

import re
import unicodedata
from typing import Any


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    out: list[str] = []
    pending_space = False
    for char in text:
        if unicodedata.category(char).startswith("M"):
            continue
        if char.isalnum():
            if pending_space and out:
                out.append(" ")
            out.append(char)
            pending_space = False
        else:
            pending_space = True
    return "".join(out).strip()


def _explicit_id(item: dict[str, Any]) -> str:
    return _text(item.get("ingredientId") or item.get("id"))


def _provider_key(item: dict[str, Any]) -> str:
    return _text(item.get("key") or item.get("foodKey") or item.get("providerFoodKey"))


def _concept_id(item: dict[str, Any]) -> str:
    return _text(item.get("conceptId"))


def _name(item: dict[str, Any]) -> str:
    return normalize_name(
        item.get("canonicalName")
        or item.get("name")
        or item.get("foodName")
        or item.get("originalName")
    )


def identity_candidates(item: Any) -> tuple[str, ...]:
    """Return stable identity candidates from strongest semantics to legacy fallback.

    Identity namespaces are deliberately distinct:
    - ``c:`` reviewed semantic concept identity;
    - ``k:`` provider-backed food key;
    - ``l:`` reviewed/source-local keyless identity;
    - ``i:`` other explicit ingredient identity;
    - ``n:`` normalized legacy name fallback.

    A semantic concept is never converted into or treated as a provider key.
    Legacy candidates remain present so existing pantry/nutrition/cost records can
    continue to match while stores migrate to concept-first identities.
    """
    if not isinstance(item, dict):
        name = normalize_name(item)
        return (f"n:{name}",) if name else ()

    values: list[str] = []
    concept = _concept_id(item)
    if concept:
        values.append(f"c:{concept}")

    key = _provider_key(item)
    if key:
        values.append(f"k:{key}")

    ident = _explicit_id(item)
    if ident:
        if ident.startswith("local:"):
            values.append(f"l:{ident}")
        elif ident != key:
            values.append(f"i:{ident}")

    name = _name(item)
    if name:
        values.append(f"n:{name}")

    return tuple(dict.fromkeys(values))


def canonical_identity(item: Any) -> str:
    candidates = identity_candidates(item)
    return candidates[0] if candidates else ""


def legacy_identity(item: Any) -> str:
    """Return the old key/name identity for migration and compatibility checks."""
    if not isinstance(item, dict):
        name = normalize_name(item)
        return f"n:{name}" if name else ""
    key = _provider_key(item)
    if key:
        return f"k:{key}"
    name = _name(item)
    return f"n:{name}" if name else ""


def same_ingredient(left: Any, right: Any) -> bool:
    left_candidates = set(identity_candidates(left))
    if not left_candidates:
        return False
    return bool(left_candidates & set(identity_candidates(right)))


def preferred_storage_identity(item: Any) -> str:
    """Alias documenting the identity new inventory/nutrition/cost records should use."""
    return canonical_identity(item)
