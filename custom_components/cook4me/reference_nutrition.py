from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any

from .reference_catalog import bundled_reference_catalog


def _text(value: Any) -> str:
    return str(value or "").strip()


@lru_cache(maxsize=1)
def bundled_generic_nutrition() -> dict[str, dict[str, Any]]:
    """Return nutrition-store-compatible immutable reference rows by food key."""
    catalog = bundled_reference_catalog()
    out: dict[str, dict[str, Any]] = {}
    for identity, row in catalog.ingredients_by_id.items():
        if not isinstance(row, dict) or row.get("nutritionConflict"):
            continue
        nutrition = row.get("nutrition")
        if not isinstance(nutrition, dict):
            continue
        out[f"k:{identity}"] = {
            "ingredient": {
                "key": identity,
                "name": _text(row.get("canonicalName") or identity),
            },
            "nutrition": deepcopy(nutrition),
            "query": _text(row.get("canonicalName")),
            "confidence": row.get("nutritionMatchConfidence"),
            "source": "bundled_reference_catalog",
        }
    return out


def merged_generic_nutrition(local: Any) -> dict[str, Any]:
    """Overlay local nutrition on top of release reference nutrition.

    Local data always wins, including exact/manual mappings. The immutable
    release catalog never overwrites user-specific or newer local evidence.
    """
    result = deepcopy(bundled_generic_nutrition())
    if isinstance(local, dict):
        for identity, row in local.items():
            result[str(identity)] = deepcopy(row)
    return result


def clear_reference_nutrition_cache() -> None:
    bundled_generic_nutrition.cache_clear()
