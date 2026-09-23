"""Review-first receipt drafts. Recognition and draft saves never change inventory.

Amounts on a receipt are line totals, not per-package paid prices. A saved draft
owns stable item IDs and freezes the stock payload before its first attempt, so
retries after a timeout or restart cannot add a second physical package.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Any
from uuid import uuid4

MAX_ITEMS = 120
MAX_DRAFTS = 30  # per user and integration entry; never silently evict drafts
KINDS = {"product", "discount", "deposit", "tax", "total", "payment", "other"}
UNITS = {"g", "kg", "ml", "cl", "dl", "l", "pcs"}
NUTRIENTS = {"energyKcal", "protein", "carbohydrates", "fat", "saturatedFat", "fiber", "sugars", "salt"}


def text(value: Any, limit: int = 300) -> str:
    return " ".join(str(value or "").split())[:limit]


def number(value: Any, *, signed: bool = False) -> float | None:
    """Accept plain decimal numbers; do not guess ambiguous thousands separators."""
    if value is None or value == "" or isinstance(value, bool):
        return None
    raw = str(value).strip().replace(",", ".")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
        return None
    try:
        result = Decimal(raw)
    except InvalidOperation:
        return None
    if not result.is_finite() or abs(result) > 10_000_000 or (result < 0 and not signed):
        return None
    return float(result)


def iso_date(value: Any) -> str:
    try:
        return date.fromisoformat(str(value)).isoformat() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)) else ""
    except ValueError:
        return ""


def _count(value: Any) -> int:
    if value is None or value == "":
        return 1
    parsed = number(value)
    if parsed is None or not parsed.is_integer() or not 1 <= parsed <= 100:
        raise ValueError("Choose between 1 and 100 packages")
    return int(parsed)


def _currency(value: Any) -> str:
    code = text(value).upper()
    return code if re.fullmatch(r"[A-Z]{3}", code) else ""


def _links(value: Any) -> list[dict[str, str]]:
    """Save explicit choices only. The stock endpoint validates current catalog IDs."""
    result, seen = [], set()
    for raw in value if isinstance(value, list) else []:
        if not isinstance(raw, dict):
            continue
        key = text(raw.get("key") or raw.get("ingredientId") or raw.get("id"), 160)
        if key and key not in seen:
            result.append({"key": key, "name": text(raw.get("name"))})
            seen.add(key)
        if len(result) > 100:
            raise ValueError("Too many ingredient mappings for one receipt item")
    return result


def _nutrition(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {"basisQuantity": 100, "basisUnit": "", "values": {}}
    basis = raw.get("basisUnit") or ""
    if basis not in {"", "g", "ml"}:
        raise ValueError("Choose a nutrition basis of 100 g or 100 ml")
    # Incomplete drafts keep entered values; applying requires a confirmed basis.
    source = raw.get("values") if isinstance(raw.get("values"), dict) else {}
    if source and raw.get("basisQuantity", 100) != 100:
        raise ValueError("Nutrition must be entered per 100 g or per 100 ml")
    values = {key: parsed for key, value in source.items()
              if key in NUTRIENTS and (parsed := number(value)) is not None}
    if any(value not in (None, "") and (key not in NUTRIENTS or number(value) is None) for key, value in source.items()):
        raise ValueError("Enter valid non-negative nutrition values")
    return {"basisQuantity": 100, "basisUnit": basis, "values": values}


def editable_item(raw: dict[str, Any], *, model: bool = False) -> dict[str, Any]:
    kind = raw.get("kind") if raw.get("kind") in KINDS else "product"
    item = {"productName": text(raw.get("productName")), "originalName": text(raw.get("originalName") or raw.get("productName")),
            "ingredientName": text(raw.get("ingredientName")), "brand": text(raw.get("brand")),
            "kind": kind, "lineTotal": number(raw.get("lineTotal"), signed=kind != "product"),
            "packageCount": _count(raw.get("packageCount")), "quantity": number(raw.get("quantity")),
            "unit": text(raw.get("unit")) if raw.get("unit") in UNITS else "",
            "note": text(raw.get("note"), 1000)}
    if not model:
        for key in ("lineTotal", "quantity"):
            if raw.get(key) not in (None, "") and item[key] is None:
                raise ValueError(f"Enter a valid {key}; leave an unknown value blank")
    if model:
        # A till receipt is not a nutrition label or an expiry-date source.
        item.update(ingredientLinks=[], nutrition={"basisQuantity": 100, "basisUnit": "", "values": {}},
                    bestBefore="", storageLocationId="", barcode="", noExpiry=False)
    else:
        item.update(ingredientLinks=_links(raw.get("ingredientLinks")), nutrition=_nutrition(raw.get("nutrition")),
                    bestBefore=iso_date(raw.get("bestBefore")), storageLocationId=text(raw.get("storageLocationId"), 160),
                    barcode=text(raw.get("barcode"), 80), noExpiry=raw.get("noExpiry") is True,
                    containerId=text(raw.get("containerId"), 160), openedAt=iso_date(raw.get("openedAt")),
                    useWithinDays=text(raw.get("useWithinDays"), 8))
    return item


def normalize_receipt(raw: Any, *, model: bool = False) -> dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get("items"), list) or not raw["items"]:
        raise ValueError("No receipt items were readable. Try a clearer photo or add items manually.")
    if len(raw["items"]) > MAX_ITEMS:
        raise ValueError(f"A receipt can contain at most {MAX_ITEMS} items; scan smaller sections separately.")
    items = []
    for row in raw["items"]:
        if not isinstance(row, dict):
            raise ValueError("Invalid receipt item")
        item = editable_item(row, model=model)
        if not item["productName"]:
            item["productName"] = text(row.get("originalName"))
        item["id"] = uuid4().hex if model else text(row.get("id"), 80)
        item["status"] = "discarded" if not model and row.get("status") == "discarded" else "pending"
        items.append(item)
    return {"merchant": text(raw.get("merchant")), "purchaseDate": iso_date(raw.get("purchaseDate")),
            "currency": _currency(raw.get("currency")), "total": number(raw.get("total")),
            "note": text(raw.get("note"), 2000), "items": items}


def product_payload(receipt: dict[str, Any], item: dict[str, Any], entry_id: str, language: str) -> dict[str, Any]:
    """One explicitly reviewed receipt line -> existing scanner stock request."""
    if item["kind"] != "product":
        raise ValueError("Deposits, discounts, totals and other non-product lines cannot be added to stock")
    links = item.get("ingredientLinks") or []
    if not links:
        raise ValueError("Choose at least one compatible catalog ingredient")
    quantity, unit = number(item.get("quantity")), item.get("unit")
    if not quantity or unit not in UNITS:
        raise ValueError("Enter the amount and unit in each package before applying this item")
    # Do not silently stamp today's date onto a receipt with an unreadable date.
    if not receipt.get("purchaseDate"):
        raise ValueError("Confirm the receipt's purchase date before applying items")
    count = item["packageCount"]
    payload = {"entry_id": entry_id, "request_id": f"receipt-{receipt['id']}-{item['id']}",
               "ingredient": links[0], "ingredient_links": links, "quantity": quantity,
               "unit": unit, "package_count": count, "best_before": "" if item.get("noExpiry") else item.get("bestBefore", ""),
               "language": language,
               "lot_metadata": {"productName": item["productName"], "brand": item.get("brand", ""),
                                "barcode": item.get("barcode", ""), "storageLocationId": item.get("storageLocationId", ""),
                                "purchaseDate": receipt["purchaseDate"], "noExpiry": item.get("noExpiry", False),
                                "containerId": item.get("containerId", ""), "openedAt": item.get("openedAt", ""),
                                "useWithinDays": item.get("useWithinDays", "")}}
    price = number(item.get("lineTotal"))
    if price is not None:
        if not receipt.get("currency"):
            raise ValueError("Confirm the receipt currency before saving a paid price")
        # Keep the full line total and total purchased quantity as price basis.
        # The existing store prorates each lot, avoiding per-package rounding drift.
        payload["paid_price"] = {"amount": price, "currency": receipt["currency"],
                                 "basisQuantity": float(Decimal(str(quantity)) * count), "basisUnit": unit,
                                 "location": receipt.get("merchant", "")}
    nutrition = item.get("nutrition") or {}
    if nutrition.get("values"):
        if nutrition.get("basisUnit") not in {"g", "ml"}:
            raise ValueError("Confirm a nutrition basis of 100 g or 100 ml before applying")
        payload["nutrition"] = deepcopy(nutrition)
    return payload


class ReceiptConflict(ValueError):
    """A newer draft or an in-flight stock operation must not be overwritten."""


class ReceiptDraftStore:
    def __init__(self, store: Any) -> None:
        self._store = store
        self._data: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    async def _load(self) -> None:
        if self._data is None:
            raw = await self._store.async_load()
            self._data = raw if isinstance(raw, dict) and isinstance(raw.get("drafts"), dict) else {"drafts": {}}

    async def _commit(self, data: dict[str, Any]) -> None:
        await self._store.async_save(deepcopy(data))
        self._data = deepcopy(data)

    def _owned(self, owner: str, ident: str) -> dict[str, Any]:
        row = self._data["drafts"].get(ident)
        if not owner or not row or row.get("owner") != owner:
            raise ValueError("Receipt draft not found")
        return row

    @staticmethod
    def _public(row: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(row)
        result.pop("owner", None)
        for item in result["items"]:
            item.pop("payload", None)
        return result

    @staticmethod
    def _check_revision(row: dict[str, Any], revision: int) -> None:
        if isinstance(revision, bool) or row["revision"] != revision:
            raise ReceiptConflict("This receipt changed on another screen. Reopen the saved draft before editing.")

    async def list(self, owner: str) -> list[dict[str, Any]]:
        async with self._lock:
            await self._load()
            return [{key: row.get(key) for key in ("id", "revision", "merchant", "purchaseDate", "currency", "updatedAt")}
                    | {"itemCount": len(row["items"]), "pendingCount": sum(i["status"] == "pending" for i in row["items"])}
                    for row in sorted(self._data["drafts"].values(), key=lambda r: r["updatedAt"], reverse=True)
                    if row.get("owner") == owner]

    async def get(self, owner: str, ident: str) -> dict[str, Any]:
        async with self._lock:
            await self._load()
            return self._public(self._owned(owner, ident))

    async def save(self, owner: str, raw: dict[str, Any], *, ident: str = "", revision: int = 0) -> dict[str, Any]:
        if not owner:
            raise ValueError("A signed-in user is required")
        cleaned = normalize_receipt(raw)
        async with self._lock:
            await self._load()
            old = self._owned(owner, ident) if ident else None
            if old:
                self._check_revision(old, revision)
                originals = {item["id"]: item for item in old["items"]}
                incoming = [text(item.get("id"), 80) for item in raw["items"]]
                if len(incoming) != len(set(incoming)) or set(incoming) != set(originals):
                    raise ValueError("Keep receipt item IDs unchanged; use discard for unwanted lines")
                for item in cleaned["items"]:
                    original = originals[item["id"]]
                    if original["status"] != "pending":
                        item.clear()
                        item.update(deepcopy(original))
            elif sum(row.get("owner") == owner for row in self._data["drafts"].values()) >= MAX_DRAFTS:
                raise ValueError("The saved receipt limit is reached. Discard a finished draft first.")
            if not old:
                ident = uuid4().hex
                for item in cleaned["items"]:
                    item["id"] = uuid4().hex
            row = {**cleaned, "id": ident, "owner": owner, "revision": (old["revision"] if old else 0) + 1,
                   "updatedAt": datetime.now(timezone.utc).isoformat()}
            data = deepcopy(self._data)
            data["drafts"][ident] = row
            await self._commit(data)
            return self._public(row)

    async def discard(self, owner: str, ident: str, revision: int, item_id: str = "") -> dict[str, Any] | None:
        async with self._lock:
            await self._load()
            row = self._owned(owner, ident)
            self._check_revision(row, revision)
            data = deepcopy(self._data)
            target = data["drafts"][ident]
            if item_id:
                item = next((item for item in target["items"] if item["id"] == item_id), None)
                if item is None:
                    raise ValueError("Receipt item not found")
                if item["status"] not in {"pending", "discarded"}:
                    raise ReceiptConflict("This item was submitted to stock; it cannot be discarded from here")
                item["status"] = "discarded"
                target["revision"] += 1
                target["updatedAt"] = datetime.now(timezone.utc).isoformat()
            else:
                if any(item["status"] == "applying" for item in target["items"]):
                    raise ReceiptConflict("Finish retrying the submitted item before discarding this receipt")
                del data["drafts"][ident]
            await self._commit(data)
            return self._public(target) if item_id else None

    async def apply(self, owner: str, ident: str, revision: int, item_id: str, *, entry_id: str,
                    language: str, add_product: Any) -> dict[str, Any]:
        # Serialize the full operation. No second caller can race through pending.
        async with self._lock:
            await self._load()
            row = self._owned(owner, ident)
            item = next((item for item in row["items"] if item["id"] == item_id), None)
            if item is None:
                raise ValueError("Receipt item not found")
            if item["status"] == "applied":
                return {"receipt": self._public(row), "alreadyApplied": True, "result": {}}
            self._check_revision(row, revision)
            if item["status"] == "discarded":
                raise ValueError("This receipt item was discarded")
            data = deepcopy(self._data)
            target = data["drafts"][ident]
            current = next(i for i in target["items"] if i["id"] == item_id)
            if current["status"] == "pending":
                current["payload"] = product_payload(target, current, entry_id, language)
                current["status"] = "applying"
                target["revision"] += 1
                await self._commit(data)  # durable intent BEFORE inventory writes
            try:
                result = await add_product(deepcopy(current["payload"]))
            except Exception as exc:
                # Validation guarantees no stock write. Unknown failures retain the
                # immutable request so retry uses the existing scanner receipt.
                if getattr(exc, "code", "") == "product_validation":
                    current["status"] = "pending"
                    current.pop("payload", None)
                    target["revision"] += 1
                    await self._commit(data)
                raise
            current["warnings"] = [text(w, 500) for w in result.get("warnings", [])][:10]
            if not current["warnings"]:
                current["status"] = "applied"
                current["lotIds"] = result.get("lotIds") or ([result["lotId"]] if result.get("lotId") else [])
            target["revision"] += 1
            target["updatedAt"] = datetime.now(timezone.utc).isoformat()
            await self._commit(data)
            return {"receipt": self._public(target), "result": result}


async def receipt_store_for_bridge(bridge: Any) -> ReceiptDraftStore:
    from homeassistant.helpers.storage import Store
    from .store_helpers import store_load_lock
    async with store_load_lock(bridge, "receipt_drafts"):
        store = getattr(bridge, "_receipt_drafts_v195", None)
        if store is None:
            store = ReceiptDraftStore(Store(bridge.hass, 1, f"cook4me.{bridge.entry.entry_id}.receipt_drafts"))
            bridge._receipt_drafts_v195 = store
        return store
