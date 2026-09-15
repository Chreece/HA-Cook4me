from __future__ import annotations

import unicodedata
from typing import Any

from .catalog_search_index import normalize_search_text

# Script transliteration only. This is deliberately not a culinary synonym table:
# query meaning still comes exclusively from the compiled multilingual catalog.
_GREEK = {
    "α":"a","β":"v","γ":"g","δ":"d","ε":"e","ζ":"z","η":"i","θ":"th",
    "ι":"i","κ":"k","λ":"l","μ":"m","ν":"n","ξ":"x","ο":"o","π":"p",
    "ρ":"r","σ":"s","ς":"s","τ":"t","υ":"y","φ":"f","χ":"ch","ψ":"ps","ω":"o",
}
_CYRILLIC = {
    "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"e","ж":"zh",
    "з":"z","и":"i","й":"i","к":"k","л":"l","м":"m","н":"n","о":"o",
    "п":"p","р":"r","с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"ts",
    "ч":"ch","ш":"sh","щ":"sht","ъ":"a","ы":"y","ь":"","э":"e","ю":"yu","я":"ya",
    "ѝ":"i",
}


def _script_transliteration(token: str) -> str:
    out: list[str] = []
    changed = False
    for char in token:
        if char in _GREEK:
            out.append(_GREEK[char]); changed = True
        elif char in _CYRILLIC:
            out.append(_CYRILLIC[char]); changed = True
        else:
            out.append(char)
    return normalize_search_text("".join(out)) if changed else ""


def _has_rows(prepared: dict[str, Any], token: str) -> bool:
    postings = prepared.get("tokenPostings") or {}
    if token in postings:
        return True
    if len(token) < 3:
        return False
    for candidate in prepared.get("_sortedTokens") or ():
        if candidate.startswith(token):
            return True
        if candidate > token and not candidate.startswith(token):
            break
    return False


def _distance(a: str, b: str, limit: int) -> int:
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        row_min = i
        for j, cb in enumerate(b, 1):
            value = min(
                current[j - 1] + 1,
                previous[j] + 1,
                previous[j - 1] + (ca != cb),
            )
            current.append(value)
            row_min = min(row_min, value)
        if row_min > limit:
            return limit + 1
        previous = current
    return previous[-1]


def _nearest_index_token(prepared: dict[str, Any], token: str) -> str:
    if len(token) < 4:
        return ""
    limit = 2 if len(token) >= 6 else 1
    best: tuple[int, int, str] | None = None
    for candidate in prepared.get("_sortedTokens") or ():
        if not candidate or candidate[0] != token[0]:
            continue
        if abs(len(candidate) - len(token)) > limit:
            continue
        if len(token) >= 5 and len(candidate) >= 2 and candidate[:2] != token[:2]:
            continue
        distance = _distance(token, candidate, limit)
        if distance > limit:
            continue
        rank = (distance, abs(len(candidate) - len(token)), candidate)
        if best is None or rank < best:
            best = rank
    return best[2] if best is not None else ""


def resolve_multilingual_query(prepared: dict[str, Any], query: str) -> tuple[str, bool]:
    """Resolve script variants against index vocabulary without food-specific aliases.

    Exact indexed text always wins. Transliteration/fuzzy recovery is attempted only
    for tokens containing Greek/Cyrillic characters and only against tokens already
    present in the immutable catalog index.
    """
    normalized = normalize_search_text(query)
    if not normalized:
        return "", False
    changed = False
    resolved: list[str] = []
    for token in normalized.split():
        if _has_rows(prepared, token):
            resolved.append(token)
            continue
        transliterated = _script_transliteration(token)
        if not transliterated:
            resolved.append(token)
            continue
        candidate = transliterated if _has_rows(prepared, transliterated) else _nearest_index_token(prepared, transliterated)
        if candidate:
            resolved.append(candidate)
            changed = changed or candidate != token
        else:
            resolved.append(token)
    return " ".join(resolved), changed
