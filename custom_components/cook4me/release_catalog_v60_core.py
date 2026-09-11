from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import importlib.util
from pathlib import Path
from typing import Any, Iterable

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
_NON_FOOD_CLASSIFICATIONS = {"equipment", "other", "ambiguous"}
_INGREDIENT_METADATA_FIELDS = (
    "conceptId",
    "classification",
    "sourceLocalIdentity",
    "providerIdentityAssigned",
    "semanticIdentityState",
    "semanticMergePolicy",
    "reviewConfidence",
    "nutritionEligible",
    "dietEligible",
    "allergenEligible",
    "needsSemanticConfirmation",
)


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
    concepts: dict[str, list[dict[str, Any]]] = {}
    for raw in payload.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        concept_id = _text(raw.get("conceptId"))
        if concept_id:
            concepts.setdefault(concept_id, []).append(raw)

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
    payload["_runtimeIngredientsByConcept"] = {
        concept_id: tuple(rows) for concept_id, rows in concepts.items()
    }


def _global_ingredient(payload: dict[str, Any], row: Any) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    lookup = payload.get("_runtimeIngredientById")
    if not isinstance(lookup, dict):
        return None
    for value in (
        row.get("ingredientId"),
        row.get("id"),
        row.get("key"),
        row.get("foodKey"),
    ):
        ident = _text(value)
        if ident and isinstance(lookup.get(ident), dict):
            return lookup[ident]
    return None


def _enrich_display_ingredient(
    payload: dict[str, Any], row: Any
) -> Any:
    if not isinstance(row, dict):
        return deepcopy(row)
    out = deepcopy(row)
    source = _global_ingredient(payload, row)
    if not isinstance(source, dict):
        return out
    for field in _INGREDIENT_METADATA_FIELDS:
        if source.get(field) not in (None, "", {}, []):
            out[field] = deepcopy(source[field])
    return out


def _enrich_recipe_row(
    payload: dict[str, Any], row: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return row
    out = deepcopy(row)
    out["ingredients"] = [
        _enrich_display_ingredient(payload, ingredient)
        for ingredient in row.get("ingredients") or []
    ]
    return out


def _alias_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        if text := _text(value):
            yield text
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _alias_strings(nested)
        return
    if isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _alias_strings(nested)


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
        "semanticIngredientConcepts": bool(source.get("semanticIngredientConcepts")),
        "semanticCoverageComplete": bool(source.get("semanticCoverageComplete")),
        "ingredientIntelligenceComplete": bool(source.get("ingredientIntelligenceComplete")),
        "sourceLocalIngredientCount": int(source.get("sourceLocalIngredientCount") or 0),
    }


def ingredient_rows(
    language: str,
    query: str = "",
    *,
    limit: int | None = None,
    include_nutrition: bool = False,
    food_only: bool = True,
) -> list[dict[str, Any]]:
    """Return compact localized ingredient choices with semantic identity.

    Equipment/other/ambiguous reviewed rows are hidden from the normal food
    picker by default, but remain in the catalog and multilingual search index.
    Nutrient blobs remain opt-in so dashboard/picker startup stays lightweight.
    """
    payload = load_release_catalog()
    wanted = _legacy._norm(query)
    maximum = None if limit is None else max(1, int(limit))
    out: list[dict[str, Any]] = []
    for raw in payload.get("ingredients") or []:
        if not isinstance(raw, dict):
            continue
        classification = _text(raw.get("classification")).lower()
        if food_only and classification in _NON_FOOD_CLASSIFICATIONS:
            continue
        name = _legacy._translated_name(raw, language)
        if not name:
            continue
        haystack_values = [name, _text(raw.get("canonicalName"))]
        haystack_values.extend(
            _text(value)
            for value in (raw.get("translations") or {}).values()
            if _text(value)
        )
        haystack_values.extend(_alias_strings(raw.get("aliases")))
        if wanted and wanted not in _legacy._norm(" ".join(haystack_values)):
            continue

        row: dict[str, Any] = {"name": name}
        ident = _text(
            raw.get("id")
            or raw.get("ingredientId")
            or raw.get("key")
            or raw.get("foodKey")
        )
        key = _text(raw.get("key") or raw.get("foodKey"))
        if ident:
            row["id"] = ident
            row["ingredientId"] = ident
        if key:
            row["key"] = key
            row["foodKey"] = key
        canonical = _text(raw.get("canonicalName"))
        if canonical:
            row["canonicalName"] = canonical
        for field in _INGREDIENT_METADATA_FIELDS:
            if raw.get(field) not in (None, "", {}, []):
                row[field] = deepcopy(raw[field])
        if include_nutrition and isinstance(raw.get("nutrition"), dict):
            row["nutrition"] = deepcopy(raw["nutrition"])
        out.append(row)
        if maximum is not None and len(out) >= maximum:
            break
    return out


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
        row = _enrich_recipe_row(
            payload,
            _legacy._recipe_row(
                raw,
                language=language,
                configured_language=configured_language,
                country=country,
            ),
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
    return _enrich_recipe_row(
        payload,
        _legacy._recipe_row(
            raw,
            language=language,
            configured_language=configured_language,
            country=country,
        ),
    )


def __getattr__(name: str):
    """Preserve compatibility for helpers not overridden by the v60 facade."""
    return getattr(_legacy, name)
