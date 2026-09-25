"""Remove recipe quantities from catalog labels, without changing source data."""
from functools import lru_cache
import re
import unicodedata

_FRACTIONS = "¼½¾⅐⅑⅒⅓⅔⅕⅖⅗⅘⅙⅚⅛⅜⅝⅞"
_NUMBER = rf"(?:\d+\s+\d+\s*/\s*\d+|\d+\s*/\s*\d+|\d+[{_FRACTIONS}]|\d+(?:[.,]\d+)?|[{_FRACTIONS}])"
_AMOUNT = rf"{_NUMBER}(?:\s*(?:[-–—]|to|bis|έως)\s*{_NUMBER})?"
_METRIC = r"(?:kilograms?|kilogramm|kg|grams?|gramm|grammes?|gr|g|mg|millilit(?:er|re)s?|ml|cl|dl|lit(?:er|re)s?|l|κιλά?|κιλό|γραμμάρια|γραμμάριο|γρ\.?|λίτρα|λίτρο)"
_SPOONS = r"(?:tablespoons?|teaspoons?|spoonfuls?|tbsp\.?|tsp\.?|cups?|esslöffel|essloeffel|eßlöffel|teelöffel|teeloeffel|el|tl|tassen?|κ\.\s*σ\.|κ\.\s*γ\.|κουταλιές|κουταλιά|κουταλάκια|κουταλάκι|φλιτζάνια|φλιτζάνι)"
_MEASURE = rf"(?:{_METRIC}|{_SPOONS})"
_EACH = r"(?:each|per (?:piece|portion)|portions?|το καθένα|η καθεμία|το τεμάχιο|ανά τεμάχιο|je (?:stück|portion))"
_QUALIFIER = r"(?:about|approx\.?|approximately|περίπου|των|à|ca\.?)"

_PAREN = re.compile(rf"\s*\(\s*(?:{_AMOUNT}\s*)?{_MEASURE}\s*\)", re.I)
_QUANTITY = re.compile(rf"(?<![\w./:])(?:{_QUALIFIER}\s*)?(?:{_NUMBER}\s*[×x]\s*)?{_AMOUNT}\s*{_MEASURE}(?!\w)(?:\s+{_EACH})?", re.I)
_PREFIX = re.compile(rf"^(?!cups?\s+noodles?\b)(?:(?:{_AMOUNT}|a|an|one)\s*)?{_MEASURE}(?=\s|$)\s*(?:of\s+|de\s+|d['’])?", re.I)
_LEADING_COUNT = re.compile(rf"^{_AMOUNT}\s+(?:of\s+)?", re.I)
# These numbers describe the food itself, rather than a requested amount.
_SPECIFICATION = re.compile(r"^(?:00\s|\d+(?:[.,]\d+)?\s*(?:%|:|/\d+\s*%)|\d+[- ](?:spice|grain|seed)\b)", re.I)
_EMBEDDED_COUNT = re.compile(rf"(?P<before>\b(?:of|από)\s+|(?<!\d)[,;:]\s*|\b(?:and|και)\s+){_AMOUNT}\s+(?!%|spice\b|grain\b|seed\b)", re.I)


@lru_cache(maxsize=32768)
def catalog_name(value: str) -> str:
    """Clean amount annotations; retain percentages, ratios, food forms and types.

    A can/tin/jar, clove, slice or fillet can identify a food form. Standalone
    words of that kind are intentionally not treated as removable units.
    """
    name = " ".join(unicodedata.normalize("NFC", str(value or "")).split())
    original = name
    name = _PAREN.sub("", name)
    without_quantity = _QUANTITY.sub("", name).strip()
    if without_quantity != name:
        without_quantity = re.sub(r"^(?:of\s+|de\s+|d['’])", "", without_quantity, flags=re.I)
    name = without_quantity
    name = _PREFIX.sub("", name)
    if not _SPECIFICATION.match(name):
        name = _LEADING_COUNT.sub("", name)
    name = _EMBEDDED_COUNT.sub(lambda match: match['before'], name)
    name = re.sub(rf"\s+(?:for|für|για)\s+{_AMOUNT}\s+(?:servings?|portions?|portionen|μερίδες)\b", "", name, flags=re.I)
    name = re.sub(r"\s+(?:and a little(?: extra)?|και λίγο επιπλέον)$", "", name, flags=re.I)
    name = re.sub(r"\s+([,;:])", r"\1", name)
    name = " ".join(name.split()).strip(" ,;:–—-")
    return name or original
