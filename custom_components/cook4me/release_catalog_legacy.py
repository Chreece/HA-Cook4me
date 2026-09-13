from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

_SCHEMA_VERSION = 1
_CATALOG_PATH = Path(__file__).with_name("catalog") / "merged_catalog.v1.json"
_MAX_PAGE_SIZE = 50


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


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


def _language(value: Any) -> str:
    return _text(value).lower().replace("_", "-").split("-", 1)[0]


def _empty_catalog(version: str) -> dict[str, Any]:
    return {
        "schemaVersion": _SCHEMA_VERSION,
        "catalogVersion": version,
        "complete": False,
        "ingredients": [],
        "recipes": [],
        "_runtimeIngredientById": {},
        "_runtimeRecipeByLanguage": {},
        "_runtimeRawVariantCount": 0,
    }


def _prepare_runtime_indexes(payload: dict[str, Any]) -> None:
    """Build small derived lookup indexes once after parsing the release file."""
    ingredient_by_id: dict[str, dict[str, Any]] = {}
    for raw in payload.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        ident = _text(raw.get("id") or raw.get("ingredientId") or raw.get("key") or raw.get("foodKey"))
        key = _text(raw.get("key") or raw.get("foodKey"))
        if ident:
            ingredient_by_id[ident] = raw
        if key:
            ingredient_by_id.setdefault(key, raw)

    by_language: dict[str, list[int]] = {}
    raw_variant_count = 0
    for index, recipe in enumerate(payload.get("recipes") or []):
        if not isinstance(recipe, dict):
            continue
        languages: set[str] = set()
        for variant in recipe.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            raw_variant_count += 1
            if lang := _language(variant.get("language")):
                languages.add(lang)
        for lang in languages:
            by_language.setdefault(lang, []).append(index)

    payload["_runtimeIngredientById"] = ingredient_by_id
    payload["_runtimeRecipeByLanguage"] = {
        lang: tuple(indices) for lang, indices in by_language.items()
    }
    payload["_runtimeRawVariantCount"] = raw_variant_count


@lru_cache(maxsize=1)
def load_release_catalog() -> dict[str, Any]:
    """Load and index the immutable release catalog shipped with the integration.

    Runtime code must never mutate the persisted catalog. Derived keys prefixed
    with ``_runtime`` exist only in this cached in-memory object. The integration
    warms the cache in an executor during setup so a large release file is never
    first-parsed on the Home Assistant event loop.
    """
    try:
        payload = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty_catalog("missing")
    if not isinstance(payload, dict) or int(payload.get("schemaVersion") or 0) != _SCHEMA_VERSION:
        return _empty_catalog("invalid")
    if not isinstance(payload.get("ingredients"), list):
        payload["ingredients"] = []
    if not isinstance(payload.get("recipes"), list):
        payload["recipes"] = []
    _prepare_runtime_indexes(payload)
    return payload


async def async_warm_release_catalog(hass: Any) -> dict[str, Any]:
    """Parse and index the immutable catalog once without blocking HA's loop."""
    return await hass.async_add_executor_job(load_release_catalog)


def release_catalog_summary() -> dict[str, Any]:
    payload = load_release_catalog()
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    return {
        "schemaVersion": _SCHEMA_VERSION,
        "catalogVersion": _text(payload.get("catalogVersion")),
        "complete": bool(payload.get("complete")),
        "generatedAt": _text(payload.get("generatedAt")),
        "ingredientCount": len(payload.get("ingredients") or []),
        "recipeCount": len(payload.get("recipes") or []),
        "sourceCatalogCount": int(source.get("sourceCatalogCount") or 0),
        "auditedCatalogCount": int(source.get("auditedCatalogCount") or source.get("sourceCatalogCount") or 0),
        "offlineSearchReady": release_catalog_ready(),
    }


def release_catalog_ready() -> bool:
    payload = load_release_catalog()
    return bool(
        payload.get("complete")
        and isinstance(payload.get("recipes"), list)
        and payload.get("recipes")
        and isinstance(payload.get("ingredients"), list)
        and payload.get("ingredients")
    )


def _translated_name(row: dict[str, Any], language: str) -> str:
    translations = row.get("translations") if isinstance(row.get("translations"), dict) else {}
    language = _language(language)
    return (
        _text(translations.get(language))
        or _text(row.get("canonicalName"))
        or _text(row.get("name"))
    )


def _ingredient_reference(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    payload = load_release_catalog()
    lookup = payload.get("_runtimeIngredientById")
    if not isinstance(lookup, dict):
        return None
    for value in (
        raw.get("ingredientId"), raw.get("id"), raw.get("key"), raw.get("foodKey")
    ):
        ident = _text(value)
        if ident and isinstance(lookup.get(ident), dict):
            return lookup[ident]
    return None


def ingredient_rows(
    language: str,
    query: str = "",
    *,
    limit: int | None = None,
    include_nutrition: bool = False,
) -> list[dict[str, Any]]:
    """Return localized offline ingredient choices.

    The normal UI/AI identity path deliberately omits nutrient payloads. Generic
    nutrient evidence remains in the immutable release catalog and callers that
    actually calculate nutrition can request it explicitly. This keeps a full
    ingredient picker small even when the release catalog contains thousands of
    nutrient profiles.
    """
    wanted = _norm(query)
    maximum = None if limit is None else max(1, int(limit))
    out: list[dict[str, Any]] = []
    for raw in load_release_catalog().get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        name = _translated_name(raw, language)
        if not name:
            continue
        haystack = " ".join(
            (
                name,
                _text(raw.get("canonicalName")),
                " ".join(
                    _text(value)
                    for value in (raw.get("translations") or {}).values()
                    if _text(value)
                ),
            )
        )
        if wanted and wanted not in _norm(haystack):
            continue
        row: dict[str, Any] = {"name": name}
        ident = _text(raw.get("id") or raw.get("ingredientId") or raw.get("key") or raw.get("foodKey"))
        key = _text(raw.get("key") or raw.get("foodKey"))
        if ident:
            row["id"] = ident
        if key:
            row["key"] = key
        if _text(raw.get("canonicalName")):
            row["canonicalName"] = _text(raw.get("canonicalName"))
        if include_nutrition and isinstance(raw.get("nutrition"), dict):
            row["nutrition"] = deepcopy(raw["nutrition"])
        out.append(row)
        if maximum is not None and len(out) >= maximum:
            break
    return out


def _variant_language(row: dict[str, Any]) -> str:
    return _language(row.get("language"))


def _variant_market(row: dict[str, Any]) -> str:
    return _text(row.get("market")).upper()


def _choose_variant(
    recipe: dict[str, Any],
    *,
    language: str,
    configured_language: str,
    country: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Choose a display variant and a *proven device-language* send variant.

    A foreign-language publication may be shown even when the configured Cookeo
    language has no sibling publication. It must then remain non-sendable rather
    than silently reusing the foreign variant as if it were device-compatible.
    """
    variants = [row for row in recipe.get("variants") or [] if isinstance(row, dict)]
    if not variants:
        return None, None
    requested = _language(language)
    configured = _language(configured_language)
    market = f"GS_{_text(country).upper()}"

    def display_score(row: dict[str, Any]) -> tuple[int, int, int, int]:
        lang = _variant_language(row)
        row_market = _variant_market(row)
        return (
            2 if lang == requested else 1 if lang == configured else 0,
            1 if row_market == market else 0,
            1 if row.get("cover") else 0,
            1 if _text(row.get("recipeFunctionalId") or row.get("variantId")) else 0,
        )

    def send_score(row: dict[str, Any]) -> tuple[int, int, int]:
        return (
            1 if _variant_market(row) == market else 0,
            1 if _text(row.get("recipeFunctionalId") or row.get("variantId")) else 0,
            1 if row.get("cover") else 0,
        )

    display = max(variants, key=display_score)
    send_candidates = [row for row in variants if _variant_language(row) == configured]
    send = max(send_candidates, key=send_score) if send_candidates else None
    return display, send


def _ingredient_search_values(raw: Any) -> list[str]:
    if not isinstance(raw, dict):
        return []
    source = _ingredient_reference(raw) or raw
    values = [
        _text(raw.get("originalName")),
        _text(source.get("canonicalName") or source.get("name") or source.get("foodName")),
    ]
    translations = source.get("translations")
    if isinstance(translations, dict):
        values.extend(_text(value) for value in translations.values())
    return [value for value in values if value]


def _recipe_search_text(recipe: dict[str, Any]) -> str:
    values = [_text(recipe.get("canonicalName"))]
    for ingredient in recipe.get("ingredients") or []:
        values.extend(_ingredient_search_values(ingredient))
    for variant in recipe.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        values.append(_text(variant.get("originalTitle")))
        values.append(_text(variant.get("title")))
        for ingredient in variant.get("ingredients") or []:
            values.extend(_ingredient_search_values(ingredient))
    return _norm(" ".join(value for value in values if value))


def _display_ingredient(raw: Any, language: str) -> Any:
    if not isinstance(raw, dict):
        return deepcopy(raw)
    source = _ingredient_reference(raw) or raw
    requested_language = _language(language)
    original_name = _text(raw.get("originalName"))
    original_language = _language(raw.get("originalLanguage"))
    translated_name = _translated_name(source, language) or _translated_name(raw, language)
    name = (
        original_name
        if original_name and original_language == requested_language
        else translated_name or original_name
    )
    ident = _text(
        raw.get("ingredientId")
        or raw.get("id")
        or source.get("id")
        or source.get("ingredientId")
        or raw.get("key")
        or source.get("key")
    )
    key = _text(
        raw.get("key")
        or raw.get("foodKey")
        or source.get("key")
        or source.get("foodKey")
    )
    row: dict[str, Any] = {}
    if ident:
        row["ingredientId"] = ident
    if key:
        row["key"] = key
        row["foodKey"] = key
    if name:
        row["name"] = name
        row["foodName"] = name
    if original_name:
        row["originalName"] = original_name
    if original_language:
        row["originalLanguage"] = original_language
    canonical = _text(source.get("canonicalName") or raw.get("canonicalName"))
    if canonical:
        row["canonicalName"] = canonical
    for field in ("quantity", "unit", "unitKey", "functionalId"):
        if raw.get(field) not in (None, ""):
            row[field] = deepcopy(raw[field])
    return row

def _recipe_row(
    recipe: dict[str, Any],
    *,
    language: str,
    configured_language: str,
    country: str,
) -> dict[str, Any] | None:
    display, send = _choose_variant(
        recipe,
        language=language,
        configured_language=configured_language,
        country=country,
    )
    if not display:
        return None
    grouping = _text(recipe.get("groupingFunctionalId") or display.get("groupingFunctionalId"))
    display_variant = _text(display.get("variantId") or display.get("searchVariantId"))
    send_grouping = _text(send.get("groupingFunctionalId") or grouping) if send else ""
    send_variant = _text(send.get("variantId") or send.get("searchVariantId")) if send else ""
    send_recipe = _text(send.get("recipeFunctionalId") or send_variant) if send else ""
    original_title = _text(display.get("originalTitle") or display.get("title"))
    original_language = _language(
        display.get("originalLanguage") or display.get("language")
    )
    requested_language = _language(language)
    fallback_title = _text(display.get("title")) or _text(recipe.get("canonicalName"))
    title = (
        original_title
        if original_title and original_language == requested_language
        else fallback_title or original_title
    )
    row: dict[str, Any] = {
        "groupingFunctionalId": grouping or None,
        "recipeFunctionalId": _text(display.get("recipeFunctionalId") or display_variant) or None,
        "variantFunctionalId": display_variant or None,
        "searchVariantId": display_variant or None,
        "displayVariantId": display_variant or None,
        "sendVariantId": send_variant or None,
        "sendGroupingFunctionalId": send_grouping or None,
        "sendRecipeFunctionalId": send_recipe or None,
        "title": title or None,
        "originalTitle": original_title or None,
        "originalLanguage": original_language or None,
        "canonicalName": _text(recipe.get("canonicalName")) or title or None,
        "cover": display.get("cover") or recipe.get("cover"),
        "language": _variant_language(display) or language,
        "market": _variant_market(display),
        "groupSize": display.get("servings") or recipe.get("servings"),
        "yield": deepcopy(display.get("yield") or recipe.get("yield")),
        "durations": deepcopy(display.get("durations") or recipe.get("durations") or {}),
        "difficulty": display.get("difficulty", recipe.get("difficulty")),
        "ingredients": [
            _display_ingredient(raw, language)
            for raw in (display.get("ingredients") or recipe.get("ingredients") or [])
        ],
        "nutrition": deepcopy(display.get("nutrition") or recipe.get("nutrition")),
        "catalogNutrition": deepcopy(display.get("nutrition") or recipe.get("nutrition")),
        "source": "cook4me_release_catalog",
        "releaseCatalogVersion": _text(load_release_catalog().get("catalogVersion")),
        "sendable": bool(send and send_grouping and send_variant and send_recipe),
        "variants": [
            {
                key: deepcopy(value)
                for key, value in {
                    "variantId": variant.get("variantId") or variant.get("searchVariantId"),
                    "recipeFunctionalId": variant.get("recipeFunctionalId"),
                    "groupingFunctionalId": variant.get("groupingFunctionalId"),
                    "title": variant.get("title"),
                    "originalTitle": variant.get("originalTitle") or variant.get("title"),
                    "language": variant.get("language"),
                    "originalLanguage": variant.get("originalLanguage") or variant.get("language"),
                    "market": variant.get("market"),
                    "servings": variant.get("servings"),
                    "yield": variant.get("yield"),
                    "cover": variant.get("cover"),
                }.items()
                if value not in (None, "", {}, [])
            }
            for variant in recipe.get("variants") or []
            if isinstance(variant, dict)
        ],
    }
    servings = sorted(
        {
            float(value)
            for variant in recipe.get("variants") or []
            if isinstance(variant, dict)
            if (value := variant.get("servings")) not in (None, "")
            if str(value).replace(".", "", 1).isdigit()
        }
    )
    if servings:
        row["availableServings"] = servings
    return {key: value for key, value in row.items() if value not in (None, "")}


def search_release_recipes(
    query: str,
    *,
    language: str,
    configured_language: str,
    country: str,
    page: int = 0,
    size: int = 20,
    strict_language: bool = False,
) -> dict[str, Any]:
    """Search the immutable merged catalog without network or full-row materialization."""
    page = max(0, int(page))
    size = max(1, min(_MAX_PAGE_SIZE, int(size)))
    wanted = _norm(query)
    payload = load_release_catalog()
    recipes = payload.get("recipes") or []
    requested = _language(language)
    by_language = payload.get("_runtimeRecipeByLanguage")
    if strict_language and isinstance(by_language, dict):
        candidate_indices = by_language.get(requested, ())
    else:
        candidate_indices = range(len(recipes))

    start = page * size
    end = start + size
    total = 0
    items: list[dict[str, Any]] = []
    for index in candidate_indices:
        try:
            raw = recipes[index]
        except (IndexError, TypeError):
            continue
        if not isinstance(raw, dict):
            continue
        if wanted and wanted not in _recipe_search_text(raw):
            continue
        if start <= total < end:
            row = _recipe_row(
                raw,
                language=language,
                configured_language=configured_language,
                country=country,
            )
            if row:
                items.append(row)
        total += 1

    total_pages = (total + size - 1) // size if total else 0
    return {
        "ok": True,
        "query": _text(query),
        "requestedLanguage": _text(language).lower(),
        "configuredLanguage": _text(configured_language).lower(),
        "market": f"GS_{_text(country).upper()}",
        "page": {
            "number": page,
            "size": size,
            "totalElements": total,
            "totalPages": total_pages,
        },
        "rawVariantCount": int(payload.get("_runtimeRawVariantCount") or 0),
        "groupedRecipeCount": len(items),
        "items": items,
        "cacheHit": True,
        "checkedOnline": False,
        "offline": True,
        "strictLanguage": bool(strict_language),
        "searchContract": "repo-release-merged-catalog-v1",
        "catalogVersion": _text(payload.get("catalogVersion")),
    }


def recipe_by_variant(
    variant_id: str,
    *,
    language: str,
    configured_language: str,
    country: str,
) -> dict[str, Any] | None:
    wanted = _text(variant_id)
    if not wanted:
        return None
    for raw in load_release_catalog().get("recipes") or []:
        if not isinstance(raw, dict):
            continue
        variants = raw.get("variants") or []
        if any(
            isinstance(variant, dict)
            and _text(variant.get("variantId") or variant.get("searchVariantId")) == wanted
            for variant in variants
        ):
            return _recipe_row(
                raw,
                language=language,
                configured_language=configured_language,
                country=country,
            )
    return None
