#!/usr/bin/env python3
"""Recipe catalog normalization for HA-Cook4me.

This module intentionally keeps recipe UI/catalog normalization separate from the
proven MQTT/device transport.  It consumes the APK-proven SEB search/detail HTTP
endpoints, preserves exact send identifiers, and normalizes only data that the
backend actually returned.
"""
from __future__ import annotations

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from copy import deepcopy
import math
import re
import urllib.parse
from typing import Any

try:
    from . import cook4me_phonefree as c4m
except ImportError:  # standalone/unit-test execution from this directory
    import cook4me_phonefree as c4m


class CatalogError(RuntimeError):
    """Recipe catalog request/normalization error."""


class CatalogAuthError(CatalogError):
    """Recipe catalog authentication needs refreshing."""


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return None
    # SEB search titles/descriptions can carry a leading formatting marker.
    text = re.sub(r"^\s*\*+\s*", "", text).strip()
    return text or None


def _fid(value: Any) -> str | None:
    if isinstance(value, dict):
        value = value.get("functionalId") or value.get("functional_id") or value.get("id")
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    bits = [part for part in text.split("/") if part]
    return bits[-1] if bits else text


def _recipe_root(payload: Any) -> dict[str, Any]:
    """Return the actual recipe object without recursively selecting brand/media data."""
    if isinstance(payload, list):
        if len(payload) == 1 and isinstance(payload[0], dict):
            return payload[0]
        for item in payload:
            if isinstance(item, dict) and (
                "steps" in item or "ingredients" in item or "groupingId" in item
            ):
                return item
        return {}
    if not isinstance(payload, dict):
        return {}
    if "steps" in payload or "ingredients" in payload or "groupingId" in payload:
        return payload
    # Known wrapper shapes only.  Do not walk every nested dictionary because
    # that is how the old implementation accidentally selected brand media.
    for key in ("recipe", "content", "data", "result"):
        candidate = payload.get(key)
        if isinstance(candidate, dict) and (
            "steps" in candidate or "ingredients" in candidate or "groupingId" in candidate
        ):
            return candidate
        if isinstance(candidate, list):
            for item in candidate:
                if isinstance(item, dict) and (
                    "steps" in item or "ingredients" in item or "groupingId" in item
                ):
                    return item
    return payload


def _media_url(media: Any) -> str | None:
    if not isinstance(media, dict):
        return None
    media_type = str(media.get("type") or "").upper()
    if media_type and media_type not in {"PHOTO", "IMAGE", "PICTURE"}:
        return None
    for key in ("thumbnail", "original"):
        value = media.get(key)
        if isinstance(value, str) and value.startswith(("https://", "http://")):
            return value
    return None


def _cover_from_cover_object(cover: Any) -> str | None:
    if not isinstance(cover, dict):
        return None
    if isinstance(cover.get("media"), dict):
        return _media_url(cover["media"])
    return _media_url(cover)


def extract_recipe_cover(root: dict[str, Any]) -> str | None:
    """Extract only the recipe's own cover, never nested brand/partner media."""
    if not isinstance(root, dict):
        return None

    value = _cover_from_cover_object(root.get("cover"))
    if value:
        return value

    medias = root.get("resourceMedias")
    if not isinstance(medias, list):
        return None
    # A root recipe resourceMedias entry with isCover=true is authoritative.
    for item in medias:
        if not isinstance(item, dict) or item.get("isCover") is not True:
            continue
        value = _media_url(item.get("media"))
        if value:
            return value
    # Some backend publications omit isCover; use only a root-level photo as a
    # fallback.  Never search technique, brand, domain, partner, or step media.
    for item in medias:
        if not isinstance(item, dict):
            continue
        value = _media_url(item.get("media"))
        if value:
            return value
    return None


def _step_texts(step: dict[str, Any]) -> list[str]:
    """Return user-facing texts in the actual SEB mobile-step field order."""
    values: list[str] = []
    # applicationDescription/applianceDescription are the fields observed in
    # the live API.  The generic keys are retained only for backend revisions.
    for key in (
        "applicationDescription",
        "applianceDescription",
        "instruction",
        "text",
        "description",
    ):
        value = step.get(key)
        if isinstance(value, str):
            text = _clean_text(value)
            if text and text not in values:
                values.append(text)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    text = _clean_text(item)
                    if text and text not in values:
                        values.append(text)
    return values


def _cookeo_program(step: dict[str, Any]) -> tuple[str | None, str | None]:
    sequences = step.get("sequences")
    if not isinstance(sequences, list):
        return None, None
    fallback: tuple[str | None, str | None] = (None, None)
    for sequence in sequences:
        if not isinstance(sequence, dict):
            continue
        group = sequence.get("applianceGroup")
        group_key = str(group.get("key") or "") if isinstance(group, dict) else ""
        operations = sequence.get("operations")
        if not isinstance(operations, list):
            continue
        for operation in operations:
            if not isinstance(operation, dict):
                continue
            program = operation.get("program")
            if not isinstance(program, dict):
                continue
            candidate = (
                _clean_text(program.get("key")),
                _clean_text(program.get("name")),
            )
            if fallback == (None, None):
                fallback = candidate
            if group_key == "APPLIANCE_GROUP_15":
                return candidate
    return fallback


def extract_recipe_steps(root: dict[str, Any]) -> list[dict[str, Any]]:
    raw = root.get("steps") if isinstance(root, dict) else None
    if not isinstance(raw, list):
        raw = []
    out: list[dict[str, Any]] = []
    for position, step in enumerate(raw):
        if not isinstance(step, dict):
            continue
        texts = _step_texts(step)
        step_type = step.get("type")
        if isinstance(step_type, dict):
            type_key = _clean_text(step_type.get("key"))
            type_name = _clean_text(step_type.get("name"))
        else:
            type_key = _clean_text(step_type)
            type_name = None
        program_key, program_name = _cookeo_program(step)
        row = {
            "functionalId": _fid(step.get("fid") or step.get("identifier") or step.get("functionalId")),
            "stepIndex": position,
            "type": type_key,
            "typeName": type_name,
            "instruction": texts[0] if texts else None,
            "instructions": texts,
            "applicationDescription": _clean_text(step.get("applicationDescription")),
            "applianceDescription": _clean_text(step.get("applianceDescription")),
            "programKey": program_key,
            "programName": program_name,
        }
        out.append({key: value for key, value in row.items() if value is not None})

    # A few publications expose fullInstructions even when steps are absent.
    if not out:
        full = root.get("fullInstructions") if isinstance(root, dict) else None
        if isinstance(full, list):
            for position, value in enumerate(full):
                if isinstance(value, str):
                    text = _clean_text(value)
                elif isinstance(value, dict):
                    texts = _step_texts(value)
                    text = texts[0] if texts else None
                else:
                    text = None
                if text:
                    out.append({"stepIndex": position, "instruction": text, "instructions": [text]})
    return out


def _unit_value(unit: Any) -> tuple[str | None, str | None]:
    if not isinstance(unit, dict):
        return None, None
    return (
        _clean_text(unit.get("abbreviation") or unit.get("name")),
        _clean_text(unit.get("key")),
    )


def extract_recipe_ingredients(root: dict[str, Any]) -> list[dict[str, Any]]:
    raw = root.get("ingredients") if isinstance(root, dict) else None
    if not isinstance(raw, list):
        raw = []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        food = item.get("food") if isinstance(item.get("food"), dict) else {}
        unit, unit_key = _unit_value(item.get("unit"))
        canonical = _clean_text(
            food.get("name")
            or item.get("applicationDescription")
            or item.get("applianceDescription")
        )
        if not canonical:
            continue
        row: dict[str, Any] = {
            "name": canonical,
            "foodName": _clean_text(food.get("name")),
            "foodKey": _clean_text(food.get("key")),
            "functionalId": _fid(item.get("fid")),
            "quantity": item.get("quantity"),
            "unit": unit,
            "unitKey": unit_key,
            "applicationDescription": _clean_text(item.get("applicationDescription")),
            "applianceDescription": _clean_text(item.get("applianceDescription")),
        }
        out.append({key: value for key, value in row.items() if value is not None})
    return out


def _key_name_list(root: dict[str, Any], key: str) -> list[dict[str, str]]:
    raw = root.get(key) if isinstance(root, dict) else None
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            row = {
                name: text
                for name in ("key", "name")
                if (text := _clean_text(item.get(name)))
            }
            if row:
                out.append(row)
        elif (text := _clean_text(item)):
            out.append({"name": text})
    return out


def _durations(root: dict[str, Any]) -> dict[str, Any]:
    data = root.get("durations") if isinstance(root.get("durations"), dict) else {}
    keys = ("prepTime", "cookingTime", "offApplianceCookingTime", "restingTime", "totalTime")
    out = {key: data.get(key) for key in keys if data.get(key) is not None}
    quick = data.get("quickRecipe", data.get("isQuickRecipe"))
    if quick is not None:
        out["isQuickRecipe"] = bool(quick)
    return out


def _yield(root: dict[str, Any]) -> dict[str, Any]:
    data = root.get("yield") if isinstance(root.get("yield"), dict) else {}
    unit, unit_key = _unit_value(data.get("unit"))
    out = {
        "quantity": data.get("quantity"),
        "quantityDisplay": _clean_text(data.get("quantityDisplay")),
        "unit": unit,
        "unitKey": unit_key,
    }
    return {key: value for key, value in out.items() if value is not None}


def _request_headers(cfg, tokens, country, configured_language, app_version, url, pcfg):
    return c4m._recipe_request_headers(
        cfg,
        tokens,
        country,
        configured_language,
        app_version,
        url,
        pcfg=pcfg,
    )


def _http_json(method: str, url: str, *, headers_iter, params=None, body=None, timeout=30):
    if c4m.curl_requests is None:
        raise CatalogError("curl-cffi is not available")
    errors: list[str] = []
    saw_auth_error = False
    for name, headers in headers_iter:
        try:
            if method == "GET":
                response = c4m.curl_requests.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    allow_redirects=True,
                    impersonate="chrome",
                )
            else:
                response = c4m.curl_requests.post(
                    url,
                    params=params,
                    headers=headers,
                    json=body if body is not None else {},
                    timeout=timeout,
                    allow_redirects=True,
                    impersonate="chrome",
                )
        except Exception as exc:
            errors.append(f"{name}=network:{type(exc).__name__}")
            continue
        status = int(response.status_code)
        if 200 <= status < 300:
            try:
                return response.json(), name
            except Exception as exc:
                raise CatalogError(f"SEB recipe endpoint returned invalid JSON: {type(exc).__name__}") from None
        if status in {401, 403}:
            saw_auth_error = True
        errors.append(f"{name}=HTTP{status}")
    message = " | ".join(errors)
    if saw_auth_error:
        raise CatalogAuthError("SEB recipe authentication failed (tokens redacted): " + message)
    raise CatalogError("SEB recipe request failed: " + message)


def _platform_context(cfg, country, configured_language, app_version):
    # Locale selection for RCU/auth remains the configured appliance/account
    # locale.  The recipe query's display language is independent below.
    return c4m.discover_rcu(
        cfg,
        country,
        configured_language,
        app_version,
        save=False,
    )


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
    variant = _fid(variant_id)
    if not variant:
        raise CatalogError("Recipe variant ID is required")
    configured_language = (configured_language or language or "de").lower()
    language = (language or configured_language).lower()
    pcfg = pcfg or _platform_context(cfg, country, configured_language, app_version)
    base = cfg["platform_base_url"].rstrip("/")
    url = base + "/common-api/v3/recipes/PRO/" + urllib.parse.quote(variant, safe="") + "/?format=mobile"
    payload, auth_mode = _http_json(
        "GET",
        url,
        headers_iter=_request_headers(cfg, tokens, country, configured_language, app_version, url, pcfg),
    )
    root = _recipe_root(payload)
    grouping_id = _fid(root.get("groupingId")) or _fid(root.get("topRecipeId"))
    recipe_id = _fid(root.get("fid")) or _fid(root.get("identifier")) or variant
    steps = extract_recipe_steps(root)
    title = _clean_text(root.get("title") or root.get("shortTitle") or root.get("normalizedTitle"))
    normalized = {
        "groupingFunctionalId": grouping_id,
        "recipeFunctionalId": recipe_id,
        "variantFunctionalId": recipe_id,
        "searchVariantId": variant,
        "title": title,
        "cover": extract_recipe_cover(root),
        "stepCount": len(steps),
        "steps": steps,
        "ingredients": extract_recipe_ingredients(root),
        "excludedFoods": _key_name_list(root, "excludedFoods"),
        "detectedExcludedFoods": _key_name_list(root, "detectedExcludedFoods"),
        "courses": _key_name_list(root, "courses"),
        "occasions": _key_name_list(root, "occasions"),
        "durations": _durations(root),
        "yield": _yield(root),
        "difficulty": root.get("difficulty"),
        "recipeType": root.get("recipeType"),
        "language": _clean_text(root.get("lang")) or language,
        "market": _clean_text(root.get("market")),
        "groupSize": root.get("groupSize"),
        "isAutomaticallyGenerated": bool(root.get("isAutomaticallyGenerated")),
        "isPremium": bool(root.get("isPremium")),
        "sendable": bool(grouping_id and recipe_id),
        "source": "sebplatform_mobile_recipe",
        "authMode": auth_mode,
    }
    return {key: value for key, value in normalized.items() if value is not None}


def _search_cover(raw: dict[str, Any]) -> str | None:
    # Search DTO has a dedicated RecipesCover field; inspect exactly that.
    return _cover_from_cover_object(raw.get("cover"))


def _light_search_row(raw: dict[str, Any]) -> dict[str, Any] | None:
    variant = _fid(raw.get("identifier")) or _fid(raw.get("fid")) or _fid(raw.get("functionalId"))
    if not variant:
        return None
    grouping = _fid(raw.get("groupingId"))
    row: dict[str, Any] = {
        "searchVariantId": variant,
        "variantFunctionalId": variant,
        "groupingFunctionalId": grouping,
        "source": "sebplatform_search",
        "title": _clean_text(raw.get("title") or raw.get("shortTitle") or raw.get("normalizedTitle")),
        "cover": _search_cover(raw),
        "language": _clean_text(raw.get("lang")),
        "market": _clean_text(raw.get("market")),
        "groupSize": raw.get("groupSize"),
        "yield": _yield(raw),
        "difficulty": raw.get("difficulty"),
    }
    return {key: value for key, value in row.items() if value is not None}


def _servings(item: dict[str, Any]) -> float | None:
    value = (item.get("yield") or {}).get("quantity") if isinstance(item.get("yield"), dict) else None
    if value is None:
        value = item.get("groupSize")
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _variant_score(
    item: dict[str, Any],
    *,
    preferred_language: str,
    configured_language: str,
    country: str,
) -> float:
    language = str(item.get("language") or "").lower()
    market = str(item.get("market") or "").upper()
    score = 0.0
    if language == preferred_language.lower():
        score += 200
    elif language == configured_language.lower():
        score += 90
    elif not language:
        score += 5
    if market == f"GS_{country.upper()}":
        score += 55
    if item.get("sendable"):
        score += 25
    if item.get("cover"):
        score += 12
    if any((step.get("instruction") or step.get("programName")) for step in item.get("steps") or [] if isinstance(step, dict)):
        score += 12
    servings = _servings(item)
    if servings is not None:
        score += max(0.0, 10.0 - abs(servings - 4.0) * 2.0)
    return score


def collapse_variants(
    items: list[dict[str, Any]],
    *,
    preferred_language: str,
    configured_language: str,
    country: str,
) -> list[dict[str, Any]]:
    """Return one card per proven recipe grouping while retaining send variant."""
    groups: "OrderedDict[str, list[dict[str, Any]]]" = OrderedDict()
    for item in items:
        if not isinstance(item, dict):
            continue
        grouping = _fid(item.get("groupingFunctionalId"))
        variant = _fid(item.get("searchVariantId") or item.get("variantFunctionalId"))
        key = "g:" + grouping if grouping else "v:" + str(variant or len(groups))
        groups.setdefault(key, []).append(item)

    output: list[dict[str, Any]] = []
    for variants in groups.values():
        display = max(
            variants,
            key=lambda item: _variant_score(
                item,
                preferred_language=preferred_language,
                configured_language=configured_language,
                country=country,
            ),
        )
        # Sending should stay on the device/account locale when available even
        # if a sibling translation is used for display.
        send = max(
            variants,
            key=lambda item: _variant_score(
                item,
                preferred_language=configured_language,
                configured_language=configured_language,
                country=country,
            ),
        )
        result = deepcopy(display)
        result["displayVariantId"] = display.get("searchVariantId") or display.get("variantFunctionalId")
        result["sendVariantId"] = send.get("searchVariantId") or send.get("variantFunctionalId")
        result["sendGroupingFunctionalId"] = send.get("groupingFunctionalId")
        result["sendRecipeFunctionalId"] = send.get("recipeFunctionalId") or send.get("variantFunctionalId")
        result["sendable"] = bool(
            send.get("sendable")
            and result.get("sendVariantId")
            and result.get("sendGroupingFunctionalId")
            and result.get("sendRecipeFunctionalId")
        )
        result["variants"] = [
            {
                key: value
                for key, value in {
                    "variantId": item.get("searchVariantId") or item.get("variantFunctionalId"),
                    "recipeFunctionalId": item.get("recipeFunctionalId"),
                    "language": item.get("language"),
                    "market": item.get("market"),
                    "yield": item.get("yield"),
                    "cover": item.get("cover"),
                }.items()
                if value is not None
            }
            for item in variants
        ]
        servings = sorted({value for item in variants if (value := _servings(item)) is not None})
        if servings:
            result["availableServings"] = servings
        output.append(result)
    return output


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
    if c4m.curl_requests is None:
        raise CatalogError("curl-cffi is not available")
    page = max(0, int(page))
    size = max(1, min(int(size), 50))
    max_details = max(0, min(int(max_details), 50))
    country = str(country or "DE").upper()
    configured_language = str(configured_language or language or "de").lower()
    language = str(language or configured_language).lower()

    cfg = dict(cfg)
    pcfg = _platform_context(cfg, country, configured_language, app_version)
    base = cfg["platform_base_url"].rstrip("/")
    url = base + "/common-api/v4/search/recipes"
    params = {
        "lang": language,
        "market": f"GS_{country}",
        "page": page,
        "size": size,
        "q": str(query or ""),
        "groupBy": "",
        "myUniverse": "false",
        "myOwnRecipe": "false",
        "withAutomaticSpellcheck": "true",
    }
    payload, auth_mode = _http_json(
        "POST",
        url,
        headers_iter=_request_headers(cfg, tokens, country, configured_language, app_version, url, pcfg),
        params=params,
        body={},
    )
    if not isinstance(payload, dict):
        raise CatalogError("SEB recipe search returned an unexpected response")
    raw_content = payload.get("content") if isinstance(payload.get("content"), list) else []
    lightweight = [row for raw in raw_content if isinstance(raw, dict) if (row := _light_search_row(raw))]
    enriched = [deepcopy(row) for row in lightweight]

    count = min(max_details, len(lightweight))
    if count:
        def load(index: int):
            variant = lightweight[index]["searchVariantId"]
            detail = recipe_detail(
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
                except Exception as exc:
                    enriched[index]["detailError"] = type(exc).__name__
                    continue
                # Detail is authoritative, but search DTO cover/grouping/title
                # remains a useful fallback when a publication omits one.
                merged = dict(lightweight[index])
                merged.update(detail)
                if not merged.get("cover"):
                    merged["cover"] = lightweight[index].get("cover")
                if not merged.get("title"):
                    merged["title"] = lightweight[index].get("title")
                if not merged.get("groupingFunctionalId"):
                    merged["groupingFunctionalId"] = lightweight[index].get("groupingFunctionalId")
                enriched[index] = {key: value for key, value in merged.items() if value is not None}

    collapsed = collapse_variants(
        enriched,
        preferred_language=language,
        configured_language=configured_language,
        country=country,
    )
    page_obj = payload.get("page") if isinstance(payload.get("page"), dict) else {"number": page, "size": size}
    return {
        "query": str(query or ""),
        "requestedLanguage": language,
        "configuredLanguage": configured_language,
        "market": f"GS_{country}",
        "page": page_obj,
        "rawVariantCount": len(lightweight),
        "groupedRecipeCount": len(collapsed),
        "items": collapsed,
        "facets": payload.get("facets") if isinstance(payload.get("facets"), list) else [],
        "authMode": auth_mode,
    }
