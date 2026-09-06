from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from typing import Any

from .vendor import cook4me_recipe_catalog as catalog

# Standalone-proven against the current KRUPS backend and the user's Cookeo.
# For de / GS_DE + q=risotto this exact contract returns 29 serving variants,
# which hydrate and collapse by groupingId to the 11 logical recipes shown by
# the KRUPS application.  Do not add the old speculative fieldList,
# FOOD_COOKING, privacy/source or empty-list filters back here without a fresh
# standalone proof.
SEARCH_CONTRACT = "standalone-proven-cookeo-brand-v5"
DEFAULT_APPLIANCE_GROUP = "APPLIANCE_GROUP_15"
DEFAULT_RECIPE_TYPE = "BRAND"


def app_search_body(
    language: str,
    market: str,
    *,
    appliance_group: str = DEFAULT_APPLIANCE_GROUP,
    recipe_type: str = DEFAULT_RECIPE_TYPE,
) -> dict[str, Any]:
    """Return the exact standalone-proven Cookeo branded-recipe search body."""

    language = str(language or "").strip().lower()
    market = str(market or "").strip().upper()
    appliance_group = str(appliance_group or DEFAULT_APPLIANCE_GROUP).strip()
    recipe_type = str(recipe_type or DEFAULT_RECIPE_TYPE).strip().upper()
    return {
        "fieldFilters": [
            {"field": "lang.key", "values": [language]},
            {"field": "market.key", "values": [market]},
            {
                "field": "applianceGroups.reference.key",
                "values": [appliance_group],
            },
            {"field": "topRecipe.type.key", "values": [recipe_type]},
        ]
    }


def search_recipes(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    query: str = "",
    *,
    page: int = 0,
    size: int = 20,
    max_details: int = 20,
    country: str = "DE",
    language: str = "de",
    configured_language: str | None = None,
    app_version: str = "36.0.0-RC3",
    appliance_group: str = DEFAULT_APPLIANCE_GROUP,
    recipe_type: str = DEFAULT_RECIPE_TYPE,
) -> dict[str, Any]:
    """Search the proven Cookeo/KRUPS catalog contract and hydrate before grouping."""

    if catalog.c4m.curl_requests is None:
        raise catalog.CatalogError("curl-cffi is not available")

    page = max(0, int(page))
    size = max(1, min(int(size), 50))
    max_details = max(0, min(int(max_details), 50))
    country = str(country or "DE").upper()
    configured_language = str(configured_language or language or "de").lower()
    language = str(language or configured_language).lower()
    market = f"GS_{country}"
    appliance_group = str(appliance_group or DEFAULT_APPLIANCE_GROUP).strip()
    recipe_type = str(recipe_type or DEFAULT_RECIPE_TYPE).strip().upper()

    cfg = dict(cfg)
    pcfg = catalog._platform_context(cfg, country, configured_language, app_version)
    base = cfg["platform_base_url"].rstrip("/")
    url = base + "/common-api/v4/search/recipes"
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
    body = app_search_body(
        language,
        market,
        appliance_group=appliance_group,
        recipe_type=recipe_type,
    )
    payload, auth_mode = catalog._http_json(
        "POST",
        url,
        headers_iter=catalog._request_headers(
            cfg, tokens, country, configured_language, app_version, url, pcfg
        ),
        params=params,
        body=body,
    )
    if not isinstance(payload, dict):
        raise catalog.CatalogError("SEB recipe search returned an unexpected response")

    raw_content = payload.get("content") if isinstance(payload.get("content"), list) else []
    lightweight = [
        row
        for raw in raw_content
        if isinstance(raw, dict)
        if (row := catalog._light_search_row(raw))
    ]
    enriched = [deepcopy(row) for row in lightweight]

    count = min(max_details, len(lightweight))
    if count:
        def load(index: int):
            variant = lightweight[index]["searchVariantId"]
            detail = catalog.recipe_detail(
                cfg,
                tokens,
                variant,
                country=country,
                language=language,
                configured_language=configured_language,
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
                except Exception as exc:  # one broken publication must not kill search
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

    collapsed = catalog.collapse_variants(
        enriched,
        preferred_language=language,
        configured_language=configured_language,
        country=country,
    )
    page_obj = (
        payload.get("page")
        if isinstance(payload.get("page"), dict)
        else {"number": page, "size": size}
    )
    return {
        "query": str(query or ""),
        "requestedLanguage": language,
        "configuredLanguage": configured_language,
        "market": market,
        "applianceGroup": appliance_group,
        "recipeType": recipe_type,
        "page": page_obj,
        "rawVariantCount": len(lightweight),
        "groupedRecipeCount": len(collapsed),
        "items": collapsed,
        "authMode": auth_mode,
        "searchContract": SEARCH_CONTRACT,
    }
