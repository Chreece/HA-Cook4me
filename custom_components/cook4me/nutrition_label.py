from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from .inventory import inventory_identity, normalize_inventory
from .nutrition import normalize_nutrition


def _text(value: Any) -> str:
    return str(value or "").strip()


async def async_save_lot_nutrition(
    store: Any,
    inventory: Any,
    *,
    lot_id: str,
    nutrition: Any,
    manually_edited: bool = False,
) -> dict[str, Any]:
    """Persist exact package nutrition against one stable inventory-lot UUID."""
    wanted = _text(lot_id)
    if not wanted:
        raise ValueError("A stock lot id is required")

    stock = normalize_inventory(inventory)
    inventory_row: dict[str, Any] | None = None
    inventory_lot: dict[str, Any] | None = None
    for row in stock:
        for lot in row.get("lots") or []:
            if _text(lot.get("id")) == wanted:
                inventory_row = row
                inventory_lot = lot
                break
        if inventory_lot is not None:
            break

    if inventory_row is None or inventory_lot is None:
        raise ValueError("Stock lot was not found")

    identity = inventory_identity(inventory_row)
    if not identity:
        raise ValueError("Stock lot has no stable ingredient identity")

    raw = dict(nutrition) if isinstance(nutrition, dict) else {}
    raw["source"] = "nutrition_label_scan"
    raw["sourceId"] = (
        _text(inventory_lot.get("barcode"))
        or wanted
    )
    raw["label"] = (
        _text(inventory_lot.get("productName"))
        or _text(inventory_row.get("name"))
        or wanted
    )
    raw["confidence"] = "exact_product"
    profile = normalize_nutrition(raw)
    if profile is None:
        raise ValueError(
            "Nutrition label needs a g/ml basis and at least one valid nutrient"
        )

    record = {
        "inventoryLotId": wanted,
        "quantity": inventory_lot.get("quantity"),
        "unit": _text(inventory_row.get("unit")),
        "bestBefore": _text(inventory_lot.get("bestBefore")),
        "barcode": _text(inventory_lot.get("barcode")),
        "productName": _text(inventory_lot.get("productName")),
        "brand": _text(inventory_lot.get("brand")),
        "nutrition": profile,
        "source": "nutrition_label_scan",
        "manuallyEdited": bool(manually_edited),
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    }
    record = {
        key: value
        for key, value in record.items()
        if value not in (None, "")
    }

    exact = store._data.setdefault("stockLots", {})
    records = exact.setdefault(identity, [])
    replaced = False
    for index, existing in enumerate(records):
        if (
            isinstance(existing, dict)
            and _text(existing.get("inventoryLotId")) == wanted
        ):
            records[index] = deepcopy(record)
            replaced = True
            break
    if not replaced:
        records.append(deepcopy(record))

    await store._save()
    return {
        "identity": identity,
        "lotId": wanted,
        "nutrition": deepcopy(profile),
        "record": deepcopy(record),
    }
