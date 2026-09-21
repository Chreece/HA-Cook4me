"""Offline shopping labels; keep identity and the calculated shortage amount."""
from copy import deepcopy

from . import release_catalog
from .recipe_languages import language_options
from .inventory import inventory_identity

COUNTRY_LANGUAGE = dict(DE="de", AT="de", CH="de", GR="el", CY="el", GB="en",
    US="en", AU="en", IE="en", CA="en", FR="fr", BE="fr", ES="es", IT="it",
    PT="pt", BR="pt", PL="pl", CZ="cs", SK="sk", HU="hu", RO="ro", BG="bg",
    HR="hr", SI="sl", UA="uk", RU="ru", TR="tr", JP="ja", KR="ko", CN="zh",
    TW="zh", AE="ar", SA="ar", NL="nl", DK="da", NO="nb", SE="sv", FI="fi")


SUPPORTED_SUPERMARKET_LANGUAGES = frozenset(
    {row["code"] for row in language_options()} | {"el"}
)


def normalize_supermarket_language(value, country="", fallback="en"):
    code = str(value or "").strip().lower().replace("_", "-").split("-", 1)[0]
    if code in SUPPORTED_SUPERMARKET_LANGUAGES:
        return code
    market = COUNTRY_LANGUAGE.get(str(country or "").upper(), "")
    if market in SUPPORTED_SUPERMARKET_LANGUAGES:
        return market
    fallback_code = str(fallback or "en").strip().lower().replace("_", "-").split("-", 1)[0]
    return fallback_code if fallback_code in SUPPORTED_SUPERMARKET_LANGUAGES else "en"


def supermarket_language_options():
    return sorted(SUPPORTED_SUPERMARKET_LANGUAGES)


def shopping_rows(rows, language, country, sources=()):
    language = str(language or "en").lower().replace("_", "-").split("-")[0]
    country_language = COUNTRY_LANGUAGE.get(str(country or "").upper(), language)
    by_identity = {}
    for source in sources:
        if isinstance(source, dict):
            by_identity.setdefault(inventory_identity(source), []).append(source)
    result = []
    for raw in rows:
        if not isinstance(raw, dict):
            result.append(raw)  # User-entered text is already intentional.
            continue
        item = deepcopy(raw)
        identity = item.get("identity") or inventory_identity(item)
        originals = by_identity.get(identity, [])
        if str(identity).startswith("k:") and not (item.get("key") or item.get("foodKey")):
            item["key"] = identity[2:]
        original = item.get("originalName") or item.get("name") or item.get("foodName") or ""
        display = release_catalog.ingredient_display_name(item, language) or original
        country_name = release_catalog.ingredient_display_name(item, country_language) or original
        alternatives = []
        names = [country_name, original, *(source.get("originalName") or source.get("name") or "" for source in originals)]
        for name in names:
            name = str(name).strip()
            if name and name.casefold() != display.casefold() and name.casefold() not in {value.casefold() for value in alternatives}:
                alternatives.append(name)
        item["originalName"] = original
        item["name"] = display + (f" ({'; '.join(alternatives)})" if alternatives else "")
        if "foodName" in item:
            item["foodName"] = item["name"]  # Legacy shopping formatter prefers it.
        # Legacy applicationDescription can contain a whole recipe sentence,
        # including the required rather than missing amount. Use structured data.
        item.pop("applicationDescription", None)
        weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
        if item.get("quantity") in (None, "") and weight.get("quantity") not in (None, ""):
            item["quantity"] = weight["quantity"]
            item["unit"] = item.get("unit") or weight.get("unit") or ""
        result.append(item)
    return result
