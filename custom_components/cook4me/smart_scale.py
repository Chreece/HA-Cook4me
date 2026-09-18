from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
import re
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .inventory import inventory_identity, normalize_inventory
from .today_logic import recipe_identity

_STORAGE_VERSION = 1
_MAX_CONTAINERS = 50
_MAX_SESSIONS = 24
_MAX_MEASUREMENTS = 80

_MASS_TO_GRAMS: dict[str, float] = {
    "ug": 0.000001,
    "mcg": 0.000001,
    "mg": 0.001,
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
    "oz": 28.349523125,
    "ounce": 28.349523125,
    "ounces": 28.349523125,
    "lb": 453.59237,
    "lbs": 453.59237,
    "pound": 453.59237,
    "pounds": 453.59237,
}


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _unit_token(value: Any) -> str:
    return (
        _text(value)
        .casefold()
        .replace("µ", "u")
        .replace("μ", "u")
        .replace("㎏", "kg")
        .replace("℔", "lb")
        .replace(".", "")
        .replace(" ", "")
    )


def mass_to_grams(value: Any, unit: Any) -> float | None:
    """Convert a proven mass unit to grams without guessing density."""
    number = _number(value)
    factor = _MASS_TO_GRAMS.get(_unit_token(unit))
    if number is None or factor is None:
        return None
    return number * factor


def grams_to_mass(value: Any, unit: Any) -> float | None:
    """Convert grams to a proven mass unit."""
    grams = _number(value)
    factor = _MASS_TO_GRAMS.get(_unit_token(unit))
    if grams is None or factor is None or factor <= 0:
        return None
    return grams / factor


def scale_reading(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """Return one Home Assistant weight sensor as a normalized gram reading."""
    wanted = _text(entity_id)
    if not wanted:
        return {"entityId": "", "available": False, "reason": "not_configured"}
    state = hass.states.get(wanted)
    if state is None:
        return {"entityId": wanted, "available": False, "reason": "entity_not_found"}
    unit = _text(state.attributes.get("unit_of_measurement"))
    grams = mass_to_grams(state.state, unit)
    available = grams is not None and str(state.state).lower() not in {"unknown", "unavailable"}
    return {
        "entityId": wanted,
        "name": _text(state.attributes.get("friendly_name")) or wanted,
        "available": bool(available),
        "state": state.state,
        "unit": unit,
        "grams": round(float(grams), 6) if grams is not None else None,
        "deviceClass": _text(state.attributes.get("device_class")),
        "lastChanged": state.last_changed.isoformat() if getattr(state, "last_changed", None) else "",
        **({} if available else {"reason": "unsupported_or_unavailable"}),
    }


def scale_entity_candidates(hass: HomeAssistant) -> list[dict[str, Any]]:
    """List numeric sensor entities whose unit is explicitly a mass unit."""
    rows: list[dict[str, Any]] = []
    for state in hass.states.async_all():
        entity_id = str(getattr(state, "entity_id", "") or "")
        if not entity_id.startswith("sensor."):
            continue
        unit = _text(state.attributes.get("unit_of_measurement"))
        if _MASS_TO_GRAMS.get(_unit_token(unit)) is None:
            continue
        numeric = _number(state.state)
        rows.append(
            {
                "entityId": entity_id,
                "name": _text(state.attributes.get("friendly_name")) or entity_id,
                "unit": unit,
                "deviceClass": _text(state.attributes.get("device_class")),
                "available": numeric is not None and str(state.state).lower() not in {"unknown", "unavailable"},
                "grams": round(float(mass_to_grams(numeric, unit) or 0.0), 6)
                if numeric is not None
                else None,
            }
        )
    rows.sort(key=lambda row: (not bool(row["available"]), row["name"].casefold(), row["entityId"]))
    return rows


def recipe_aliases(recipe: Any) -> list[str]:
    if not isinstance(recipe, dict):
        return []
    aliases: list[str] = []
    for key in (
        "groupingFunctionalId",
        "groupingId",
        "recipeFunctionalId",
        "variantFunctionalId",
        "functionalId",
        "id",
        "searchVariantId",
        "displayVariantId",
        "sendVariantId",
    ):
        value = _text(recipe.get(key))
        if value:
            aliases.append(f"{key}:{value}")
    primary = recipe_identity(recipe)
    if primary:
        aliases.append(primary)
    title = _text(recipe.get("title")).casefold()
    if title:
        aliases.append(f"title:{title}")
    return list(dict.fromkeys(aliases))


def _recipe_amount(row: dict[str, Any]) -> tuple[float | None, str]:
    amount = _number(row.get("quantity"))
    unit = _text(row.get("unit"))
    if amount is not None:
        return amount, unit
    weight = row.get("weight") if isinstance(row.get("weight"), dict) else {}
    return _number(weight.get("quantity")), _text(weight.get("unit"))


def apply_recipe_measurements(recipe: dict[str, Any], session: Any) -> dict[str, Any]:
    """Overlay actual weighed ingredient mass on a recipe copy.

    The original SEB identity/send fields are untouched. Only ingredient quantities
    recorded by the user are replaced, so post-cook stock confirmation defaults to
    what physically went into the dish.
    """
    result = deepcopy(recipe)
    if not isinstance(session, dict):
        return result
    ingredients = result.get("ingredients")
    if not isinstance(ingredients, list):
        return result
    measurements = [
        row for row in session.get("measurements") or []
        if isinstance(row, dict) and _number(row.get("grams")) is not None
    ]
    for measurement in measurements:
        grams = _number(measurement.get("grams"))
        if grams is None:
            continue
        index = measurement.get("ingredientIndex")
        target_index: int | None = None
        try:
            candidate = int(index)
            if 0 <= candidate < len(ingredients) and isinstance(ingredients[candidate], dict):
                target_index = candidate
        except (TypeError, ValueError):
            pass
        if target_index is None:
            wanted = _text(measurement.get("ingredientIdentity"))
            if wanted:
                for candidate, ingredient in enumerate(ingredients):
                    if isinstance(ingredient, dict) and inventory_identity(ingredient) == wanted:
                        target_index = candidate
                        break
        if target_index is None:
            continue
        ingredient = dict(ingredients[target_index])
        original_amount, original_unit = _recipe_amount(ingredient)
        ingredient["quantity"] = round(float(grams), 6)
        ingredient["unit"] = "g"
        ingredient["weight"] = {"quantity": round(float(grams), 6), "unit": "g"}
        ingredient["scaleMeasured"] = True
        ingredient["scaleMeasurement"] = {
            "grams": round(float(grams), 6),
            "recordedAt": _text(measurement.get("recordedAt")),
            "originalQuantity": original_amount,
            "originalUnit": original_unit,
        }
        ingredients[target_index] = ingredient
    result["ingredients"] = ingredients
    if measurements:
        result["smartScaleMeasured"] = True
    return result


def scale_recipe_guide(
    recipe: dict[str, Any], *, anchor_index: int, measured_grams: Any
) -> dict[str, Any]:
    """Build a proportional display-only recipe guide from an actual anchor weight."""
    ingredients = recipe.get("ingredients") if isinstance(recipe.get("ingredients"), list) else []
    if anchor_index < 0 or anchor_index >= len(ingredients) or not isinstance(ingredients[anchor_index], dict):
        raise ValueError("Recipe scale anchor is invalid")
    target_amount, target_unit = _recipe_amount(ingredients[anchor_index])
    target_grams = mass_to_grams(target_amount, target_unit)
    actual_grams = _number(measured_grams)
    if target_grams is None or target_grams <= 0:
        raise ValueError("Selected ingredient has no mass target that can be scaled")
    if actual_grams is None or actual_grams <= 0:
        raise ValueError("Measured ingredient weight must be greater than zero")
    factor = actual_grams / target_grams
    if factor <= 0 or not math.isfinite(factor):
        raise ValueError("Recipe scale factor is invalid")

    result = deepcopy(recipe)
    scaled_rows: list[dict[str, Any]] = []
    for raw in result.get("ingredients") or []:
        if not isinstance(raw, dict):
            scaled_rows.append(raw)
            continue
        row = dict(raw)
        quantity = _number(row.get("quantity"))
        if quantity is not None:
            row["quantity"] = round(quantity * factor, 6)
        weight = row.get("weight") if isinstance(row.get("weight"), dict) else None
        if weight is not None:
            weight_quantity = _number(weight.get("quantity"))
            if weight_quantity is not None:
                row["weight"] = {**weight, "quantity": round(weight_quantity * factor, 6)}
        scaled_rows.append(row)
    result["ingredients"] = scaled_rows
    for key in ("servings", "groupSize"):
        number = _number(result.get(key))
        if number is not None:
            result[key] = round(number * factor, 3)
    if isinstance(result.get("yield"), dict):
        yield_data = dict(result["yield"])
        quantity = _number(yield_data.get("quantity"))
        if quantity is not None:
            yield_data["quantity"] = round(quantity * factor, 3)
        result["yield"] = yield_data
    result["scaleGuide"] = {
        "factor": round(factor, 6),
        "anchorIndex": anchor_index,
        "targetGrams": round(target_grams, 6),
        "measuredGrams": round(actual_grams, 6),
        "displayOnly": True,
    }
    return result


def portion_nutrition(nutrition: Any, *, batch_grams: Any, portion_grams: Any) -> dict[str, Any]:
    """Scale whole-batch nutrition to a weighed portion."""
    batch = _number(batch_grams)
    portion = _number(portion_grams)
    if batch is None or batch <= 0:
        raise ValueError("Cooked batch weight must be greater than zero")
    if portion is None or portion <= 0:
        raise ValueError("Portion weight must be greater than zero")
    if portion > batch + 1e-6:
        raise ValueError("Portion weight cannot exceed the cooked batch weight")
    source = nutrition if isinstance(nutrition, dict) else {}
    totals = source.get("totals") if isinstance(source.get("totals"), dict) else {}
    if not totals and isinstance(source.get("perServing"), dict):
        servings = _number(source.get("servings"))
        if servings is not None and servings > 0:
            totals = {
                key: float(value) * servings
                for key, value in source["perServing"].items()
                if isinstance(value, (int, float)) and math.isfinite(float(value))
            }
    if not totals:
        raise ValueError("Whole-recipe nutrition is unavailable")
    factor = portion / batch
    values = {
        str(key): round(float(value) * factor, 2)
        for key, value in totals.items()
        if isinstance(value, (int, float)) and math.isfinite(float(value))
    }
    return {
        "batchGrams": round(batch, 3),
        "portionGrams": round(portion, 3),
        "fraction": round(factor, 6),
        "nutrition": values,
    }


def prepare_inventory_reweigh(
    inventory: Any, identity: str, *, grams: Any, lot_id: str = ""
) -> dict[str, Any]:
    """Prepare a safe stock mutation from a net scale reading."""
    amount_grams = _number(grams)
    if amount_grams is None:
        raise ValueError("Scale weight is invalid")
    rows = normalize_inventory(inventory)
    row = next((item for item in rows if inventory_identity(item) == _text(identity)), None)
    if row is None:
        raise ValueError("Stock ingredient was not found")
    if row.get("unlimited"):
        raise ValueError("Unlimited stock cannot be re-weighed")
    unit = _text(row.get("unit")) or "g"
    converted = grams_to_mass(amount_grams, unit)
    if converted is None:
        raise ValueError(f"Stock unit {unit or 'unitless'} is not a mass unit")

    lots = deepcopy(row.get("lots") or [])
    wanted_lot = _text(lot_id)
    if lots:
        index: int | None = None
        if wanted_lot:
            index = next(
                (i for i, lot in enumerate(lots) if _text(lot.get("id")) == wanted_lot),
                None,
            )
            if index is None:
                raise ValueError("Stock batch was not found")
        elif len(lots) == 1:
            index = 0
        else:
            raise ValueError("Choose which stock batch to re-weigh")
        assert index is not None
        if amount_grams <= 1e-9:
            lots.pop(index)
        else:
            lots[index]["quantity"] = round(float(converted), 9)
            lots[index]["source"] = _text(lots[index].get("source")) or "scale"
            lots[index]["weighedAt"] = datetime.now(timezone.utc).isoformat()
        return {
            "identity": _text(identity),
            "unit": unit,
            "lots": lots,
            "remove": not lots,
            "grams": round(amount_grams, 6),
        }

    return {
        "identity": _text(identity),
        "unit": unit,
        "quantity": round(float(converted), 9),
        "remove": amount_grams <= 1e-9,
        "grams": round(amount_grams, 6),
    }


class Cook4MeSmartScaleStore:
    """Persistent scale selection, container tares and recipe weighing sessions."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.smart_scale"
        )
        self._loaded = False
        self._data: dict[str, Any] = {
            "selectedEntityId": "",
            "containers": [],
            "sessions": {},
        }

    async def async_load(self) -> None:
        if self._loaded:
            return
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            self._data["selectedEntityId"] = _text(saved.get("selectedEntityId"))
            containers: list[dict[str, Any]] = []
            for raw in saved.get("containers") or []:
                if not isinstance(raw, dict):
                    continue
                name = _text(raw.get("name"))
                tare = _number(raw.get("tareGrams"))
                if not name or tare is None:
                    continue
                containers.append(
                    {
                        "id": _text(raw.get("id")) or str(uuid4()),
                        "name": name[:120],
                        "tareGrams": round(tare, 6),
                    }
                )
            self._data["containers"] = containers[-_MAX_CONTAINERS:]
            sessions = saved.get("sessions") if isinstance(saved.get("sessions"), dict) else {}
            self._data["sessions"] = {
                str(key): deepcopy(value)
                for key, value in list(sessions.items())[-_MAX_SESSIONS:]
                if isinstance(value, dict)
            }
        self._loaded = True

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    @property
    def selected_entity_id(self) -> str:
        return _text(self._data.get("selectedEntityId"))

    @property
    def containers(self) -> list[dict[str, Any]]:
        return deepcopy(self._data.get("containers") or [])

    async def async_select_entity(self, entity_id: str) -> str:
        self._data["selectedEntityId"] = _text(entity_id)
        await self._save()
        return self.selected_entity_id

    async def async_save_container(
        self, name: str, tare_grams: Any, *, container_id: str = ""
    ) -> dict[str, Any]:
        label = _text(name)
        tare = _number(tare_grams)
        if not label:
            raise ValueError("Container name is required")
        if tare is None:
            raise ValueError("Container tare is invalid")
        wanted = _text(container_id)
        row = {
            "id": wanted or str(uuid4()),
            "name": label[:120],
            "tareGrams": round(tare, 6),
        }
        rows = [item for item in self._data["containers"] if _text(item.get("id")) != row["id"]]
        rows.append(row)
        self._data["containers"] = rows[-_MAX_CONTAINERS:]
        await self._save()
        return deepcopy(row)

    async def async_delete_container(self, container_id: str) -> bool:
        wanted = _text(container_id)
        before = len(self._data["containers"])
        self._data["containers"] = [
            row for row in self._data["containers"] if _text(row.get("id")) != wanted
        ]
        changed = before != len(self._data["containers"])
        if changed:
            await self._save()
        return changed

    def _session_key(self, recipe: dict[str, Any]) -> str | None:
        wanted = set(recipe_aliases(recipe))
        if not wanted:
            return None
        for key, row in self._data["sessions"].items():
            aliases = set(str(value) for value in row.get("aliases") or [])
            if wanted & aliases:
                return key
        primary = recipe_identity(recipe)
        if primary:
            return primary
        return next(iter(wanted), None)

    def session_for(self, recipe: Any) -> dict[str, Any] | None:
        if not isinstance(recipe, dict):
            return None
        key = self._session_key(recipe)
        row = self._data["sessions"].get(key) if key else None
        return deepcopy(row) if isinstance(row, dict) else None

    def _ensure_session(self, recipe: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        key = self._session_key(recipe)
        if key and isinstance(self._data["sessions"].get(key), dict):
            row = self._data["sessions"][key]
            row["aliases"] = list(dict.fromkeys((row.get("aliases") or []) + recipe_aliases(recipe)))
            return key, row
        key = recipe_identity(recipe) or (recipe_aliases(recipe)[0] if recipe_aliases(recipe) else "")
        if not key:
            raise ValueError("Recipe has no stable identity")
        row = {
            "recipeKey": key,
            "aliases": recipe_aliases(recipe),
            "title": _text(recipe.get("title"))[:200],
            "measurements": [],
            "batchWeightGrams": None,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        self._data["sessions"][key] = row
        return key, row

    async def async_record_measurement(
        self,
        recipe: dict[str, Any],
        *,
        ingredient_index: int,
        ingredient: dict[str, Any],
        grams: Any,
    ) -> dict[str, Any]:
        amount = _number(grams)
        if amount is None or amount <= 0:
            raise ValueError("Ingredient weight must be greater than zero")
        key, session = self._ensure_session(recipe)
        measurement = {
            "ingredientIndex": int(ingredient_index),
            "ingredientIdentity": inventory_identity(ingredient),
            "ingredientName": _text(ingredient.get("foodName") or ingredient.get("name"))[:200],
            "grams": round(amount, 6),
            "recordedAt": datetime.now(timezone.utc).isoformat(),
        }
        rows = [
            row for row in session.get("measurements") or []
            if int(row.get("ingredientIndex", -1)) != int(ingredient_index)
        ]
        rows.append(measurement)
        session["measurements"] = rows[-_MAX_MEASUREMENTS:]
        session["updatedAt"] = datetime.now(timezone.utc).isoformat()
        self._data["sessions"][key] = session
        self._trim_sessions()
        await self._save()
        return deepcopy(session)

    async def async_set_batch_weight(self, recipe: dict[str, Any], grams: Any) -> dict[str, Any]:
        amount = _number(grams)
        if amount is None or amount <= 0:
            raise ValueError("Cooked batch weight must be greater than zero")
        key, session = self._ensure_session(recipe)
        session["batchWeightGrams"] = round(amount, 6)
        session["updatedAt"] = datetime.now(timezone.utc).isoformat()
        self._data["sessions"][key] = session
        self._trim_sessions()
        await self._save()
        return deepcopy(session)

    async def async_clear_session(self, recipe: Any) -> bool:
        if not isinstance(recipe, dict):
            return False
        key = self._session_key(recipe)
        if not key or key not in self._data["sessions"]:
            return False
        self._data["sessions"].pop(key, None)
        await self._save()
        return True

    def _trim_sessions(self) -> None:
        while len(self._data["sessions"]) > _MAX_SESSIONS:
            oldest = min(
                self._data["sessions"],
                key=lambda key: _text(self._data["sessions"][key].get("updatedAt")),
            )
            self._data["sessions"].pop(oldest, None)

    def snapshot(self, *, recipe: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "selectedEntityId": self.selected_entity_id,
            "containers": self.containers,
            "session": self.session_for(recipe) if recipe else None,
        }


async def smart_scale_store_for_bridge(bridge: Any) -> Cook4MeSmartScaleStore:
    store = getattr(bridge, "_smart_scale_store", None)
    if store is None:
        store = Cook4MeSmartScaleStore(bridge.hass, bridge.entry.entry_id)
        await store.async_load()
        bridge._smart_scale_store = store
    return store
