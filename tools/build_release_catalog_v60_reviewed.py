#!/usr/bin/env python3
"""v60 capture facade that applies committed canonical-English review evidence.

The network/provider capture remains exactly the proven v59/v60 path. This layer
only replaces fallback labels that were explicitly marked as needing canonical
English review, using versioned repository evidence bound to provider identities
or exact native title labels. It then recomputes capture completeness and search
/safety indexes. Provider/group/variant identities are never changed.

The release capture additionally tolerates bounded transient network timeouts on
both the proven single-page catalog manifest request and individual recipe-detail
hydration. It retries only the identical request and never falls back to
pagination, partial-market capture, skipped detail validation, or relaxed
validation.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import time
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60 as base
import release_catalog_canonical_reviews_v60 as canonical_reviews
import release_catalog_detail_not_found_v60 as detail_not_found

_SEARCH_TIMEOUT_ATTEMPTS = 3
_SEARCH_TIMEOUT_DELAY_SECONDS = 1.0
_DETAIL_TIMEOUT_ATTEMPTS = 3
_DETAIL_TIMEOUT_DELAY_SECONDS = 1.0


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _network_timeout_only(exc: BaseException) -> bool:
    """Return True only for the exact all-network-timeout provider failure shape."""
    catalog_module = base._core.v59.catalog
    if isinstance(exc, catalog_module.CatalogAuthError):
        return False
    if not isinstance(exc, catalog_module.CatalogError):
        return False
    marker = "SEB recipe request failed:"
    message = str(exc)
    if marker not in message:
        return False
    details = message.split(marker, 1)[1].strip()
    parts = [part.strip() for part in details.split("|") if part.strip()]
    return bool(parts) and all(part.endswith("=network:Timeout") for part in parts)


def _retry_search_rows(
    search_func: Callable[..., list[dict[str, Any]]],
    *args: Any,
    sleep_func: Callable[[float], None] = time.sleep,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Retry only an identical proven manifest request after pure timeouts."""
    for attempt in range(1, _SEARCH_TIMEOUT_ATTEMPTS + 1):
        try:
            return search_func(*args, **kwargs)
        except Exception as exc:
            if not _network_timeout_only(exc) or attempt >= _SEARCH_TIMEOUT_ATTEMPTS:
                raise
            language = _text(kwargs.get("language")) or "?"
            country = _text(kwargs.get("country")) or "?"
            print(
                f"[catalog] {language}/GS_{country} network timeout; "
                f"retry {attempt + 1}/{_SEARCH_TIMEOUT_ATTEMPTS}",
                flush=True,
            )
            sleep_func(_SEARCH_TIMEOUT_DELAY_SECONDS)
    raise AssertionError("unreachable")


def _retry_detail(
    detail_func: Callable[..., dict[str, Any]],
    *args: Any,
    sleep_func: Callable[[float], None] = time.sleep,
    **kwargs: Any,
) -> dict[str, Any]:
    """Retry only an identical recipe-detail request after pure timeouts."""
    for attempt in range(1, _DETAIL_TIMEOUT_ATTEMPTS + 1):
        try:
            return detail_func(*args, **kwargs)
        except Exception as exc:
            if not _network_timeout_only(exc) or attempt >= _DETAIL_TIMEOUT_ATTEMPTS:
                raise
            variant_id = _text(kwargs.get("variant_id")) or "?"
            print(
                f"[detail] {variant_id} network timeout; "
                f"retry {attempt + 1}/{_DETAIL_TIMEOUT_ATTEMPTS}",
                flush=True,
            )
            sleep_func(_DETAIL_TIMEOUT_DELAY_SECONDS)
    raise AssertionError("unreachable")


def _build_with_search_timeout_retry(args: Any) -> dict[str, Any]:
    """Run v60 with temporary timeout-only manifest and detail wrappers.

    The established function name is retained for compatibility with existing
    release tooling/tests; it now protects both provider-request stages.
    """
    v59 = base._core.v59
    original_search = v59._all_search_rows
    original_detail = v59._detail

    def retried_search(*call_args: Any, **call_kwargs: Any) -> list[dict[str, Any]]:
        return _retry_search_rows(
            original_search,
            *call_args,
            **call_kwargs,
        )

    def retried_detail(*call_args: Any, **call_kwargs: Any) -> dict[str, Any]:
        return _retry_detail(
            original_detail,
            *call_args,
            **call_kwargs,
        )

    v59._all_search_rows = retried_search
    v59._detail = retried_detail
    try:
        return base.build(args)
    finally:
        v59._all_search_rows = original_search
        v59._detail = original_detail


def _capture_complete(payload: dict[str, Any]) -> bool:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    if int(source.get("unresolvedCanonicalIngredientNames") or 0):
        return False
    if int(source.get("unresolvedCanonicalRecipeNames") or 0):
        return False
    if int(source.get("failedDetailCount") or 0):
        return False
    if not detail_not_found.accounting_complete(payload):
        return False

    catalogs = source.get("catalogs") if isinstance(source.get("catalogs"), list) else []
    if len(catalogs) != int(source.get("auditedCatalogCount") or 0):
        return False
    for row in catalogs:
        if not isinstance(row, dict):
            return False
        if int(row.get("failedDetails") or 0):
            return False

    if source.get("nutritionRequiredForComplete") is not False:
        provider_food_count = sum(
            isinstance(row, dict) and not row.get("sourceLocalIdentity")
            for row in payload.get("ingredients") or []
        )
        if int(source.get("nutritionResolvedCount") or 0) != provider_food_count:
            return False
    return True


def apply_capture_canonical_reviews(
    payload: dict[str, Any],
    *,
    review_root: Path = TOOLS,
) -> dict[str, Any]:
    """Apply exact committed reviews to a captured v60 payload, offline."""
    result = deepcopy(payload)
    bundle = canonical_reviews.load_review_bundle(review_root)

    ingredient_rows = [
        row for row in result.get("ingredients") or [] if isinstance(row, dict)
    ]
    ingredients = {
        _text(row.get("id") or row.get("ingredientId") or row.get("key")): row
        for row in ingredient_rows
        if _text(row.get("id") or row.get("ingredientId") or row.get("key"))
    }
    provider_applied = canonical_reviews.apply_provider_food_reviews(
        ingredients, bundle.provider_foods
    )

    groups: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(result.get("recipes") or []):
        if not isinstance(row, dict):
            continue
        grouping = _text(row.get("groupingFunctionalId"))
        key = grouping or f"row:{index}"
        if key in groups:
            raise RuntimeError(f"duplicate recipe group identity during review overlay: {key}")
        groups[key] = row
    group_stats = canonical_reviews.apply_recipe_group_reviews(groups, bundle)

    unresolved_ingredients = sum(
        row.get("canonicalEnglishNeedsReview") is True for row in ingredient_rows
    )
    unresolved_recipes = sum(
        row.get("canonicalEnglishNeedsReview") is True
        for row in result.get("recipes") or []
        if isinstance(row, dict)
    )

    source = result.setdefault("source", {})
    if not isinstance(source, dict):
        source = {}
        result["source"] = source
    source.update(
        {
            "canonicalReviewOverlayApplied": True,
            "canonicalReviewProviderIdentityChanged": False,
            "canonicalReviewRecipeGroupingChanged": False,
            "canonicalReviewTranslationMergesGroups": False,
            "reviewedProviderFoodEnglishApplied": provider_applied,
            **group_stats,
            "unresolvedCanonicalIngredientNames": unresolved_ingredients,
            "unresolvedCanonicalRecipeNames": unresolved_recipes,
        }
    )

    # Canonical labels participate in the multilingual search index, so rebuild
    # that derived artifact after review application. Safety is refreshed too so
    # the independently validating release artifact stays byte-for-structure
    # consistent with the current v60 compiler.
    result["searchIndex"] = base._core.search_index.compile_search_index(result)
    source["compiledMultilingualSearchIndex"] = True
    source["compiledMultilingualSearchIndexSchemaVersion"] = int(
        (result.get("searchIndex") or {}).get("schemaVersion") or 0
    )
    result["complete"] = _capture_complete(result)
    return base._refresh_safety(result)


def build(args: Any) -> dict[str, Any]:
    payload = _build_with_search_timeout_retry(args)
    payload = apply_capture_canonical_reviews(payload)
    base._core._save_compact(Path(args.output), payload)
    return payload


apply_reviewed_nutrition = base.apply_reviewed_nutrition


def main() -> int:
    args = base._core._parser().parse_args()
    payload = build(args)
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    output = Path(args.output)
    print(
        json.dumps(
            {
                "catalogVersion": payload.get("catalogVersion"),
                "catalogComplete": bool(payload.get("complete")),
                "semanticCoverageComplete": bool(source.get("semanticCoverageComplete")),
                "canonicalReviewOverlayApplied": bool(
                    source.get("canonicalReviewOverlayApplied")
                ),
                "unresolvedCanonicalIngredientNames": int(
                    source.get("unresolvedCanonicalIngredientNames") or 0
                ),
                "unresolvedCanonicalRecipeNames": int(
                    source.get("unresolvedCanonicalRecipeNames") or 0
                ),
                "reviewedProviderFoodEnglishApplied": int(
                    source.get("reviewedProviderFoodEnglishApplied") or 0
                ),
                "entryMealTitleReviewsApplied": int(
                    source.get("entryMealTitleReviewsApplied") or 0
                ),
                "exactRecipeTitleReviewsApplied": int(
                    source.get("exactRecipeTitleReviewsApplied") or 0
                ),
                "outputBytes": output.stat().st_size if output.exists() else 0,
                "output": str(output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload.get("complete") else 2


def __getattr__(name: str):
    return getattr(base, name)


if __name__ == "__main__":
    raise SystemExit(main())
