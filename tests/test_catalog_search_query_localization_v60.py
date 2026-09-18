from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components/cook4me/catalog_search_index.py"
spec = importlib.util.spec_from_file_location(
    "cook4me_catalog_search_query_localization_test",
    MODULE,
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class CatalogSearchQueryLocalizationV60Tests(unittest.TestCase):
    def _payload_without_greek_risotto_aliases(self):
        return {
            "ingredients": [
                {
                    "id": "concept:food:tomato",
                    "canonicalName": "Tomato",
                    "aliases": {
                        "en": ["Tomato"],
                        "el": ["Ντομάτα"],
                    },
                },
                {
                    "id": "concept:food:mushroom",
                    "canonicalName": "Mushroom",
                    "aliases": {
                        "en": ["Mushroom"],
                        "el": ["Μανιτάρι"],
                    },
                },
            ],
            "recipes": [
                {
                    "groupingFunctionalId": "GROUP_TOMATO_RISOTTO",
                    "canonicalName": "Tomato risotto",
                    "variants": [
                        {
                            "variantId": "PL_RISOTTO",
                            "language": "pl",
                            "title": "Risotto pomidorowe",
                            "ingredients": [
                                {"ingredientId": "concept:food:tomato"},
                            ],
                        }
                    ],
                },
                {
                    "groupingFunctionalId": "GROUP_MUSHROOM_RISOTTO",
                    "canonicalName": "Mushroom risotto",
                    "variants": [
                        {
                            "variantId": "IT_RISOTTO",
                            "language": "it",
                            "title": "Risotto ai funghi",
                            "ingredients": [
                                {"ingredientId": "concept:food:mushroom"},
                            ],
                        }
                    ],
                },
                {
                    "groupingFunctionalId": "GROUP_TOMATO_SOUP",
                    "canonicalName": "Tomato soup",
                    "variants": [
                        {
                            "variantId": "FR_SOUP",
                            "language": "fr",
                            "title": "Soupe de tomates",
                            "ingredients": [
                                {"ingredientId": "concept:food:tomato"},
                            ],
                        }
                    ],
                },
            ],
        }

    def setUp(self):
        payload = self._payload_without_greek_risotto_aliases()
        self.index = mod.prepare_search_index(mod.compile_search_index(payload))

    def test_exact_greek_loanword_finds_foreign_risotto_without_greek_catalog_alias(self):
        self.assertNotIn("ριζοτο", self.index["tokenPostings"])
        result = mod.search_index(
            self.index,
            "ριζότο",
            language="el",
            strict_language=False,
            size=10,
        )
        self.assertEqual(result["indices"], [0, 1])
        self.assertEqual(result["total"], 2)

    def test_localized_token_composes_with_existing_greek_ingredient_alias(self):
        result = mod.search_index(
            self.index,
            "ριζότο ντομάτα",
            language="el",
            strict_language=False,
            size=10,
        )
        self.assertEqual(result["indices"], [0])
        self.assertEqual(result["total"], 1)

    def test_query_script_is_independent_of_ui_language_without_fuzzy_guessing(self):
        german = mod.search_index(
            self.index,
            "ριζότο",
            language="de",
            strict_language=False,
            size=10,
        )
        misspelling = mod.search_index(
            self.index,
            "ριζότα",
            language="el",
            strict_language=False,
            size=10,
        )
        self.assertEqual(german["indices"], [0, 1])
        self.assertEqual(misspelling["indices"], [])


if __name__ == "__main__":
    unittest.main()
