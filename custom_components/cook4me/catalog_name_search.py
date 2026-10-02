"""Food-name search, separate from immutable recipe/source alias evidence.

Clauses after comma/semicolon/colon are recipe annotations, not independent
names of this ingredient. Preserve digits in amounts/specifications, word
prefixes, multilingual names, and actual compound food names. Do not use this
projection to merge identities, assign stock, or infer dietary compatibility.
The browser mirror is checked against every shipped alias by the audit suite.
"""
from __future__ import annotations

from functools import lru_cache
import re
import unicodedata

NAME_SEARCH_VERSION = 270
_CLAUSE = re.compile(r"[,;；，]|:(?!\d)")
# Only explicit preparation/use instructions; never remove food-form adjectives
# such as dried, frozen, canned, ground, smoked, wholemeal or lactose-free.
_TAIL = re.compile(
    r"\s+(?:cut into|cut in|cut to|chopped into|sliced into|diced into|"
    r"mixed with|combined with|seasoned with|season with|rubbed with|"
    r"served with|to taste|as needed|as required|for serving|for garnish|"
    r"for decoration|for finishing|for greasing|zum servieren|zum wurzen|"
    r"nach geschmack|in wurfel geschnitten|in scheiben geschnitten|"
    r"pour servir|pour decorer|pour garnir|au gout|selon le gout|"
    r"para servir|para decorar|al gusto|a gusto|a gosto|per servire|"
    r"per guarnire|a piacere|για σερβιρισμα|για γαρνιρισμα|"
    r"για διακοσμηση|κατα προτιμηση)(?:\s|$).*"
)
_PAREN = re.compile(r"\(([^()]*)\)")
_NOTE = re.compile(
    r"^(?:cut |chopped|sliced|diced|peeled|washed|rinsed|drained|"
    r"for |to taste|as needed|quantity |or |optional|zum |nach geschmack|"
    r"pour |para |per servire|για |προαιρετικ)"
)


def normalize_name_search(value: object) -> str:
    folded = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join("".join(
        char if char.isalnum() else " "
        for char in folded if not unicodedata.category(char).startswith("M")
    ).split())


@lru_cache(maxsize=65536)
def _food_name_alias(text: str) -> str:
    text = _PAREN.sub(lambda m: "" if _NOTE.match(normalize_name_search(m[1])) else m[0], text)
    # Do not mistake decimal commas for a clause delimiter.
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    head = _CLAUSE.split(text, maxsplit=1)[0]
    return _TAIL.sub("", normalize_name_search(head)).strip()


def food_name_alias(value: object) -> str:
    return _food_name_alias(str(value or "").strip())


def food_name_aliases(aliases, *, names=()) -> list[str]:
    return sorted({alias for value in aliases if (alias := food_name_alias(value))}
                  | {normalize_name_search(value) for value in names if value})


# German storage/form/origin qualifiers are commonly joined to the food name. Keep
# both the compound and its food stem (Tiefkühlspargel -> Spargel; Meersalz -> Salz). This is not
# arbitrary infix matching: e.g. apple must not match pineapple.
_FORM_COMPOUND = re.compile(r"^(?:tiefkuhl|tk|konserven|dosen|trocken|vollkorn|meer|stein|tafel|jod|gewurz|krauter)([a-z]{3,})$")


@lru_cache(maxsize=65536)
def name_search_tokens(alias: str) -> tuple[str, ...]:
    tokens = alias.split()
    return tuple(tokens + [match[1] for token in tokens if (match := _FORM_COMPOUND.match(token))])
