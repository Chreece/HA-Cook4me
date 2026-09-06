from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any


def _lang(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", "-").split("-", 1)[0]


def _market(value: Any) -> str:
    return str(value or "").strip().upper()


def _grouping(item: dict[str, Any]) -> str:
    return str(item.get("groupingFunctionalId") or item.get("sendGroupingFunctionalId") or "").strip()


def _variant_id(item: dict[str, Any]) -> str:
    return str(
        item.get("variantId")
        or item.get("displayVariantId")
        or item.get("searchVariantId")
        or item.get("variantFunctionalId")
        or item.get("sendVariantId")
        or ""
    ).strip()


def _servings(item: dict[str, Any]) -> float | None:
    value = None
    yield_value = item.get("yield")
    if isinstance(yield_value, dict):
        value = yield_value.get("quantity")
        if value is None:
            value = yield_value.get("quantityDisplay")
    if value is None:
        value = item.get("groupSize")
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def _serving_label(item: dict[str, Any], value: float | None) -> str | None:
    y = item.get("yield")
    if isinstance(y, dict) and y.get("quantityDisplay") not in (None, ""):
        return str(y["quantityDisplay"])
    if value is None:
        return None
    return str(int(value)) if value.is_integer() else str(value)


def _variant_record(item: dict[str, Any], *, inherit: dict[str, Any] | None = None) -> dict[str, Any] | None:
    variant = _variant_id(item)
    if not variant:
        return None
    parent = inherit or {}
    grouping = _grouping(item) or _grouping(parent)
    row = {
        "variantId": variant,
        "recipeFunctionalId": item.get("recipeFunctionalId")
        or item.get("variantFunctionalId")
        or parent.get("recipeFunctionalId")
        or variant,
        "groupingFunctionalId": grouping or None,
        "language": _lang(item.get("language") or parent.get("language")) or None,
        "market": item.get("market") or parent.get("market"),
        "yield": deepcopy(item.get("yield") if item.get("yield") is not None else parent.get("yield")),
        "cover": item.get("cover") or parent.get("cover"),
    }
    return {key: value for key, value in row.items() if value is not None}


def _variants(item: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    base = _variant_record(item)
    if base:
        seen.add(_variant_id(base))
        out.append(base)
    for raw in item.get("variants") or []:
        if not isinstance(raw, dict):
            continue
        row = _variant_record(raw, inherit=item)
        if row is None:
            continue
        variant = _variant_id(row)
        if variant in seen:
            continue
        seen.add(variant)
        out.append(row)
    return out


def _content_score(item: dict[str, Any]) -> int:
    score = 0
    if str(item.get("title") or "").strip():
        score += 20
    if item.get("cover"):
        score += 10
    if item.get("ingredients"):
        score += 8
    if item.get("steps"):
        score += 8
    if _grouping(item):
        score += 5
    return score


def _clean_title(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _merge_catalog_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge rows already proven to represent the same logical recipe family."""
    richest = max(rows, key=_content_score)
    result = deepcopy(richest)
    variant_rows: list[dict[str, Any]] = []
    seen_variants: set[str] = set()
    grouping_ids: list[str] = []
    for item in rows:
        grouping = _grouping(item)
        if grouping and grouping not in grouping_ids:
            grouping_ids.append(grouping)
        for variant in _variants(item):
            variant_id = _variant_id(variant)
            if not variant_id or variant_id in seen_variants:
                continue
            seen_variants.add(variant_id)
            variant_rows.append(variant)
    result["variants"] = variant_rows
    if grouping_ids:
        result["groupingFunctionalId"] = grouping_ids[0]
        if len(grouping_ids) > 1:
            # Exact title+cover+language duplicates can occasionally be
            # published under different top IDs. Preserve every exact grouping
            # on its serving variant instead of discarding delivery identity.
            result["groupingFunctionalIds"] = grouping_ids
    servings = sorted({value for row in variant_rows if (value := _servings(row)) is not None})
    if servings:
        result["availableServings"] = servings
    return result


def _coalesce_catalog(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse grouping IDs, then exact same-title/photo serving publications."""
    first: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for index, item in enumerate(items):
        grouping = _grouping(item)
        variant = _variant_id(item)
        key = f"g:{grouping}" if grouping else f"v:{variant or index}"
        if key not in first:
            first[key] = []
            order.append(key)
        first[key].append(item)
    grouped = [_merge_catalog_rows(first[key]) for key in order]

    # Some SEB serving publications expose different top/grouping IDs even
    # though the hydrated recipe has the exact same source-language title and
    # exact same recipe cover. This is strong local evidence of one logical
    # recipe with serving variants (e.g. identical 2/4/6-serving cards), so
    # collapse that exact duplicate shape as a second pass. We deliberately do
    # not use fuzzy title or image matching.
    second: dict[str, list[dict[str, Any]]] = {}
    second_order: list[str] = []
    for index, item in enumerate(grouped):
        title = _clean_title(item.get("title"))
        cover = str(item.get("cover") or "").strip()
        language = _lang(item.get("language"))
        if title and cover and language:
            key = f"tc:{language}:{title}:{cover}"
        else:
            key = f"keep:{index}"
        if key not in second:
            second[key] = []
            second_order.append(key)
        second[key].append(item)
    return [_merge_catalog_rows(second[key]) for key in second_order]


def _variant_score(row: dict[str, Any], language: str, country: str) -> int:
    score = 0
    row_language = _lang(row.get("language"))
    row_market = _market(row.get("market"))
    if row_language == _lang(language):
        score += 100
    if row_market == f"GS_{str(country).upper()}":
        score += 60
    if row.get("recipeFunctionalId"):
        score += 10
    return score


def _best_rows_by_serving(rows: list[dict[str, Any]], language: str, country: str) -> dict[str, dict[str, Any]]:
    best: dict[str, tuple[int, dict[str, Any]]] = {}
    for row in rows:
        serving = _servings(row)
        key = f"n:{serving:g}" if serving is not None else "default"
        score = _variant_score(row, language, country)
        current = best.get(key)
        if current is None or score > current[0]:
            best[key] = (score, row)
    return {key: value for key, (_score, value) in best.items()}


def _language_variants(
    display: dict[str, Any],
    device: dict[str, Any] | None,
    *,
    target_language: str,
    configured_language: str,
    device_country: str,
) -> list[dict[str, Any]]:
    display_rows = _variants(display)
    device_rows = _variants(device) if device else []
    if not display_rows and not device_rows:
        return []

    rows_by_language: dict[str, list[dict[str, Any]]] = {}
    language_order: list[str] = []
    for row in [*display_rows, *device_rows]:
        language = _lang(row.get("language"))
        if not language:
            continue
        if language not in rows_by_language:
            rows_by_language[language] = []
            language_order.append(language)
        variant = _variant_id(row)
        if not any(_variant_id(existing) == variant for existing in rows_by_language[language]):
            rows_by_language[language].append(row)

    target = _lang(target_language)
    configured = _lang(configured_language)
    language_order.sort(key=lambda code: (code != target, code != configured, code))
    device_by_serving = _best_rows_by_serving(device_rows, configured_language, device_country)

    result: list[dict[str, Any]] = []
    for language in language_order:
        language_rows = rows_by_language[language]
        display_by_serving = _best_rows_by_serving(language_rows, language, device_country)
        serving_options: list[dict[str, Any]] = []
        for serving_key, display_row in display_by_serving.items():
            send_row = device_by_serving.get(serving_key)
            serving = _servings(display_row)
            row = {
                "servings": serving,
                "label": _serving_label(display_row, serving),
                "displayVariantId": _variant_id(display_row),
                "displayRecipeFunctionalId": display_row.get("recipeFunctionalId") or _variant_id(display_row),
                "displayGroupingFunctionalId": _grouping(display_row) or None,
                "sendVariantId": _variant_id(send_row or {}) or None,
                "sendRecipeFunctionalId": (send_row or {}).get("recipeFunctionalId") or _variant_id(send_row or {}) or None,
                "sendGroupingFunctionalId": _grouping(send_row or {}) or None,
                "language": language,
                "market": display_row.get("market"),
            }
            serving_options.append({key: value for key, value in row.items() if value is not None})
        serving_options.sort(
            key=lambda row: (
                row.get("servings") is None,
                row.get("servings") or 0,
                row.get("displayVariantId") or "",
            )
        )
        if not serving_options:
            continue
        result.append(
            {
                "language": language,
                "market": next((row.get("market") for row in language_rows if row.get("market")), None),
                "servingVariants": serving_options,
                "availableServings": [
                    row["servings"] for row in serving_options if row.get("servings") is not None
                ],
                "sendable": any(row.get("sendVariantId") for row in serving_options),
            }
        )
    return result


def _decorate(
    display: dict[str, Any],
    device: dict[str, Any] | None,
    *,
    target_language: str,
    configured_language: str,
    device_country: str,
) -> dict[str, Any]:
    result = deepcopy(display)
    if device:
        result["deviceSourceLanguage"] = device.get("language")
        result["deviceSourceMarket"] = device.get("market")

    languages = _language_variants(
        result,
        device,
        target_language=target_language,
        configured_language=configured_language,
        device_country=device_country,
    )
    if languages:
        result["languageVariants"] = languages
        result["availableLanguages"] = [row["language"] for row in languages]
        source_language = _lang(result.get("language"))
        target = _lang(target_language)
        active = next((row for row in languages if row["language"] == target), None)
        if active is None and source_language:
            active = next((row for row in languages if row["language"] == source_language), None)
        if active is None:
            active = languages[0]
        result["selectedLanguage"] = active["language"]
        result["servingVariants"] = deepcopy(active["servingVariants"])
        result["availableServings"] = deepcopy(active["availableServings"])

        options = result["servingVariants"]
        selected = min(
            options,
            key=lambda row: abs(float(row.get("servings") or 4) - 4),
        )
        result["displayVariantId"] = selected.get("displayVariantId") or result.get("displayVariantId")
        result["sendVariantId"] = selected.get("sendVariantId")
        result["sendGroupingFunctionalId"] = selected.get("sendGroupingFunctionalId")
        result["sendRecipeFunctionalId"] = selected.get("sendRecipeFunctionalId")
        result["selectedServings"] = selected.get("servings")

    source_language = _lang(result.get("language"))
    target = _lang(target_language)
    result["requestedLanguage"] = target
    result["translationRequired"] = bool(source_language and source_language != target)
    if result["translationRequired"]:
        result["sourceLanguage"] = source_language
    else:
        result.pop("sourceLanguage", None)
    result["sendable"] = bool(result.get("sendVariantId"))
    return result


def _by_group(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {_grouping(row): row for row in items if _grouping(row)}


def merge_hydrated_catalogs(
    display_result: dict[str, Any] | None,
    device_result: dict[str, Any] | None,
    *,
    target_language: str,
    configured_language: str,
    device_country: str,
    strict_language: bool,
) -> dict[str, Any]:
    """Merge hydrated catalogs into one card per logical recipe.

    A logical recipe owns language variants; each language owns serving
    variants.  This prevents both serving duplicates and same-recipe language
    duplicates from becoming separate cards when SEB provides a proven common
    groupingId. Exact same-language title+cover duplicates are additionally
    collapsed for publications whose serving variants use different top IDs.
    """
    display_result = display_result if isinstance(display_result, dict) else {}
    device_result = device_result if isinstance(device_result, dict) else {}
    display_items = _coalesce_catalog(
        [row for row in display_result.get("items") or [] if isinstance(row, dict)]
    )
    device_items = _coalesce_catalog(
        [row for row in device_result.get("items") or [] if isinstance(row, dict)]
    )
    target = _lang(target_language)

    display_by_group = _by_group(display_items)
    device_by_group = _by_group(device_items)
    output: list[dict[str, Any]] = []
    seen: set[str] = set()

    if strict_language:
        # The request itself is language constrained by the v8 app-equivalent
        # search body. Keep only rows whose hydrated source confirms the chosen
        # language, but retain all same-group language metadata for the per-card
        # language selector when the backend returns it.
        for display in display_items:
            display_languages = {_lang(row.get("language")) for row in _variants(display)}
            if target not in display_languages and _lang(display.get("language")) != target:
                continue
            group = _grouping(display)
            device = device_by_group.get(group) if group else None
            output.append(
                _decorate(
                    display,
                    device,
                    target_language=target,
                    configured_language=configured_language,
                    device_country=device_country,
                )
            )
            if group:
                seen.add(group)
    else:
        for device in device_items:
            group = _grouping(device)
            display = display_by_group.get(group) if group else None
            if display is None:
                display = device
            output.append(
                _decorate(
                    display,
                    device,
                    target_language=target,
                    configured_language=configured_language,
                    device_country=device_country,
                )
            )
            if group:
                seen.add(group)
        for display in display_items:
            group = _grouping(display)
            if group and group in seen:
                continue
            display_languages = {_lang(row.get("language")) for row in _variants(display)}
            if target not in display_languages and _lang(display.get("language")) != target:
                continue
            output.append(
                _decorate(
                    display,
                    None,
                    target_language=target,
                    configured_language=configured_language,
                    device_country=device_country,
                )
            )

    result = deepcopy(device_result if device_result else display_result)
    result["items"] = output
    result["requestedLanguage"] = target
    result["strictLanguage"] = bool(strict_language)
    result["groupedRecipeCount"] = len(output)
    result["languageVariantCount"] = sum(len(row.get("languageVariants") or []) for row in output)
    result["servingVariantCount"] = sum(
        sum(len(language.get("servingVariants") or []) for language in row.get("languageVariants") or [])
        for row in output
    )
    return result
