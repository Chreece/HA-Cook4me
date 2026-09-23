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
            "catalogLanguages": sorted((payload.get("_runtimeSearchIndex") or {}).get("recipeLanguages", {})),
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


def ingredient_nutrition_profile(ingredient: Any) -> dict[str, Any] | None:
    load_release_catalog()
    return _core.ingredient_nutrition_profile(ingredient)


def ingredient_choices(language: str, query: str = "", limit: int | None = None):
    return _core._presentation.ingredient_choices(load_release_catalog(), language, query, limit)


def ingredient_display_name(ingredient: Any, language: str) -> str:
    raw = _core._global_ingredient(load_release_catalog(), ingredient)
    return _core._presentation.display_name(raw or ingredient, language)


def ingredient_stock_identities(ingredient: Any) -> tuple[str, ...]:
    """Return stable inventory identities for one semantic ingredient concept.

    The release catalog can contain language/market-specific source ingredient
    IDs for the same reviewed concept. Inventory lots may have been linked
    through any of those source rows, while a recipe can reference another one.
    Only exact catalog concept membership is expanded; names are never fuzzily
    merged here.
    """
    payload = load_release_catalog()
    raw = ingredient if isinstance(ingredient, dict) else {}
    source = _core._global_ingredient(payload, raw)
    rows: list[dict[str, Any]] = []
    if isinstance(source, dict):
        concept_id = _text(source.get("conceptId"))
        if concept_id:
            rows.extend(
                row
                for row in (payload.get("_runtimeIngredientsByConcept") or {}).get(
                    concept_id, ()
                )
                if isinstance(row, dict)
            )
        if not rows:
            rows.append(source)
    if isinstance(raw, dict):
        rows.append(raw)

    identities: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for field in ("key", "foodKey", "ingredientId", "id"):
            value = _text(row.get(field))
            if not value:
                continue
            identity = f"k:{value}"
            if identity not in seen:
                seen.add(identity)
                identities.append(identity)
        for value in row.get("sourceIngredientIds") or []:
            value = _text(value)
            identity = f"k:{value}" if value else ""
            if identity and identity not in seen:
                seen.add(identity)
                identities.append(identity)
    return tuple(identities)


def ingredient_nutrition_references(ingredient: Any, language: str):
    """Offer explicitly different food types for comparison, not an assigned profile."""
    payload = load_release_catalog()
    source = _core._global_ingredient(payload, ingredient)
    if not source or ingredient_nutrition_profile(ingredient):
        return []
    wanted = _core._presentation.name_key(source.get("canonicalName", ""))
    if not wanted or len(wanted.split()) > 2:
        return []
    candidates = []
    for raw in payload.get("ingredients", []):
        name = _core._presentation.name_key(_core._presentation.clean_name(raw.get("canonicalName")))
        if name == wanted or not name.endswith(" "+wanted) or not raw.get("nutrition"):
            continue
        profile = ingredient_nutrition_profile({"ingredientId": raw["id"]})
        if profile:
            candidates.append((name, raw, profile))
    candidates.sort(key=lambda value: (value[0] not in {"cooked rice", "basmati rice", "brown rice"}, len(value[0]), value[0]))
    output, seen = [], set()
    for name, raw, profile in candidates:
        key = (name, str(profile.get("sourceId")))
        if key in seen:
            continue
        seen.add(key)
        output.append({"ingredientId": raw["id"], "name": _core._presentation.display_name(raw, language), "nutrition": profile, "referenceOnly": True})
        if len(output) == 4:
            break
    return output


def _display_family_row(payload, members, language, configured_language, country, preferred_variant=""):
    def materialize(raw, variant_id, display_language, enrich=True):
        row = _core._legacy._recipe_row(raw, language=display_language, configured_language=configured_language, country=country, variant_id=variant_id)
        return _core._enrich_recipe_row(payload, row) if enrich else row
    return _core._presentation.family_row(payload, members, language=language, configured_language=configured_language, country=country, materialize=materialize, preferred_variant=preferred_variant)


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
    catalog_languages: Iterable[str] | None = None,
    group_families: bool = False,
    filter_rows=None,
    all_results: bool = False,
    progress=None,
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

    # Source-language filters and the typed query's language are independent.
    selected_languages = None if catalog_languages is None else tuple(dict.fromkeys(
        _core._language(value) for value in catalog_languages if _text(value)
    ))
    by_language = runtime_search.get("recipeLanguages") or {}
    if selected_languages is not None:
        source_allowed: set[int] = set()
        for selected in selected_languages:
            source_allowed.update(by_language.get(selected, ()))
        allowed = source_allowed if allowed is None else set(allowed) & source_allowed

    match = _core.search_index(
        runtime_search,
        query,
        language=language,
        strict_language=strict_language,
        allowed_indices=allowed,
        page=0 if group_families else page,
        size=max(1, len(recipes)) if group_families else size,
    )

    family_members = {}
    if group_families:
        roots = payload["_runtimeDisplayFamily"]
        for index in match["indices"]:
            family_members.setdefault(roots[index], []).append(index)
        match["rawTotal"] = match["total"]
        match["total"] = len(family_members)
        matching_families = list(family_members.values())
        match["indices"] = [members[0] for members in (matching_families if filter_rows or all_results else matching_families[page*size:(page+1)*size])]

    items: list[dict[str, Any]] = []
    scores = match.get("scores") if isinstance(match.get("scores"), dict) else {}
    indices = match.get("indices") or []
    if progress:
        progress("catalog_index", completed=0, total=len(indices))
    for completed, recipe_index in enumerate(indices, 1):
        try:
            raw = recipes[recipe_index]
        except (IndexError, TypeError):
            continue
        if not isinstance(raw, dict):
            continue
        display_language = next((
            selected for selected in selected_languages or ()
            if recipe_index in by_language.get(selected, ())
        ), language)
        if group_families:
            display_language = language
        if group_families:
            family = payload["_runtimeDisplayFamily"][recipe_index]
            members = family_members[family]
            # Editions may have different ingredient IDs or nutrition even
            # when their display names agree. Filter each original publication
            # before selecting the family
            # representative, so a nonmatching German row cannot hide a match
            # from another selected catalog.
            groups = [[member] for member in members] if filter_rows else [members]
            candidates = [(group[0], _display_family_row(payload, group, display_language, configured_language, country)) for group in groups]
        else:
            candidates = [(recipe_index, _core._enrich_recipe_row(payload,
                _core._legacy._recipe_row(raw, language=display_language, configured_language=configured_language, country=country)))]
        for source_index, row in candidates:
            if row:
                row["catalogLanguage"] = row.get("language") or display_language
                if source_index in scores:
                    row["searchScore"] = scores[source_index]
                if safety_filtered:
                    row["safety"] = _safety.recipe_safety(runtime_safety, source_index, diet=diet_value, allergies=allergy_values)
                items.append(row)
        if progress and (completed % 25 == 0 or completed == len(indices)):
            progress("catalog_index", completed=completed, total=len(indices))

    if filter_rows is not None:
        items = filter_rows(items)
        if group_families:
            surviving_families = {}
            for row in items:
                if row.get("displayFamilyId"):
                    surviving_families.setdefault(row["displayFamilyId"], []).append(row)
            merged_items, seen = [], set()
            for row in items:
                family = row.get("displayFamilyId")
                if len(surviving_families.get(family, [])) > 1:
                    if family in seen:
                        continue
                    seen.add(family)
                    members = list(dict.fromkeys(payload["_runtimeRecipeByVariant"][str(item["displayVariantId"])] for item in surviving_families[family]))
                    merged = _display_family_row(payload, members, language, configured_language, country, str(row["displayVariantId"]))
                    # Keep the winning publication's measured filter/rank data.
                    row = {**row, **merged, **{key: row[key] for key in ("match", "nutrition", "cost", "mealTypes", "mealTypeSource", "safety") if key in row}}
                merged_items.append(row)
            items = merged_items
        match["total"] = len(items)
        if not all_results:
            items = items[page*size:(page+1)*size]
    total = int(match.get("total") or 0)
    total_pages = (total + size - 1) // size if total else 0
    return {
        "ok": True,
        "query": _text(query),
        "resolvedQuery": _core.resolved_query_text(query, language, runtime_search.get("catalogQueryAliases")),
        "queryRecovered": _core.resolved_query_text(query, language, runtime_search.get("catalogQueryAliases")) != _core.normalize_search_text(query),
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
        "rawMatchedPublications": match.get("rawTotal", total),
        "displayFamilies": group_families,
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
    group_families: bool = False,
) -> dict[str, Any] | None:
    payload = load_release_catalog()
    if group_families:
        index = payload["_runtimeRecipeByVariant"].get(str(variant_id))
        if index is None:
            return None
        members = payload["_runtimeDisplayFamilyMembers"][payload["_runtimeDisplayFamily"][index]]
        return _display_family_row(payload, members, language, configured_language, country, str(variant_id))
    return _core.recipe_by_variant(
        variant_id,
        language=language,
        configured_language=configured_language,
        country=country,
    )


def __getattr__(name: str):
    """Preserve the established release-catalog helper API."""
    return getattr(_core, name)


def ingredient_price_label(ingredient: Any, language: str) -> dict[str, Any]:
    """Return a catalog-backed market name with honest translation provenance.

    Called by price lookup preparation in HA's executor. No AI, live translation
    or fuzzy mapping is used; a missing translation cannot change the market.
    """
    item = ingredient if isinstance(ingredient, dict) else {'name': str(ingredient or '')}
    # Reviewed recipe overrides can retain an older provider ingredientId.
    # The effective key must win, even when it is a synthetic reviewed identity.
    key = item.get('key') or item.get('foodKey') or item.get('ingredientId') or item.get('id')
    matched = _core._global_ingredient(load_release_catalog(), {'ingredientId': key} if key else {})
    raw = matched or item
    presentation = _core._presentation
    canonical = str(raw.get('canonicalName') or raw.get('name') or raw.get('foodName') or '').strip()
    code = str(language or 'en').lower().replace('_', '-').split('-', 1)[0]
    label_key = presentation.name_key(presentation.clean_name(canonical))
    overlay = presentation.labels().get(code, {}).get(label_key)
    translated = (raw.get('translations') or {}).get(code)
    known_english = bool(matched or raw.get('canonicalName'))
    translated_available = bool(overlay or (translated and code != 'en') or (code == 'en' and known_english))
    name = presentation.display_name(raw, code)
    actual_language = code if translated_available else ('en' if known_english else str(raw.get('language') or raw.get('displayLanguage') or ''))
    return {'name': name, 'canonicalName': canonical,
            'language': actual_language, 'translationAvailable': translated_available,
            'source': 'catalog_overlay' if overlay else 'catalog_translation' if translated and code != 'en'
                      else 'canonical_fallback' if known_english else 'unresolved'}
