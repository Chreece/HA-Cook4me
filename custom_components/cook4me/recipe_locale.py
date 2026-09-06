from __future__ import annotations

from copy import deepcopy
from typing import Any

# SEB recipe search is market-aware as well as language-aware. Home Assistant
# UI language is independent from the appliance/account country, so use a
# language-appropriate display market for catalog localization while retaining
# a separate device-market result for safe sending.
_LANGUAGE_DEFAULT_COUNTRY: dict[str, str] = {
    "el": "GR",
    "de": "DE",
    "en": "GB",
    "fr": "FR",
    "it": "IT",
    "es": "ES",
    "pt": "PT",
    "nl": "NL",
    "pl": "PL",
    "cs": "CZ",
    "sk": "SK",
    "hu": "HU",
    "bg": "BG",
    "ro": "RO",
    "sl": "SI",
    "hr": "HR",
    "sv": "SE",
    "da": "DK",
    "fi": "FI",
    "no": "NO",
    "tr": "TR",
    "uk": "UA",
    "ru": "RU",
}


def normalize_language(value: str | None, fallback: str = "en") -> str:
    text = str(value or fallback or "en").strip().lower().replace("_", "-")
    return text.split("-", 1)[0] or fallback


def display_country_for_language(language: str | None, fallback_country: str) -> str:
    language = normalize_language(language)
    return _LANGUAGE_DEFAULT_COUNTRY.get(language, str(fallback_country or "DE").upper())


def _group_key(item: dict[str, Any]) -> str:
    grouping = str(item.get("groupingFunctionalId") or item.get("sendGroupingFunctionalId") or "").strip()
    if grouping:
        return "g:" + grouping
    variant = str(
        item.get("displayVariantId")
        or item.get("searchVariantId")
        or item.get("variantFunctionalId")
        or item.get("sendVariantId")
        or ""
    ).strip()
    return "v:" + variant


def _language(item: dict[str, Any]) -> str:
    return normalize_language(str(item.get("language") or ""), "")


def _send_fields(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "sendVariantId": item.get("sendVariantId")
        or item.get("displayVariantId")
        or item.get("searchVariantId")
        or item.get("variantFunctionalId"),
        "sendGroupingFunctionalId": item.get("sendGroupingFunctionalId")
        or item.get("groupingFunctionalId"),
        "sendRecipeFunctionalId": item.get("sendRecipeFunctionalId")
        or item.get("recipeFunctionalId")
        or item.get("variantFunctionalId")
        or item.get("searchVariantId"),
    }


def _has_send_fields(item: dict[str, Any]) -> bool:
    values = _send_fields(item)
    return bool(
        values.get("sendVariantId")
        and values.get("sendGroupingFunctionalId")
        and values.get("sendRecipeFunctionalId")
    )


def merge_display_and_device_catalogs(
    display_result: dict[str, Any] | None,
    device_result: dict[str, Any] | None,
    *,
    target_language: str,
) -> dict[str, Any]:
    """Overlay localized display recipes onto device-compatible send variants.

    Device-market results remain the authority for the exact recipe variant used
    when sending. Display-market siblings are used only for title/photo/
    ingredients/steps. If no localized sibling exists, the device result is
    kept and marked ``translationRequired`` for the frontend translation
    fallback. The final send path still refetches official detail and validates
    exact IDs before publishing, so lightweight device search rows are safe to
    use as send-variant hints here.
    """

    target = normalize_language(target_language)
    display_result = display_result if isinstance(display_result, dict) else {}
    device_result = device_result if isinstance(device_result, dict) else {}
    display_items = [x for x in display_result.get("items") or [] if isinstance(x, dict)]
    device_items = [x for x in device_result.get("items") or [] if isinstance(x, dict)]

    localized_by_group: dict[str, dict[str, Any]] = {}
    fallback_display_by_group: dict[str, dict[str, Any]] = {}
    for item in display_items:
        key = _group_key(item)
        fallback_display_by_group.setdefault(key, item)
        if _language(item) == target:
            localized_by_group.setdefault(key, item)

    output: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Base the visible list on device-market results whenever possible so every
    # card can keep a proven device-locale send variant.
    for device in device_items:
        key = _group_key(device)
        display = localized_by_group.get(key) or fallback_display_by_group.get(key)
        if display is not None:
            merged = deepcopy(display)
            merged["deviceSourceLanguage"] = device.get("language")
            merged["deviceSourceMarket"] = device.get("market")
            for name, value in _send_fields(device).items():
                if value is not None:
                    merged[name] = value
            merged["sendable"] = _has_send_fields(merged)
        else:
            merged = deepcopy(device)
            for name, value in _send_fields(device).items():
                if value is not None:
                    merged[name] = value
            merged["sendable"] = _has_send_fields(merged)

        source_language = _language(merged)
        merged["requestedLanguage"] = target
        merged["translationRequired"] = bool(source_language and source_language != target)
        if source_language and source_language != target:
            merged["sourceLanguage"] = source_language
        else:
            merged["localizedBySeb"] = bool(source_language == target)
        output.append(merged)
        seen.add(key)

    # Append target-language display-only groups too. They remain viewable but
    # deliberately unsendable until a device-market sibling is proven.
    for display in display_items:
        key = _group_key(display)
        if key in seen:
            continue
        source_language = _language(display)
        # When device results exist, only append genuinely localized display
        # extras; otherwise a second set of foreign-language cards would defeat
        # the purpose of the display-market pass.
        if device_items and source_language != target:
            continue
        merged = deepcopy(display)
        merged["requestedLanguage"] = target
        merged["translationRequired"] = bool(source_language and source_language != target)
        if source_language and source_language != target:
            merged["sourceLanguage"] = source_language
        else:
            merged["localizedBySeb"] = bool(source_language == target)
        merged["sendable"] = False
        merged["deviceVariantMissing"] = True
        output.append(merged)
        seen.add(key)

    result = deepcopy(device_result if device_result else display_result)
    result["items"] = output
    result["requestedLanguage"] = target
    result["displayMarket"] = display_result.get("market")
    result["deviceMarket"] = device_result.get("market")
    result["localizedResultCount"] = sum(1 for item in output if item.get("localizedBySeb"))
    result["translationRequiredCount"] = sum(1 for item in output if item.get("translationRequired"))
    return result
