from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"


def _load():
    package = types.ModuleType("cook4me_query_test")
    package.__path__ = [str(COMPONENT)]
    sys.modules["cook4me_query_test"] = package
    search_spec = importlib.util.spec_from_file_location(
        "cook4me_query_test.catalog_search_index", COMPONENT / "catalog_search_index.py"
    )
    search = importlib.util.module_from_spec(search_spec)
    sys.modules[search_spec.name] = search
    search_spec.loader.exec_module(search)
    query_spec = importlib.util.spec_from_file_location(
        "cook4me_query_test.multilingual_query", COMPONENT / "multilingual_query.py"
    )
    query = importlib.util.module_from_spec(query_spec)
    sys.modules[query_spec.name] = query
    query_spec.loader.exec_module(query)
    return query


def _prepared(*tokens):
    return {
        "tokenPostings": {token: ((0, 12),) for token in tokens},
        "_sortedTokens": tuple(sorted(tokens)),
    }


def test_script_recovery_is_generic_not_food_alias_table():
    query = _load()
    prepared = _prepared("paprika", "risotto", "pasta")
    assert query.resolve_multilingual_query(prepared, "πάπρικα") == ("paprika", True)
    assert query.resolve_multilingual_query(prepared, "ριζότο") == ("risotto", True)
    assert query.resolve_multilingual_query(prepared, "ризото") == ("risotto", True)
    assert query.resolve_multilingual_query(prepared, "паста") == ("pasta", True)


def test_exact_catalog_script_token_wins_before_transliteration():
    query = _load()
    prepared = _prepared("ριζοτο", "risotto")
    assert query.resolve_multilingual_query(prepared, "ριζότο") == ("ριζοτο", False)
