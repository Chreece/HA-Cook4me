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
    """Overlay exact target-language siblings onto device-compatible variants.

    The device-market result is the fallback source of visible recipe content and
    the authority for send-variant hints. A display-market sibling replaces its
    visible fields only when that sibling is actually in ``target_language``.
    This avoids showing an arbitrary Slovak/Hungarian/etc. fallback merely
    because a target-market search happened to return it.
    """

    target = normalize_language(target_language)
    display_result = display_result if isinstance(display_result, dict) else {}
    device_result = device_result if isinstance(device_result, dict) else {}
    display_items = [x for x in display_result.get("items") or [] if isinstance(x, dict)]
    device_items = [x for x in device_result.get("items") or [] if isinstance(x, dict)]

    localized_by_group: dict[str, dict[str, Any]] = {}
    for item in display_items:
        if _language(item) == target:
            localized_by_group.setdefault(_group_key(item), item)

    output: list[dict[str, Any]] = []
    seen: set[str] = set()

    for device in device_items:
        key = _group_key(device)
        display = localized_by_group.get(key)
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

    # Exact target-language display-only groups stay visible, but sending is
    # disabled until a device-market sibling has been proven.
    for display in display_items:
        key = _group_key(display)
        if key in seen or _language(display) != target:
            continue
        merged = deepcopy(display)
        merged["requestedLanguage"] = target
        merged["translationRequired"] = False
        merged["localizedBySeb"] = True
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
