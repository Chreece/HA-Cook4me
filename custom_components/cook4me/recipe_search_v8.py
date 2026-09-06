from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
from typing import Any

from .vendor import cook4me_recipe_catalog as catalog

SEARCH_CONTRACT = "standalone-proven-cookeo-brand-v5"
DEFAULT_APPLIANCE_GROUP = "APPLIANCE_GROUP_15"
DEFAULT_RECIPE_TYPE = "BRAND"
_MAX_FILL_PAGES = 10


def app_search_body(
    language: str,
    market: str,
    *,
    appliance_group: str = DEFAULT_APPLIANCE_GROUP,
    recipe_type: str = DEFAULT_RECIPE_TYPE,
) -> dict[str, Any]:
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


def _page_request(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    query: str,
    page: int,
    size: int,
    country: str,
    language: str,
    configured_language: str,
    app_version: str,
    appliance_group: str,
    recipe_type: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    market = f"GS_{country}"
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
    payload, auth_mode = catalog._http_json(
        "POST",
        url,
        headers_iter=catalog._request_headers(
            cfg, tokens, country, configured_language, app_version, url, pcfg
        ),
        params=params,
        body=app_search_body(
            language,
            market,
            appliance_group=appliance_group,
            recipe_type=recipe_type,
        ),
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
    return payload, lightweight, auth_mode


def _hydrate_rows(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    country: str,
    language: str,
    configured_language: str,
    app_version: str,
    pcfg: dict[str, Any],
) -> tuple[list[dict[str, Any]], int]:
    if not rows:
        return [], 0

    def load(index: int):
        variant = rows[index]["searchVariantId"]
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

    valid: dict[int, dict[str, Any]] = {}
    failed = 0
    with ThreadPoolExecutor(max_workers=min(4, len(rows))) as pool:
        futures = {pool.submit(load, index): index for index in range(len(rows))}
        for future in as_completed(futures):
            index = futures[future]
            try:
                _, detail = future.result()
            except Exception:
                # Search indexes can retain stale publications (observed in ES/PT).
                # A dead detail must consume neither a card nor the requested quota.
                failed += 1
                continue
            merged = dict(rows[index])
            merged.update(detail)
            if not merged.get("cover"):
                merged["cover"] = rows[index].get("cover")
            if not merged.get("title"):
                merged["title"] = rows[index].get("title")
            if not merged.get("groupingFunctionalId"):
                merged["groupingFunctionalId"] = rows[index].get("groupingFunctionalId")
            valid[index] = {key: value for key, value in merged.items() if value is not None}
    return [valid[index] for index in sorted(valid)], failed


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
    """Search the proven contract, skipping dead publications while filling cards."""
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

    first_payload: dict[str, Any] | None = None
    auth_mode = ""
    raw_count = 0
    skipped = 0
    hydrated: list[dict[str, Any]] = []
    lightweight_only: list[dict[str, Any]] = []
    desired = min(size, max_details) if max_details else 0
    source_size = 50 if max_details else size

    for offset in range(_MAX_FILL_PAGES):
        current_page = page + offset
        payload, lightweight, page_auth = _page_request(
            cfg,
            tokens,
            pcfg,
            query=query,
            page=current_page,
            size=source_size,
            country=country,
            language=language,
            configured_language=configured_language,
            app_version=app_version,
            appliance_group=appliance_group,
            recipe_type=recipe_type,
        )
        if first_payload is None:
            first_payload = payload
            auth_mode = page_auth
        raw_count += len(lightweight)

        if not max_details:
            lightweight_only.extend(deepcopy(lightweight))
            break

        valid, failed = _hydrate_rows(
            cfg,
            tokens,
            lightweight,
            country=country,
            language=language,
            configured_language=configured_language,
            app_version=app_version,
            pcfg=pcfg,
        )
        skipped += failed
        hydrated.extend(valid)
        collapsed = catalog.collapse_variants(
            hydrated,
            preferred_language=language,
            configured_language=configured_language,
            country=country,
        )
        if len(collapsed) >= desired:
            break

        page_obj = payload.get("page") if isinstance(payload.get("page"), dict) else {}
        total_pages = page_obj.get("totalPages")
        number = page_obj.get("number", current_page)
        if not lightweight:
            break
        try:
            if total_pages is not None and int(number) + 1 >= int(total_pages):
                break
        except (TypeError, ValueError):
            pass

    first_payload = first_payload or {}
    source_rows = hydrated if max_details else lightweight_only
    collapsed = (
        catalog.collapse_variants(
            source_rows,
            preferred_language=language,
            configured_language=configured_language,
            country=country,
        )
        if max_details
        else source_rows
    )
    if desired:
        collapsed = collapsed[:desired]
    page_obj = (
        first_payload.get("page")
        if isinstance(first_payload.get("page"), dict)
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
        "rawVariantCount": raw_count,
        "groupedRecipeCount": len(collapsed),
        "items": collapsed,
        "skippedDeadPublications": skipped,
        "authMode": auth_mode,
        "searchContract": SEARCH_CONTRACT,
    }
