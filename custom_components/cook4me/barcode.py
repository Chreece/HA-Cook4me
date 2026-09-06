from __future__ import annotations

from copy import deepcopy
import json
import math
import re
import time
import unicodedata
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_MAX_MAPPINGS = 1000
_OFF_BASE = "https://world.openfoodfacts.org/api/v3/product"
_OFF_FIELDS = (
    "code,product_name,generic_name,quantity,product_quantity,"
    "product_quantity_unit,brands,categories,categories_tags"
)
_USER_AGENT = "HA-Cook4me/2026.9.6.22 (https://github.com/Chreece/HA-Cook4me)"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_barcode(value: Any) -> str:
    code = re.sub(r"[\s-]+", "", str(value or "").strip())
    if not code.isdigit() or len(code) not in {8, 12, 13, 14}:
        raise ValueError("Barcode must be an EAN-8, UPC-A, EAN-13, or GTIN-14 number")
    return code


def _norm(value: Any) -> str:
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


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def parse_package_quantity(value: Any) -> tuple[float | None, str]:
    """Parse language-neutral SI/count package quantities from product metadata."""
    text = _text(value).replace("×", "x")
    if not text:
        return None, ""
    number = r"(\d+(?:[.,]\d+)?)"
    unit = r"(kg|mg|g|ml|cl|dl|l|pcs?|pc)"
    multi = re.search(rf"{number}\s*x\s*{number}\s*{unit}\b", text, re.IGNORECASE)
    if multi:
        packs = _number(multi.group(1))
        each = _number(multi.group(2))
        if packs is not None and each is not None:
            return packs * each, multi.group(3).lower()
    simple = re.search(rf"{number}\s*{unit}\b", text, re.IGNORECASE)
    if simple:
        return _number(simple.group(1)), simple.group(2).lower()
    return None, ""


def normalize_openfoodfacts_payload(code: str, payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"barcode": code, "found": False}
    product = payload.get("product") if isinstance(payload.get("product"), dict) else {}
    if not product:
        return {"barcode": code, "found": False}

    product_name = _text(product.get("product_name"))
    generic_name = _text(product.get("generic_name"))
    brand = _text(product.get("brands"))
    raw_quantity = _text(product.get("quantity"))
    quantity = _number(product.get("product_quantity"))
    unit = _text(product.get("product_quantity_unit")).lower()
    if quantity is None or not unit:
        parsed_quantity, parsed_unit = parse_package_quantity(raw_quantity)
        if quantity is None:
            quantity = parsed_quantity
        if not unit:
            unit = parsed_unit

    categories: list[str] = []
    raw_categories = product.get("categories_tags")
    if isinstance(raw_categories, list):
        for value in raw_categories:
            text = _text(value)
            if not text:
                continue
            if ":" in text:
                text = text.split(":", 1)[1].replace("-", " ")
            categories.append(text)
    category_text = _text(product.get("categories"))
    if category_text:
        categories.extend(part.strip() for part in category_text.split(",") if part.strip())

    return {
        "barcode": code,
        "found": True,
        "name": generic_name or product_name or code,
        "productName": product_name,
        "genericName": generic_name,
        "brand": brand,
        "quantity": quantity,
        "unit": unit,
        "rawQuantity": raw_quantity,
        "categories": list(dict.fromkeys(categories))[:80],
        "source": "open_food_facts",
    }


def lookup_open_food_facts(code: str, timeout: int = 20) -> dict[str, Any]:
    code = normalize_barcode(code)
    query = urllib.parse.urlencode({"fields": _OFF_FIELDS})
    url = f"{_OFF_BASE}/{urllib.parse.quote(code, safe='')}?{query}"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": _USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"barcode": code, "found": False, "source": "open_food_facts"}
        raise RuntimeError(f"Product barcode lookup failed with HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Product barcode lookup failed: {type(exc).__name__}") from None
    return normalize_openfoodfacts_payload(code, payload)


def _tokens(value: Any) -> set[str]:
    return {token for token in _norm(value).split() if len(token) >= 2}


def _near_token(left: str, right: str) -> bool:
    """Return true for a conservative short suffix/prefix variation.

    This is intentionally language-neutral and suggestion-only. It catches forms such
    as German ``Dattel`` / ``Datteln`` without introducing language-specific stemming.
    """
    if len(left) < 4 or len(right) < 4 or abs(len(left) - len(right)) > 2:
        return False
    return left.startswith(right) or right.startswith(left)


def _near_token_set(candidate_tokens: set[str], source_tokens: set[str]) -> bool:
    if not candidate_tokens or not source_tokens:
        return False
    return all(any(_near_token(candidate, source) for source in source_tokens) for candidate in candidate_tokens)


def suggest_catalog_matches(
    product: dict[str, Any], catalog: list[dict[str, Any]], *, limit: int = 12
) -> list[dict[str, Any]]:
    generic = _norm(product.get("genericName"))
    product_name = _norm(product.get("productName") or product.get("name"))
    generic_tokens = _tokens(generic)
    product_tokens = _tokens(product_name)
    category_names = {_norm(value) for value in product.get("categories") or [] if _norm(value)}

    ranked: list[dict[str, Any]] = []
    for row in catalog:
        if not isinstance(row, dict):
            continue
        name = _text(row.get("name"))
        candidate = _norm(name)
        if not candidate:
            continue
        candidate_tokens = _tokens(candidate)
        score = 0.0
        reason = ""
        if generic and candidate == generic:
            score, reason = 1.0, "generic_exact"
        elif generic_tokens and candidate_tokens and candidate_tokens <= generic_tokens:
            score, reason = 0.98, "generic_tokens"
        elif product_name and candidate == product_name:
            score, reason = 0.97, "product_exact"
        elif product_tokens and candidate_tokens and candidate_tokens <= product_tokens:
            score, reason = 0.95, "product_tokens"
        elif candidate in category_names:
            score, reason = 0.94, "category_exact"
        elif _near_token_set(candidate_tokens, generic_tokens) or _near_token_set(candidate_tokens, product_tokens):
            score, reason = 0.93, "near_token"
        elif product_tokens and candidate_tokens:
            union = product_tokens | candidate_tokens
            overlap = len(product_tokens & candidate_tokens) / len(union) if union else 0.0
            if overlap >= 0.5:
                score, reason = min(0.89, 0.72 + overlap * 0.17), "token_similarity"
        if score <= 0:
            continue
        ranked.append(
            {
                "ingredient": {
                    **({"key": str(row["key"])} if row.get("key") else {}),
                    "name": name,
                },
                "score": round(score, 3),
                "reason": reason,
            }
        )
    ranked.sort(key=lambda item: (-float(item["score"]), _norm(item["ingredient"]["name"])))
    return ranked[: max(1, min(int(limit), 30))]


def confident_match(suggestions: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not suggestions:
        return None
    first = suggestions[0]
    score = float(first.get("score") or 0)
    if score < 0.95:
        return None
    if len(suggestions) > 1:
        second = float(suggestions[1].get("score") or 0)
        if score - second < 0.02:
            return None
    return deepcopy(first)


class Cook4MeBarcodeMappingStore:
    """Remember barcode -> Cook4Me ingredient/package mappings per config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.barcode_mappings"
        )
        self._data: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            self._data = {
                str(code): deepcopy(row)
                for code, row in saved.items()
                if isinstance(row, dict)
            }

    def get(self, code: str) -> dict[str, Any] | None:
        row = self._data.get(normalize_barcode(code))
        return deepcopy(row) if isinstance(row, dict) else None

    async def async_set(self, code: str, mapping: dict[str, Any]) -> dict[str, Any]:
        code = normalize_barcode(code)
        ingredient = mapping.get("ingredient") if isinstance(mapping.get("ingredient"), dict) else {}
        name = _text(ingredient.get("name"))
        if not name:
            raise ValueError("Mapped Cook4Me ingredient name is required")
        row = {
            "barcode": code,
            "ingredient": {
                **({"key": _text(ingredient.get("key"))} if _text(ingredient.get("key")) else {}),
                "name": name,
            },
            "quantity": _number(mapping.get("quantity")),
            "unit": _text(mapping.get("unit")),
            "productName": _text(mapping.get("productName")),
            "brand": _text(mapping.get("brand")),
            "updatedAt": time.time(),
        }
        self._data[code] = row
        if len(self._data) > _MAX_MAPPINGS:
            oldest = sorted(
                self._data,
                key=lambda key: float(self._data[key].get("updatedAt") or 0),
            )[: len(self._data) - _MAX_MAPPINGS]
            for key in oldest:
                self._data.pop(key, None)
        await self._store.async_save(deepcopy(self._data))
        return deepcopy(row)
