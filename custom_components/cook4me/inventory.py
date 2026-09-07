from __future__ import annotations

from copy import deepcopy
from datetime import date
import math
import re
import unicodedata
from typing import Any

_MAX_ITEMS = 500
_UNSET = object()


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm_name(value: Any) -> str:
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


def inventory_identity(item: Any) -> str:
    if not isinstance(item, dict):
        name = _norm_name(item)
        return f"n:{name}" if name else ""
    key = _text(item.get("key") or item.get("foodKey"))
    if key:
        return f"k:{key}"
    name = _norm_name(item.get("name") or item.get("foodName"))
    return f"n:{name}" if name else ""


def _quantity(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < 0:
        return None
    return number


def _unit_token(value: Any) -> str:
    text = unicodedata.normalize("NFKC", _text(value).casefold())
    text = text.replace("ℓ", "l").replace("µ", "u").replace("μ", "u")
    return re.sub(r"[\s._-]+", "", text)


def _best_before(value: Any, *, strict: bool = False) -> str:
    text = _text(value)
    if not text:
        return ""
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        if strict:
            raise ValueError("Best-before date must use YYYY-MM-DD") from None
        return ""


def _merge_best_before(current: Any, incoming: Any) -> str:
    """Keep the earliest known date when multiple stock additions are merged."""
    left = _best_before(current)
    right = _best_before(incoming)
    if left and right:
        return min(left, right)
    return left or right


# Only language-neutral symbols are converted. Unknown/localized units are still
# supported when both sides use the exact same token; we never guess meanings.
_UNIT_SCALE: dict[str, tuple[str, float]] = {
    "mg": ("mass", 0.001),
    "g": ("mass", 1.0),
    "kg": ("mass", 1000.0),
    "ul": ("volume", 0.001),
    "ml": ("volume", 1.0),
    "cl": ("volume", 10.0),
    "dl": ("volume", 100.0),
    "l": ("volume", 1000.0),
    "pc": ("count", 1.0),
    "pcs": ("count", 1.0),
    "x": ("count", 1.0),
}


def convert_amount(value: Any, from_unit: Any, to_unit: Any) -> float | None:
    amount = _quantity(value)
    if amount is None:
        return None
    source = _unit_token(from_unit)
    target = _unit_token(to_unit)
    if source == target:
        return amount
    # Recipe count quantities frequently have no explicit unit. Treat an empty
    # unit as count only when the other side is an explicit count symbol.
    if not source and target in {"pc", "pcs", "x"}:
        source = "pcs"
    if not target and source in {"pc", "pcs", "x"}:
        target = "pcs"
    left = _UNIT_SCALE.get(source)
    right = _UNIT_SCALE.get(target)
    if not left or not right or left[0] != right[0]:
        return None
    return amount * left[1] / right[1]


def _normalized_row(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, str):
        name = _text(raw)
        return {"name": name} if name else None
    if not isinstance(raw, dict):
        return None
    key = _text(raw.get("key") or raw.get("foodKey"))
    name = _text(raw.get("name") or raw.get("foodName"))
    if not name:
        return None
    unlimited = bool(raw.get("unlimited"))
    quantity = None if unlimited else _quantity(raw.get("quantity"))
    unit = _text(raw.get("unit"))
    best_before = _best_before(raw.get("bestBefore") or raw.get("best_before"))
    row: dict[str, Any] = {"name": name}
    if key:
        row["key"] = key
    if unlimited:
        row["unlimited"] = True
    elif quantity is not None:
        row["quantity"] = quantity
    if unit:
        row["unit"] = unit
    if best_before:
        row["bestBefore"] = best_before
    return row


def normalize_inventory(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        value = [part.strip() for part in value.replace(",", "\n").splitlines()]
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    index: dict[str, int] = {}
    for raw in value:
        row = _normalized_row(raw)
        if not row:
            continue
        ident = inventory_identity(row)
        if not ident:
            continue
        if ident not in index:
            index[ident] = len(out)
            out.append(row)
        else:
            pos = index[ident]
            current = out[pos]
            # Preserve the first stable display name/key, but merge duplicate
            # finite stock when its unit can be converted safely.
            if row.get("unlimited"):
                current.pop("quantity", None)
                current["unlimited"] = True
                if row.get("unit") and not current.get("unit"):
                    current["unit"] = row["unit"]
            elif not current.get("unlimited") and row.get("quantity") is not None:
                if current.get("quantity") is None:
                    current["quantity"] = row["quantity"]
                    if row.get("unit"):
                        current["unit"] = row["unit"]
                else:
                    converted = convert_amount(
                        row["quantity"], row.get("unit", ""), current.get("unit", "")
                    )
                    if converted is not None:
                        current["quantity"] = float(current["quantity"]) + converted
            merged_date = _merge_best_before(current.get("bestBefore"), row.get("bestBefore"))
            if merged_date:
                current["bestBefore"] = merged_date
        if len(out) >= _MAX_ITEMS:
            break
    return out


def add_inventory_item(
    inventory: Any,
    ingredient: dict[str, Any],
    *,
    quantity: Any = None,
    unit: str = "",
    unlimited: bool = False,
    best_before: Any = "",
) -> list[dict[str, Any]]:
    rows = normalize_inventory(inventory)
    normalized_best_before = _best_before(
        best_before, strict=bool(_text(best_before))
    )
    addition = _normalized_row(
        {
            "key": ingredient.get("key") or ingredient.get("foodKey"),
            "name": ingredient.get("name") or ingredient.get("foodName"),
            "quantity": quantity,
            "unit": unit,
            "unlimited": unlimited,
            "bestBefore": normalized_best_before,
        }
    )
    if not addition:
        raise ValueError("Ingredient name is required")
    ident = inventory_identity(addition)
    for current in rows:
        if inventory_identity(current) != ident:
            continue
        if normalized_best_before:
            current["bestBefore"] = _merge_best_before(
                current.get("bestBefore"), normalized_best_before
            )
        if unlimited:
            current.pop("quantity", None)
            current["unlimited"] = True
            if unit:
                current["unit"] = _text(unit)
            return rows
        amount = _quantity(quantity)
        if amount is None:
            return rows
        if current.get("unlimited"):
            return rows
        if current.get("quantity") is None:
            current["quantity"] = amount
            if unit:
                current["unit"] = _text(unit)
            return rows
        converted = convert_amount(amount, unit, current.get("unit", ""))
        if converted is None:
            raise ValueError(
                f"Cannot add {unit or 'unitless'} stock to existing {current.get('unit') or 'unitless'} stock; use the same or a convertible unit"
            )
        current["quantity"] = float(current["quantity"]) + converted
        return rows
    rows.append(addition)
    return rows[:_MAX_ITEMS]


def update_inventory_item(
    inventory: Any,
    identity: str,
    *,
    quantity: Any = None,
    unit: str = "",
    unlimited: bool = False,
    best_before: Any = _UNSET,
) -> list[dict[str, Any]]:
    rows = normalize_inventory(inventory)
    for current in rows:
        if inventory_identity(current) != identity:
            continue
        current["unit"] = _text(unit) if unit else ""
        if not current["unit"]:
            current.pop("unit", None)
        if unlimited:
            current.pop("quantity", None)
            current["unlimited"] = True
        else:
            current.pop("unlimited", None)
            amount = _quantity(quantity)
            if amount is None:
                current.pop("quantity", None)
            else:
                current["quantity"] = amount
        if best_before is not _UNSET:
            if _text(best_before):
                current["bestBefore"] = _best_before(best_before, strict=True)
            else:
                current.pop("bestBefore", None)
        return rows
    raise ValueError("House ingredient was not found")


def remove_inventory_item(inventory: Any, identity: str) -> list[dict[str, Any]]:
    return [row for row in normalize_inventory(inventory) if inventory_identity(row) != identity]


def _recipe_amount(item: dict[str, Any]) -> tuple[float | None, str]:
    amount = _quantity(item.get("quantity"))
    unit = _text(item.get("unit"))
    if amount is not None:
        return amount, unit
    weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
    return _quantity(weight.get("quantity")), _text(weight.get("unit"))


def _find_stock(inventory: list[dict[str, Any]], ingredient: dict[str, Any]) -> dict[str, Any] | None:
    key = _text(ingredient.get("foodKey") or ingredient.get("key"))
    if key:
        wanted = f"k:{key}"
        for row in inventory:
            if inventory_identity(row) == wanted:
                return row
    name = _norm_name(ingredient.get("foodName") or ingredient.get("name"))
    if name:
        wanted = f"n:{name}"
        for row in inventory:
            if inventory_identity(row) == wanted:
                return row
    return None


def recipe_consumption_items(recipe: dict[str, Any], inventory: Any) -> list[dict[str, Any]]:
    stock = normalize_inventory(inventory)
    out: list[dict[str, Any]] = []
    by_identity: dict[str, int] = {}
    for ingredient in recipe.get("ingredients") or []:
        if not isinstance(ingredient, dict):
            continue
        current = _find_stock(stock, ingredient)
        if not current:
            continue
        ident = inventory_identity(current)
        amount, unit = _recipe_amount(ingredient)
        name = _text(ingredient.get("foodName") or ingredient.get("name") or current.get("name"))
        row = {
            "identity": ident,
            **({"key": current["key"]} if current.get("key") else {}),
            "name": name or current["name"],
            "quantity": amount,
            "unit": unit,
            "consume": True,
            "stockQuantity": current.get("quantity"),
            "stockUnit": current.get("unit", ""),
            "stockUnlimited": bool(current.get("unlimited")),
            "stockBestBefore": current.get("bestBefore", ""),
        }
        if ident not in by_identity:
            by_identity[ident] = len(out)
            out.append(row)
            continue
        existing = out[by_identity[ident]]
        if amount is None:
            continue
        if existing.get("quantity") is None:
            existing["quantity"] = amount
            existing["unit"] = unit
            continue
        converted = convert_amount(amount, unit, existing.get("unit", ""))
        if converted is not None:
            existing["quantity"] = float(existing["quantity"]) + converted
    return out


def apply_consumption(
    inventory: Any, consumptions: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    rows = normalize_inventory(inventory)
    report: dict[str, list[dict[str, Any]]] = {"deducted": [], "skipped": [], "depleted": []}
    for request in consumptions:
        if not isinstance(request, dict) or not bool(request.get("consume", True)):
            continue
        ident = _text(request.get("identity")) or inventory_identity(request)
        current = next((row for row in rows if inventory_identity(row) == ident), None)
        if not current:
            report["skipped"].append({"identity": ident, "reason": "not_in_inventory"})
            continue
        if current.get("unlimited"):
            report["skipped"].append({"identity": ident, "reason": "unlimited"})
            continue
        stock_quantity = _quantity(current.get("quantity"))
        amount = _quantity(request.get("quantity"))
        if stock_quantity is None or amount is None:
            report["skipped"].append({"identity": ident, "reason": "amount_unknown"})
            continue
        converted = convert_amount(amount, request.get("unit", ""), current.get("unit", ""))
        if converted is None:
            report["skipped"].append({"identity": ident, "reason": "unit_mismatch"})
            continue
        remaining = stock_quantity - converted
        report["deducted"].append(
            {
                "identity": ident,
                "name": current.get("name"),
                "quantity": converted,
                "unit": current.get("unit", ""),
            }
        )
        if remaining <= 1e-9:
            rows.remove(current)
            report["depleted"].append({"identity": ident, "name": current.get("name")})
        else:
            current["quantity"] = round(remaining, 9)
    return rows, report


def format_stock(row: dict[str, Any]) -> str:
    if row.get("unlimited"):
        return "∞"
    amount = _quantity(row.get("quantity"))
    if amount is None:
        return "?"
    shown = str(int(amount)) if float(amount).is_integer() else f"{amount:g}"
    unit = _text(row.get("unit"))
    return f"{shown} {unit}".strip()
