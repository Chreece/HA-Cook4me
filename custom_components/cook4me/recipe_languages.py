from __future__ import annotations

# Official Cookeo source catalogs proven by the 2026-09-06 standalone v2 audit.
# UI/AI translation targets are intentionally separate: Home Assistant may use
# languages such as Greek even when SEB exposes no official Cookeo source catalog
# for that language.
SUPPORTED_RECIPE_LANGUAGES: tuple[dict[str, str], ...] = (
    {"code": "ar", "country": "AE"},
    {"code": "bg", "country": "BG"},
    {"code": "cs", "country": "CZ"},
    {"code": "de", "country": "DE"},
    {"code": "en", "country": "GB"},
    {"code": "es", "country": "ES"},
    {"code": "fr", "country": "FR"},
    {"code": "hr", "country": "HR"},
    {"code": "hu", "country": "HU"},
    {"code": "it", "country": "IT"},
    {"code": "ja", "country": "JP"},
    {"code": "ko", "country": "KR"},
    {"code": "pl", "country": "PL"},
    {"code": "pt", "country": "PT"},
    {"code": "ro", "country": "RO"},
    {"code": "ru", "country": "RU"},
    {"code": "sk", "country": "SK"},
    {"code": "sl", "country": "SI"},
    {"code": "tr", "country": "TR"},
    {"code": "uk", "country": "UA"},
    {"code": "zh", "country": "TW"},
)

_COUNTRY_BY_LANGUAGE = {row["code"]: row["country"] for row in SUPPORTED_RECIPE_LANGUAGES}
_SUPPORTED_CODES = frozenset(_COUNTRY_BY_LANGUAGE)


def normalize_catalog_language(language: str | None, fallback: str = "de") -> str:
    code = str(language or "").strip().lower().replace("_", "-").split("-", 1)[0]
    fallback_code = str(fallback or "de").strip().lower().replace("_", "-").split("-", 1)[0]
    if code in _SUPPORTED_CODES:
        return code
    if fallback_code in _SUPPORTED_CODES:
        return fallback_code
    return "de"


def country_for_language(language: str | None, fallback_country: str) -> str:
    code = str(language or "").strip().lower().replace("_", "-").split("-", 1)[0]
    return _COUNTRY_BY_LANGUAGE.get(code, str(fallback_country or "DE").upper())


def is_official_catalog_language(language: str | None) -> bool:
    code = str(language or "").strip().lower().replace("_", "-").split("-", 1)[0]
    return code in _SUPPORTED_CODES


def language_options() -> list[dict[str, str]]:
    return [dict(row) for row in SUPPORTED_RECIPE_LANGUAGES]
