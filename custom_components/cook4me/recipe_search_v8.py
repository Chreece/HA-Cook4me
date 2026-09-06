from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from typing import Any

from .vendor import cook4me_recipe_catalog as catalog

# SearchRecipesV2 / wc0.a body fields recovered from the current KRUPS APK.
# Keep this deliberately conservative: every field/filter below is directly
# evidenced by the app.  We do not invent a PRODUCT value for the user's cooker
# until the exact selected-appliance search filter is available from account
# metadata.
_APP_FIELD_LIST: tuple[str, ...] = (
    "resourceMedias",
    "domain",
    "identifier",
    "title",
    "lang",
    "market",
    "brand",
    "creator",
    "publicationDate",
    "creationDate",
    "modificationDate",
    "community",
    "topRecipe.type",
    "topRecipe.id",
    "privacyLevel",
    "durations.totalTime",
    "classifications",
    "marketingFood",
    "yield.quantity",
    "yield.unit",
    "isPersonalizedAdaptation",
)


def app_search_body(language: str, market: str) -> dict[str, Any]:
    """Return the evidence-backed SearchRecipesV2 request body.

    The APK builds the same lang/market constraints both as query parameters and
    as field filters.  The previous HA implementation sent only ``{}``, which
    allowed unrelated-language variants into a market result and made strict
    post-filtering drop otherwise valid searches.
    """

    language = str(language or "").strip().lower()
    market = str(market or "").strip().upper()
    return {
        "fieldList": list(_APP_FIELD_LIST),
        "fieldFilters": [
            {"field": "lang.key", "values": [language]},
            {"field": "market.key", "values": [market]},
            {"field": "privacyLevel.key", "values": ["COMMUNITY", "PUBLIC"]},
            {"field": "id.sourceSystem.key", "values": ["PRO"]},
            {
                "field": "classifications.key_FOOD_COOKING",
                "values": ["IS_FOOD_COOKING"],
                "type": "inclusion",
            },
        ],
        "facetFilters": [],
        "ingredientsSelectedNestedFieldFiltersGroups": [],
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
) -> dict[str, Any]:
    """Search with the current-app body, then hydrate before grouping/rendering."""

    if catalog.c4m.curl_requests is None:
        raise catalog.CatalogError("curl-cffi is not available")

    page = max(0, int(page))
    size = max(1, min(int(size), 50))
    max_details = max(0, min(int(max_details), 50))
    country = str(country or "DE").upper()
    configured_language = str(configured_language or language or "de").lower()
    language = str(language or configured_language).lower()
    market = f"GS_{country}"

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
    body = app_search_body(language, market)
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
        "page": page_obj,
        "rawVariantCount": len(lightweight),
        "groupedRecipeCount": len(collapsed),
        "items": collapsed,
        "authMode": auth_mode,
        "searchContract": "apk-searchrecipesv2-v4",
    }
