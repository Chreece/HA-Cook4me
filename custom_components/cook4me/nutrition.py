from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import re
import unicodedata
from typing import Any
from uuid import uuid4
import urllib.error
import urllib.parse
import urllib.request

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_MAX_GENERIC_ITEMS = 5000
_MAX_STOCK_LOTS = 5000
_FDC_BASE = "https://api.nal.usda.gov/fdc/v1/foods/search"
_DEMO_KEY = "DEMO_KEY"

NUTRIENT_KEYS = (
    "energyKcal",
    "energyKJ",
    "protein",
    "carbohydrates",
    "sugars",
    "fat",
    "saturatedFat",
    "fiber",
    "salt",
    "sodium",
)

_MASS_SCALE = {"mg": 0.001, "g": 1.0, "kg": 1000.0}
_VOLUME_SCALE = {"ul": 0.001, "ml": 1.0, "cl": 10.0, "dl": 100.0, "l": 1000.0}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


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


def _unit(value: Any) -> str:
    text = unicodedata.normalize("NFKC", _text(value).casefold())
    return text.replace("ℓ", "l").replace("µ", "u").replace("μ", "u").replace(" ", "")


def _dimension(unit: Any) -> str:
    token = _unit(unit)
    if token in _MASS_SCALE:
        return "mass"
    if token in _VOLUME_SCALE:
        return "volume"
    return ""


def convert_amount(value: Any, from_unit: Any, to_unit: Any) -> float | None:
    amount = _number(value)
    if amount is None:
        return None
    source = _unit(from_unit)
    target = _unit(to_unit)
    if source == target:
        return amount
    source_dim = _dimension(source)
    target_dim = _dimension(target)
    if not source_dim or source_dim != target_dim:
        return None
    table = _MASS_SCALE if source_dim == "mass" else _VOLUME_SCALE
    return amount * table[source] / table[target]


def ingredient_identity(item: Any) -> str:
    if not isinstance(item, dict):
        name = _norm(item)
        return f"n:{name}" if name else ""
    key = _text(item.get("key") or item.get("foodKey"))
    if key:
        return f"k:{key}"
    name = _norm(item.get("name") or item.get("foodName"))
    return f"n:{name}" if name else ""


def normalize_nutrition(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    basis_quantity = _number(value.get("basisQuantity")) or 100.0
    basis_unit = _unit(value.get("basisUnit") or "g")
    if basis_unit not in {"g", "ml"} or basis_quantity <= 0:
        return None
    raw_values = value.get("values") if isinstance(value.get("values"), dict) else value
    values: dict[str, float] = {}
    for key in NUTRIENT_KEYS:
        number = _number(raw_values.get(key)) if isinstance(raw_values, dict) else None
        if number is not None:
            values[key] = number
    if not values:
        return None
    out: dict[str, Any] = {
        "basisQuantity": basis_quantity,
        "basisUnit": basis_unit,
        "values": values,
    }
    for key in ("source", "sourceId", "label", "confidence"):
        text = _text(value.get(key))
        if text:
            out[key] = text
    return out


def nutrition_for_amount(profile: Any, quantity: Any, unit: Any) -> dict[str, float] | None:
    normalized = normalize_nutrition(profile)
    if normalized is None:
        return None
    converted = convert_amount(quantity, unit, normalized["basisUnit"])
    if converted is None:
        return None
    factor = converted / float(normalized["basisQuantity"])
    return {key: value * factor for key, value in normalized["values"].items()}


def _rounded_values(values: dict[str, float]) -> dict[str, float]:
    out: dict[str, float] = {}
    for key, value in values.items():
        if not math.isfinite(float(value)):
            continue
        digits = 1 if key in {"energyKcal", "energyKJ"} else 2
        out[key] = round(float(value), digits)
    return out


def _add_values(target: dict[str, float], values: dict[str, float] | None) -> None:
    if not values:
        return
    for key, value in values.items():
        target[key] = target.get(key, 0.0) + float(value)


def nutrition_from_open_food_facts(
    product: Any,
    *,
    barcode: str = "",
    product_unit: str = "",
) -> dict[str, Any] | None:
    if not isinstance(product, dict):
        return None
    nutriments = product.get("nutriments") if isinstance(product.get("nutriments"), dict) else {}
    if not nutriments:
        return None

    def pick(*keys: str) -> float | None:
        for key in keys:
            value = _number(nutriments.get(key))
            if value is not None:
                return value
        return None

    values: dict[str, float] = {}
    mapping = {
        "energyKcal": ("energy-kcal_100g",),
        "energyKJ": ("energy-kj_100g", "energy_100g"),
        "protein": ("proteins_100g", "protein_100g"),
        "carbohydrates": ("carbohydrates_100g",),
        "sugars": ("sugars_100g",),
        "fat": ("fat_100g",),
        "saturatedFat": ("saturated-fat_100g",),
        "fiber": ("fiber_100g", "fibre_100g"),
        "salt": ("salt_100g",),
        "sodium": ("sodium_100g",),
    }
    for target, source_keys in mapping.items():
        value = pick(*source_keys)
        if value is not None:
            values[target] = value
    if "energyKcal" not in values and "energyKJ" in values:
        values["energyKcal"] = values["energyKJ"] / 4.184
    if "energyKJ" not in values and "energyKcal" in values:
        values["energyKJ"] = values["energyKcal"] * 4.184
    if "salt" not in values and "sodium" in values:
        values["salt"] = values["sodium"] * 2.5
    if "sodium" not in values and "salt" in values:
        values["sodium"] = values["salt"] / 2.5
    if not values:
        return None

    basis_unit = "ml" if _dimension(product_unit) == "volume" else "g"
    return normalize_nutrition(
        {
            "basisQuantity": 100,
            "basisUnit": basis_unit,
            "values": values,
            "source": "open_food_facts",
            "sourceId": barcode,
            "label": product.get("product_name") or product.get("generic_name") or barcode,
            "confidence": "exact_product",
        }
    )


def _fdc_candidate_score(query: str, food: dict[str, Any]) -> float:
    wanted = _norm(query)
    description = _norm(food.get("description"))
    if not wanted or not description:
        return 0.0
    if description == wanted:
        text_score = 1.0
    elif description.startswith(wanted + " ") or description.startswith(wanted + ","):
        text_score = 0.96
    else:
        wanted_tokens = set(wanted.split())
        description_tokens = set(description.split())
        if wanted_tokens and wanted_tokens <= description_tokens:
            text_score = 0.88
        else:
            overlap = len(wanted_tokens & description_tokens) / max(1, len(wanted_tokens))
            text_score = 0.75 * overlap
    data_type = _text(food.get("dataType")).casefold()
    type_bonus = {
        "foundation": 0.03,
        "sr legacy": 0.02,
        "survey (fndds)": 0.01,
    }.get(data_type, 0.0)
    return min(1.0, text_score + type_bonus)


def _fdc_value(food: dict[str, Any], *patterns: str, unit: str | None = None) -> float | None:
    nutrients = food.get("foodNutrients") if isinstance(food.get("foodNutrients"), list) else []
    for row in nutrients:
        if not isinstance(row, dict):
            continue
        name = _norm(row.get("nutrientName") or row.get("name"))
        unit_name = _text(row.get("unitName") or row.get("unit")).casefold()
        if unit is not None and unit_name != unit.casefold():
            continue
        if any(pattern in name for pattern in patterns):
            value = _number(row.get("value") if "value" in row else row.get("amount"))
            if value is not None:
                return value
    return None


def nutrition_from_fdc_food(food: Any, *, query: str = "") -> dict[str, Any] | None:
    if not isinstance(food, dict):
        return None
    kcal = _fdc_value(food, "energy", unit="kcal")
    kj = _fdc_value(food, "energy", unit="kj")
    values = {
        "energyKcal": kcal,
        "energyKJ": kj,
        "protein": _fdc_value(food, "protein"),
        "carbohydrates": _fdc_value(food, "carbohydrate by difference", "carbohydrate"),
        "sugars": _fdc_value(food, "total sugars", "sugars total"),
        "fat": _fdc_value(food, "total lipid fat", "total fat"),
        "saturatedFat": _fdc_value(food, "fatty acids total saturated", "saturated fat"),
        "fiber": _fdc_value(food, "fiber total dietary", "dietary fiber"),
    }
    sodium_mg = _fdc_value(food, "sodium na", "sodium", unit="mg")
    if sodium_mg is None:
        sodium_g = _fdc_value(food, "sodium na", "sodium", unit="g")
    else:
        sodium_g = sodium_mg / 1000.0
    if sodium_g is not None:
        values["sodium"] = sodium_g
        values["salt"] = sodium_g * 2.5
    values = {key: value for key, value in values.items() if value is not None}
    if "energyKcal" not in values and "energyKJ" in values:
        values["energyKcal"] = values["energyKJ"] / 4.184
    if "energyKJ" not in values and "energyKcal" in values:
        values["energyKJ"] = values["energyKcal"] * 4.184
    if not values:
        return None
    return normalize_nutrition(
        {
            "basisQuantity": 100,
            "basisUnit": "g",
            "values": values,
            "source": "usda_fdc",
            "sourceId": food.get("fdcId"),
            "label": food.get("description") or query,
            "confidence": "generic_reference",
        }
    )


def select_fdc_candidate(query: str, foods: Any) -> tuple[dict[str, Any] | None, float]:
    if not isinstance(foods, list):
        return None, 0.0
    scored: list[tuple[float, dict[str, Any]]] = []
    for food in foods:
        if not isinstance(food, dict):
            continue
        score = _fdc_candidate_score(query, food)
        if score > 0:
            scored.append((score, food))
    if not scored:
        return None, 0.0
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1], scored[0][0]


def lookup_food_data_central(query: str, api_key: str = _DEMO_KEY, timeout: int = 20) -> dict[str, Any]:
    query = _text(query)
    if not query:
        return {"ok": False, "reason": "empty_query"}
    body = json.dumps(
        {
            "query": query,
            "pageSize": 12,
            "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
        }
    ).encode("utf-8")
    url = f"{_FDC_BASE}?{urllib.parse.urlencode({'api_key': api_key or _DEMO_KEY})}"
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "reason": f"http_{exc.code}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "reason": type(exc).__name__}
    food, score = select_fdc_candidate(query, payload.get("foods"))
    if food is None or score < 0.86:
        return {"ok": False, "reason": "ambiguous", "confidence": round(score, 3)}
    nutrition = nutrition_from_fdc_food(food, query=query)
    if nutrition is None:
        return {"ok": False, "reason": "no_nutrition", "confidence": round(score, 3)}
    return {
        "ok": True,
        "query": query,
        "confidence": round(score, 3),
        "fdcId": food.get("fdcId"),
        "description": food.get("description"),
        "dataType": food.get("dataType"),
        "nutrition": nutrition,
    }


def _recipe_amount(item: dict[str, Any]) -> tuple[float | None, str]:
    amount = _number(item.get("quantity"))
    unit = _unit(item.get("unit"))
    if amount is not None:
        return amount, unit
    weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
    return _number(weight.get("quantity")), _unit(weight.get("unit"))


def _recipe_servings(recipe: dict[str, Any]) -> float | None:
    candidates = [recipe.get("servings"), recipe.get("groupSize")]
    yield_data = recipe.get("yield") if isinstance(recipe.get("yield"), dict) else {}
    candidates.extend([yield_data.get("quantity"), yield_data.get("quantityDisplay")])
    for value in candidates:
        number = _number(value)
        if number is not None and number > 0:
            return number
    return None


def _inventory_rows(inventory: Any) -> list[dict[str, Any]]:
    return [row for row in inventory if isinstance(row, dict)] if isinstance(inventory, list) else []


def _find_inventory_row(inventory: Any, ingredient: dict[str, Any]) -> dict[str, Any] | None:
    wanted = ingredient_identity(ingredient)
    if wanted:
        for row in _inventory_rows(inventory):
            if ingredient_identity(row) == wanted:
                return row
    return None


def _generic_profile(generic: dict[str, Any], identity: str) -> dict[str, Any] | None:
    row = generic.get(identity) if isinstance(generic, dict) else None
    if isinstance(row, dict) and isinstance(row.get("nutrition"), dict):
        return normalize_nutrition(row["nutrition"])
    return normalize_nutrition(row)


def _stock_lots_for_identity(stock_lots: dict[str, Any], identity: str) -> list[dict[str, Any]]:
    rows = stock_lots.get(identity) if isinstance(stock_lots, dict) else None
    if not isinstance(rows, list):
        return []
    def sort_key(row: dict[str, Any]) -> tuple[bool, str, str]:
        stamp = _text(row.get("bestBefore"))
        return (not bool(stamp), stamp or "9999-12-31", _text(row.get("addedAt")))
    return sorted((deepcopy(row) for row in rows if isinstance(row, dict)), key=sort_key)


def calculate_recipe_nutrition(
    recipe: dict[str, Any],
    inventory: Any,
    *,
    generic: dict[str, Any] | None = None,
    stock_lots: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generic = generic or {}
    stock_lots = stock_lots or {}
    totals: dict[str, float] = {}
    details: list[dict[str, Any]] = []
    coverage_fractions: list[float] = []
    source_kinds: set[str] = set()

    for ingredient in recipe.get("ingredients") or []:
        if not isinstance(ingredient, dict):
            continue
        identity = ingredient_identity(ingredient)
        name = _text(ingredient.get("foodName") or ingredient.get("name"))
        amount, unit = _recipe_amount(ingredient)
        detail: dict[str, Any] = {"identity": identity, "name": name, "quantity": amount, "unit": unit}
        if amount is None or not unit:
            detail["coverage"] = 0.0
            detail["reason"] = "amount_or_unit_unknown"
            details.append(detail)
            continue

        row = _find_inventory_row(inventory, ingredient)
        exact_fraction = 0.0
        exact_values: dict[str, float] = {}
        exact_sources: list[dict[str, Any]] = []
        if row and not row.get("unlimited"):
            stock_unit = _unit(row.get("unit"))
            required_stock = convert_amount(amount, unit, stock_unit) if stock_unit else None
            if required_stock is not None and required_stock > 0:
                remaining = required_stock
                for lot in _stock_lots_for_identity(stock_lots, identity):
                    lot_amount = _number(lot.get("quantity")) or 0.0
                    lot_unit = _unit(lot.get("unit"))
                    available = convert_amount(lot_amount, lot_unit, stock_unit)
                    if available is None or available <= 0 or remaining <= 1e-12:
                        continue
                    take = min(available, remaining)
                    values = nutrition_for_amount(lot.get("nutrition"), take, stock_unit)
                    if values is None:
                        continue
                    _add_values(exact_values, values)
                    exact_fraction += take / required_stock
                    remaining -= take
                    source_kinds.add("exact_product")
                    exact_sources.append(
                        {
                            "type": "exact_product",
                            "barcode": lot.get("barcode"),
                            "productName": lot.get("productName"),
                            "quantity": round(take, 6),
                            "unit": stock_unit,
                            "bestBefore": lot.get("bestBefore"),
                        }
                    )

        exact_fraction = min(1.0, max(0.0, exact_fraction))
        _add_values(totals, exact_values)
        uncovered_fraction = max(0.0, 1.0 - exact_fraction)
        generic_profile = _generic_profile(generic, identity)
        generic_values = None
        if uncovered_fraction > 1e-9 and generic_profile is not None:
            generic_values = nutrition_for_amount(generic_profile, amount * uncovered_fraction, unit)
            if generic_values is not None:
                _add_values(totals, generic_values)
                source_kinds.add("generic_reference")
        generic_fraction = uncovered_fraction if generic_values is not None else 0.0
        coverage = min(1.0, exact_fraction + generic_fraction)
        coverage_fractions.append(coverage)
        detail["coverage"] = round(coverage, 3)
        detail["sources"] = exact_sources
        if generic_fraction > 0:
            detail["sources"].append(
                {
                    "type": "generic_reference",
                    "quantityFraction": round(generic_fraction, 3),
                    "source": generic_profile.get("source"),
                    "label": generic_profile.get("label"),
                }
            )
        if coverage < 1.0:
            detail["reason"] = "nutrition_reference_missing_or_incompatible_unit"
        details.append(detail)

    coverage = sum(coverage_fractions) / len(coverage_fractions) if coverage_fractions else 0.0
    totals_rounded = _rounded_values(totals)
    servings = _recipe_servings(recipe)
    per_serving = (
        _rounded_values({key: value / servings for key, value in totals.items()})
        if servings and servings > 0
        else {}
    )
    return {
        "totals": totals_rounded,
        "perServing": per_serving,
        "servings": servings,
        "coverage": round(coverage, 3),
        "fullyCovered": bool(coverage_fractions) and all(value >= 0.999 for value in coverage_fractions),
        "estimated": "generic_reference" in source_kinds or coverage < 0.999,
        "sourceKinds": sorted(source_kinds),
        "ingredients": details,
    }


class Cook4MeNutritionStore:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.nutrition"
        )
        self._loaded = False
        self._data: dict[str, Any] = {"generic": {}, "stockLots": {}}

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            generic = saved.get("generic") if isinstance(saved.get("generic"), dict) else {}
            stock_lots = saved.get("stockLots") if isinstance(saved.get("stockLots"), dict) else {}
            self._data = {"generic": generic, "stockLots": stock_lots}
        self._loaded = True

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    @property
    def generic(self) -> dict[str, Any]:
        return deepcopy(self._data.get("generic") or {})

    @property
    def stock_lots(self) -> dict[str, Any]:
        return deepcopy(self._data.get("stockLots") or {})

    @property
    def generic_count(self) -> int:
        return len(self._data.get("generic") or {})

    def get_generic(self, identity: str) -> dict[str, Any] | None:
        row = (self._data.get("generic") or {}).get(identity)
        return deepcopy(row) if isinstance(row, dict) else None

    async def async_set_generic(
        self,
        identity: str,
        ingredient: dict[str, Any],
        nutrition: dict[str, Any],
        *,
        query: str = "",
        confidence: Any = None,
    ) -> dict[str, Any]:
        profile = normalize_nutrition(nutrition)
        if not identity or profile is None:
            raise ValueError("Valid ingredient identity and nutrition are required")
        row = {
            "ingredient": {
                **({"key": _text(ingredient.get("key") or ingredient.get("foodKey"))} if ingredient.get("key") or ingredient.get("foodKey") else {}),
                "name": _text(ingredient.get("name") or ingredient.get("foodName")),
            },
            "nutrition": profile,
            "query": _text(query),
            "confidence": _number(confidence),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        generic = self._data.setdefault("generic", {})
        if identity not in generic and len(generic) >= _MAX_GENERIC_ITEMS:
            oldest = next(iter(generic))
            generic.pop(oldest, None)
        generic[identity] = row
        await self._save()
        return deepcopy(row)

    async def async_add_stock_lot(
        self,
        ingredient: dict[str, Any],
        *,
        quantity: Any,
        unit: str,
        best_before: str = "",
        nutrition: Any,
        barcode: str = "",
        product_name: str = "",
        brand: str = "",
    ) -> dict[str, Any] | None:
        identity = ingredient_identity(ingredient)
        amount = _number(quantity)
        profile = normalize_nutrition(nutrition)
        if not identity or amount is None or amount <= 0 or profile is None:
            return None
        record = {
            "id": str(uuid4()),
            "quantity": amount,
            "unit": _unit(unit),
            "bestBefore": _text(best_before),
            "nutrition": profile,
            "barcode": _text(barcode),
            "productName": _text(product_name),
            "brand": _text(brand),
            "addedAt": datetime.now(timezone.utc).isoformat(),
        }
        lots = self._data.setdefault("stockLots", {}).setdefault(identity, [])
        lots.append(record)
        if sum(len(rows) for rows in self._data["stockLots"].values() if isinstance(rows, list)) > _MAX_STOCK_LOTS:
            for key in list(self._data["stockLots"]):
                rows = self._data["stockLots"].get(key)
                if isinstance(rows, list) and rows:
                    rows.pop(0)
                    if not rows:
                        self._data["stockLots"].pop(key, None)
                    break
        await self._save()
        return deepcopy(record)

    def _inventory_capacity(self, row: dict[str, Any]) -> tuple[str, dict[str, float]]:
        unit = _unit(row.get("unit"))
        capacities: dict[str, float] = {}
        if row.get("unlimited"):
            return unit, capacities
        lots = row.get("lots") if isinstance(row.get("lots"), list) else []
        if lots:
            for lot in lots:
                if not isinstance(lot, dict):
                    continue
                amount = _number(lot.get("quantity"))
                if amount is None or amount <= 0:
                    continue
                stamp = _text(lot.get("bestBefore"))
                capacities[stamp] = capacities.get(stamp, 0.0) + amount
        else:
            amount = _number(row.get("quantity"))
            if amount is not None and amount > 0:
                capacities[_text(row.get("bestBefore"))] = amount
        return unit, capacities

    async def async_reconcile_inventory(self, inventory: Any) -> None:
        by_identity = {
            ingredient_identity(row): row
            for row in _inventory_rows(inventory)
            if ingredient_identity(row)
        }
        changed = False
        stock_lots = self._data.setdefault("stockLots", {})
        for identity in list(stock_lots):
            row = by_identity.get(identity)
            if row is None or row.get("unlimited"):
                stock_lots.pop(identity, None)
                changed = True
                continue
            target_unit, capacities = self._inventory_capacity(row)
            kept: list[dict[str, Any]] = []
            records = stock_lots.get(identity) if isinstance(stock_lots.get(identity), list) else []
            for record in sorted(records, key=lambda item: (_text(item.get("bestBefore")) or "9999-12-31", _text(item.get("addedAt")))):
                stamp = _text(record.get("bestBefore"))
                capacity = capacities.get(stamp, 0.0)
                if capacity <= 1e-12:
                    changed = True
                    continue
                converted = convert_amount(record.get("quantity"), record.get("unit"), target_unit)
                if converted is None or converted <= 0:
                    changed = True
                    continue
                keep_amount = min(converted, capacity)
                capacities[stamp] = capacity - keep_amount
                next_record = deepcopy(record)
                next_record["quantity"] = round(keep_amount, 9)
                next_record["unit"] = target_unit
                kept.append(next_record)
                if abs(keep_amount - converted) > 1e-9 or _unit(record.get("unit")) != target_unit:
                    changed = True
            if kept:
                stock_lots[identity] = kept
            else:
                stock_lots.pop(identity, None)
                changed = True
        if changed:
            await self._save()

    async def async_consume_report(self, report: Any) -> dict[str, Any]:
        deducted = report.get("deductedLots") if isinstance(report, dict) else None
        if not isinstance(deducted, list):
            return {"totals": {}, "coverage": 0.0, "sourceKinds": []}
        totals: dict[str, float] = {}
        fractions: list[float] = []
        stock_lots = self._data.setdefault("stockLots", {})
        generic = self._data.get("generic") or {}
        changed = False
        for request in deducted:
            if not isinstance(request, dict):
                continue
            identity = _text(request.get("identity"))
            amount = _number(request.get("quantity"))
            unit = _unit(request.get("unit"))
            stamp = _text(request.get("bestBefore"))
            if not identity or amount is None or amount <= 0 or not unit:
                continue
            remaining = amount
            exact_covered = 0.0
            records = stock_lots.get(identity) if isinstance(stock_lots.get(identity), list) else []
            kept: list[dict[str, Any]] = []
            for record in records:
                converted = convert_amount(record.get("quantity"), record.get("unit"), unit)
                if converted is None or converted <= 0:
                    kept.append(record)
                    continue
                if stamp and _text(record.get("bestBefore")) != stamp:
                    kept.append(record)
                    continue
                take = min(converted, remaining) if remaining > 1e-12 else 0.0
                if take <= 0:
                    kept.append(record)
                    continue
                values = nutrition_for_amount(record.get("nutrition"), take, unit)
                if values is not None:
                    _add_values(totals, values)
                    exact_covered += take
                remaining -= take
                left = converted - take
                if left > 1e-9:
                    next_record = deepcopy(record)
                    next_record["quantity"] = round(left, 9)
                    next_record["unit"] = unit
                    kept.append(next_record)
                changed = True
            if kept:
                stock_lots[identity] = kept
            else:
                stock_lots.pop(identity, None)
            generic_profile = _generic_profile(generic, identity)
            generic_covered = 0.0
            if remaining > 1e-9 and generic_profile is not None:
                values = nutrition_for_amount(generic_profile, remaining, unit)
                if values is not None:
                    _add_values(totals, values)
                    generic_covered = remaining
            fractions.append(min(1.0, (exact_covered + generic_covered) / amount))
        if changed:
            await self._save()
        coverage = sum(fractions) / len(fractions) if fractions else 0.0
        kinds = []
        if totals:
            kinds.append("exact_product_or_generic")
        return {
            "totals": _rounded_values(totals),
            "coverage": round(coverage, 3),
            "sourceKinds": kinds,
        }


async def nutrition_store_for_bridge(bridge: Any) -> Cook4MeNutritionStore:
    store = getattr(bridge, "_nutrition_store", None)
    if store is None:
        store = Cook4MeNutritionStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._nutrition_store = store
    return store


DEMO_KEY = _DEMO_KEY
