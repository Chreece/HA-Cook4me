"""Offline shopping labels; keep identity and the calculated shortage amount."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata

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


@lru_cache(maxsize=1)
def _unit_presentation():
    path = Path(__file__).with_name("catalog") / "ui_units.v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("labels") or {}, data.get("aliases") or {}


def _fold_unit(value):
    text = unicodedata.normalize("NFKD", str(value or "").strip().casefold())
    text = "".join(char for char in text if not unicodedata.category(char).startswith("M"))
    return re.sub(r"[\\s._-]+", "", text)


def shopping_display_unit(unit, quantity, language):
    """Localize a unit for display without changing its calculation identity."""
    labels, aliases = _unit_presentation()
    raw = str(unit or "").strip()
    if not raw:
        return ""
    code = str(language or "en").strip().lower().replace("_", "-").split("-", 1)[0]
    if code not in {"en", "de", "el"}:
        code = "en"
    folded = _fold_unit(raw)
    kind = aliases.get(folded) or aliases.get(raw.casefold())
    if kind is None and raw in labels:
        kind = raw
    forms = (labels.get(kind) or {}).get(code) if kind else None
    if not forms:
        return raw
    try:
        one = abs(float(quantity) - 1.0) <= 1e-9
    except (TypeError, ValueError):
        one = False
    return str(forms[0 if one else min(1, len(forms) - 1)])


def shopping_rows(
    rows,
    language,
    country,
    sources=(),
    supermarket_language=None,
):
    """Present shopping rows as UI name (market name) (original name).

    The UI language is always primary. A configured/local supermarket language
    is appended only when it produces a different label, followed by one
    original recipe/source label when that also differs. Identity and calculated
    shortage quantities are never changed.
    """
    ui_language = normalize_supermarket_language(language, fallback="en")
    market_language = normalize_supermarket_language(
        supermarket_language,
        country=country,
        fallback=COUNTRY_LANGUAGE.get(str(country or "").upper(), ui_language),
    )

    by_identity = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        identities = {inventory_identity(source)}
        try:
            identities.update(release_catalog.ingredient_stock_identities(source))
        except Exception:
            pass
        for identity in identities:
            if identity:
                by_identity.setdefault(identity, []).append(source)

    result = []
    for raw in rows:
        if not isinstance(raw, dict):
            result.append(raw)  # User-entered text is already intentional.
            continue
        item = deepcopy(raw)
        identity = item.get("identity") or inventory_identity(item)
        if str(identity).startswith("k:") and not (
            item.get("key") or item.get("foodKey")
        ):
            item["key"] = str(identity)[2:]

        original = str(
            item.get("originalName")
            or item.get("name")
            or item.get("foodName")
            or ""
        ).strip()
        display = release_catalog.ingredient_display_name(item, ui_language) or original
        market_name = (
            release_catalog.ingredient_display_name(item, market_language) or original
        )

        # Prefer one original label from the recipe/source rows when available.
        source_original = ""
        source_rows = []
        for candidate_identity in (
            [identity] + list(item.get("identities") or [])
        ):
            source_rows.extend(by_identity.get(candidate_identity, []))
        for source in source_rows:
            candidate = str(
                source.get("originalName")
                or source.get("name")
                or source.get("foodName")
                or ""
            ).strip()
            if candidate:
                source_original = candidate
                break
        original = source_original or original

        alternatives = []
        for candidate in (market_name, original):
            candidate = str(candidate or "").strip()
            if not candidate:
                continue
            if candidate.casefold() == str(display).casefold():
                continue
            if candidate.casefold() in {value.casefold() for value in alternatives}:
                continue
            alternatives.append(candidate)

        item["originalName"] = original
        item["uiLanguage"] = ui_language
        item["supermarketLanguage"] = market_language
        item["uiName"] = str(display)
        item["supermarketName"] = str(market_name)
        item["shoppingDisplayName"] = display + (
            f" ({'; '.join(alternatives)})" if alternatives else ""
        )
        item["displayUnit"] = shopping_display_unit(
            item.get("unit"), item.get("quantity"), ui_language
        )
        item["name"] = item["shoppingDisplayName"]
        if "foodName" in item:
            item["foodName"] = item["name"]

        # Legacy applicationDescription can contain a whole recipe sentence,
        # including the required rather than missing amount. Use structured data.
        item.pop("applicationDescription", None)
        weight = item.get("weight") if isinstance(item.get("weight"), dict) else {}
        if item.get("quantity") in (None, "") and weight.get("quantity") not in (
            None,
            "",
        ):
            item["quantity"] = weight["quantity"]
            item["unit"] = item.get("unit") or weight.get("unit") or ""
        result.append(item)
    return result
