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
_STORAGE_VALUES = {"", "fridge", "freezer", "pantry", "cupboard", "shelf", "drawer", "countertop", "cellar", "other"}


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


def ingredient_identities(item: Any) -> set[str]:
    """Return every explicit stable identity carried by a stock/request row."""
    identities: set[str] = set()
    primary = inventory_identity(item)
    if primary:
        identities.add(primary)
    if isinstance(item, dict):
        for value in item.get("identities") or []:
            text = _text(value)
            if text:
                identities.add(text)
    return identities


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
    printed = "" if lot.get("noExpiry") is True else _best_before(lot.get("bestBefore"))
    opened = _best_before(lot.get("openedAt"))
    use_days = _positive_int(lot.get("useWithinDays"))
    opened_limit = ""
    if opened and use_days and lot.get("applyOpeningExpiry") is not False:
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
    links = normalize_ingredient_links(raw.get("ingredientLinks"))
    if links:
        out["ingredientLinks"] = links
    lot_id = _text(raw.get("id") or raw.get("lotId"))
    if lot_id:
        out["id"] = lot_id[:160]
    if raw.get("noExpiry") is True:
        out["noExpiry"] = True
    for key in ("applyOpeningExpiry", "openingConditionsConfirmed"):
        if key in raw and raw[key] not in (None, ""):
            if type(raw[key]) is not bool:
                if strict:
                    raise ValueError("Use-within opening options must be checkboxes")
            else:
                out[key] = raw[key]
    storage = _text(raw.get("storage")).lower()
    if storage:
        if storage not in _STORAGE_VALUES:
            if strict:
                raise ValueError("Storage type is not supported")
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
    for key in ("barcode", "productName", "brand", "source", "nutritionSource", "storageLocationId", "containerId", "revision", "openingRuleId"):
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
    stamp = "" if raw.get("noExpiry") is True else _best_before(
        raw.get("bestBefore") or raw.get("best_before"), strict=strict
    )
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
        metadata = _lot_metadata(raw)
        for key in (
            "storage", "storageLocationId", "productName", "brand",
            "barcode", "containerId", "source", "ingredientLinks"
        ):
            if metadata.get(key):
                row[key] = metadata[key]
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
                for key in (
                    "storage", "storageLocationId", "productName", "brand",
                    "barcode", "containerId", "source"
                ):
                    if row.get(key):
                        current[key] = row[key]
                links = normalize_ingredient_links([
                    *(current.get("ingredientLinks") or []),
                    *(row.get("ingredientLinks") or []),
                ])
                if links:
                    current["ingredientLinks"] = links
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
        metadata = _lot_metadata(lot_metadata or {}, strict=True)
        for key in (
            "storage", "storageLocationId", "productName", "brand",
            "barcode", "containerId", "source", "ingredientLinks"
        ):
            if metadata.get(key):
                incoming[key] = metadata[key]
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
            for key in (
                "storage", "storageLocationId", "productName", "brand",
                "barcode", "containerId", "source"
            ):
                if incoming.get(key):
                    current[key] = incoming[key]
            links = normalize_ingredient_links([
                *(current.get("ingredientLinks") or []),
                *(incoming.get("ingredientLinks") or []),
            ])
            if links:
                current["ingredientLinks"] = links
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
    ingredient_links: Any = _UNSET,
) -> list[dict[str, Any]]:
    if ingredient_links is not _UNSET and (not unlimited or not isinstance(ingredient_links, list)):
        raise ValueError("Catalog links on a stock item require unlimited stock and a list")
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
            if ingredient_links is not _UNSET:
                links = normalize_ingredient_links(ingredient_links)
            else:
                links = normalize_ingredient_links([
                    *(current.get("ingredientLinks") or []),
                    *(link for lot in current.get("lots") or [] for link in lot.get("ingredientLinks") or []),
                ])
            if links:
                current["ingredientLinks"] = links
            else:
                current.pop("ingredientLinks", None)
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
    linked = stock_for_ingredient(inventory, ingredient)
    if linked is not None:
        return linked
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
    seen_lots: set[str] = set()
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
            if lot.get("id") in seen_lots:
                continue
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
        if lot.get("id"):
            seen_lots.add(lot["id"])
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


def _apply_primary_consumption(
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
            take = min(lot_amount, remaining_request) if remaining_request > 1e-12 and (not request.get("lotId") or request["lotId"] == lot.get("id")) else 0.0
            left = lot_amount - take
            if take > 1e-12:
                opening = next((item for item in request.get("packageOpenings", [])
                                if item.get("lotId") == lot.get("id")), None)
                if opening is not None:
                    from .product_opening import mark_package_opened
                    lot = mark_package_opened(current, lot, opening, opened_on=request.get("_openingDate"))
                lot_report = {
                    "identity": ident,
                    "name": current.get("name"),
                    "quantity": round(take, 9),
                    "unit": current.get("unit", ""),
                    "lotId": lot.get("id"),
                    **({"markedOpened": True} if opening is not None else {}),
                    "bestBefore": lot.get("bestBefore"),
                    "effectiveBestBefore": _effective_best_before(lot),
                    "storage": lot.get("storage"),
                    "storageLocationId": lot.get("storageLocationId"),
                    "barcode": lot.get("barcode"),
                    "productName": lot.get("productName"),
                    "brand": lot.get("brand"),
                    "source": lot.get("source"),
                    "nutritionSource": lot.get("nutritionSource"),
                    "purchaseDate": lot.get("purchaseDate"),
                    "openedAt": lot.get("openedAt"),
                    "useWithinDays": lot.get("useWithinDays"),
                    **{key: lot.get(key) for key in (
                        "applyOpeningExpiry", "openingRuleId", "openingConditionsConfirmed", "noExpiry", "containerId")},
                    "addedAt": lot.get("addedAt"),
                    "revision": lot.get("revision"),
                    "ingredientLinks": deepcopy(lot.get("ingredientLinks") or []),
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



def consumption_shortfalls(consumptions, report):
    """Return finite requested amounts that were not fully deducted."""
    deducted = report.get("deductedLots") if isinstance(report, dict) else []
    skipped = report.get("skipped") if isinstance(report, dict) else []
    deducted = deducted if isinstance(deducted, list) else []
    skipped = skipped if isinstance(skipped, list) else []
    result = []
    for request in consumptions if isinstance(consumptions, list) else []:
        if not isinstance(request, dict) or not request.get("consume", True):
            continue
        requested = _quantity(request.get("quantity"))
        if requested is None or requested <= 0:
            continue
        ident = _text(request.get("identity")) or inventory_identity(request)
        lot_id = _text(request.get("lotId"))
        # Unlimited stock is intentionally non-depleting.
        if any(
            _text(row.get("identity")) == ident and row.get("reason") == "unlimited"
            for row in skipped if isinstance(row, dict)
        ):
            continue
        actual = 0.0
        for row in deducted:
            if not isinstance(row, dict) or _text(row.get("identity")) != ident:
                continue
            if lot_id and _text(row.get("lotId")) != lot_id:
                continue
            amount = convert_amount(
                row.get("quantity"), row.get("unit", ""), request.get("unit", "")
            )
            if amount is not None:
                actual += float(amount)
        if actual + 1e-9 < requested:
            result.append(
                {
                    "identity": ident,
                    "lotId": lot_id or None,
                    "requested": round(float(requested), 9),
                    "deducted": round(actual, 9),
                    "unit": _text(request.get("unit")),
                }
            )
    return result


def format_stock(row: dict[str, Any]) -> str:
    if row.get("unlimited"):
        return "∞"
    amount = _quantity(row.get("quantity"))
    if amount is None:
        return "?"
    shown = str(int(amount)) if float(amount).is_integer() else f"{amount:g}"
    unit = _text(row.get("unit"))
    return f"{shown} {unit}".strip()


def normalize_ingredient_links(value):
    """Persist stable catalogue identities, never another copy of the stock."""
    result, seen = [], set()
    for raw in value if isinstance(value, list) else []:
        if not isinstance(raw, dict):
            continue
        row = {"key": _text(raw.get("key") or raw.get("ingredientId") or raw.get("id")),
               "name": _text(raw.get("name") or raw.get("foodName"))}
        identity = inventory_identity(row)
        if row["name"] and identity not in seen:
            result.append(row)
            seen.add(identity)
    return result


def stock_for_ingredient(stock, ingredient, used=None):
    """Read a product through any stable identity/link, subtracting reservations."""
    if isinstance(ingredient, str):
        wanted = {ingredient}
        primary_identity = ingredient
    else:
        wanted = ingredient_identities(ingredient)
        direct = _text(ingredient.get("identity")) if isinstance(ingredient, dict) else ""
        if direct:
            wanted.add(direct)
        primary_identity = direct or inventory_identity(ingredient)
    candidates, fallback = [], None
    for row in stock:
        row_identity = inventory_identity(row)
        primary = row_identity in wanted
        row_linked = {
            identity
            for link in row.get("ingredientLinks") or []
            for identity in ingredient_identities(link)
        }
        linked_row = bool(wanted & row_linked)
        if row.get("unlimited") and (primary or linked_row):
            return deepcopy(row)
        if primary or linked_row:
            fallback = row
        for lot in row.get("lots") or []:
            linked = {
                identity
                for link in lot.get("ingredientLinks") or []
                for identity in ingredient_identities(link)
            }
            if primary or linked_row or bool(wanted & linked):
                candidates.append((row, lot))
    if not candidates:
        return deepcopy(fallback) if fallback else None
    target = next((row.get("unit", "") for row, _ in candidates), "")
    requested_unit = ingredient.get("unit") if isinstance(ingredient, dict) else None
    if requested_unit and any(convert_amount(1, row.get("unit", ""), requested_unit) is not None for row, _ in candidates):
        target = requested_unit
    lots = []
    for row, lot in candidates:
        amount = convert_amount(lot.get("quantity"), row.get("unit", ""), target)
        if amount is None:
            continue
        taken = (used or {}).get(lot.get("id"))
        if taken:
            amount -= convert_amount(taken[0], taken[1], target) or 0
        lots.append({**deepcopy(lot), "quantity": max(0.0, amount), "sourceIdentity": inventory_identity(row)})
    lots.sort(key=_lot_sort_key)
    identity = {"key": primary_identity[2:]} if primary_identity.startswith("k:") else {}
    name = (ingredient.get("name") or ingredient.get("foodName")) if isinstance(ingredient, dict) else primary_identity[2:]
    dates = {key: min((lot[key] for lot in lots if lot.get(key)), default="") for key in ("bestBefore", "effectiveBestBefore")}
    return {**identity, "name": name or primary_identity[2:], "unit": target,
            "quantity": round(sum(lot["quantity"] for lot in lots), 9), "lots": lots, **dates}


def reserve_lot(used, lot, quantity, unit):
    previous = used.get(lot.get("id"))
    total = float(quantity)
    if previous:
        total += convert_amount(previous[0], previous[1], unit) or 0
    used[lot["id"]] = (total, unit)


def reserve_requirement(used, row, quantity, unit):
    if not row or row.get("unlimited"):
        return
    remaining = convert_amount(quantity, unit, row.get("unit", ""))
    if remaining is None:
        return
    for lot in row.get("lots") or []:
        take = min(remaining, float(lot.get("quantity") or 0))
        reserve_lot(used, lot, take, row.get("unit", ""))
        remaining -= take
        if remaining <= 1e-9:
            break



def restore_consumption(inventory, report):
    """Restore a previous confirmed deduction before applying an edited history record.

    Stable lot IDs are preserved. Existing lot metadata wins; when a depleted lot
    must be recreated, the metadata captured in the meal-history deduction report
    is used. This makes a history edit change real stock instead of only changing
    presentation text.
    """
    rows = normalize_inventory(inventory)
    lots = report.get("deductedLots") if isinstance(report, dict) else None
    if not isinstance(lots, list):
        return rows, {"restored": [], "skipped": []}
    restored: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    metadata_keys = (
        "bestBefore", "storage", "storageLocationId", "barcode", "productName", "brand", "source",
        "nutritionSource", "purchaseDate", "openedAt", "useWithinDays",
        "applyOpeningExpiry", "openingRuleId", "openingConditionsConfirmed", "noExpiry", "containerId",
        "addedAt", "revision", "ingredientLinks",
    )
    for raw in lots:
        if not isinstance(raw, dict):
            continue
        ident = _text(raw.get("identity"))
        amount = _quantity(raw.get("quantity"))
        unit = _text(raw.get("unit"))
        if not ident or amount is None or amount <= 0:
            continue
        row = next((item for item in rows if inventory_identity(item) == ident), None)
        if row is not None and row.get("unlimited"):
            skipped.append({"identity": ident, "reason": "unlimited"})
            continue
        if row is None:
            name = _text(raw.get("name") or raw.get("productName"))
            if not name:
                name = ident[2:] if len(ident) > 2 else ident
            row = {"name": name, "unit": unit, "lots": []}
            if ident.startswith("k:"):
                row["key"] = ident[2:]
            rows.append(row)
        target_unit = _text(row.get("unit") or unit)
        if not row.get("unit") and target_unit:
            row["unit"] = target_unit
        converted = convert_amount(amount, unit, target_unit)
        if converted is None:
            skipped.append({"identity": ident, "reason": "unit_mismatch"})
            continue
        lot_id = _text(raw.get("lotId") or raw.get("id"))
        existing = next(
            (lot for lot in row.get("lots") or [] if lot_id and _text(lot.get("id")) == lot_id),
            None,
        )
        if existing is not None:
            existing["quantity"] = round(
                float(existing.get("quantity") or 0.0) + float(converted), 9
            )
        else:
            lot = {"quantity": round(float(converted), 9)}
            if lot_id:
                lot["id"] = lot_id
            for key in metadata_keys:
                value = raw.get(key)
                if value not in (None, "", []):
                    lot[key] = deepcopy(value)
            normalized = _normalize_lot(lot, target_unit=target_unit, strict=True)
            if normalized is None:
                skipped.append({"identity": ident, "reason": "invalid_lot"})
                continue
            row.setdefault("lots", []).append(normalized)
        _refresh_row_totals(row)
        restored.append({
            "identity": ident,
            "name": row.get("name"),
            "quantity": round(float(converted), 9),
            "unit": target_unit,
            **({"lotId": lot_id} if lot_id else {}),
        })
    return normalize_inventory(rows), {"restored": restored, "skipped": skipped}


def _consume_inventory(inventory, consumptions):
    """Consume linked products once, retaining the owner's lot IDs and FEFO order."""
    rows = normalize_inventory(inventory)
    if not any(row.get("ingredientLinks") or any(lot.get("ingredientLinks") for lot in row.get("lots") or []) for row in rows):
        return _apply_primary_consumption(rows, consumptions)
    report = {key: [] for key in ("deducted", "deductedLots", "skipped", "depleted")}
    from .stock_allocation import allocate_stock
    requests = [request for request in consumptions if isinstance(request, dict) and request.get("consume", True)]
    for request, view in zip(requests, allocate_stock(rows, requests)):
        identity = request.get("identity") or inventory_identity(request)
        remaining = _quantity(request.get("quantity"))
        if view and view.get("unlimited"):
            report["skipped"].append({"identity": identity, "reason": "unlimited"})
            continue
        if not view or remaining is None or convert_amount(remaining, request.get("unit", ""), view.get("unit", "")) is None or not view.get("lots"):
            _, skipped = _apply_primary_consumption(rows, [request])
            report["skipped"].extend(skipped["skipped"])
            continue
        for lot in view["lots"]:
            amount = convert_amount(lot["quantity"], view["unit"], request.get("unit", ""))
            take = min(remaining, amount or 0)
            if take <= 1e-9 or request.get("lotId") and request["lotId"] != lot["id"]:
                continue
            rows, partial = _apply_primary_consumption(rows, [{**request, "identity": lot["sourceIdentity"], "lotId": lot["id"], "quantity": take}])
            for key in report:
                report[key].extend(partial[key])
            remaining -= take
            if remaining <= 1e-9:
                break
    return rows, report


def apply_consumption(inventory, consumptions):
    """Commit opening changes only for exact packages actually consumed."""
    for request in consumptions:
        openings = request.get("packageOpenings", []) if isinstance(request, dict) else []
        if not isinstance(openings, list) or any(
            not isinstance(item, dict) or not item.get("lotId") for item in openings
        ):
            raise ValueError("Choose a package to mark opened")
    rows, report = _consume_inventory(inventory, consumptions)
    consumed = {item.get("lotId") for item in report["deductedLots"] if item.get("markedOpened")}
    for request in consumptions:
        if not isinstance(request, dict):
            continue
        if any(item["lotId"] not in consumed for item in request.get("packageOpenings", [])):
            raise ValueError("An opened package was not used; review its selected amount")
    return rows, report
