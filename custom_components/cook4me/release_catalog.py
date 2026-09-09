from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any

_SCHEMA_VERSION = 1
_CATALOG_PATH = Path(__file__).parent / "catalog" / "release_catalog.json"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _language(value: Any) -> str:
    return _text(value).lower().replace("_", "-").split("-", 1)[0]


def _tokens(value: Any) -> set[str]:
    return {part for part in re.split(r"[^\w]+", _text(value).casefold()) if part}


def _matches_query(recipe: dict[str, Any], query: str) -> bool:
    wanted = _tokens(query)
    if not wanted:
        return True
    fields = [
        recipe.get("canonicalTitle"),
        recipe.get("fallbackTitle"),
        *((recipe.get("titles") or {}).values() if isinstance(recipe.get("titles"), dict) else ()),
    ]
    haystack = set()
    for value in fields:
        haystack.update(_tokens(value))
    return wanted <= haystack or all(any(token in candidate for candidate in haystack) for token in wanted)


def _variant_for_language(recipe: dict[str, Any], language: str) -> dict[str, Any] | None:
    variants = [row for row in recipe.get("variants") or [] if isinstance(row, dict)]
    if not variants:
        return None
    wanted = _language(language)
    exact = next((row for row in variants if _language(row.get("language")) == wanted), None)
    if exact is not None:
        return exact
    english = next((row for row in variants if _language(row.get("language")) == "en"), None)
    return english or variants[0]


def _release_audit_complete(release: dict[str, Any]) -> bool:
    """Return true only for an explicitly complete, non-partial release audit."""
    if not bool(release.get("complete")):
        return False
    if release.get("failedLanguages"):
        return False
    try:
        if int(release.get("failedDetailCount") or 0) > 0:
            return False
    except (TypeError, ValueError):
        return False
    audits = release.get("languageAudit")
    if isinstance(audits, list) and any(
        bool(row.get("truncated")) for row in audits if isinstance(row, dict)
    ):
        return False
    return True


def _recipe_card(recipe: dict[str, Any], language: str) -> dict[str, Any]:
    variant = _variant_for_language(recipe, language)
    titles = recipe.get("titles") if isinstance(recipe.get("titles"), dict) else {}
    title = _text(titles.get(_language(language))) or _text(recipe.get("canonicalTitle")) or _text(recipe.get("fallbackTitle"))
    result = {
        "releaseCatalogId": _text(recipe.get("id")),
        "title": title,
        "canonicalTitle": _text(recipe.get("canonicalTitle")),
        "language": _language((variant or {}).get("language") or language),
        "source": "cook4me_release_catalog",
        "releaseCatalog": True,
    }
    for key in (
        "ingredients",
        "nutrition",
        "officialNutrition",
        "courses",
        "occasions",
        "excludedFoods",
        "detectedExcludedFoods",
        "durations",
        "yield",
        "difficulty",
        "recipeType",
        "groupSize",
        "cover",
        "mealTypes",
    ):
        if key in recipe:
            result[key] = deepcopy(recipe[key])
    if variant:
        for source, target in (
            ("variantId", "searchVariantId"),
            ("variantId", "variantFunctionalId"),
            ("recipeFunctionalId", "recipeFunctionalId"),
            ("groupingFunctionalId", "groupingFunctionalId"),
            ("market", "market"),
            ("cover", "cover"),
            ("yield", "yield"),
            ("groupSize", "groupSize"),
        ):
            value = variant.get(source)
            if value not in (None, ""):
                result[target] = deepcopy(value)
        result["displayVariantId"] = variant.get("variantId")
        result["sendVariantId"] = variant.get("variantId")
        result["sendGroupingFunctionalId"] = variant.get("groupingFunctionalId")
        result["sendRecipeFunctionalId"] = variant.get("recipeFunctionalId") or variant.get("variantId")
        result["sendable"] = bool(
            result.get("sendVariantId")
            and result.get("sendGroupingFunctionalId")
            and result.get("sendRecipeFunctionalId")
        )
    result["variants"] = deepcopy(recipe.get("variants") or [])
    return {key: value for key, value in result.items() if value not in (None, "")}


class Cook4MeReleaseCatalog:
    """Immutable compact catalog shipped with an integration release.

    Runtime code never mutates this file. Detailed recipes, translations and
    prices remain local/persistent runtime caches. A release snapshot is used
    only when the release audit is explicitly complete, so an interrupted
    catalog build cannot hide the proven live SEB fallback.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        release = payload.get("release") if isinstance(payload.get("release"), dict) else {}
        self.release = deepcopy(release)
        self.ingredients = [deepcopy(row) for row in payload.get("ingredients") or [] if isinstance(row, dict)]
        self.recipes = [deepcopy(row) for row in payload.get("recipes") or [] if isinstance(row, dict)]
        self._ingredients_by_id = {
            _text(row.get("id")): row for row in self.ingredients if _text(row.get("id"))
        }
        self._recipes_by_id = {
            _text(row.get("id")): row for row in self.recipes if _text(row.get("id"))
        }

    @property
    def complete(self) -> bool:
        return _release_audit_complete(self.release)

    @property
    def usable(self) -> bool:
        return self.complete and bool(self.recipes) and bool(self.ingredients)

    def metadata(self) -> dict[str, Any]:
        return {
            **deepcopy(self.release),
            "schemaVersion": _SCHEMA_VERSION,
            "ingredientCount": len(self.ingredients),
            "recipeCount": len(self.recipes),
            "auditComplete": self.complete,
            "usable": self.usable,
        }

    def ingredient(self, identity: str) -> dict[str, Any] | None:
        row = self._ingredients_by_id.get(_text(identity))
        return deepcopy(row) if row is not None else None

    def ingredient_rows(self, language: str = "en") -> list[dict[str, Any]]:
        wanted = _language(language)
        out: list[dict[str, Any]] = []
        for raw in self.ingredients:
            names = raw.get("names") if isinstance(raw.get("names"), dict) else {}
            name = _text(names.get(wanted)) or _text(raw.get("canonicalName")) or _text(raw.get("fallbackName"))
            if not name:
                continue
            row: dict[str, Any] = {"key": _text(raw.get("id")), "name": name}
            if raw.get("nutrition") is not None:
                row["nutrition"] = deepcopy(raw["nutrition"])
            if raw.get("canonicalName"):
                row["canonicalName"] = _text(raw.get("canonicalName"))
            out.append(row)
        return out

    def recipes_for_language(self, language: str, query: str = "", size: int = 50) -> list[dict[str, Any]]:
        wanted = _language(language)
        out: list[dict[str, Any]] = []
        for recipe in self.recipes:
            if not _matches_query(recipe, query):
                continue
            variants = [row for row in recipe.get("variants") or [] if isinstance(row, dict)]
            if wanted and variants and not any(_language(row.get("language")) == wanted for row in variants):
                continue
            out.append(_recipe_card(recipe, wanted or "en"))
            if len(out) >= max(1, int(size)):
                break
        return out

    def search(self, languages: list[str], query: str = "", size: int = 20) -> list[dict[str, Any]]:
        selected = [_language(value) for value in languages if _language(value)] or ["en"]
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for language in selected:
            for row in self.recipes_for_language(language, query=query, size=max(size, 1)):
                identity = _text(row.get("releaseCatalogId")) or _text(row.get("groupingFunctionalId")) or _text(row.get("searchVariantId"))
                if identity and identity in seen:
                    continue
                if identity:
                    seen.add(identity)
                row["officialCatalogLanguage"] = language
                out.append(row)
                if len(out) >= max(1, int(size)):
                    return out
        return out


def load_release_catalog(path: Path | str | None = None) -> Cook4MeReleaseCatalog:
    source = Path(path) if path is not None else _CATALOG_PATH
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict) or int(payload.get("schemaVersion") or 0) != _SCHEMA_VERSION:
        payload = {
            "schemaVersion": _SCHEMA_VERSION,
            "release": {"id": "invalid", "complete": False},
            "ingredients": [],
            "recipes": [],
        }
    return Cook4MeReleaseCatalog(payload)


_RELEASE_CATALOG: Cook4MeReleaseCatalog | None = None


def release_catalog() -> Cook4MeReleaseCatalog:
    global _RELEASE_CATALOG
    if _RELEASE_CATALOG is None:
        _RELEASE_CATALOG = load_release_catalog()
    return _RELEASE_CATALOG
