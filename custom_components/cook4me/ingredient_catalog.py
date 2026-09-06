from __future__ import annotations

from copy import deepcopy
import re
import time
import unicodedata
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION = 1
_TTL = 24 * 60 * 60
_MAX_LANGUAGES = 8
_MAX_ITEMS = 5000
_RECIPE_FALLBACK_SOURCE_V2 = "hydrated_official_recipes_fallback:v2_amount_clean"

# Unicode vulgar fractions used in recipe quantities. Python's \d already
# matches non-ASCII decimal digits (for example Arabic-Indic numerals).
_VULGAR_FRACTIONS = "¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞"
_NUMBER = rf"(?:\d+(?:[.,٫]\d+)?|\d+\s*/\s*\d+|[{_VULGAR_FRACTIONS}])"
_AMOUNT = rf"(?:{_NUMBER})(?:\s*(?:[-–—]\s*|to\s+){_NUMBER})?"
_GENERIC_AMOUNT_PREFIX = re.compile(rf"^\s*{_AMOUNT}\s+", re.IGNORECASE | re.UNICODE)


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _quantity_strings(value: Any) -> list[str]:
    """Return textual forms that SEB may use for a structured quantity."""
    if value in (None, ""):
        return []
    forms: list[str] = []
    text = _text(value)
    if text:
        forms.append(text)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return list(dict.fromkeys(forms))
    if number.is_integer():
        forms.append(str(int(number)))
    else:
        compact = f"{number:g}"
        forms.extend((compact, compact.replace(".", ",")))
    return list(dict.fromkeys(forms))


def _strip_structured_amount(name: str, item: dict[str, Any]) -> str:
    """Strip recipe quantity/unit prefix without language assumptions."""
    quantity_forms = _quantity_strings(item.get("quantity"))
    unit = _text(item.get("unit"))
    boundary = r"(?=\s|[-–—,:;]|$)"
    patterns: list[str] = []

    if unit:
        escaped_unit = re.escape(unit)
        # The generic numeric form also catches display fractions such as ½
        # when the structured quantity is stored as 0.5.
        patterns.append(
            rf"^\s*{_AMOUNT}\s*{escaped_unit}{boundary}\s*[-–—,:;]?\s*"
        )

    for quantity in sorted(quantity_forms, key=len, reverse=True):
        escaped_q = re.escape(quantity)
        if unit:
            escaped_unit = re.escape(unit)
            patterns.append(
                rf"^\s*{escaped_q}\s*{escaped_unit}{boundary}\s*[-–—,:;]?\s*"
            )
        # Unitless structured quantities (eggs, onions, cloves...) still need
        # the amount removed. This is safe because quantity came from SEB's
        # structured field rather than a guessed language token.
        patterns.append(rf"^\s*{escaped_q}\s+")

    for pattern in patterns:
        cleaned = re.sub(
            pattern,
            "",
            name,
            count=1,
            flags=re.IGNORECASE | re.UNICODE,
        ).strip()
        if cleaned != name and cleaned:
            return cleaned
    return name


def _strip_generic_amount_prefix(name: str) -> str:
    """Remove a leading numeric amount when only free-form text exists."""
    cleaned = _GENERIC_AMOUNT_PREFIX.sub("", name, count=1).strip()
    return cleaned or name


def _starts_with_amount(value: Any) -> bool:
    return bool(_GENERIC_AMOUNT_PREFIX.match(_text(value)))


def catalog_ingredient_name(item: Any) -> str:
    """Return an amount-free ingredient label suitable for catalog selection.

    Prefer SEB's canonical food name. If it is absent, applianceDescription is
    generally quantity-free. Only then fall back to recipe descriptions, where
    structured quantity/unit data and a Unicode numeric fallback remove the
    recipe-specific amount. This logic is language-independent.
    """
    if isinstance(item, str):
        return _strip_generic_amount_prefix(_text(item))
    if not isinstance(item, dict):
        return ""

    canonical = _text(item.get("foodName"))
    if canonical:
        return canonical

    appliance = _text(item.get("applianceDescription"))
    if appliance:
        cleaned = _strip_structured_amount(appliance, item)
        return _strip_generic_amount_prefix(cleaned)

    candidate = _text(item.get("name") or item.get("applicationDescription"))
    if not candidate:
        return ""
    cleaned = _strip_structured_amount(candidate, item)
    return _strip_generic_amount_prefix(cleaned)


def ingredient_identity(item: Any) -> tuple[str | None, str]:
    if isinstance(item, str):
        return None, _text(item)
    if not isinstance(item, dict):
        return None, ""
    key = _text(item.get("foodKey") or item.get("key")) or None
    name = _text(
        item.get("foodName")
        or item.get("name")
        or item.get("applicationDescription")
        or item.get("applianceDescription")
    )
    return key, name


def normalize_house_ingredients(value: Any) -> list[dict[str, str]]:
    if isinstance(value, str):
        value = [part.strip() for part in value.replace(",", "\n").splitlines()]
    if not isinstance(value, list):
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in value:
        key, name = ingredient_identity(raw)
        if not name:
            continue
        identity = f"k:{key}" if key else f"n:{_norm(name)}"
        if not identity or identity in seen:
            continue
        seen.add(identity)
        row = {"name": name}
        if key:
            row["key"] = key
        out.append(row)
        if len(out) >= 500:
            break
    return out


def _clean_catalog_rows(rows: list[Any]) -> list[dict[str, str]]:
    """Normalize and dedupe catalog rows."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, (str, dict)):
            continue
        key = _text(raw.get("key")) if isinstance(raw, dict) else ""
        name = catalog_ingredient_name(raw)
        if not name:
            continue
        identity = f"k:{key}" if key else f"n:{_norm(name)}"
        if not identity or identity in seen:
            continue
        seen.add(identity)
        row = {"name": name}
        if key:
            row["key"] = key
        out.append(row)
        if len(out) >= _MAX_ITEMS:
            break
    return sorted(out, key=lambda row: _norm(row["name"]))


def catalog_items_from_recipes(recipes: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, Any]] = []
    for recipe in recipes:
        if not isinstance(recipe, dict):
            continue
        for ingredient in recipe.get("ingredients") or []:
            if not isinstance(ingredient, (str, dict)):
                continue
            if isinstance(ingredient, dict):
                key = _text(ingredient.get("foodKey") or ingredient.get("key"))
                row = dict(ingredient)
                if key:
                    row["key"] = key
                rows.append(row)
            else:
                rows.append({"name": ingredient})
            if len(rows) >= _MAX_ITEMS * 4:
                break
        if len(rows) >= _MAX_ITEMS * 4:
            break
    return _clean_catalog_rows(rows)


def _localized_name(value: Any, language: str) -> str:
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, dict):
        return _text(value.get("value") or value.get("name") or value.get("label"))
    if not isinstance(value, list):
        return ""
    language = str(language or "").lower()
    fallback = ""
    for row in value:
        if isinstance(row, str):
            fallback = fallback or _text(row)
            continue
        if not isinstance(row, dict):
            continue
        name = _text(row.get("value") or row.get("name") or row.get("label"))
        if not name:
            continue
        fallback = fallback or name
        row_language = _text(
            row.get("lang") or row.get("language") or row.get("languageKey")
        ).lower().replace("_", "-").split("-", 1)[0]
        if row_language == language:
            return name
    return fallback


def marketing_food_items(payload: Any, language: str) -> list[dict[str, str]]:
    """Normalize the flexible DcpMarketingFood wrapper returned by SEB."""
    if not isinstance(payload, dict):
        return []
    candidates: list[Any] = []
    for key in ("content", "marketingFoods", "items", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, dict):
            nested = value.get("content") or value.get("items") or value.get("marketingFoods")
            if isinstance(nested, list):
                candidates.extend(nested)
    if not candidates and payload.get("key"):
        candidates = [payload]

    rows: list[dict[str, str]] = []
    for raw in candidates:
        if not isinstance(raw, dict):
            continue
        key = _text(raw.get("key") or raw.get("id") or raw.get("reference"))
        name = _localized_name(raw.get("name"), language)
        if not name:
            name = _text(raw.get("label") or raw.get("title"))
        if not name:
            continue
        row = {"name": name}
        if key:
            row["key"] = key
        rows.append(row)
    return _clean_catalog_rows(rows)


def enrich_match_with_house_keys(
    recipe: dict[str, Any], match: dict[str, Any], house_ingredients: Any
) -> dict[str, Any]:
    result = deepcopy(match)
    house = normalize_house_ingredients(house_ingredients)
    house_keys = {row["key"] for row in house if row.get("key")}
    house_names = {_norm(row["name"]) for row in house if row.get("name")}
    matched_names = {_norm(name) for name in result.get("matchedIngredients") or []}
    missing_names = {_norm(name) for name in result.get("missingIngredients") or []}

    availability: list[dict[str, Any]] = []
    matched: list[str] = []
    missing: list[str] = []
    relevant = 0
    for ingredient in recipe.get("ingredients") or []:
        key, name = ingredient_identity(ingredient)
        if not name:
            continue
        normalized = _norm(name)
        if (key and key in house_keys) or normalized in house_names or normalized in matched_names:
            status = "at_home"
            matched.append(name)
            relevant += 1
        elif normalized in missing_names:
            status = "missing"
            missing.append(name)
            relevant += 1
        else:
            status = "staple"
        availability.append(
            {
                **({"key": key} if key else {}),
                "name": name,
                "status": status,
                "missing": status == "missing",
            }
        )

    result["matchedIngredients"] = list(dict.fromkeys(matched))
    result["missingIngredients"] = list(dict.fromkeys(missing))
    result["ingredientAvailability"] = availability
    result["pantryCoverage"] = round(1.0 if relevant == 0 else len(matched) / relevant, 3)
    return result


def shopping_item_name(item: Any) -> str:
    if isinstance(item, str):
        return _text(item)
    if not isinstance(item, dict):
        return ""
    description = _text(item.get("applicationDescription"))
    if description:
        return description
    _key, name = ingredient_identity(item)
    parts: list[str] = []
    quantity = item.get("quantity")
    if quantity not in (None, ""):
        parts.append(str(quantity))
    unit = _text(item.get("unit"))
    if unit:
        parts.append(unit)
    if name:
        parts.append(name)
    return _text(" ".join(parts))


class Cook4MeIngredientCatalogCache:
    """Persist a bounded per-language ingredient catalog for 24 hours."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.ingredient_catalog"
        )
        self._data: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        saved = await self._store.async_load()
        if isinstance(saved, dict):
            self._data = {
                str(language): row
                for language, row in saved.items()
                if isinstance(row, dict) and isinstance(row.get("items"), list)
            }
        self._prune()

    def _prune(self) -> None:
        now = time.time()
        current = {
            language: row
            for language, row in self._data.items()
            if now - float(row.get("timestamp") or 0) <= _TTL
        }
        if len(current) > _MAX_LANGUAGES:
            current = dict(
                sorted(
                    current.items(),
                    key=lambda pair: float(pair[1].get("timestamp") or 0),
                    reverse=True,
                )[:_MAX_LANGUAGES]
            )
        self._data = current

    def get(self, language: str) -> dict[str, Any] | None:
        self._prune()
        row = self._data.get(str(language))
        if not row:
            return None
        # v11 recipe-derived rows may already have lost quantity/unit structure,
        # so do not guess how to clean them. Force one immediate rebuild under
        # the v2 amount-clean contract instead of waiting for the 24h TTL.
        if str(row.get("source") or "") == "hydrated_official_recipes_fallback":
            self._data.pop(str(language), None)
            return None
        result = deepcopy(row)
        result["items"] = _clean_catalog_rows(result.get("items") or [])
        return result

    async def async_set(self, language: str, items: list[dict[str, str]], *, source: str) -> None:
        self._data[str(language)] = {
            "timestamp": time.time(),
            "source": str(source),
            "items": deepcopy(_clean_catalog_rows(items)),
        }
        self._prune()
        await self._store.async_save(deepcopy(self._data))
