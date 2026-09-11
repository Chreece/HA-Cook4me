from __future__ import annotations

from functools import lru_cache
import importlib.util
from pathlib import Path
from typing import Any, Iterable

try:
    from . import release_catalog_v60_core as _core
    from . import recipe_safety_index_v60 as _safety
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

    _core = _load_sibling(
        "cook4me_release_catalog_v60_core_test", "release_catalog_v60_core.py"
    )
    _safety = _load_sibling(
        "cook4me_recipe_safety_runtime_test", "recipe_safety_index_v60.py"
    )

_SCHEMA_VERSION = _core._SCHEMA_VERSION
_CATALOG_PATH = _core._CATALOG_PATH
_MAX_PAGE_SIZE = _core._MAX_PAGE_SIZE


def _text(value: Any) -> str:
    return _core._text(value)


def _valid_precompiled_safety(payload: dict[str, Any], value: Any) -> bool:
    return bool(
        isinstance(value, dict)
        and value.get("kind") == "cook4me-recipe-safety-index"
        and int(value.get("schemaVersion") or 0) == 1
        and int(value.get("recipeCount") or 0)
        == len(payload.get("recipes") or [])
    )


def _prepare_safety_index(payload: dict[str, Any]) -> None:
    compiled = payload.get("recipeSafetyIndex")
    precompiled = _valid_precompiled_safety(payload, compiled)
    if not precompiled:
        # Backward-compatible fallback for old/dev catalogs. Release v60 builds
        # ship recipeSafetyIndex so production startup only prepares frozen sets.
        compiled = _safety.compile_recipe_safety_index(payload)
    payload["_runtimeRecipeSafetyIndex"] = _safety.prepare_recipe_safety_index(
        compiled
    )
    payload["_runtimeSafetyPrecompiled"] = precompiled


@lru_cache(maxsize=1)
def load_release_catalog() -> dict[str, Any]:
    """Load once, prepare search/identity core once, then prepare safety sets."""
    _core._CATALOG_PATH = _CATALOG_PATH
    _core.load_release_catalog.cache_clear()
    payload = _core.load_release_catalog()
    # Core performs _prepare_fast_indexes(payload) and exposes _runtimeSearchIndex.
    _prepare_safety_index(payload)
    return payload


async def async_warm_release_catalog(hass: Any) -> dict[str, Any]:
    """Parse and prepare all immutable release indexes off the HA event loop."""
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
    summary = dict(_core.release_catalog_summary())
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    runtime_safety = (
        payload.get("_runtimeRecipeSafetyIndex")
        if isinstance(payload.get("_runtimeRecipeSafetyIndex"), dict)
        else {}
    )
    summary.update(
        {
            "compiledSafetyReady": bool(runtime_safety.get("_prepared")),
            "compiledSafetyPrebuilt": bool(payload.get("_runtimeSafetyPrecompiled")),
            "compiledSafetyRecipeCount": int(runtime_safety.get("recipeCount") or 0),
            "strictDietAllergyUnknownIsSafe": False,
            "dietAllergyIntelligenceComplete": bool(
                source.get("dietAllergyIntelligenceComplete")
            ),
        }
    )
    return summary


def ingredient_rows(
    language: str,
    query: str = "",
    *,
    limit: int | None = None,
    include_nutrition: bool = False,
    food_only: bool = True,
) -> list[dict[str, Any]]:
    load_release_catalog()
    return _core.ingredient_rows(
        language,
        query,
        limit=limit,
        include_nutrition=include_nutrition,
        food_only=food_only,
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
    diet: str = "",
    allergies: Iterable[str] = (),
) -> dict[str, Any]:
    """Intersect precompiled search and strict safety sets before pagination."""
    page = max(0, int(page))
    size = max(1, min(_MAX_PAGE_SIZE, int(size)))
    payload = load_release_catalog()
    recipes = payload.get("recipes") or []
    runtime_search = payload.get("_runtimeSearchIndex") or {}
    runtime_safety = payload.get("_runtimeRecipeSafetyIndex") or {}
    allergy_values = tuple(
        dict.fromkeys(_text(value).lower() for value in allergies if _text(value))
    )
    diet_value = _text(diet).lower()
    safety_filtered = bool(diet_value or allergy_values)
    allowed = (
        _safety.allowed_recipe_indices(
            runtime_safety,
            diet=diet_value,
            allergies=allergy_values,
        )
        if safety_filtered
        else None
    )

    match = _core.search_index(
        runtime_search,
        query,
        language=language,
        strict_language=strict_language,
        allowed_indices=allowed,
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
        row = _core._enrich_recipe_row(
            payload,
            _core._legacy._recipe_row(
                raw,
                language=language,
                configured_language=configured_language,
                country=country,
            ),
        )
        if row:
            if recipe_index in scores:
                row["searchScore"] = scores[recipe_index]
            if safety_filtered:
                row["safety"] = _safety.recipe_safety(
                    runtime_safety,
                    recipe_index,
                    diet=diet_value,
                    allergies=allergy_values,
                )
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
        "safetyFiltered": safety_filtered,
        "diet": diet_value,
        "allergies": list(allergy_values),
        "safetyContract": "strict-precompiled-recipe-safety-v1",
        "safetyIndexPrebuilt": bool(payload.get("_runtimeSafetyPrecompiled")),
        "catalogVersion": _text(payload.get("catalogVersion")),
    }


def recipe_by_variant(
    variant_id: str,
    *,
    language: str,
    configured_language: str,
    country: str,
) -> dict[str, Any] | None:
    load_release_catalog()
    return _core.recipe_by_variant(
        variant_id,
        language=language,
        configured_language=configured_language,
        country=country,
    )


def __getattr__(name: str):
    """Preserve the established release-catalog helper API."""
    return getattr(_core, name)
