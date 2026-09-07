#!/usr/bin/env python3
"""SEB recipe-detail normalization with evidence-safe official nutrition."""
from __future__ import annotations

import urllib.parse
from typing import Any

try:
    from . import cook4me_recipe_catalog as catalog
    from .cook4me_official_nutrition import extract_official_nutrition
except ImportError:  # direct vendor-directory execution
    import cook4me_recipe_catalog as catalog
    from cook4me_official_nutrition import extract_official_nutrition


def recipe_detail(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    variant_id: str,
    *,
    country: str = "DE",
    language: str = "de",
    configured_language: str | None = None,
    app_version: str = "36.0.0-RC3",
    pcfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch one official recipe and retain SEB nutrition evidence.

    This mirrors the proven ``cook4me_recipe_catalog.recipe_detail`` request and
    normalization contract.  The only added field is ``officialNutrition``.
    """
    variant = catalog._fid(variant_id)
    if not variant:
        raise catalog.CatalogError("Recipe variant ID is required")
    configured_language = (configured_language or language or "de").lower()
    language = (language or configured_language).lower()
    pcfg = pcfg or catalog._platform_context(
        cfg, country, configured_language, app_version
    )
    base = cfg["platform_base_url"].rstrip("/")
    url = (
        base
        + "/common-api/v3/recipes/PRO/"
        + urllib.parse.quote(variant, safe="")
        + "/?format=mobile"
    )
    payload, auth_mode = catalog._http_json(
        "GET",
        url,
        headers_iter=catalog._request_headers(
            cfg,
            tokens,
            country,
            configured_language,
            app_version,
            url,
            pcfg,
        ),
    )
    root = catalog._recipe_root(payload)
    grouping_id = catalog._fid(root.get("groupingId")) or catalog._fid(
        root.get("topRecipeId")
    )
    recipe_id = (
        catalog._fid(root.get("fid"))
        or catalog._fid(root.get("identifier"))
        or variant
    )
    steps = catalog.extract_recipe_steps(root)
    title = catalog._clean_text(
        root.get("title") or root.get("shortTitle") or root.get("normalizedTitle")
    )
    normalized = {
        "groupingFunctionalId": grouping_id,
        "recipeFunctionalId": recipe_id,
        "variantFunctionalId": recipe_id,
        "searchVariantId": variant,
        "title": title,
        "cover": catalog.extract_recipe_cover(root),
        "stepCount": len(steps),
        "steps": steps,
        "ingredients": catalog.extract_recipe_ingredients(root),
        "excludedFoods": catalog._key_name_list(root, "excludedFoods"),
        "detectedExcludedFoods": catalog._key_name_list(
            root, "detectedExcludedFoods"
        ),
        "courses": catalog._key_name_list(root, "courses"),
        "occasions": catalog._key_name_list(root, "occasions"),
        "durations": catalog._durations(root),
        "yield": catalog._yield(root),
        "difficulty": root.get("difficulty"),
        "recipeType": root.get("recipeType"),
        "language": catalog._clean_text(root.get("lang")) or language,
        "market": catalog._clean_text(root.get("market")),
        "groupSize": root.get("groupSize"),
        "officialNutrition": extract_official_nutrition(root),
        "isAutomaticallyGenerated": bool(root.get("isAutomaticallyGenerated")),
        "isPremium": bool(root.get("isPremium")),
        "sendable": bool(grouping_id and recipe_id),
        "source": "sebplatform_mobile_recipe",
        "authMode": auth_mode,
    }
    return {key: value for key, value in normalized.items() if value is not None}
