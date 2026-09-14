from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components/cook4me/catalog_search_index.py"
spec = importlib.util.spec_from_file_location("cook4me_catalog_search_index_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class CatalogSearchIndexTests(unittest.TestCase):
    def _payload(self):
        return {
            "ingredients": [
                {
                    "id": "concept:food:tomato",
                    "canonicalName": "Tomato",
                    "aliases": {
                        "en": ["Tomato"],
                        "de": ["Tomate"],
                        "el": ["Ντομάτα"],
                    },
                },
                {
                    "id": "concept:food:mushroom",
                    "canonicalName": "Mushroom",
                    "aliases": {
                        "en": ["Mushroom"],
                        "de": ["Pilz"],
                        "el": ["Μανιτάρι"],
                    },
                },
                {
                    "id": "concept:food:rice",
                    "canonicalName": "Rice",
                    "aliases": {
                        "en": ["Rice"],
                        "de": ["Reis"],
                        "el": ["Ρύζι"],
                    },
                },
            ],
            "recipes": [
                {
                    "groupingFunctionalId": "GROUP_TOMATO_RISOTTO",
                    "canonicalName": "Tomato risotto",
                    "searchAliases": {
                        "de": ["Tomatenrisotto"],
                        "el": ["Ριζότο με ντομάτα"],
                    },
                    "variants": [
                        {
                            "variantId": "PL_RISOTTO",
                            "language": "pl",
                            "title": "Risotto pomidorowe",
                            "ingredients": [
                                {"ingredientId": "concept:food:tomato"},
                                {"ingredientId": "concept:food:rice"},
                            ],
                        }
                    ],
                },
                {
                    "groupingFunctionalId": "GROUP_MUSHROOM_RISOTTO",
                    "canonicalName": "Mushroom risotto",
                    "searchAliases": {
                        "de": ["Pilzrisotto"],
                        "el": ["Ριζότο με μανιτάρια"],
                    },
                    "variants": [
                        {
                            "variantId": "IT_RISOTTO",
                            "language": "it",
                            "title": "Risotto ai funghi",
                            "ingredients": [
                                {"ingredientId": "concept:food:mushroom"},
                                {"ingredientId": "concept:food:rice"},
                            ],
                        }
                    ],
                },
                {
                    "groupingFunctionalId": "GROUP_TOMATO_SOUP",
                    "canonicalName": "Tomato soup",
                    "searchAliases": {
                        "de": ["Tomatensuppe"],
                        "el": ["Ντοματόσουπα"],
                    },
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
        self.compiled = mod.compile_search_index(self._payload())
        self.index = mod.prepare_search_index(self.compiled)

    def test_one_german_query_finds_foreign_recipes_through_concept_alias(self):
        result = mod.search_index(self.index, "Tomate", size=10)
        self.assertEqual(set(result["indices"]), {0, 2})
        self.assertEqual(result["total"], 2)

    def test_one_greek_query_finds_same_foreign_recipes(self):
        result = mod.search_index(self.index, "Ντομάτα", size=10)
        self.assertEqual(set(result["indices"]), {0, 2})
        self.assertEqual(result["total"], 2)

    def test_title_search_crosses_catalog_languages(self):
        result = mod.search_index(self.index, "risotto", size=10)
        self.assertEqual(result["indices"], [0, 1])

    def test_precompiled_search_alias_can_match_user_language_without_native_variant(self):
        result = mod.search_index(self.index, "Tomatenrisotto", size=10)
        self.assertEqual(result["indices"], [0])

    def test_prefix_search_supports_fast_typeahead(self):
        result = mod.search_index(self.index, "riso", size=10)
        self.assertEqual(result["indices"], [0, 1])

    def test_strict_language_filters_after_global_query_semantics(self):
        result = mod.search_index(
            self.index,
            "risotto",
            language="pl",
            strict_language=True,
            size=10,
        )
        self.assertEqual(result["indices"], [0])

        result = mod.search_index(
            self.index,
            "risotto",
            language="de",
            strict_language=True,
            size=10,
        )
        self.assertEqual(result["indices"], [])

    def test_title_hits_rank_above_ingredient_only_hits(self):
        payload = self._payload()
        payload["recipes"].append(
            {
                "groupingFunctionalId": "GROUP_RICE",
                "canonicalName": "Simple rice",
                "variants": [
                    {
                        "variantId": "EN_RICE",
                        "language": "en",
                        "title": "Simple rice",
                        "ingredients": [{"ingredientId": "concept:food:tomato"}],
                    }
                ],
            }
        )
        index = mod.prepare_search_index(mod.compile_search_index(payload))
        result = mod.search_index(index, "tomato", size=10)
        self.assertEqual(result["indices"][0], 0)
        self.assertEqual(result["indices"][1], 2)
        self.assertEqual(result["indices"][-1], 3)

    def test_empty_query_uses_index_recipe_count_without_catalog_scan(self):
        result = mod.search_index(self.index, "", page=1, size=2)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["indices"], [2])

    def test_compiled_index_is_json_serializable_shape(self):
        self.assertEqual(self.compiled["schemaVersion"], 1)
        self.assertEqual(
            self.compiled["kind"],
            "cook4me-multilingual-recipe-search-index",
        )
        self.assertIsInstance(self.compiled["tokenPostings"]["risotto"], list)
        self.assertGreater(self.compiled["stats"]["tokens"], 0)
        self.assertGreater(self.compiled["stats"]["prefixes"], 0)


if __name__ == "__main__":
    unittest.main()
