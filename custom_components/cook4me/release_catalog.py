from __future__ import annotations

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing import Any

try:
    from . import release_catalog_legacy as _legacy
    from .catalog_search_index import (
        compile_search_index,
        prepare_search_index,
        search_index,
    )
except ImportError:  # Standalone unit-test import via spec_from_file_location.
    def _load_sibling(module_name: str, filename: str):
        spec = importlib.util.spec_from_file_location(
            module_name, Path(__file__).with_name(filename)
        )
        if spec is None or spec.loader is None:
            raise ImportError(filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    _legacy = _load_sibling(
        "cook4me_release_catalog_legacy_test", "release_catalog_legacy.py"
    )
    _search_module = _load_sibling(
        "cook4me_catalog_search_index_runtime_test", "catalog_search_index.py"
    )
    compile_search_index = _search_module.compile_search_index
    prepare_search_index = _search_module.prepare_search_index
    search_index = _search_module.search_index


_SCHEMA_VERSION = _legacy._SCHEMA_VERSION
_CATALOG_PATH = _legacy._CATALOG_PATH
_MAX_PAGE_SIZE = _legacy._MAX_PAGE_SIZE


def _text(value: Any) -> str:
    return _legacy._text(value)


def _language(value: Any) -> str:
    return _legacy._language(value)


def _valid_precompiled_index(payload: dict[str, Any], compiled: Any) -> bool:
    return bool(
        isinstance(compiled, dict)
        and compiled.get("kind") == "cook4me-multilingual-recipe-search-index"
        and int(compiled.get("schemaVersion") or 0) == 1
        and int(compiled.get("recipeCount") or 0)
        == len(payload.get("recipes") or [])
    )


def _prepare_fast_indexes(payload: dict[str, Any]) -> None:
    compiled = payload.get("searchIndex")
    precompiled = _valid_precompiled_index(payload, compiled)
    if not precompiled:
        # Backward-compatible fallback for old/dev catalog files. Production
        # release builds should ship searchIndex so this work stays build-time.
        compiled = compile_search_index(payload)
    payload["_runtimeSearchIndex"] = prepare_search_index(compiled)
    payload["_runtimeSearchPrecompiled"] = precompiled

    variants: dict[str, int] = {}
    for recipe_index, recipe in enumerate(payload.get("recipes") or []):
        if not isinstance(recipe, dict):
            continue
        for variant in recipe.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            ident = _text(
                variant.get("variantId")
                or variant.get("searchVariantId")
                or variant.get("recipeFunctionalId")
            )
            if ident:
                variants.setdefault(ident, recipe_index)
    payload["_runtimeRecipeByVariant"] = variants


@lru_cache(maxsize=1)
def load_release_catalog() -> dict[str, Any]:
    """Load the immutable catalog and prepare compiled runtime lookup structures."""
    _legacy._CATALOG_PATH = _CATALOG_PATH
    _legacy.load_release_catalog.cache_clear()
    payload = _legacy.load_release_catalog()
    _prepare_fast_indexes(payload)
    return payload


async def async_warm_release_catalog(hass: Any) -> dict[str, Any]:
    """Parse and prepare the release catalog outside Home Assistant's event loop."""
    return await hass.async_add_executor_job(load_release_catalog)


def release_catalog_ready() -> bool:
    payload = load_release_catalog()
    return bool(
        payload.get("complete")
        and isinstance(payload.get("recipes"), list)
        and payload.get("recipes")
        and isinstance(payload.get("ingredients"), list)
        and payload.get("ingredients")
    )


def release_catalog_summary() -> dict[str, Any]:
    payload = load_release_catalog()
    source = (
        payload.get("source")
        if isinstance(payload.get("source"), dict)
        else {}
    )
    runtime_index = (
        payload.get("_runtimeSearchIndex")
        if isinstance(payload.get("_runtimeSearchIndex"), dict)
        else {}
    )
    return {
        "schemaVersion": _SCHEMA_VERSION,
        "catalogVersion": _text(payload.get("catalogVersion")),
        "complete": bool(payload.get("complete")),
        "generatedAt": _text(payload.get("generatedAt")),
        "ingredientCount": len(payload.get("ingredients") or []),
        "recipeCount": len(payload.get("recipes") or []),
        "sourceCatalogCount": int(source.get("sourceCatalogCount") or 0),
        "auditedCatalogCount": int(
            source.get("auditedCatalogCount")
            or source.get("sourceCatalogCount")
            or 0
        ),
        "offlineSearchReady": release_catalog_ready(),
        "compiledSearchReady": bool(runtime_index.get("_prepared")),
        "compiledSearchPrebuilt": bool(payload.get("_runtimeSearchPrecompiled")),
        "compiledSearchStats": dict(runtime_index.get("stats") or {}),
    }


def ingredient_rows(
    language: str,
    query: str = "",
    *,
    limit: int | None = None,
    include_nutrition: bool = False,
) -> list[dict[str, Any]]:
    # Prime the legacy loader with this wrapper's selected catalog path first.
    load_release_catalog()
    return _legacy.ingredient_rows(
        language,
        query,
        limit=limit,
        include_nutrition=include_nutrition,
    )


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
    """Search precompiled postings and materialize only the requested page."""
    page = max(0, int(page))
    size = max(1, min(_MAX_PAGE_SIZE, int(size)))
    payload = load_release_catalog()
    recipes = payload.get("recipes") or []
    runtime_index = payload.get("_runtimeSearchIndex") or {}
    match = search_index(
        runtime_index,
        query,
        language=language,
        strict_language=strict_language,
        page=page,
        size=size,
    )

    items: list[dict[str, Any]] = []
    scores = match.get("scores") if isinstance(match.get("scores"), dict) else {}
    for recipe_index in match.get("indices") or []:
        try:
            raw = recipes[recipe_index]
        except (IndexError, TypeError):
            continue
        if not isinstance(raw, dict):
            continue
        row = _legacy._recipe_row(
            raw,
            language=language,
            configured_language=configured_language,
            country=country,
        )
        if row:
            if recipe_index in scores:
                row["searchScore"] = scores[recipe_index]
            items.append(row)

    total = int(match.get("total") or 0)
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
        "searchContract": "repo-release-compiled-multilingual-index-v2",
        "searchIndexPrebuilt": bool(payload.get("_runtimeSearchPrecompiled")),
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
    payload = load_release_catalog()
    lookup = payload.get("_runtimeRecipeByVariant")
    if not isinstance(lookup, dict):
        return None
    recipe_index = lookup.get(wanted)
    if not isinstance(recipe_index, int):
        return None
    recipes = payload.get("recipes") or []
    try:
        raw = recipes[recipe_index]
    except (IndexError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    return _legacy._recipe_row(
        raw,
        language=language,
        configured_language=configured_language,
        country=country,
    )


def __getattr__(name: str):
    """Preserve compatibility for helpers not overridden by the v60 facade."""
    return getattr(_legacy, name)
