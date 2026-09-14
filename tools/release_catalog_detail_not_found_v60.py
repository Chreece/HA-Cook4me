#!/usr/bin/env python3
"""Evidence-gated accounting for Cook4Me search rows with no recipe detail.

Real v60 capture evidence proved that some provider search manifests contain
stable recipe IDs whose exact v3 PRO detail resource returns HTTP 404 through
both the app-header and access_rcu request modes, while known-present controls
from the same catalogs succeed. Other bearer/remote fallbacks return 401.

This module does not infer that every failed detail is stale. It recognizes only
that exact, already-redacted provider result shape. During capture such rows are
accounted separately from genuine failures, their exact provider IDs are kept as
release audit evidence, and rows with no successful detail anywhere are omitted
from the recipe table. Any other failure remains fail-closed.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import re
from threading import Lock
from typing import Any, Callable

_POLICY = "search-manifest-app-access-rcu-404-accounted-v1"
_SENTINEL = "_v60SearchListedDetailNotFound"
_ALLOWED_PROVIDER_MODES = {
    "app",
    "access_rcu",
    "access_rcu_remote",
    "id_rcu",
    "id_rcu_remote",
    "access_bearer",
    "id_bearer",
}
_RESULT_RE = re.compile(
    r"^([a-z0-9_]+)=(HTTP\d{3}|network:[A-Za-z0-9_.-]+)$",
    re.IGNORECASE,
)


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def safe_provider_results(exc: BaseException) -> dict[str, str]:
    """Extract only allow-listed result classes from an already-redacted error."""
    message = str(exc)
    markers = (
        "SEB recipe authentication failed (tokens redacted):",
        "SEB recipe request failed:",
    )
    details = ""
    for marker in markers:
        if marker in message:
            details = message.split(marker, 1)[1].strip()
            break
    if not details:
        return {}

    results: dict[str, str] = {}
    for part in details.split("|"):
        match = _RESULT_RE.fullmatch(part.strip())
        if not match:
            return {}
        mode = match.group(1).lower()
        if mode not in _ALLOWED_PROVIDER_MODES or mode in results:
            return {}
        result = match.group(2)
        if result.upper().startswith("HTTP"):
            result = "HTTP" + result[4:]
        else:
            result = "network:" + result.split(":", 1)[1]
        results[mode] = result
    return dict(sorted(results.items()))


def is_search_listed_detail_not_found(
    exc: BaseException,
    catalog_module: Any,
) -> bool:
    """Return True only for the exact live-proven 404 + auth-fallback shape."""
    if not isinstance(exc, catalog_module.CatalogAuthError):
        return False
    matrix = safe_provider_results(exc)
    if not matrix:
        return False
    if matrix.get("app") != "HTTP404":
        return False
    if matrix.get("access_rcu") != "HTTP404":
        return False
    if any(value.startswith("network:") for value in matrix.values()):
        return False
    statuses = {
        int(value[4:])
        for value in matrix.values()
        if value.startswith("HTTP") and value[4:].isdigit()
    }
    return bool(statuses and statuses <= {401, 403, 404})


def _variant_id(row: dict[str, Any]) -> str:
    return _text(row.get("variantId") or row.get("searchVariantId"))


def _strip_unsuccessful_sentinels(
    payload: dict[str, Any],
    *,
    not_found_ids: set[str],
    successful_ids: set[str],
) -> None:
    """Remove only provider IDs for which no detail call succeeded anywhere."""
    remove_ids = not_found_ids - successful_ids
    if not remove_ids:
        return
    recipes: list[dict[str, Any]] = []
    for raw_group in payload.get("recipes") or []:
        if not isinstance(raw_group, dict):
            continue
        group = deepcopy(raw_group)
        variants = [
            deepcopy(row)
            for row in group.get("variants") or []
            if isinstance(row, dict) and _variant_id(row) not in remove_ids
        ]
        if not variants:
            continue
        group["variants"] = variants
        recipes.append(group)
    payload["recipes"] = recipes


def _recompute_recipe_review_count(payload: dict[str, Any]) -> int:
    return sum(
        row.get("canonicalEnglishNeedsReview") is True
        for row in payload.get("recipes") or []
        if isinstance(row, dict)
    )


def apply_accounting(
    payload: dict[str, Any],
    *,
    by_language: dict[str, set[str]],
    successful_ids: set[str],
) -> dict[str, Any]:
    """Attach deterministic per-catalog evidence and repair v59 hydration counts."""
    result = deepcopy(payload)
    all_not_found = set().union(*by_language.values()) if by_language else set()
    _strip_unsuccessful_sentinels(
        result,
        not_found_ids=all_not_found,
        successful_ids=successful_ids,
    )

    source = result.setdefault("source", {})
    if not isinstance(source, dict):
        source = {}
        result["source"] = source
    catalogs = source.get("catalogs") if isinstance(source.get("catalogs"), list) else []

    total = 0
    for raw in catalogs:
        if not isinstance(raw, dict):
            continue
        language = _text(raw.get("language")).lower()
        ids = sorted(by_language.get(language, set()))
        count = len(ids)
        total += count
        raw["detailNotFoundCount"] = count
        raw["detailNotFoundVariantIds"] = ids
        if count:
            raw["hydratedVariants"] = max(
                0,
                int(raw.get("hydratedVariants") or 0) - count,
            )

    source["detailNotFoundCount"] = total
    source["detailNotFoundPolicy"] = _POLICY
    source["detailNotFoundVariantIdsStored"] = True
    source["unresolvedCanonicalRecipeNames"] = _recompute_recipe_review_count(result)
    return result


def build_with_detail_not_found(
    v59: Any,
    build_func: Callable[[Any, Any], dict[str, Any]],
    args: Any,
) -> dict[str, Any]:
    """Run one v59-backed capture while accounting only exact proven 404 rows."""
    original_detail = v59._detail
    not_found_by_language: dict[str, set[str]] = defaultdict(set)
    successful_ids: set[str] = set()
    lock = Lock()

    def wrapped_detail(*call_args: Any, **call_kwargs: Any) -> dict[str, Any]:
        variant_id = _text(call_kwargs.get("variant_id"))
        language = _text(call_kwargs.get("source_language")).lower()
        try:
            detail = original_detail(*call_args, **call_kwargs)
        except Exception as exc:
            if not is_search_listed_detail_not_found(exc, v59.catalog):
                raise
            if not variant_id or not language:
                raise
            with lock:
                not_found_by_language[language].add(variant_id)
            return {
                "variantId": variant_id,
                "recipeFunctionalId": variant_id,
                "language": language,
                "ingredients": [],
                _SENTINEL: True,
            }
        with lock:
            if variant_id:
                successful_ids.add(variant_id)
        return detail

    v59._detail = wrapped_detail
    try:
        payload = build_func(v59, args)
    finally:
        v59._detail = original_detail

    return apply_accounting(
        payload,
        by_language=dict(not_found_by_language),
        successful_ids=successful_ids,
    )


def validation_errors(payload: dict[str, Any]) -> list[str]:
    """Independently validate detail-attempt accounting encoded in an artifact."""
    errors: list[str] = []
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    catalogs = source.get("catalogs")
    if catalogs is None:
        return errors
    if not isinstance(catalogs, list):
        return ["source.catalogs must be a list for detail accounting"]

    total_not_found = 0
    total_failed = 0
    for index, row in enumerate(catalogs):
        if not isinstance(row, dict):
            errors.append(f"source.catalogs[{index}] is not an object")
            continue
        unique = int(row.get("uniqueVariants") or 0)
        hydrated = int(row.get("hydratedVariants") or 0)
        failed = int(row.get("failedDetails") or 0)
        not_found = int(row.get("detailNotFoundCount") or 0)
        ids = row.get("detailNotFoundVariantIds")
        ids = [] if ids is None else ids

        if not isinstance(ids, list):
            errors.append(
                f"source.catalogs[{index}].detailNotFoundVariantIds must be a list"
            )
            ids = []
        normalized = [_text(value) for value in ids]
        if any(not value for value in normalized):
            errors.append(
                f"source.catalogs[{index}] has empty detail-not-found provider identity"
            )
        if normalized != sorted(set(normalized)):
            errors.append(
                f"source.catalogs[{index}].detailNotFoundVariantIds must be sorted and unique"
            )
        if len(normalized) != not_found:
            errors.append(
                f"source.catalogs[{index}] detailNotFoundCount does not match stored IDs"
            )
        if min(unique, hydrated, failed, not_found) < 0:
            errors.append(f"source.catalogs[{index}] has negative detail accounting")
        if hydrated + failed + not_found != unique:
            errors.append(
                f"source.catalogs[{index}] detail accounting does not equal uniqueVariants"
            )
        total_not_found += not_found
        total_failed += failed

    source_not_found = int(source.get("detailNotFoundCount") or 0)
    if source_not_found != total_not_found:
        errors.append("source.detailNotFoundCount does not match catalog totals")
    if int(source.get("failedDetailCount") or 0) != total_failed:
        errors.append("source.failedDetailCount does not match catalog totals")
    if source_not_found:
        if source.get("detailNotFoundPolicy") != _POLICY:
            errors.append("source.detailNotFoundPolicy is invalid")
        if source.get("detailNotFoundVariantIdsStored") is not True:
            errors.append("source.detailNotFoundVariantIdsStored must be true")
    return errors


def accounting_complete(payload: dict[str, Any]) -> bool:
    return not validation_errors(payload)
