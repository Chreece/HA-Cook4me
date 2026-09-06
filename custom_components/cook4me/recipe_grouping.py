from __future__ import annotations

from copy import deepcopy
import math
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


def _variants(item: dict[str, Any]) -> list[dict[str, Any]]:
    raw = item.get("variants")
    out = [dict(row) for row in raw or [] if isinstance(row, dict) and _variant_id(row)]
    if out:
        return out
    variant = _variant_id(item)
    if not variant:
        return []
    return [
        {
            "variantId": variant,
            "recipeFunctionalId": item.get("recipeFunctionalId") or item.get("variantFunctionalId"),
            "language": item.get("language"),
            "market": item.get("market"),
            "yield": deepcopy(item.get("yield")),
            "cover": item.get("cover"),
        }
    ]


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


def _best_per_serving(item: dict[str, Any], language: str, country: str) -> dict[str, dict[str, Any]]:
    best: dict[str, tuple[int, dict[str, Any]]] = {}
    for row in _variants(item):
        serving = _servings(row)
        key = f"n:{serving:g}" if serving is not None else "default"
        score = _variant_score(row, language, country)
        current = best.get(key)
        if current is None or score > current[0]:
            best[key] = (score, row)
    return {key: value for key, (_score, value) in best.items()}


def _serving_options(
    display: dict[str, Any],
    device: dict[str, Any] | None,
    *,
    display_language: str,
    device_language: str,
    device_country: str,
) -> list[dict[str, Any]]:
    if not device:
        return []
    device_rows = _best_per_serving(device, device_language, device_country)
    display_rows = _best_per_serving(display, display_language, device_country)
    options: list[dict[str, Any]] = []
    grouping = _grouping(device) or _grouping(display)
    for key, send_row in device_rows.items():
        send_variant = _variant_id(send_row)
        if not send_variant:
            continue
        display_row = display_rows.get(key)
        # A target-language sibling with another serving amount would show the
        # wrong ingredient quantities. Fall back to the exact device variant if
        # there is no same-serving display sibling.
        display_variant = _variant_id(display_row or {}) or send_variant
        serving = _servings(send_row)
        options.append(
            {
                "servings": serving,
                "label": _serving_label(send_row, serving),
                "displayVariantId": display_variant,
                "sendVariantId": send_variant,
                "recipeFunctionalId": send_row.get("recipeFunctionalId") or send_variant,
                "groupingFunctionalId": grouping or None,
                "language": _lang(send_row.get("language")) or None,
                "market": send_row.get("market"),
            }
        )
    options.sort(key=lambda row: (row.get("servings") is None, row.get("servings") or 0, row.get("sendVariantId") or ""))
    return [{key: value for key, value in row.items() if value is not None} for row in options]


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
        result["sendGroupingFunctionalId"] = device.get("sendGroupingFunctionalId") or device.get("groupingFunctionalId")
        result["sendRecipeFunctionalId"] = device.get("sendRecipeFunctionalId") or device.get("recipeFunctionalId") or device.get("variantFunctionalId")
        result["sendVariantId"] = device.get("sendVariantId") or device.get("displayVariantId") or device.get("searchVariantId") or device.get("variantFunctionalId")
    options = _serving_options(
        result,
        device,
        display_language=target_language,
        device_language=configured_language,
        device_country=device_country,
    )
    if options:
        result["servingVariants"] = options
        result["availableServings"] = [row["servings"] for row in options if row.get("servings") is not None]
        default_send = str(result.get("sendVariantId") or "")
        selected = next((row for row in options if str(row.get("sendVariantId")) == default_send), None)
        if selected is None:
            selected = min(
                options,
                key=lambda row: abs(float(row.get("servings") or 4) - 4),
            )
        result["sendVariantId"] = selected.get("sendVariantId")
        # Preserve an exact same-serving display sibling when one exists.
        result["displayVariantId"] = selected.get("displayVariantId") or result.get("displayVariantId")
        result["selectedServings"] = selected.get("servings")
    source_language = _lang(result.get("language"))
    target = _lang(target_language)
    result["requestedLanguage"] = target
    result["translationRequired"] = bool(source_language and source_language != target)
    if result["translationRequired"]:
        result["sourceLanguage"] = source_language
    else:
        result.pop("sourceLanguage", None)
    result["sendable"] = bool(
        device
        and result.get("sendVariantId")
        and (result.get("sendGroupingFunctionalId") or result.get("groupingFunctionalId"))
    )
    return result


def merge_hydrated_catalogs(
    display_result: dict[str, Any] | None,
    device_result: dict[str, Any] | None,
    *,
    target_language: str,
    configured_language: str,
    device_country: str,
    strict_language: bool,
) -> dict[str, Any]:
    """Merge fully hydrated catalogs into one card per recipe grouping.

    The display catalog owns visible text/media. The device catalog owns send
    variants. Serving variants are retained as choices on that single recipe
    card instead of being rendered as duplicates.
    """
    display_result = display_result if isinstance(display_result, dict) else {}
    device_result = device_result if isinstance(device_result, dict) else {}
    display_items = [row for row in display_result.get("items") or [] if isinstance(row, dict)]
    device_items = [row for row in device_result.get("items") or [] if isinstance(row, dict)]
    target = _lang(target_language)

    display_by_group = {_grouping(row): row for row in display_items if _grouping(row)}
    device_by_group = {_grouping(row): row for row in device_items if _grouping(row)}
    output: list[dict[str, Any]] = []
    seen: set[str] = set()

    if strict_language:
        # A selected language means exactly that language. Only hydrated rows
        # that actually report the selected language survive.
        for display in display_items:
            if _lang(display.get("language")) != target:
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
        # Automatic mode: one device-compatible recipe card is the baseline.
        # Replace its visible content only when a real target-language sibling
        # with the same proven groupingId exists.
        for device in device_items:
            group = _grouping(device)
            display = display_by_group.get(group) if group else None
            if display is None or _lang(display.get("language")) != target:
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
        # Target-language recipes without a matching device-market sibling are
        # useful for browsing but are intentionally not sendable.
        for display in display_items:
            group = _grouping(display)
            if group and group in seen:
                continue
            if _lang(display.get("language")) != target:
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
    result["servingVariantCount"] = sum(len(row.get("servingVariants") or []) for row in output)
    return result
