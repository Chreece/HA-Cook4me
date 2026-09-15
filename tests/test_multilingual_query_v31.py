from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

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


class MultilingualQueryV31Tests(unittest.TestCase):
    def setUp(self):
        self.query = _load()

    def test_canonical_translation_wins_over_nearby_foreign_token(self):
        prepared = _prepared("makaronie", "pasta", "rizoto", "risotto")
        self.assertEqual(self.query.resolve_multilingual_query(prepared, "ριζότο"), ("risotto", True))
        self.assertEqual(self.query.resolve_multilingual_query(prepared, "μακαρόνια"), ("pasta", True))

    def test_general_recipe_phrase_composes_dish_modifier_and_ingredient(self):
        prepared = _prepared("creamy", "risotto", "mushroom")
        self.assertEqual(
            self.query.resolve_multilingual_query(prepared, "κρεμώδες ριζότο με μανιτάρια"),
            ("creamy risotto mushroom", True),
        )

    def test_unknown_words_and_negations_are_not_discarded_or_guessed(self):
        prepared = _prepared("risotto", "sopa", "pasta")
        self.assertEqual(self.query.resolve_multilingual_query(prepared, "ριζότα"), ("ριζοτα", False))
        self.assertEqual(self.query.resolve_multilingual_query(prepared, "σούπα χωρίς αλάτι"), ("soup χωρισ αλατι", True))

    def test_multiword_alias_is_resolved_before_function_words(self):
        self.assertEqual(self.query.resolve_multilingual_query({}, "pommes de terre", "fr"), ("potato", True))


if __name__ == "__main__":
    unittest.main()
