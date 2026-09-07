#!/usr/bin/env python3
"""Evidence-safe normalization of nutrition fields returned by SEB recipe detail.

SEB's recipe model contains both explicitly per-100-g values and other numeric
fields whose basis is not established by our captures.  This module preserves
both, but only labels values as per-100-g when the source field says so.
"""
from __future__ import annotations

import math
from typing import Any


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _unit_metadata(value: Any) -> dict[str, str] | None:
    if isinstance(value, str):
        text = _text(value)
        return {"name": text} if text else None
    if not isinstance(value, dict):
        return None
    out: dict[str, str] = {}
    for source, target in (
        ("key", "key"),
        ("name", "name"),
        ("abbreviation", "abbreviation"),
        ("symbol", "symbol"),
    ):
        text = _text(value.get(source))
        if text:
            out[target] = text
    return out or None


def _flat_nutrients(value: Any) -> list[dict[str, Any]]:
    """Preserve SEB nutrient quantities without inventing their basis."""
    rows: list[tuple[str | None, Any]] = []
    if isinstance(value, dict):
        rows = [(str(key), raw) for key, raw in value.items()]
    elif isinstance(value, list):
        rows = [(None, raw) for raw in value]

    out: list[dict[str, Any]] = []
    for map_key, raw in rows:
        if not isinstance(raw, dict):
            continue
        key = _text(raw.get("key")) or _text(map_key)
        name = _text(raw.get("name"))
        quantity = _number(raw.get("quantity"))
        unit = _unit_metadata(raw.get("unit"))
        row: dict[str, Any] = {}
        if key:
            row["key"] = key
        if name:
            row["name"] = name
        if quantity is not None:
            row["quantity"] = quantity
            row["basis"] = "unspecified"
        if unit:
            row["unit"] = unit
        if row:
            out.append(row)
    return out


def _hierarchical_nutrients(value: Any) -> list[dict[str, Any]]:
    """Flatten only values explicitly exposed by SEB as valuePer100g."""
    if not isinstance(value, list):
        return []

    out: list[dict[str, Any]] = []

    def visit(raw: Any, path: list[str]) -> None:
        if not isinstance(raw, dict):
            return
        name = _text(raw.get("name"))
        next_path = [*path, name] if name else list(path)
        per100g = _number(raw.get("valuePer100g"))
        unit = _unit_metadata(raw.get("unit"))
        order = raw.get("order")
        if per100g is not None:
            row: dict[str, Any] = {
                "valuePer100g": per100g,
                "basisQuantity": 100,
                "basisUnit": "g",
            }
            if name:
                row["name"] = name
            if next_path:
                row["path"] = next_path
            if unit:
                row["unit"] = unit
            if isinstance(order, int):
                row["order"] = order
            out.append(row)
        children = raw.get("hierarchicalNutrients")
        if isinstance(children, list):
            for child in children:
                visit(child, next_path)

    for row in value:
        visit(row, [])
    return out


def _indicator(value: Any) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    out = {
        key: text
        for key in ("key", "name")
        if (text := _text(value.get(key)))
    }
    return out or None


def extract_official_nutrition(root: Any) -> dict[str, Any] | None:
    """Return SEB nutrition evidence without promoting ambiguous semantics.

    Proven semantics:
      * ``energyValue`` backs the app model's ``energyPer100gValue`` field.
      * ``hierarchicalNutrients[].valuePer100g`` is explicitly per 100 g.

    ``nutrients[].quantity`` is retained with ``basis=unspecified`` and must not
    be used for meal totals until its basis is independently established.
    """
    if not isinstance(root, dict):
        return None
    nutrition = root.get("nutrition")
    if not isinstance(nutrition, dict) or not nutrition:
        return None

    energy = _number(nutrition.get("energyValue"))
    hierarchical = _hierarchical_nutrients(nutrition.get("hierarchicalNutrients"))
    flat = _flat_nutrients(nutrition.get("nutrients"))
    score = nutrition.get("nutritionalScore")
    part_weight = _number(nutrition.get("partWeight"))
    ecological_score = _text(nutrition.get("ecologicalScore"))
    indicator = _indicator(nutrition.get("nutritionalIndicator"))

    out: dict[str, Any] = {
        "source": "seb_recipe",
        "confidence": "official_reference",
        "hasPer100gValues": bool(energy is not None or hierarchical),
        "hasNumericValues": bool(
            energy is not None
            or hierarchical
            or any("quantity" in row for row in flat)
        ),
    }
    if energy is not None:
        # The app model proves the basis but the captured model does not expose
        # the energy unit here, so keep the value unit-neutral.
        out["energyPer100gValue"] = energy
        out["energyBasisQuantity"] = 100
        out["energyBasisUnit"] = "g"
    if hierarchical:
        out["hierarchicalNutrients"] = hierarchical
    if flat:
        out["nutrients"] = flat
    if isinstance(score, int):
        out["nutritionalScore"] = score
    if part_weight is not None:
        out["partWeight"] = part_weight
    if ecological_score:
        out["ecologicalScore"] = ecological_score
    if indicator:
        out["nutritionalIndicator"] = indicator
    for key in (
        "areHPnnsPortionsManuallyModified",
        "areNutritionalIndicatorManuallyModified",
    ):
        if isinstance(nutrition.get(key), bool):
            out[key] = nutrition[key]

    meaningful = set(out) - {
        "source",
        "confidence",
        "hasPer100gValues",
        "hasNumericValues",
        "areHPnnsPortionsManuallyModified",
        "areNutritionalIndicatorManuallyModified",
    }
    return out if meaningful or flat else None
