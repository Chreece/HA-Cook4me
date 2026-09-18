from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from functools import lru_cache
import json
from pathlib import Path
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


@lru_cache(maxsize=1)
def _query_vocabulary() -> tuple[dict, dict]:
    """Load small query translations separately from immutable provider data."""
    payload = json.loads(Path(__file__).with_name("query_vocabulary.json").read_text(encoding="utf-8"))
    aliases: dict[str, dict[str, tuple[str, ...]]] = defaultdict(dict)
    for row in payload["terms"]:
        canonical = tuple(dict.fromkeys(normalize_search_text(v) for v in row["en"]))
        for language, values in row.items():
            for value in values:
                alias = normalize_search_text(value)
                previous = aliases[language].get(alias, ())
                aliases[language][alias] = tuple(dict.fromkeys((*previous, *canonical)))
    stops = {
        language: frozenset(normalize_search_text(value) for value in values)
        for language, values in payload["stopwords"].items()
    }
    return dict(aliases), stops


def _query_language(query: str, language: str) -> str:
    # Script is evidence about the typed query, not about source catalog filters.
    if any("GREEK" in unicodedata.name(char, "") for char in query):
        return "el"
    return _language(language)


def prepare_catalog_query_aliases(payload, localized_labels):
    """Index the complete reviewed bilingual catalog, not a dish whitelist.

    These are query alternatives only. They cannot merge ingredient identity,
    transfer nutrients, change dietary evidence or assign provider recipe IDs.
    """
    base, stops = _query_vocabulary()
    aliases = {language: {key: list(values) for key, values in rows.items()} for language, rows in base.items()}
    def add(language, label, canonical):
        language = _language(language)
        label, canonical = normalize_search_text(label), normalize_search_text(canonical)
        if not label or not canonical or not language:
            return
        values = aliases.setdefault(language, {}).setdefault(label, [])
        if canonical not in values:
            values.append(canonical)
    for language, labels in localized_labels.items():
        for canonical, label in labels.items():
            add(language, label, canonical)
    for ingredient in payload.get("ingredients", []):
        canonical = ingredient.get("canonicalName")
        if not canonical or ingredient.get("classification") in {"equipment", "other", "ambiguous"}:
            continue
        for field in ("translations", "aliases"):
            for language, values in (ingredient.get(field) or {}).items():
                for label in _strings(values):
                    add(language, label, canonical)
        add(ingredient.get("originalLanguage") or ingredient.get("language"), ingredient.get("originalName"), canonical)
    for recipe in payload.get("recipes", []):
        canonical = recipe.get("canonicalName")
        if not canonical:
            continue
        for variant in recipe.get("variants", []):
            add(variant.get("originalLanguage") or variant.get("language"), variant.get("originalTitle") or variant.get("title"), canonical)

    # Recover independently identifiable words from existing bilingual labels.
    # E.g. removing a known translation of "noodles" from a food label leaves
    # its dish qualifier. Ambiguous residual phrases are never guessed.
    english = {word: values[0] for word, values in base.get("en", {}).items()
        if " " not in word and values and " " not in values[0]}
    english_stops = set(stops.get("en", ())) | {"of"}
    def words(value):
        return {english.get(word, word) for word in value.split() if word not in english_stops}
    for language, labels in aliases.items():
        if language == "en":
            continue
        source_stops = stops.get(language, ())
        pairs = [(set(label.split())-set(source_stops), set().union(*(words(value) for value in values))) for label, values in labels.items()]
        for _ in range(4):
            known = {label: set().union(*(words(value) for value in values)) for label, values in labels.items() if " " not in label}
            contexts = defaultdict(list)
            for source, target in pairs:
                for word in source:
                    if word in known or len(word) < 2:
                        continue
                    other = source - {word}
                    residual = target - set().union(*(known.get(part, set()) for part in other))
                    if residual:
                        contexts[word].append((residual, all(part in known for part in other)))
            learned = {}
            for word, evidence in contexts.items():
                common = set.intersection(*(values for values, _ in evidence))
                if len(common) == 1 and (len(evidence) > 1 or evidence[0][1]):
                    learned[word] = sorted(common)
                elif all(len(values) == 1 and complete for values, complete in evidence):
                    learned[word] = sorted(set.union(*(values for values, _ in evidence)))
            if not learned:
                break
            labels.update(learned)
    universal = {}
    for labels in aliases.values():
        for label, values in labels.items():
            target = universal.setdefault(label, [])
            target.extend(value for value in values if value not in target)
    aliases["*"] = universal
    return {language: {key: tuple(values) for key, values in labels.items()} for language, labels in aliases.items()}


def query_terms(query: str, language: str = "", catalog_aliases=None) -> tuple[tuple[str, ...], ...]:
    """AND query terms, OR their exact translations; retain the original wording.

    Longest known phrases are consumed together (e.g. pommes de terre). Unknown
    words are retained, including negations: never silently broaden a request by
    dropping content words or choosing a nearby, unrelated catalog token.
    """
    normalized = normalize_search_text(query)
    words = normalized.split()
    aliases, stopwords = _query_vocabulary()
    language = _query_language(normalized, language)
    mapping = dict((catalog_aliases or {}).get("*", {}))
    mapping.update(aliases.get("en", {}))
    mapping.update((catalog_aliases or {}).get(language, {}))
    mapping.update(aliases.get(language, {}))
    stops = stopwords.get(language, frozenset())
    result: list[tuple[str, ...]] = []
    position = 0
    while position < len(words):
        selected = None
        for length in range(len(words) - position, 0, -1):
            phrase = " ".join(words[position:position + length])
            if phrase in mapping:
                selected = (phrase, length, mapping[phrase])
                break
        if selected is not None:
            phrase, length, equivalents = selected
            result.append(tuple(dict.fromkeys((phrase, *equivalents))))
            position += length
            continue
        word = words[position]
        if word not in stops:
            result.append((word,))
        position += 1
    return tuple(result)


def resolved_query_text(query: str, language: str = "", catalog_aliases=None) -> str:
    terms = query_terms(query, language, catalog_aliases)
    english = _query_vocabulary()[0].get("en", {})
    return " ".join(
        english[term[0]][0] if term[0] in english
        else term[1] if len(term) > 1 else term[0]
        for term in terms
    )


def _query_phrase_variants(normalized: str, language: str, catalog_aliases=None) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in (
        normalize_search_text(normalized), resolved_query_text(normalized, language, catalog_aliases)
    ) if value))


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


def _serialize_postings(
    values: dict[str, dict[int, int]]
) -> dict[str, list[list[int]]]:
    return {
        key: [[index, scores[index]] for index in sorted(scores)]
        for key, scores in sorted(values.items())
        if scores
    }


def _prefix_count(tokens: Iterable[str]) -> int:
    prefixes: set[str] = set()
    for token in tokens:
        if len(token) < _MIN_PREFIX:
            continue
        for length in range(_MIN_PREFIX, min(len(token), _MAX_PREFIX) + 1):
            prefixes.add(token[:length])
    return len(prefixes)


def compile_search_index(payload: dict[str, Any]) -> dict[str, Any]:
    """Compile a compact JSON-serializable all-language recipe search index.

    Exact token and phrase postings are persisted. Prefix postings are deliberately
    not duplicated in the release file; runtime derives prefix matches from the
    sorted exact-token table with the same score penalty. This preserves typeahead
    semantics while removing the largest redundant part of the catalog artifact.
    """
    token_postings: dict[str, dict[int, int]] = defaultdict(dict)
    phrase_postings: dict[str, dict[int, int]] = defaultdict(dict)
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
                recipe_index=recipe_index,
                alias=alias,
                token_weight=_TITLE_TOKEN_WEIGHT,
                phrase_weight=_TITLE_PHRASE_WEIGHT,
            )
        for alias in _recipe_ingredient_aliases(recipe, ingredient_by_id):
            _add_alias(
                token_postings,
                phrase_postings,
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
        # Retain the field as an explicit empty compatibility marker. Older v60
        # indexes with materialized prefix postings remain readable by prepare().
        "prefixPostings": {},
        "recipeLanguages": {
            language: sorted(indices)
            for language, indices in sorted(recipe_languages.items())
        },
        "stats": {
            "tokens": len(token_postings),
            "phrases": len(phrase_postings),
            "prefixes": _prefix_count(token_postings),
            "prefixPostingsPersisted": False,
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
            "_sortedTokens": (),
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

    _query_vocabulary()  # Warm the query lexicon alongside the release indexes.
    token_postings = postings("tokenPostings")
    return {
        "schemaVersion": SEARCH_INDEX_SCHEMA_VERSION,
        "kind": "cook4me-multilingual-recipe-search-index",
        "recipeCount": max(0, int(compiled.get("recipeCount") or 0)),
        "tokenPostings": token_postings,
        "phrasePostings": postings("phrasePostings"),
        "prefixPostings": postings("prefixPostings"),
        "recipeLanguages": languages,
        "stats": dict(compiled.get("stats") or {}),
        "_sortedTokens": tuple(sorted(token_postings)),
        "_prepared": True,
    }


def _posting_map(rows: Iterable[tuple[int, int]]) -> dict[int, int]:
    return {index: score for index, score in rows}


def _prefix_rows(
    prepared: dict[str, Any], prefix: str
) -> tuple[tuple[int, int], ...]:
    """Resolve one prefix from legacy postings or the sorted exact-token table."""
    if len(prefix) < _MIN_PREFIX or len(prefix) > _MAX_PREFIX:
        return ()
    legacy = prepared.get("prefixPostings") or {}
    rows = legacy.get(prefix)
    if rows:
        return tuple(rows)

    tokens = prepared.get("_sortedTokens") or ()
    token_postings = prepared.get("tokenPostings") or {}
    if not tokens:
        return ()
    start = bisect_left(tokens, prefix)
    merged: dict[int, int] = {}
    for position in range(start, len(tokens)):
        token = tokens[position]
        if not token.startswith(prefix):
            break
        for index, score in token_postings.get(token, ()):
            value = max(1, int(score) - _PREFIX_PENALTY)
            merged[index] = max(merged.get(index, 0), value)
    return tuple((index, merged[index]) for index in sorted(merged))


def search_index(
    prepared: dict[str, Any],
    query: str,
    *,
    language: str = "",
    strict_language: bool = False,
    allowed_indices: Iterable[int] | None = None,
    page: int = 0,
    size: int = 20,
) -> dict[str, Any]:
    """Search compiled postings and apply precomputed filters before pagination."""
    if not prepared.get("_prepared"):
        prepared = prepare_search_index(prepared)

    page = max(0, int(page))
    size = max(1, int(size))
    recipe_count = max(0, int(prepared.get("recipeCount") or 0))
    language_key = _language(language)
    allowed: frozenset[int] | None = None
    if allowed_indices is not None:
        allowed = frozenset(
            index
            for index in allowed_indices
            if isinstance(index, int) and 0 <= index < recipe_count
        )
    if strict_language:
        language_allowed = (prepared.get("recipeLanguages") or {}).get(
            language_key, frozenset()
        )
        allowed = (
            language_allowed
            if allowed is None
            else frozenset(allowed & language_allowed)
        )

    normalized = normalize_search_text(query)
    catalog_aliases = prepared.get("catalogQueryAliases")
    terms = query_terms(normalized, language_key, catalog_aliases)
    token_postings = prepared.get("tokenPostings") or {}
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

    if not terms:
        return {"indices": [], "scores": {}, "total": 0, "page": page, "size": size}

    per_term: list[dict[int, int]] = []
    for alternatives in terms:
        current: dict[int, int] = {}
        for alternative in alternatives:
            # One translated term can contain several words (e.g. olive oil).
            parts: list[dict[int, int]] = []
            for word in _tokens(alternative):
                rows = token_postings.get(word) or _prefix_rows(prepared, word)
                parts.append(_posting_map(rows or ()))
            matching = set(parts[0]) if parts else set()
            for part in parts[1:]:
                matching.intersection_update(part)
            for index in matching:
                score = sum(part[index] for part in parts)
                current[index] = max(current.get(index, 0), score)
        if not current:
            return {
                "indices": [],
                "scores": {},
                "total": 0,
                "page": page,
                "size": size,
            }
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
    for phrase in _query_phrase_variants(normalized, language_key, catalog_aliases):
        for index, phrase_score in phrase_postings.get(phrase, ()):
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
