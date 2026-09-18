from __future__ import annotations

from typing import Any

from .catalog_search_index import normalize_search_text, resolved_query_text


def resolve_multilingual_query(
    prepared: dict[str, Any], query: str, language: str = ""
) -> tuple[str, bool]:
    """Describe exact query translations; search keeps original and translated terms.

    Kept for v31 callers. Nearest-word guessing was removed because real catalog
    vocabulary can redirect a Greek dish name to an unrelated foreign word.
    """
    resolved = resolved_query_text(query, language)
    return resolved, resolved != normalize_search_text(query)
