from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import math
import re
import unicodedata
from typing import Any
from uuid import uuid4

_MAX_ITEMS = 500
_UNSET = object()
DEFAULT_EXPIRY_WARNING_DAYS = 3
_STORAGE_VALUES = {"", "fridge", "freezer", "pantry", "other"}


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


def _positive_int(value: Any, *, maximum: int = 3650) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    if number <= 0 or number > maximum:
        return None
    return number


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
    if not source and target in {"pc", "pcs", "x"}:
        source = "pcs"
    if not target and source in {"pc", "pcs", "x"}:
        target = "pcs"
    left = _UNIT_SCALE.get(source)
    right = _UNIT_SCALE.get(target)
    if not left or not right or left[0] != right[0]:
        return None
    return amount * left[1] / right[1]


def _effective_best_before(lot: dict[str, Any]) -> str:
    printed = _best_before(lot.get("bestBefore"))
    opened = _best_before(lot.get("openedAt"))
    use_days = _positive_int(lot.get("useWithinDays"))
    opened_limit = ""
    if opened and use_days:
        opened_limit = (date.fromisoformat(opened) + timedelta(days=use_days)).isoformat()
    if printed and opened_limit:
        return min(printed, opened_limit)
    return printed or opened_limit


def _lot_sort_key(lot: dict[str, Any]) -> tuple[bool, str, str]:
    stamp = _effective_best_before(lot)
    return (not bool(stamp), stamp or "9999-12-31", _text(lot.get("addedAt")))


def _lot_metadata(raw: Any, *, strict: bool = False) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    lot_id = _text(raw.get("id") or raw.get("lotId"))
    if lot_id:
        out["id"] = lot_id[:160]
    storage = _text(raw.get("storage")).lower()
    if storage:
        if storage not in _STORAGE_VALUES:
            if strict:
                raise ValueError("Storage must be fridge, freezer, pantry, or other")
        else:
            out["storage"] = storage
    for key in ("purchaseDate", "openedAt"):
        if raw.get(key) not in (None, ""):
            stamp = _best_before(raw.get(key), strict=strict)
            if stamp:
                out[key] = stamp
    use_days = _positive_int(raw.get("useWithinDays"))
    if raw.get("useWithinDays") not in (None, "") and use_days is None and strict:
        raise ValueError("Use-within days must be between 1 and 3650")
    if use_days:
        out["useWithinDays"] = use_days
    for key in ("barcode", "productName", "brand", "source", "nutritionSource"):
        value = _text(raw.get(key))
        if value:
            out[key] = value[:300]
    added = _text(raw.get("addedAt"))
    if added:
        out["addedAt"] = added[:80]
    return out


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
                raise ValueError(f"Cannot convert inventory batch from {lot_unit} to {target_unit}")
            return None
        amount = converted
    elif target_unit and not lot_unit:
        lot_unit = target_unit
    stamp = _best_before(raw.get("bestBefore") or raw.get("best_before"), strict=strict)
    lot: dict[str, Any] = {"quantity": amount, **_lot_metadata(raw, strict=strict)}
    if stamp:
        lot["bestBefore"] = stamp
    if not lot.get("id"):
        lot["id"] = str(uuid4())
    if not lot.get("addedAt"):
        lot["addedAt"] = datetime.now(timezone.utc).isoformat()
    effective = _effective_best_before(lot)
    if effective:
        lot["effectiveBestBefore"] = effective
    else:
        lot.pop("effectiveBestBefore", None)
    return lot


def _refresh_row_totals(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("unlimited"):
        row.pop("quantity", None)
        row.pop("lots", None)
        stamp = _best_before(row.get("bestBefore"))
        if stamp:
            row["bestBefore"] = stamp
            row["effectiveBestBefore"] = stamp
        else:
            row.pop("bestBefore", None)
            row.pop("effectiveBestBefore", None)
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
        amount = _quantity(row.get("quantity"))
        if amount is not None and amount > 0:
            lot: dict[str, Any] = {"quantity": amount}
            stamp = _best_before(row.get("bestBefore"))
            if stamp:
                lot["bestBefore"] = stamp
            normalized = _normalize_lot(lot, target_unit=unit)
            if normalized:
                lots.append(normalized)

    if lots:
        lots.sort(key=_lot_sort_key)
        row["lots"] = lots
        row["quantity"] = round(sum(float(lot["quantity"]) for lot in lots), 9)
        printed = [str(lot["bestBefore"]) for lot in lots if lot.get("bestBefore")]
        effective = [_effective_best_before(lot) for lot in lots if _effective_best_before(lot)]
        if printed:
            row["bestBefore"] = min(printed)
        else:
            row.pop("bestBefore", None)
        if effective:
            row["effectiveBestBefore"] = min(effective)
        else:
            row.pop("effectiveBestBefore", None)
    else:
        row.pop("lots", None)
        row.pop("quantity", None)
        stamp = _best_before(row.get("bestBefore"))
        if stamp:
            row["bestBefore"] = stamp
            row["effectiveBestBefore"] = stamp
        else:
            row.pop("bestBefore", None)
            row.pop("effectiveBestBefore", None)
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
    current: dict[str, Any], lot: dict[str, Any], *, from_unit: str, strict: bool
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
    candidate = {**deepcopy(lot), "quantity": amount}
    normalized = _normalize_lot(candidate, target_unit=target_unit, strict=strict)
    if not normalized:
        return False
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
                for lot in row.get("lots") or []:
                    _append_lot_converted(
                        current, lot, from_unit=str(row.get("unit") or ""), strict=False
                    )
                _refresh_row_totals(current)
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
    lot_metadata: dict[str, Any] | None = None,
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
        lot: dict[str, Any] = {"quantity": amount, **(lot_metadata or {})}
        if normalized_best_before:
            lot["bestBefore"] = normalized_best_before
        normalized_lot = _normalize_lot(lot, target_unit=incoming_unit, strict=True)
        incoming["lots"] = [normalized_lot] if normalized_lot else []
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
            _refresh_row_totals(current)
            return rows
        if current.get("unlimited"):
            return rows
        if amount is None:
            return rows
        if not current.get("unit") and incoming_unit and not current.get("quantity"):
            current["unit"] = incoming_unit
        lot = {"quantity": amount, **(lot_metadata or {})}
        if normalized_best_before:
            lot["bestBefore"] = normalized_best_before
        _append_lot_converted(current, lot, from_unit=incoming_unit, strict=True)
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
        old_unit = _text(current.get("unit"))
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
            _refresh_row_totals(current)
            return rows

        current.pop("unlimited", None)
        if lots is not _UNSET:
            if lots is None:
                lots = []
            if not isinstance(lots, list):
                raise ValueError("Inventory batches must be a list")
            normalized_lots: list[dict[str, Any]] = []
            for raw_lot in lots:
                candidate = dict(raw_lot) if isinstance(raw_lot, dict) else raw_lot
                if isinstance(candidate, dict) and "unit" not in candidate:
                    candidate["unit"] = old_unit or new_unit
                lot = _normalize_lot(candidate, target_unit=new_unit, strict=True)
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
            normalized = _normalize_lot(lot, target_unit=new_unit, strict=True)
            current["lots"] = [normalized] if normalized else []
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
        _refresh_row_totals(current)
        return rows
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
    """Return individual batches whose effective expiry enters the warning window."""
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
            candidates = [{
                **base,
                **({"unlimited": True} if row.get("unlimited") else {}),
                **({"quantity": row["quantity"]} if row.get("quantity") is not None else {}),
                "bestBefore": row.get("bestBefore"),
                "effectiveBestBefore": row.get("effectiveBestBefore") or row.get("bestBefore"),
                "lotIndex": None,
            }]
        else:
            candidates = [
                {**base, **deepcopy(lot), "lotIndex": index}
                for index, lot in enumerate(row.get("lots") or [])
            ]
        for item in candidates:
            stamp = _effective_best_before(item)
            if not stamp:
                continue
            days_remaining = (date.fromisoformat(stamp) - reference).days
            if days_remaining > horizon:
                continue
            if days_remaining < 0 and not include_past:
                continue
            item["effectiveBestBefore"] = stamp
            item["daysRemaining"] = days_remaining
            item["pastBestBefore"] = days_remaining < 0
            item["openedDrivenExpiry"] = bool(
                item.get("openedAt") and item.get("useWithinDays") and stamp != _best_before(item.get("bestBefore"))
            )
            out.append(item)
    out.sort(key=lambda row: (int(row["daysRemaining"]), _norm_name(row.get("name")), int(row.get("lotIndex") or 0)))
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
                candidates.append({"bestBefore": current.get("bestBefore"), "quantity": current.get("quantity")})
        else:
            candidates.extend(current.get("lots") or [])
        qualifying: list[tuple[int, dict[str, Any], str]] = []
        for lot in candidates:
            stamp = _effective_best_before(lot)
            if not stamp:
                continue
            days_remaining = (date.fromisoformat(stamp) - reference).days
            if 0 <= days_remaining <= horizon:
                qualifying.append((days_remaining, lot, stamp))
        if not qualifying:
            continue
        days_remaining, lot, stamp = min(qualifying, key=lambda item: item[0])
        seen.add(ident)
        urgency = (horizon + 1 - days_remaining) / (horizon + 1)
        priority += urgency
        match = {
            "identity": ident,
            "name": current.get("name"),
            "bestBefore": lot.get("bestBefore"),
            "effectiveBestBefore": stamp,
            "daysRemaining": days_remaining,
            "urgency": round(urgency, 3),
            "storage": lot.get("storage"),
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
            "stockBestBefore": current.get("effectiveBestBefore") or current.get("bestBefore", ""),
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
    """Deduct finite stock FEFO using effective expiry, then undated batches."""
    rows = normalize_inventory(inventory)
    report: dict[str, list[dict[str, Any]]] = {
        "deducted": [], "deductedLots": [], "skipped": [], "depleted": []
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
                    "lotId": lot.get("id"),
                    "bestBefore": lot.get("bestBefore"),
                    "effectiveBestBefore": _effective_best_before(lot),
                    "storage": lot.get("storage"),
                    "barcode": lot.get("barcode"),
                    "productName": lot.get("productName"),
                    "brand": lot.get("brand"),
                    "source": lot.get("source"),
                }
                report["deductedLots"].append({k: v for k, v in lot_report.items() if v not in (None, "")})
                remaining_request -= take
            if left > 1e-9:
                kept_lot = deepcopy(lot)
                kept_lot["quantity"] = round(left, 9)
                kept.append(kept_lot)
        actual = to_deduct - max(0.0, remaining_request)
        report["deducted"].append({
            "identity": ident,
            "name": current.get("name"),
            "quantity": round(actual, 9),
            "unit": current.get("unit", ""),
        })
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
