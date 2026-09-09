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


@lru_cache(maxsize=1)
def load_release_catalog() -> dict[str, Any]:
    """Load the immutable release catalog shipped with the integration.

    Runtime code must never mutate this object. Callers receive deep copies from
    the public lookup helpers below.
    """
    try:
        payload = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "schemaVersion": _SCHEMA_VERSION,
            "catalogVersion": "missing",
            "complete": False,
            "ingredients": [],
            "recipes": [],
        }
    if not isinstance(payload, dict) or int(payload.get("schemaVersion") or 0) != _SCHEMA_VERSION:
        return {
            "schemaVersion": _SCHEMA_VERSION,
            "catalogVersion": "invalid",
            "complete": False,
            "ingredients": [],
            "recipes": [],
        }
    if not isinstance(payload.get("ingredients"), list):
        payload["ingredients"] = []
    if not isinstance(payload.get("recipes"), list):
        payload["recipes"] = []
    return payload


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
    language = _text(language).lower().replace("_", "-").split("-", 1)[0]
    return (
        _text(translations.get(language))
        or _text(row.get("canonicalName"))
        or _text(row.get("name"))
    )


def ingredient_rows(language: str, query: str = "", *, limit: int = 5000) -> list[dict[str, Any]]:
    """Return offline ingredient choices in the requested UI/catalog language."""
    wanted = _norm(query)
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
        key = _text(raw.get("key") or raw.get("foodKey"))
        if key:
            row["key"] = key
        if _text(raw.get("canonicalName")):
            row["canonicalName"] = _text(raw.get("canonicalName"))
        if isinstance(raw.get("nutrition"), dict):
            row["nutrition"] = deepcopy(raw["nutrition"])
        out.append(row)
        if len(out) >= max(1, int(limit)):
            break
    return out


def _variant_language(row: dict[str, Any]) -> str:
    return _text(row.get("language")).lower().replace("_", "-").split("-", 1)[0]


def _variant_market(row: dict[str, Any]) -> str:
    return _text(row.get("market")).upper()


def _choose_variant(
    recipe: dict[str, Any],
    *,
    language: str,
    configured_language: str,
    country: str,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    variants = [row for row in recipe.get("variants") or [] if isinstance(row, dict)]
    if not variants:
        return None, None
    requested = _text(language).lower().replace("_", "-").split("-", 1)[0]
    configured = _text(configured_language).lower().replace("_", "-").split("-", 1)[0]
    market = f"GS_{_text(country).upper()}"

    def score(row: dict[str, Any], preferred: str) -> tuple[int, int, int, int]:
        lang = _variant_language(row)
        row_market = _variant_market(row)
        return (
            2 if lang == preferred else 1 if lang == configured else 0,
            1 if row_market == market else 0,
            1 if row.get("cover") else 0,
            1 if _text(row.get("recipeFunctionalId") or row.get("variantId")) else 0,
        )

    display = max(variants, key=lambda row: score(row, requested))
    send = max(variants, key=lambda row: score(row, configured))
    return display, send


def _recipe_search_text(recipe: dict[str, Any]) -> str:
    values = [_text(recipe.get("canonicalName"))]
    for variant in recipe.get("variants") or []:
        if isinstance(variant, dict):
            values.append(_text(variant.get("title")))
    for ingredient in recipe.get("ingredients") or []:
        if isinstance(ingredient, dict):
            values.append(_text(ingredient.get("canonicalName") or ingredient.get("name")))
            translations = ingredient.get("translations")
            if isinstance(translations, dict):
                values.extend(_text(value) for value in translations.values())
    return _norm(" ".join(value for value in values if value))


def _display_ingredient(raw: Any, language: str) -> Any:
    if not isinstance(raw, dict):
        return deepcopy(raw)
    row = deepcopy(raw)
    name = _translated_name(row, language)
    if name:
        row["name"] = name
        row.setdefault("foodName", name)
    key = _text(row.get("key") or row.get("foodKey"))
    if key:
        row["key"] = key
        row["foodKey"] = key
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
    if not display or not send:
        return None
    grouping = _text(recipe.get("groupingFunctionalId") or display.get("groupingFunctionalId"))
    display_variant = _text(display.get("variantId") or display.get("searchVariantId"))
    send_variant = _text(send.get("variantId") or send.get("searchVariantId"))
    send_recipe = _text(send.get("recipeFunctionalId") or send_variant)
    title = _text(display.get("title")) or _text(recipe.get("canonicalName"))
    row: dict[str, Any] = {
        "groupingFunctionalId": grouping or None,
        "recipeFunctionalId": _text(display.get("recipeFunctionalId") or display_variant) or None,
        "variantFunctionalId": display_variant or None,
        "searchVariantId": display_variant or None,
        "displayVariantId": display_variant or None,
        "sendVariantId": send_variant or None,
        "sendGroupingFunctionalId": grouping or None,
        "sendRecipeFunctionalId": send_recipe or None,
        "title": title or None,
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
        "officialNutrition": deepcopy(
            display.get("officialNutrition") or recipe.get("officialNutrition")
        ),
        "catalogNutrition": deepcopy(display.get("nutrition") or recipe.get("nutrition")),
        "source": "cook4me_release_catalog",
        "releaseCatalogVersion": _text(load_release_catalog().get("catalogVersion")),
        "sendable": bool(grouping and send_variant and send_recipe),
        "variants": deepcopy(recipe.get("variants") or []),
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
    """Search the immutable merged catalog without network or persistent I/O."""
    page = max(0, int(page))
    size = max(1, min(_MAX_PAGE_SIZE, int(size)))
    wanted = _norm(query)
    matches: list[dict[str, Any]] = []
    for raw in load_release_catalog().get("recipes") or []:
        if not isinstance(raw, dict):
            continue
        if wanted and wanted not in _recipe_search_text(raw):
            continue
        if strict_language:
            requested = _text(language).lower().replace("_", "-").split("-", 1)[0]
            if not any(
                isinstance(variant, dict) and _variant_language(variant) == requested
                for variant in (raw.get("variants") or [])
            ):
                continue
        row = _recipe_row(
            raw,
            language=language,
            configured_language=configured_language,
            country=country,
        )
        if row:
            matches.append(row)
    start = page * size
    items = matches[start : start + size]
    total = len(matches)
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
        "rawVariantCount": sum(len(row.get("variants") or []) for row in load_release_catalog().get("recipes") or []),
        "groupedRecipeCount": len(items),
        "items": items,
        "cacheHit": True,
        "checkedOnline": False,
        "offline": True,
        "strictLanguage": bool(strict_language),
        "searchContract": "repo-release-merged-catalog-v1",
        "catalogVersion": _text(load_release_catalog().get("catalogVersion")),
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
