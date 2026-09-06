from __future__ import annotations

# Official Cookeo source-language/market pairs live-audited on 2026-09-06
# against the proven BRAND + APPLIANCE_GROUP_15 search contract. Each entry
# returned Cookeo recipes whose hydrated metadata matched the requested
# language and market. Languages whose exact mapping returned zero recipes
# (and no hit in the other known markets) are deliberately not exposed as
# official source catalogs.
#
# Home Assistant's UI/AI translation language is separate from this list.
# For example, Greek can remain the HA UI/translation target even though no
# official Greek Cookeo source catalog was found in the audit.
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
_CODES = frozenset(_COUNTRY_BY_LANGUAGE)


def normalize_language(language: str | None) -> str:
    return str(language or "").strip().lower().replace("_", "-").split("-", 1)[0]


def is_supported_source_language(language: str | None) -> bool:
    return normalize_language(language) in _CODES


def default_source_language(configured_language: str | None) -> str:
    """Return the source catalog selected by the Cook4Me config entry.

    The setup language is authoritative whenever it is one of the audited
    source catalogs. Existing entries whose old configured language has no
    audited Cookeo catalog fall back to German rather than silently following
    the Home Assistant UI language.
    """
    code = normalize_language(configured_language)
    return code if code in _CODES else "de"


def country_for_language(language: str | None, fallback_country: str) -> str:
    code = normalize_language(language)
    return _COUNTRY_BY_LANGUAGE.get(code, str(fallback_country or "DE").upper())


def language_options() -> list[dict[str, str]]:
    return [dict(row) for row in SUPPORTED_RECIPE_LANGUAGES]
