#!/usr/bin/env python3
"""Standalone-proven KRUPS/Cookeo recipe search used by HA and the vendor CLI.

This module intentionally contains only the request shape that was proven
outside Home Assistant against the current KRUPS backend.  For the German
Cookeo `risotto` proof it returns 29 serving variants which collapse by the
real SEB groupingId into the 11 logical recipes shown by the KRUPS app.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from typing import Any

try:
    from . import cook4me_recipe_catalog as catalog
except ImportError:  # direct script/import from the vendor directory
    import cook4me_recipe_catalog as catalog

SEARCH_CONTRACT = "standalone-proven-cookeo-brand-v5"
DEFAULT_APPLIANCE_GROUP = "APPLIANCE_GROUP_15"
DEFAULT_RECIPE_TYPE = "BRAND"


def search_body(
    language: str,
    market: str,
    *,
    appliance_group: str = DEFAULT_APPLIANCE_GROUP,
    recipe_type: str = DEFAULT_RECIPE_TYPE,
) -> dict[str, Any]:
    return {
        "fieldFilters": [
            {"field": "lang.key", "values": [str(language or "").strip().lower()]},
            {"field": "market.key", "values": [str(market or "").strip().upper()]},
            {
                "field": "applianceGroups.reference.key",
                "values": [str(appliance_group or DEFAULT_APPLIANCE_GROUP).strip()],
            },
            {
                "field": "topRecipe.type.key",
                "values": [str(recipe_type or DEFAULT_RECIPE_TYPE).strip().upper()],
            },
        ]
    }


def search_recipes(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    query: str = "",
    page: int = 0,
    size: int = 20,
    include_details: bool = True,
    max_details: int = 20,
    country: str = "DE",
    language: str = "de",
    app_version: str = "36.0.0-RC3",
    *,
    appliance_group: str = DEFAULT_APPLIANCE_GROUP,
    recipe_type: str = DEFAULT_RECIPE_TYPE,
) -> dict[str, Any]:
    if catalog.c4m.curl_requests is None:
        raise RuntimeError("curl-cffi is not available")

    page = max(0, int(page))
    size = max(1, min(int(size), 50))
    max_details = max(0, min(int(max_details), 50))
    country = str(country or "DE").upper()
    language = str(language or "de").lower().replace("_", "-").split("-", 1)[0]
    market = f"GS_{country}"
    appliance_group = str(appliance_group or DEFAULT_APPLIANCE_GROUP).strip()
    recipe_type = str(recipe_type or DEFAULT_RECIPE_TYPE).strip().upper()

    cfg = dict(cfg)
    pcfg = catalog._platform_context(cfg, country, language, app_version)
    url = cfg["platform_base_url"].rstrip("/") + "/common-api/v4/search/recipes"
    params = {
        "lang": language,
        "market": market,
        "page": page,
        "size": size,
        "q": str(query or ""),
        "groupBy": "",
        "myUniverse": "false",
        "myOwnRecipe": "false",
        "withAutomaticSpellcheck": "true",
    }
    body = search_body(
        language,
        market,
        appliance_group=appliance_group,
        recipe_type=recipe_type,
    )
    payload, auth_mode = catalog._http_json(
        "POST",
        url,
        headers_iter=catalog._request_headers(
            cfg, tokens, country, language, app_version, url, pcfg
        ),
        params=params,
        body=body,
    )
    if not isinstance(payload, dict):
        raise RuntimeError("SEB recipe search returned an unexpected response")

    raw_content = payload.get("content") if isinstance(payload.get("content"), list) else []
    lightweight = [
        row
        for raw in raw_content
        if isinstance(raw, dict)
        if (row := catalog._light_search_row(raw))
    ]
    enriched = [deepcopy(row) for row in lightweight]

    count = min(max_details, len(lightweight)) if include_details else 0
    if count:
        def load(index: int):
            variant = lightweight[index]["searchVariantId"]
            detail = catalog.recipe_detail(
                cfg,
                tokens,
                variant,
                country=country,
                language=language,
                configured_language=language,
                app_version=app_version,
                pcfg=pcfg,
            )
            return index, detail

        with ThreadPoolExecutor(max_workers=min(4, count)) as pool:
            futures = {pool.submit(load, index): index for index in range(count)}
            for future in as_completed(futures):
                index = futures[future]
                try:
                    _, detail = future.result()
                except Exception as exc:
                    enriched[index]["detailError"] = type(exc).__name__
                    continue
                merged = dict(lightweight[index])
                merged.update(detail)
                if not merged.get("cover"):
                    merged["cover"] = lightweight[index].get("cover")
                if not merged.get("title"):
                    merged["title"] = lightweight[index].get("title")
                if not merged.get("groupingFunctionalId"):
                    merged["groupingFunctionalId"] = lightweight[index].get("groupingFunctionalId")
                enriched[index] = {
                    key: value for key, value in merged.items() if value is not None
                }

    items = (
        catalog.collapse_variants(
            enriched,
            preferred_language=language,
            configured_language=language,
            country=country,
        )
        if include_details
        else enriched
    )
    page_obj = (
        payload.get("page")
        if isinstance(payload.get("page"), dict)
        else {"number": page, "size": size}
    )
    return {
        "query": str(query or ""),
        "requestedLanguage": language,
        "configuredLanguage": language,
        "market": market,
        "applianceGroup": appliance_group,
        "recipeType": recipe_type,
        "page": page_obj,
        "rawVariantCount": len(lightweight),
        "groupedRecipeCount": len(items),
        "items": items,
        "authMode": auth_mode,
        "searchContract": SEARCH_CONTRACT,
    }
