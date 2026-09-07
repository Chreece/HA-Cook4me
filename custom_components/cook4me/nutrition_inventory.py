from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from .inventory import inventory_identity, normalize_inventory
from .nutrition import (
    convert_amount,
    ingredient_identity,
    normalize_nutrition,
    nutrition_for_amount,
)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> float | None:
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _add(target: dict[str, float], values: dict[str, float] | None) -> None:
    if not values:
        return
    for key, value in values.items():
        target[key] = target.get(key, 0.0) + float(value)


def _rounded(values: dict[str, float]) -> dict[str, float]:
    return {
        key: round(float(value), 1 if key in {"energyKcal", "energyKJ"} else 2)
        for key, value in values.items()
        if math.isfinite(float(value))
    }


def _generic_profile(store, identity: str) -> dict[str, Any] | None:
    row = (store._data.get("generic") or {}).get(identity)
    if isinstance(row, dict) and isinstance(row.get("nutrition"), dict):
        return normalize_nutrition(row["nutrition"])
    return normalize_nutrition(row)


async def async_link_latest_stock_nutrition(
    store,
    ingredient: dict[str, Any],
    *,
    inventory_lot_id: str,
) -> bool:
    """Bind the newest exact nutrition record to the canonical stock lot UUID."""
    identity = ingredient_identity(ingredient)
    lot_id = _text(inventory_lot_id)
    rows = (store._data.get("stockLots") or {}).get(identity)
    if not identity or not lot_id or not isinstance(rows, list) or not rows:
        return False
    # The barcode add path appends the nutrition row immediately before linking.
    for record in reversed(rows):
        if not isinstance(record, dict):
            continue
        if record.get("inventoryLotId"):
            continue
        record["inventoryLotId"] = lot_id
        await store._save()
        return True
    return False


async def async_reconcile_nutrition_inventory(store, inventory: Any) -> None:
    """Keep exact nutrition quantities aligned with inventory lots by stable lot id.

    Old nutrition records without lot ids retain a conservative best-before fallback,
    which keeps pre-upgrade data usable. Editing an expiry/storage field no longer
    destroys exact nutrition for new linked lots.
    """
    stock = normalize_inventory(inventory)
    by_identity = {inventory_identity(row): row for row in stock if inventory_identity(row)}
    exact = store._data.setdefault("stockLots", {})
    changed = False

    for identity in list(exact):
        row = by_identity.get(identity)
        if row is None or row.get("unlimited"):
            exact.pop(identity, None)
            changed = True
            continue
        target_unit = _text(row.get("unit"))
        inventory_lots = [lot for lot in row.get("lots") or [] if isinstance(lot, dict)]
        by_lot_id = {_text(lot.get("id")): lot for lot in inventory_lots if _text(lot.get("id"))}
        legacy_capacity: dict[str, float] = {}
        for lot in inventory_lots:
            stamp = _text(lot.get("bestBefore"))
            amount = _number(lot.get("quantity")) or 0.0
            legacy_capacity[stamp] = legacy_capacity.get(stamp, 0.0) + amount

        kept: list[dict[str, Any]] = []
        for record in exact.get(identity) or []:
            if not isinstance(record, dict):
                continue
            lot_id = _text(record.get("inventoryLotId"))
            inv_lot = by_lot_id.get(lot_id) if lot_id else None
            if inv_lot is not None:
                capacity = _number(inv_lot.get("quantity")) or 0.0
                converted = convert_amount(record.get("quantity"), record.get("unit"), target_unit)
                if converted is None or converted <= 0 or capacity <= 0:
                    changed = True
                    continue
                keep_amount = min(converted, capacity)
                next_record = deepcopy(record)
                next_record["quantity"] = round(keep_amount, 9)
                next_record["unit"] = target_unit
                next_record["bestBefore"] = _text(inv_lot.get("bestBefore"))
                next_record["inventoryLotId"] = lot_id
                kept.append(next_record)
                if keep_amount != converted or next_record != record:
                    changed = True
                continue

            # Legacy pre-lot-id exact nutrition: retain only against matching date.
            stamp = _text(record.get("bestBefore"))
            capacity = legacy_capacity.get(stamp, 0.0)
            converted = convert_amount(record.get("quantity"), record.get("unit"), target_unit)
            if converted is None or converted <= 0 or capacity <= 0:
                changed = True
                continue
            keep_amount = min(converted, capacity)
            legacy_capacity[stamp] = max(0.0, capacity - keep_amount)
            next_record = deepcopy(record)
            next_record["quantity"] = round(keep_amount, 9)
            next_record["unit"] = target_unit
            kept.append(next_record)
            if keep_amount != converted or _text(record.get("unit")) != target_unit:
                changed = True

        if kept:
            exact[identity] = kept
        else:
            exact.pop(identity, None)
            changed = True

    if changed:
        await store._save()


def _record_score(request: dict[str, Any], record: dict[str, Any]) -> int:
    lot_id = _text(request.get("lotId"))
    if lot_id and lot_id == _text(record.get("inventoryLotId")):
        return 100
    score = 0
    barcode = _text(request.get("barcode"))
    if barcode and barcode == _text(record.get("barcode")):
        score += 20
    stamp = _text(request.get("bestBefore"))
    if stamp == _text(record.get("bestBefore")):
        score += 10
    product = _text(request.get("productName")).casefold()
    if product and product == _text(record.get("productName")).casefold():
        score += 4
    return score


async def async_consume_nutrition_report(store, report: Any) -> dict[str, Any]:
    """Calculate confirmed meal nutrition from the exact lots actually deducted."""
    requests = report.get("deductedLots") if isinstance(report, dict) else None
    if not isinstance(requests, list):
        return {"totals": {}, "coverage": 0.0, "sourceKinds": []}
    totals: dict[str, float] = {}
    fractions: list[float] = []
    source_kinds: set[str] = set()
    exact = store._data.setdefault("stockLots", {})
    changed = False

    for request in requests:
        if not isinstance(request, dict):
            continue
        identity = _text(request.get("identity"))
        amount = _number(request.get("quantity"))
        unit = _text(request.get("unit"))
        if not identity or amount is None or amount <= 0 or not unit:
            continue
        remaining = amount
        exact_covered = 0.0
        records = exact.get(identity) if isinstance(exact.get(identity), list) else []
        ranked = sorted(
            enumerate(records),
            key=lambda item: _record_score(request, item[1]),
            reverse=True,
        )
        consumed_indices: dict[int, float] = {}
        for index, record in ranked:
            if remaining <= 1e-12 or _record_score(request, record) <= 0:
                break
            available = convert_amount(record.get("quantity"), record.get("unit"), unit)
            if available is None or available <= 0:
                continue
            take = min(available, remaining)
            values = nutrition_for_amount(record.get("nutrition"), take, unit)
            if values is None:
                continue
            _add(totals, values)
            exact_covered += take
            remaining -= take
            consumed_indices[index] = take
            source_kinds.add("exact_product")

        if consumed_indices:
            kept: list[dict[str, Any]] = []
            for index, record in enumerate(records):
                take = consumed_indices.get(index, 0.0)
                if take <= 0:
                    kept.append(record)
                    continue
                original_in_request_unit = convert_amount(record.get("quantity"), record.get("unit"), unit) or 0.0
                left_request_unit = max(0.0, original_in_request_unit - take)
                if left_request_unit <= 1e-9:
                    changed = True
                    continue
                left_record_unit = convert_amount(left_request_unit, unit, record.get("unit"))
                if left_record_unit is None or left_record_unit <= 1e-9:
                    changed = True
                    continue
                next_record = deepcopy(record)
                next_record["quantity"] = round(left_record_unit, 9)
                kept.append(next_record)
                changed = True
            if kept:
                exact[identity] = kept
            else:
                exact.pop(identity, None)

        generic = _generic_profile(store, identity)
        generic_covered = 0.0
        if remaining > 1e-9 and generic is not None:
            values = nutrition_for_amount(generic, remaining, unit)
            if values is not None:
                _add(totals, values)
                generic_covered = remaining
                source_kinds.add("generic_reference")
        fractions.append(min(1.0, (exact_covered + generic_covered) / amount))

    if changed:
        await store._save()
    coverage = sum(fractions) / len(fractions) if fractions else 0.0
    return {
        "totals": _rounded(totals),
        "coverage": round(coverage, 3),
        "fullyCovered": bool(fractions) and all(value >= 0.999 for value in fractions),
        "estimated": "generic_reference" in source_kinds or coverage < 0.999,
        "sourceKinds": sorted(source_kinds),
    }
