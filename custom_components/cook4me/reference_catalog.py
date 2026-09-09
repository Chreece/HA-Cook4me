from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import gzip
import json
import math
from pathlib import Path
import re
import unicodedata
from typing import Any

SCHEMA_VERSION = 1
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
_DATA_DIR = Path(__file__).with_name("data")
_JSON_PATH = _DATA_DIR / "reference_catalog.json"
_GZIP_PATH = _DATA_DIR / "reference_catalog.json.gz"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    out: list[str] = []
    pending = False
    for char in text:
        if unicodedata.category(char).startswith("M"):
            continue
        if char.isalnum():
            if pending and out:
                out.append(" ")
            out.append(char)
            pending = False
        else:
            pending = True
    return "".join(out).strip()


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def _unit(value: Any) -> str:
    return (
        unicodedata.normalize("NFKC", _text(value).casefold())
        .replace("ℓ", "l")
        .replace("µ", "u")
        .replace("μ", "u")
        .replace(" ", "")
    )


def _convert_amount(value: Any, source_unit: Any, target_unit: Any) -> float | None:
    amount = _number(value)
    if amount is None:
        return None
    source = _unit(source_unit)
    target = _unit(target_unit)
    if source == target:
        return amount
    if source in _MASS_SCALE and target in _MASS_SCALE:
        return amount * _MASS_SCALE[source] / _MASS_SCALE[target]
    if source in _VOLUME_SCALE and target in _VOLUME_SCALE:
        return amount * _VOLUME_SCALE[source] / _VOLUME_SCALE[target]
    # Deliberately no piece↔mass, piece↔volume or density conversion.
    return None


def normalize_reference_nutrition(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    basis_quantity = _number(value.get("basisQuantity")) or 100.0
    basis_unit = _unit(value.get("basisUnit") or "g")
    if basis_unit not in {"g", "ml"} or basis_quantity <= 0:
        return None
    raw = value.get("values") if isinstance(value.get("values"), dict) else value
    values: dict[str, float] = {}
    if isinstance(raw, dict):
        for key in NUTRIENT_KEYS:
            number = _number(raw.get(key))
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


def nutrition_for_reference_amount(
    profile: Any, quantity: Any, unit: Any
) -> dict[str, float] | None:
    normalized = normalize_reference_nutrition(profile)
    if normalized is None:
        return None
    converted = _convert_amount(quantity, unit, normalized["basisUnit"])
    if converted is None:
        return None
    factor = converted / float(normalized["basisQuantity"])
    return {key: float(value) * factor for key, value in normalized["values"].items()}


def calculate_reference_recipe_nutrition(
    recipe: dict[str, Any],
    ingredients_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    totals: dict[str, float] = {}
    details: list[dict[str, Any]] = []
    coverage: list[float] = []
    source_kinds: set[str] = set()

    for raw in recipe.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        ingredient_id = _text(raw.get("id") or raw.get("key") or raw.get("foodKey"))
        quantity = _number(raw.get("quantity"))
        unit = _unit(raw.get("unit"))
        ref = ingredients_by_id.get(ingredient_id)
        detail = {
            "id": ingredient_id,
            "quantity": quantity,
            "unit": unit,
            "covered": False,
        }
        if (
            ref
            and not ref.get("nutritionConflict")
            and quantity is not None
            and unit
            and isinstance(ref.get("nutrition"), dict)
        ):
            values = nutrition_for_reference_amount(ref["nutrition"], quantity, unit)
            if values is not None:
                for key, value in values.items():
                    totals[key] = totals.get(key, 0.0) + float(value)
                detail["covered"] = True
                detail["source"] = _text(ref["nutrition"].get("source"))
                coverage.append(1.0)
                source_kinds.add(detail["source"] or "bundled_reference")
            else:
                detail["reason"] = "incompatible_unit"
                coverage.append(0.0)
        else:
            detail["reason"] = (
                "nutrition_conflict"
                if ref and ref.get("nutritionConflict")
                else "nutrition_reference_missing"
            )
            coverage.append(0.0)
        details.append(detail)

    def rounded(values: dict[str, float]) -> dict[str, float]:
        return {
            key: round(float(value), 1 if key in {"energyKcal", "energyKJ"} else 2)
            for key, value in values.items()
            if math.isfinite(float(value))
        }

    servings = _number(recipe.get("servings"))
    if servings is None:
        yield_data = recipe.get("yield")
        if isinstance(yield_data, dict):
            servings = _number(
                yield_data.get("quantity") or yield_data.get("quantityDisplay")
            )
    fraction = sum(coverage) / len(coverage) if coverage else 0.0
    totals_rounded = rounded(totals)
    per_serving = (
        rounded({key: value / servings for key, value in totals.items()})
        if servings and servings > 0
        else {}
    )
    return {
        "totals": totals_rounded,
        "perServing": per_serving,
        "servings": servings,
        "coverage": round(fraction, 3),
        "fullyCovered": bool(coverage) and all(value >= 0.999 for value in coverage),
        "estimated": fraction < 0.999,
        "sourceKinds": sorted(source_kinds),
        "ingredients": details,
        "source": "bundled_ingredient_reference",
    }


def _display_name(row: dict[str, Any], language: str) -> str:
    language = _text(language).lower().replace("_", "-").split("-", 1)[0]
    names = row.get("names") if isinstance(row.get("names"), dict) else {}
    for key in (language, "en"):
        value = _text(names.get(key))
        if value:
            return value
    return _text(row.get("canonicalName") or row.get("name") or row.get("id"))


def validate_reference_catalog(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Reference catalog must be a JSON object")
    if int(payload.get("schemaVersion") or 0) != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported reference catalog schema {payload.get('schemaVersion')!r}"
        )
    ingredients = payload.get("ingredients")
    recipes = payload.get("recipes")
    if not isinstance(ingredients, list) or not isinstance(recipes, list):
        raise ValueError("Reference catalog must contain ingredient and recipe arrays")

    seen_ingredients: set[str] = set()
    for row in ingredients:
        if not isinstance(row, dict):
            raise ValueError("Ingredient rows must be objects")
        identity = _text(row.get("id"))
        if not identity or identity in seen_ingredients:
            raise ValueError(f"Invalid or duplicate ingredient id {identity!r}")
        seen_ingredients.add(identity)
        if not _text(row.get("canonicalName")):
            raise ValueError(f"Ingredient {identity!r} has no canonical name")
        nutrition = row.get("nutrition")
        if nutrition is not None and normalize_reference_nutrition(nutrition) is None:
            raise ValueError(f"Ingredient {identity!r} has invalid nutrition")

    seen_recipes: set[str] = set()
    for row in recipes:
        if not isinstance(row, dict):
            raise ValueError("Recipe rows must be objects")
        identity = _text(row.get("id"))
        if not identity or identity in seen_recipes:
            raise ValueError(f"Invalid or duplicate recipe id {identity!r}")
        seen_recipes.add(identity)
        if not _text(row.get("canonicalName")):
            raise ValueError(f"Recipe {identity!r} has no canonical name")
        variants = row.get("variants")
        if not isinstance(variants, list) or not variants:
            raise ValueError(f"Recipe {identity!r} has no proven variants")
    return payload


def _read_payload(path: Path | None = None) -> dict[str, Any]:
    if path is not None:
        selected = path
    elif _GZIP_PATH.exists():
        selected = _GZIP_PATH
    else:
        selected = _JSON_PATH
    if selected.suffix == ".gz":
        with gzip.open(selected, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = json.loads(selected.read_text(encoding="utf-8"))
    return validate_reference_catalog(payload)


class ReferenceCatalog:
    """Immutable release-bundled Cook4Me reference index.

    The catalog contains only release-time reference data. User-specific state,
    credentials, exact purchases and live prices never belong here.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = validate_reference_catalog(deepcopy(payload))
        self.ingredients_by_id = {
            str(row["id"]): row for row in self.payload.get("ingredients") or []
        }
        self.recipes_by_id = {
            str(row["id"]): row for row in self.payload.get("recipes") or []
        }
        self._ingredient_search = [
            (
                row,
                _norm(
                    " ".join(
                        [
                            _text(row.get("canonicalName")),
                            *[
                                _text(value)
                                for value in (row.get("names") or {}).values()
                                if _text(value)
                            ],
                        ]
                    )
                ),
            )
            for row in self.ingredients_by_id.values()
        ]
        self._recipe_search = [
            (
                row,
                _norm(
                    " ".join(
                        [
                            _text(row.get("canonicalName")),
                            *[
                                _text(value)
                                for value in (row.get("names") or {}).values()
                                if _text(value)
                            ],
                        ]
                    )
                ),
            )
            for row in self.recipes_by_id.values()
        ]

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "catalogVersion": _text(self.payload.get("catalogVersion")),
            "generatedAt": _text(self.payload.get("generatedAt")),
            "source": _text(self.payload.get("source")),
            "ingredientCount": len(self.ingredients_by_id),
            "recipeCount": len(self.recipes_by_id),
            "languages": deepcopy(self.payload.get("languages") or []),
            "populationComplete": bool(self.payload.get("populationComplete")),
        }

    def ingredient(
        self, ingredient_id: str, *, language: str = "en"
    ) -> dict[str, Any] | None:
        row = self.ingredients_by_id.get(_text(ingredient_id))
        if row is None:
            return None
        result = deepcopy(row)
        result["name"] = _display_name(row, language)
        return result

    def ingredients(
        self, *, language: str = "en", query: str = "", limit: int = 5000
    ) -> list[dict[str, Any]]:
        wanted = _norm(query)
        out: list[dict[str, Any]] = []
        for row, searchable in self._ingredient_search:
            if wanted and wanted not in searchable:
                continue
            out.append(
                {
                    "id": row["id"],
                    "key": row["id"],
                    "name": _display_name(row, language),
                    "canonicalName": row.get("canonicalName"),
                    "hasNutrition": isinstance(row.get("nutrition"), dict),
                    "nutrition": deepcopy(row.get("nutrition")),
                }
            )
            if len(out) >= max(1, min(int(limit), 5000)):
                break
        return out

    def recipe(
        self, recipe_id: str, *, language: str = "en"
    ) -> dict[str, Any] | None:
        row = self.recipes_by_id.get(_text(recipe_id))
        if row is None:
            return None
        result = deepcopy(row)
        result["title"] = _display_name(row, language)
        return result

    def recipes(
        self,
        *,
        language: str = "en",
        query: str = "",
        source_languages: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        wanted = _norm(query)
        allowed = {
            _text(value).lower().replace("_", "-").split("-", 1)[0]
            for value in source_languages or []
            if _text(value)
        }
        out: list[dict[str, Any]] = []
        for row, searchable in self._recipe_search:
            if wanted and wanted not in searchable:
                continue
            variants = [
                deepcopy(variant)
                for variant in row.get("variants") or []
                if isinstance(variant, dict)
                and (
                    not allowed
                    or _text(variant.get("language")).lower() in allowed
                )
            ]
            if not variants:
                continue
            out.append(
                {
                    "id": row["id"],
                    "groupingFunctionalId": row.get("groupingFunctionalId")
                    or row["id"],
                    "title": _display_name(row, language),
                    "canonicalName": row.get("canonicalName"),
                    "names": deepcopy(row.get("names") or {}),
                    "cover": row.get("cover"),
                    "servings": row.get("servings"),
                    "nutrition": deepcopy(row.get("nutrition")),
                    "ingredients": deepcopy(row.get("ingredients") or []),
                    "variants": variants,
                    "source": "bundled_reference_catalog",
                    "referenceCatalogVersion": self.metadata["catalogVersion"],
                }
            )
            if len(out) >= max(1, min(int(limit), 500)):
                break
        return out

    def variant(
        self,
        recipe_id: str,
        *,
        language: str,
        fallback_language: str = "",
    ) -> dict[str, Any] | None:
        row = self.recipes_by_id.get(_text(recipe_id))
        if not row:
            return None
        wanted = _text(language).lower().replace("_", "-").split("-", 1)[0]
        fallback = (
            _text(fallback_language).lower().replace("_", "-").split("-", 1)[0]
        )
        variants = [
            variant
            for variant in row.get("variants") or []
            if isinstance(variant, dict)
        ]
        for candidate in (wanted, fallback, "en"):
            if not candidate:
                continue
            match = next(
                (
                    variant
                    for variant in variants
                    if _text(variant.get("language")).lower() == candidate
                ),
                None,
            )
            if match:
                return deepcopy(match)
        return deepcopy(variants[0]) if variants else None


@lru_cache(maxsize=1)
def bundled_reference_catalog() -> ReferenceCatalog:
    return ReferenceCatalog(_read_payload())


def clear_reference_catalog_cache() -> None:
    bundled_reference_catalog.cache_clear()
