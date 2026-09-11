#!/usr/bin/env python3
"""Shared fail-closed provenance checks for reviewed Cook4Me v60 nutrition."""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Any


def text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", text(value)).casefold()


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _numeric_values(value: Any) -> bool:
    if not isinstance(value, dict) or not value:
        return False
    for number in value.values():
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            return False
        if not math.isfinite(float(number)):
            return False
    return True


def is_reviewed_profile(
    value: Any,
    *,
    ingredient_id: Any = "",
    canonical_name: Any = "",
) -> bool:
    """Return true only for exact-ID nutrition produced by the reviewed resolver.

    Structural ``per100g`` data alone is deliberately insufficient. Legacy v59
    fuzzy USDA search results also used that shape, so v60 requires explicit
    exact-FDC review provenance before a profile may satisfy release nutrition.
    """
    if not isinstance(value, dict):
        return False
    if value.get("basis") != "per100g" or not _numeric_values(value.get("values")):
        return False
    if text(value.get("source")).casefold() != "usda_fdc":
        return False
    if _positive_int(value.get("sourceId")) is None:
        return False
    if not text(value.get("reviewFile")):
        return False
    reviewed_name = text(value.get("reviewedCanonicalEnglishName"))
    if not reviewed_name:
        return False

    wanted_id = text(ingredient_id)
    if wanted_id and text(value.get("ingredientId")) != wanted_id:
        return False
    wanted_name = text(canonical_name)
    if wanted_name and norm(reviewed_name) != norm(wanted_name):
        return False
    return True
