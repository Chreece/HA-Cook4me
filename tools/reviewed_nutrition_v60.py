#!/usr/bin/env python3
"""Shared fail-closed provenance checks for reviewed Cook4Me v60 nutrition."""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

import nutrition_review_holds_v60 as holds


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
    """Return true only for explicitly reviewed, exact-identity nutrition.

    Structural ``per100g`` data alone is deliberately insufficient. Legacy v59
    fuzzy USDA search results also used that shape, so v60 accepts only either
    exact-FDC review provenance or a tightly-scoped reviewed official food-table
    record with an explicit stable source identifier and data type.
    """
    if holds.profile_hold(value, ingredient_id=ingredient_id) is not None:
        return False
    if not isinstance(value, dict):
        return False
    if value.get("basis") != "per100g" or not _numeric_values(value.get("values")):
        return False
    source = text(value.get("source")).casefold()
    if source == "usda_fdc":
        if _positive_int(value.get("sourceId")) is None:
            return False
    elif source in {"official_food_table", "authoritative_primary_composition"}:
        source_id = text(value.get("sourceId"))
        data_type = text(value.get("dataType"))
        if not source_id or ":" not in source_id or not data_type:
            return False
        if not text(value.get("nutritionReviewTargetId")):
            return False
        if text(value.get("nutritionReviewTargetKind")) not in {
            "provider-identity",
            "semantic-concept",
        }:
            return False
    else:
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
