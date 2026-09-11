from __future__ import annotations

from collections import defaultdict
import re
import unicodedata
from typing import Any, Iterable

SEARCH_INDEX_SCHEMA_VERSION = 1
_TITLE_TOKEN_WEIGHT = 12
_TITLE_PHRASE_WEIGHT = 36
_INGREDIENT_TOKEN_WEIGHT = 5
_INGREDIENT_PHRASE_WEIGHT = 15
_PREFIX_PENALTY = 2
_MIN_PREFIX = 3
_MAX_PREFIX = 12


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def normalize_search_text(value: Any) -> str:
    """Normalize text for language-agnostic matching without ASCII-only loss."""
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    out: list[str] = []
    pending_space = False
    for char in text:
        if unicodedata.category(char).startswith("M"):
            continue
        if char.isalnum():
            if pending_space and out:
                out.append(" ")
            out.append(char)
            pending_space = False
        else:
            pending_space = True
    return "".join(out).strip()


def _tokens(value: Any) -> tuple[str, ...]:
    normalized = normalize_search_text(value)
    if not normalized:
        return ()
    return tuple(dict.fromkeys(part for part in normalized.split(" ") if part))


def _language(value: Any) -> str:
    return _text(value).lower().replace("_", "-").split("-", 1)[0]


def _strings(value: Any) -> Iterable[str]:
    """Yield human labels from the compact alias/translation shapes we ship."""
    if isinstance(value, str):
        if text := _text(value):
            yield text
        return
    if isinstance(value, dict):
        direct = _text(value.get("value") or value.get("name") or value.get("label"))
        if direct:
            yield direct
        for key, nested in value.items():
            if key in {"value", "name", "label"}:
                continue
            yield from _strings(nested)
        return
    if isinstance(value, (list, tuple, set)):
        for nested in value:
            yield from _strings(nested)


def _row_aliases(row: dict[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for field in (
        "canonicalName",
        "canonicalEnglish",
        "name",
        "foodName",
        "originalName",
        "title",
        "originalTitle",
    ):
        if text := _text(row.get(field)):
            values.append(text)
    for field in ("translations", "aliases", "searchAliases"):
        values.extend(_strings(row.get(field)))
    return tuple(dict.fromkeys(value for value in values if value))


def _ingredient_lookup(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in payload.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        for value in (
            row.get("id"),
            row.get("ingredientId"),
            row.get("conceptId"),
            row.get("key"),
            row.get("foodKey"),
        ):
            ident = _text(value)
            if ident:
                out.setdefault(ident, row)
    return out


def _ingredient_aliases(
    raw: Any, ingredient_by_id: dict[str, dict[str, Any]]
) -> tuple[str, ...]:
    if not isinstance(raw, dict):
        return (_text(raw),) if _text(raw) else ()

    values = list(_row_aliases(raw))
    source: dict[str, Any] | None = None
    for value in (
        raw.get("ingredientId"),
        raw.get("id"),
        raw.get("conceptId"),
        raw.get("key"),
        raw.get("foodKey"),
    ):
        ident = _text(value)
        if ident and isinstance(ingredient_by_id.get(ident), dict):
            source = ingredient_by_id[ident]
            break
    if source is not None:
        values.extend(_row_aliases(source))
    return tuple(dict.fromkeys(value for value in values if value))


def _recipe_title_aliases(recipe: dict[str, Any]) -> tuple[str, ...]:
    values = list(_row_aliases(recipe))
    for variant in recipe.get("variants") or []:
        if isinstance(variant, dict):
            values.extend(_row_aliases(variant))
    return tuple(dict.fromkeys(value for value in values if value))


def _recipe_ingredient_aliases(
    recipe: dict[str, Any], ingredient_by_id: dict[str, dict[str, Any]]
) -> tuple[str, ...]:
    values: list[str] = []
    for raw in recipe.get("ingredients") or []:
        values.extend(_ingredient_aliases(raw, ingredient_by_id))
    for variant in recipe.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        for raw in variant.get("ingredients") or []:
            values.extend(_ingredient_aliases(raw, ingredient_by_id))
    return tuple(dict.fromkeys(value for value in values if value))


def _recipe_languages(recipe: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    if language := _language(recipe.get("language")):
        out.add(language)
    for variant in recipe.get("variants") or []:
        if not isinstance(variant, dict):
            continue
        if language := _language(
            variant.get("language") or variant.get("originalLanguage")
        ):
            out.add(language)
    return out


def _add_alias(
    token_postings: dict[str, dict[int, int]],
    phrase_postings: dict[str, dict[int, int]],
    prefix_postings: dict[str, dict[int, int]],
    *,
    recipe_index: int,
    alias: str,
    token_weight: int,
    phrase_weight: int,
) -> None:
    normalized = normalize_search_text(alias)
    if not normalized:
        return
    phrase_scores = phrase_postings[normalized]
    phrase_scores[recipe_index] = max(
        phrase_scores.get(recipe_index, 0), phrase_weight
    )
    for token in _tokens(normalized):
        token_scores = token_postings[token]
        token_scores[recipe_index] = max(
            token_scores.get(recipe_index, 0), token_weight
        )
        if len(token) < _MIN_PREFIX:
            continue
        prefix_weight = max(1, token_weight - _PREFIX_PENALTY)
        for length in range(_MIN_PREFIX, min(len(token), _MAX_PREFIX) + 1):
            prefix = token[:length]
            prefix_scores = prefix_postings[prefix]
            prefix_scores[recipe_index] = max(
                prefix_scores.get(recipe_index, 0), prefix_weight
            )


def _serialize_postings(
    values: dict[str, dict[int, int]]
) -> dict[str, list[list[int]]]:
    return {
        key: [[index, scores[index]] for index in sorted(scores)]
        for key, scores in sorted(values.items())
        if scores
    }


def compile_search_index(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile a JSON-serializable all-language recipe search index.

    This is maintenance/build work. Runtime search consumes the resulting
    postings directly and never rebuilds recipe search strings per query.
    """
    token_postings: dict[str, dict[int, int]] = defaultdict(dict)
    phrase_postings: dict[str, dict[int, int]] = defaultdict(dict)
    prefix_postings: dict[str, dict[int, int]] = defaultdict(dict)
    recipe_languages: dict[str, set[int]] = defaultdict(set)
    ingredient_by_id = _ingredient_lookup(payload)

    recipes = payload.get("recipes") or []
    for recipe_index, recipe in enumerate(recipes):
        if not isinstance(recipe, dict):
            continue
        for language in _recipe_languages(recipe):
            recipe_languages[language].add(recipe_index)

        for alias in _recipe_title_aliases(recipe):
            _add_alias(
                token_postings,
                phrase_postings,
                prefix_postings,
                recipe_index=recipe_index,
                alias=alias,
                token_weight=_TITLE_TOKEN_WEIGHT,
                phrase_weight=_TITLE_PHRASE_WEIGHT,
            )
        for alias in _recipe_ingredient_aliases(recipe, ingredient_by_id):
            _add_alias(
                token_postings,
                phrase_postings,
                prefix_postings,
                recipe_index=recipe_index,
                alias=alias,
                token_weight=_INGREDIENT_TOKEN_WEIGHT,
                phrase_weight=_INGREDIENT_PHRASE_WEIGHT,
            )

    return {
        "schemaVersion": SEARCH_INDEX_SCHEMA_VERSION,
        "kind": "cook4me-multilingual-recipe-search-index",
        "recipeCount": len(recipes),
        "tokenPostings": _serialize_postings(token_postings),
        "phrasePostings": _serialize_postings(phrase_postings),
        "prefixPostings": _serialize_postings(prefix_postings),
        "recipeLanguages": {
            language: sorted(indices)
            for language, indices in sorted(recipe_languages.items())
        },
        "stats": {
            "tokens": len(token_postings),
            "phrases": len(phrase_postings),
            "prefixes": len(prefix_postings),
            "languages": len(recipe_languages),
        },
    }


def prepare_search_index(compiled: Any) -> dict[str, Any]:
    """Validate/prepare a compiled index for cheap repeated runtime queries."""
    if (
        not isinstance(compiled, dict)
        or int(compiled.get("schemaVersion") or 0) != SEARCH_INDEX_SCHEMA_VERSION
        or compiled.get("kind") != "cook4me-multilingual-recipe-search-index"
    ):
        return {
            "schemaVersion": SEARCH_INDEX_SCHEMA_VERSION,
            "kind": "cook4me-multilingual-recipe-search-index",
            "recipeCount": 0,
            "tokenPostings": {},
            "phrasePostings": {},
            "prefixPostings": {},
            "recipeLanguages": {},
            "_prepared": True,
        }

    def postings(name: str) -> dict[str, tuple[tuple[int, int], ...]]:
        out: dict[str, tuple[tuple[int, int], ...]] = {}
        source = compiled.get(name)
        if not isinstance(source, dict):
            return out
        for key, rows in source.items():
            normalized = normalize_search_text(key)
            if not normalized or not isinstance(rows, list):
                continue
            cleaned: list[tuple[int, int]] = []
            for row in rows:
                if (
                    isinstance(row, (list, tuple))
                    and len(row) == 2
                    and isinstance(row[0], int)
                    and isinstance(row[1], int)
                    and row[0] >= 0
                    and row[1] > 0
                ):
                    cleaned.append((row[0], row[1]))
            if cleaned:
                out[normalized] = tuple(cleaned)
        return out

    languages: dict[str, frozenset[int]] = {}
    raw_languages = compiled.get("recipeLanguages")
    if isinstance(raw_languages, dict):
        for language, indices in raw_languages.items():
            if isinstance(indices, list):
                languages[_language(language)] = frozenset(
                    index
                    for index in indices
                    if isinstance(index, int) and index >= 0
                )

    return {
        "schemaVersion": SEARCH_INDEX_SCHEMA_VERSION,
        "kind": "cook4me-multilingual-recipe-search-index",
        "recipeCount": max(0, int(compiled.get("recipeCount") or 0)),
        "tokenPostings": postings("tokenPostings"),
        "phrasePostings": postings("phrasePostings"),
        "prefixPostings": postings("prefixPostings"),
        "recipeLanguages": languages,
        "stats": dict(compiled.get("stats") or {}),
        "_prepared": True,
    }


def _posting_map(rows: Iterable[tuple[int, int]]) -> dict[int, int]:
    return {index: score for index, score in rows}


def search_index(
    prepared: dict[str, Any],
    query: str,
    *,
    language: str = "",
    strict_language: bool = False,
    page: int = 0,
    size: int = 20,
) -> dict[str, Any]:
    """Search only compiled postings; no recipe/catalog scan occurs here."""
    if not prepared.get("_prepared"):
        prepared = prepare_search_index(prepared)

    page = max(0, int(page))
    size = max(1, int(size))
    recipe_count = max(0, int(prepared.get("recipeCount") or 0))
    language_key = _language(language)
    allowed: frozenset[int] | None = None
    if strict_language:
        allowed = (prepared.get("recipeLanguages") or {}).get(
            language_key, frozenset()
        )

    normalized = normalize_search_text(query)
    query_tokens = _tokens(normalized)
    token_postings = prepared.get("tokenPostings") or {}
    prefix_postings = prepared.get("prefixPostings") or {}
    phrase_postings = prepared.get("phrasePostings") or {}

    if not normalized:
        indices = (
            sorted(allowed)
            if allowed is not None
            else list(range(recipe_count))
        )
        total = len(indices)
        start = page * size
        return {
            "indices": indices[start : start + size],
            "scores": {},
            "total": total,
            "page": page,
            "size": size,
        }

    per_term: list[dict[int, int]] = []
    for token in query_tokens:
        rows = token_postings.get(token)
        if not rows and len(token) >= _MIN_PREFIX:
            rows = prefix_postings.get(token)
        if not rows:
            return {
                "indices": [],
                "scores": {},
                "total": 0,
                "page": page,
                "size": size,
            }
        current = _posting_map(rows)
        if allowed is not None:
            current = {
                index: score
                for index, score in current.items()
                if index in allowed
            }
        if not current:
            return {
                "indices": [],
                "scores": {},
                "total": 0,
                "page": page,
                "size": size,
            }
        per_term.append(current)

    candidates = set(per_term[0])
    for current in per_term[1:]:
        candidates.intersection_update(current)
        if not candidates:
            break

    scores: dict[int, int] = {
        index: sum(current.get(index, 0) for current in per_term)
        for index in candidates
    }
    for index, phrase_score in phrase_postings.get(normalized, ()):
        if index in scores:
            scores[index] += phrase_score

    ranked = sorted(scores, key=lambda index: (-scores[index], index))
    total = len(ranked)
    start = page * size
    selected = ranked[start : start + size]
    return {
        "indices": selected,
        "scores": {index: scores[index] for index in selected},
        "total": total,
        "page": page,
        "size": size,
    }
