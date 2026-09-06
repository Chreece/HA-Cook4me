from __future__ import annotations

# Language/market pairs observed in the SEB/KRUPS recipe-content corpus used by
# this integration.  They are exposed to the frontend as selectable catalog
# languages; display names are rendered by the browser using Intl.DisplayNames.
#
# A language selection controls only recipe catalog display/filtering.  Device
# delivery continues to resolve and validate the appliance/account-locale
# variant independently.
SUPPORTED_RECIPE_LANGUAGES: tuple[dict[str, str], ...] = (
    {"code": "ar", "country": "AE"},
    {"code": "bg", "country": "BG"},
    {"code": "cs", "country": "CZ"},
    {"code": "da", "country": "DK"},
    {"code": "de", "country": "DE"},
    {"code": "el", "country": "GR"},
    {"code": "en", "country": "GB"},
    {"code": "es", "country": "ES"},
    {"code": "fa", "country": "AE"},
    {"code": "fi", "country": "FI"},
    {"code": "fr", "country": "FR"},
    {"code": "hr", "country": "HR"},
    {"code": "hu", "country": "HU"},
    {"code": "it", "country": "IT"},
    {"code": "ja", "country": "JP"},
    {"code": "ko", "country": "KR"},
    {"code": "nl", "country": "NL"},
    {"code": "no", "country": "NO"},
    {"code": "pl", "country": "PL"},
    {"code": "pt", "country": "PT"},
    {"code": "ro", "country": "RO"},
    {"code": "ru", "country": "RU"},
    {"code": "sk", "country": "SK"},
    {"code": "sl", "country": "SI"},
    {"code": "sv", "country": "SE"},
    {"code": "tr", "country": "TR"},
    {"code": "uk", "country": "UA"},
    {"code": "zh", "country": "TW"},
)

_COUNTRY_BY_LANGUAGE = {row["code"]: row["country"] for row in SUPPORTED_RECIPE_LANGUAGES}


def country_for_language(language: str | None, fallback_country: str) -> str:
    code = str(language or "").strip().lower().replace("_", "-").split("-", 1)[0]
    return _COUNTRY_BY_LANGUAGE.get(code, str(fallback_country or "DE").upper())


def language_options() -> list[dict[str, str]]:
    return [dict(row) for row in SUPPORTED_RECIPE_LANGUAGES]
