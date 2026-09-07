from __future__ import annotations

from copy import deepcopy
from datetime import date
import math
import re
import unicodedata
from typing import Any

_MAX_ITEMS = 500
_UNSET = object()
DEFAULT_EXPIRY_WARNING_DAYS = 3


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


def _lot_sort_key(lot: dict[str, Any]) -> tuple[bool, str]:
    stamp = _best_before(lot.get("bestBefore"))
    # Dated stock is consumed before undated stock; dated lots use FEFO.
    return (not bool(stamp), stamp or "9999-12-31")


def _normalize_lot(
    raw: Any,
    *,
    target_unit: str = "",
    source_unit: str = "",
    strict: bool = False,
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        if strict:
            raise ValueError("Inventory batch must be an object")
        return None
    amount = _quantity(raw.get("quantity"))
    if amount is None or amount <= 0:
        if strict:
            raise ValueError("Inventory batch amount must be greater than zero")
        return None
    lot_unit = _text(raw.get("unit") or source_unit)
    if target_unit and lot_unit and _unit_token(target_unit) != _unit_token(lot_unit):
        converted = convert_amount(amount, lot_unit, target_unit)
        if converted is None:
            if strict:
                raise ValueError(
                    f"Cannot convert inventory batch from {lot_unit} to {target_unit}"
                )
            return None
        amount = converted
    elif target_unit and not lot_unit:
        # Canonical stored lots omit their unit and inherit the ingredient unit.
        lot_unit = target_unit
    stamp = _best_before(raw.get("bestBefore") or raw.get("best_before"), strict=strict)
    lot: dict[str, Any] = {"quantity": amount}
    if stamp:
        lot["bestBefore"] = stamp
    return lot


def _refresh_row_totals(row: dict[str, Any]) -> dict[str, Any]:
    """Keep legacy total/next-expiry fields derived from canonical finite lots."""
    if row.get("unlimited"):
        row.pop("quantity", None)
        row.pop("lots", None)
        stamp = _best_before(row.get("bestBefore"))
        if stamp:
            row["bestBefore"] = stamp
        else:
            row.pop("bestBefore", None)
        return row

    unit = _text(row.get("unit"))
    raw_lots = row.get("lots") if isinstance(row.get("lots"), list) else None
    lots: list[dict[str, Any]] = []
    if raw_lots is not None:
        for raw in raw_lots:
            lot = _normalize_lot(raw, target_unit=unit)
            if lot:
                lots.append(lot)
    else:
        # Seamless migration from the v20 single quantity + bestBefore model.
        amount = _quantity(row.get("quantity"))
        if amount is not None and amount > 0:
            lot: dict[str, Any] = {"quantity": amount}
            stamp = _best_before(row.get("bestBefore"))
            if stamp:
                lot["bestBefore"] = stamp
            lots.append(lot)

    if lots:
        lots.sort(key=_lot_sort_key)
        row["lots"] = lots
        row["quantity"] = round(sum(float(lot["quantity"]) for lot in lots), 9)
        dated = [str(lot["bestBefore"]) for lot in lots if lot.get("bestBefore")]
        if dated:
            row["bestBefore"] = min(dated)
        else:
            row.pop("bestBefore", None)
    else:
        row.pop("lots", None)
        row.pop("quantity", None)
        # A legacy/unknown-amount ingredient may still carry a date. Preserve it
        # for compatibility, although all new finite dated additions require an amount.
        stamp = _best_before(row.get("bestBefore"))
        if stamp:
            row["bestBefore"] = stamp
        else:
            row.pop("bestBefore", None)
    return row


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
    row: dict[str, Any] = {"name": name}
    if key:
        row["key"] = key
    unit = _text(raw.get("unit"))
    if unit:
        row["unit"] = unit
    if bool(raw.get("unlimited")):
        row["unlimited"] = True
        stamp = _best_before(raw.get("bestBefore") or raw.get("best_before"))
        if stamp:
            row["bestBefore"] = stamp
        return _refresh_row_totals(row)

    if isinstance(raw.get("lots"), list):
        row["lots"] = deepcopy(raw["lots"])
    else:
        amount = _quantity(raw.get("quantity"))
        if amount is not None:
            row["quantity"] = amount
        stamp = _best_before(raw.get("bestBefore") or raw.get("best_before"))
        if stamp:
            row["bestBefore"] = stamp
    return _refresh_row_totals(row)


def _append_lot_converted(
    current: dict[str, Any],
    lot: dict[str, Any],
    *,
    from_unit: str,
    strict: bool,
) -> bool:
    target_unit = _text(current.get("unit"))
    source_unit = _text(from_unit)
    amount = _quantity(lot.get("quantity"))
    if amount is None or amount <= 0:
        return False
    if target_unit or source_unit:
        converted = convert_amount(amount, source_unit, target_unit)
        if converted is None:
            if strict:
                raise ValueError(
                    f"Cannot add {source_unit or 'unitless'} stock to existing "
                    f"{target_unit or 'unitless'} stock; use the same or a convertible unit"
                )
            return False
        amount = converted
    normalized: dict[str, Any] = {"quantity": amount}
    stamp = _best_before(lot.get("bestBefore"))
    if stamp:
        normalized["bestBefore"] = stamp
    current.setdefault("lots", []).append(normalized)
    return True


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
            current = out[index[ident]]
            if row.get("unlimited"):
                # Preserve previous behavior: unlimited wins over finite stock.
                previous_date = _best_before(current.get("bestBefore"))
                incoming_date = _best_before(row.get("bestBefore"))
                current.pop("quantity", None)
                current.pop("lots", None)
                current["unlimited"] = True
                if row.get("unit") and not current.get("unit"):
                    current["unit"] = row["unit"]
                dates = [x for x in (previous_date, incoming_date) if x]
                if dates:
                    current["bestBefore"] = min(dates)
                _refresh_row_totals(current)
            elif not current.get("unlimited"):
                if not current.get("unit") and row.get("unit") and not current.get("quantity"):
                    current["unit"] = row["unit"]
                row_lots = row.get("lots") or []
                if row_lots:
                    for lot in row_lots:
                        _append_lot_converted(
                            current,
                            lot,
                            from_unit=str(row.get("unit") or ""),
                            strict=False,
                        )
                    _refresh_row_totals(current)
                elif not current.get("quantity") and row.get("bestBefore"):
                    current["bestBefore"] = row["bestBefore"]
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
    normalized_best_before = _best_before(best_before, strict=bool(_text(best_before)))
    name = _text(ingredient.get("name") or ingredient.get("foodName"))
    key = _text(ingredient.get("key") or ingredient.get("foodKey"))
    if not name:
        raise ValueError("Ingredient name is required")
    amount = _quantity(quantity)
    if not unlimited and normalized_best_before and amount is None:
        raise ValueError("A finite best-before date must be attached to an amount")

    incoming: dict[str, Any] = {"name": name}
    if key:
        incoming["key"] = key
    incoming_unit = _text(unit)
    if incoming_unit:
        incoming["unit"] = incoming_unit
    if unlimited:
        incoming["unlimited"] = True
        if normalized_best_before:
            incoming["bestBefore"] = normalized_best_before
    elif amount is not None and amount > 0:
        lot: dict[str, Any] = {"quantity": amount}
        if normalized_best_before:
            lot["bestBefore"] = normalized_best_before
        incoming["lots"] = [lot]
    elif amount == 0:
        raise ValueError("Inventory amount must be greater than zero")

    ident = inventory_identity(incoming)
    for current in rows:
        if inventory_identity(current) != ident:
            continue
        if unlimited:
            previous_date = _best_before(current.get("bestBefore"))
            current.pop("quantity", None)
            current.pop("lots", None)
            current["unlimited"] = True
            if incoming_unit:
                current["unit"] = incoming_unit
            dates = [x for x in (previous_date, normalized_best_before) if x]
            if dates:
                current["bestBefore"] = min(dates)
            return _refresh_row_totals(current) and rows
        if current.get("unlimited"):
            return rows
        if amount is None:
            return rows
        if not current.get("unit") and incoming_unit and not current.get("quantity"):
            current["unit"] = incoming_unit
        lot = {"quantity": amount}
        if normalized_best_before:
            lot["bestBefore"] = normalized_best_before
        _append_lot_converted(
            current,
            lot,
            from_unit=incoming_unit,
            strict=True,
        )
        _refresh_row_totals(current)
        return rows

    rows.append(_refresh_row_totals(incoming))
    return rows[:_MAX_ITEMS]


def update_inventory_item(
    inventory: Any,
    identity: str,
    *,
    quantity: Any = None,
    unit: str = "",
    unlimited: bool = False,
    best_before: Any = _UNSET,
    lots: Any = _UNSET,
) -> list[dict[str, Any]]:
    rows = normalize_inventory(inventory)
    for current in rows:
        if inventory_identity(current) != identity:
            continue
        new_unit = _text(unit)
        if new_unit:
            current["unit"] = new_unit
        else:
            current.pop("unit", None)

        if unlimited:
            current.pop("quantity", None)
            current.pop("lots", None)
            current["unlimited"] = True
            if best_before is not _UNSET:
                if _text(best_before):
                    current["bestBefore"] = _best_before(best_before, strict=True)
                else:
                    current.pop("bestBefore", None)
            return _refresh_row_totals(current) and rows

        current.pop("unlimited", None)
        if lots is not _UNSET:
            if lots is None:
                lots = []
            if not isinstance(lots, list):
                raise ValueError("Inventory batches must be a list")
            normalized_lots: list[dict[str, Any]] = []
            for raw_lot in lots:
                lot = _normalize_lot(raw_lot, target_unit=new_unit, strict=True)
                if lot:
                    normalized_lots.append(lot)
            if normalized_lots:
                current["lots"] = normalized_lots
            else:
                current.pop("lots", None)
            current.pop("quantity", None)
            current.pop("bestBefore", None)
            _refresh_row_totals(current)
            return rows

        # Compatibility for older clients: aggregate edits intentionally become
        # one finite batch because they cannot represent multiple dates.
        amount = _quantity(quantity)
        if amount is not None and amount > 0:
            lot: dict[str, Any] = {"quantity": amount}
            stamp = ""
            if best_before is not _UNSET:
                stamp = _best_before(best_before, strict=bool(_text(best_before)))
            else:
                stamp = _best_before(current.get("bestBefore"))
            if stamp:
                lot["bestBefore"] = stamp
            current["lots"] = [lot]
        elif amount == 0:
            current.pop("lots", None)
            current.pop("quantity", None)
            current.pop("bestBefore", None)
        else:
            current.pop("lots", None)
            current.pop("quantity", None)
            if best_before is not _UNSET:
                if _text(best_before):
                    raise ValueError("A finite best-before date must be attached to an amount")
                current.pop("bestBefore", None)
        return _refresh_row_totals(current) and rows
    raise ValueError("House ingredient was not found")


def remove_inventory_item(inventory: Any, identity: str) -> list[dict[str, Any]]:
    return [row for row in normalize_inventory(inventory) if inventory_identity(row) != identity]


def expiring_inventory_items(
    inventory: Any,
    *,
    today: date | None = None,
    within_days: int = DEFAULT_EXPIRY_WARNING_DAYS,
    include_past: bool = True,
) -> list[dict[str, Any]]:
    """Return individual dated batches that are past or enter the warning window."""
    reference = today or date.today()
    horizon = max(0, int(within_days))
    out: list[dict[str, Any]] = []
    for row in normalize_inventory(inventory):
        base = {
            "name": row.get("name"),
            **({"key": row["key"]} if row.get("key") else {}),
            **({"unit": row["unit"]} if row.get("unit") else {}),
            "identity": inventory_identity(row),
        }
        if row.get("unlimited") or not row.get("lots"):
            candidates = [
                {
                    **base,
                    **({"unlimited": True} if row.get("unlimited") else {}),
                    **({"quantity": row["quantity"]} if row.get("quantity") is not None else {}),
                    "bestBefore": row.get("bestBefore"),
                    "lotIndex": None,
                }
            ]
        else:
            candidates = [
                {
                    **base,
                    "quantity": lot.get("quantity"),
                    "bestBefore": lot.get("bestBefore"),
                    "lotIndex": index,
                }
                for index, lot in enumerate(row.get("lots") or [])
            ]
        for item in candidates:
            stamp = _best_before(item.get("bestBefore"))
            if not stamp:
                continue
            days_remaining = (date.fromisoformat(stamp) - reference).days
            if days_remaining > horizon:
                continue
            if days_remaining < 0 and not include_past:
                continue
            item["bestBefore"] = stamp
            item["daysRemaining"] = days_remaining
            item["pastBestBefore"] = days_remaining < 0
            out.append(item)
    out.sort(
        key=lambda row: (
            int(row["daysRemaining"]),
            _norm_name(row.get("name")),
            int(row.get("lotIndex") or 0),
        )
    )
    return out


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


def recipe_expiry_priority(
    recipe: dict[str, Any],
    inventory: Any,
    *,
    today: date | None = None,
    within_days: int = DEFAULT_EXPIRY_WARNING_DAYS,
) -> dict[str, Any]:
    """Describe soon-expiring stock batches used by one recipe for ranking."""
    reference = today or date.today()
    horizon = max(0, int(within_days))
    stock = normalize_inventory(inventory)
    seen: set[str] = set()
    matches: list[dict[str, Any]] = []
    priority = 0.0
    for ingredient in recipe.get("ingredients") or []:
        if not isinstance(ingredient, dict):
            continue
        current = _find_stock(stock, ingredient)
        if not current:
            continue
        ident = inventory_identity(current)
        if not ident or ident in seen:
            continue

        candidates: list[dict[str, Any]] = []
        if current.get("unlimited") or not current.get("lots"):
            if current.get("bestBefore"):
                candidates.append(
                    {
                        "bestBefore": current.get("bestBefore"),
                        "quantity": current.get("quantity"),
                    }
                )
        else:
            candidates.extend(current.get("lots") or [])

        qualifying: list[tuple[int, dict[str, Any]]] = []
        for lot in candidates:
            stamp = _best_before(lot.get("bestBefore"))
            if not stamp:
                continue
            days_remaining = (date.fromisoformat(stamp) - reference).days
            if 0 <= days_remaining <= horizon:
                qualifying.append((days_remaining, lot))
        if not qualifying:
            continue
        days_remaining, lot = min(qualifying, key=lambda item: item[0])
        stamp = _best_before(lot.get("bestBefore"))
        seen.add(ident)
        urgency = (horizon + 1 - days_remaining) / (horizon + 1)
        priority += urgency
        match = {
            "identity": ident,
            "name": current.get("name"),
            "bestBefore": stamp,
            "daysRemaining": days_remaining,
            "urgency": round(urgency, 3),
        }
        if lot.get("quantity") is not None:
            match["quantity"] = lot.get("quantity")
        if current.get("unit"):
            match["unit"] = current.get("unit")
        matches.append(match)
    matches.sort(key=lambda row: (int(row["daysRemaining"]), _norm_name(row.get("name"))))
    return {"priority": round(priority, 3), "ingredients": matches}


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
            "stockLots": deepcopy(current.get("lots") or []),
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
    """Deduct finite stock FEFO: earliest best-before batch first, undated last."""
    rows = normalize_inventory(inventory)
    report: dict[str, list[dict[str, Any]]] = {
        "deducted": [],
        "deductedLots": [],
        "skipped": [],
        "depleted": [],
    }
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

        requested_in_stock_unit = max(0.0, float(converted))
        to_deduct = min(stock_quantity, requested_in_stock_unit)
        remaining_request = to_deduct
        lots = deepcopy(current.get("lots") or [])
        lots.sort(key=_lot_sort_key)
        kept: list[dict[str, Any]] = []
        for lot in lots:
            lot_amount = float(lot.get("quantity") or 0.0)
            if lot_amount <= 0:
                continue
            take = min(lot_amount, remaining_request) if remaining_request > 1e-12 else 0.0
            left = lot_amount - take
            if take > 1e-12:
                lot_report = {
                    "identity": ident,
                    "name": current.get("name"),
                    "quantity": round(take, 9),
                    "unit": current.get("unit", ""),
                }
                if lot.get("bestBefore"):
                    lot_report["bestBefore"] = lot.get("bestBefore")
                report["deductedLots"].append(lot_report)
                remaining_request -= take
            if left > 1e-9:
                kept_lot: dict[str, Any] = {"quantity": round(left, 9)}
                if lot.get("bestBefore"):
                    kept_lot["bestBefore"] = lot.get("bestBefore")
                kept.append(kept_lot)

        actual = to_deduct - max(0.0, remaining_request)
        report["deducted"].append(
            {
                "identity": ident,
                "name": current.get("name"),
                "quantity": round(actual, 9),
                "unit": current.get("unit", ""),
            }
        )
        if kept:
            current["lots"] = kept
            _refresh_row_totals(current)
        else:
            rows.remove(current)
            report["depleted"].append({"identity": ident, "name": current.get("name")})
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
