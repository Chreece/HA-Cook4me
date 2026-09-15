"""Greek query equivalence and lossless regional publication grouping."""
from copy import deepcopy
import importlib
from pathlib import Path
import socket
import sys
import types
import unittest
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/cook4me"
LANGUAGES = ["de", "en", "fr", "es", "it"]


class MultilingualCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = types.ModuleType("cook4me_general_catalog_v65_test")
        package.__path__ = [str(COMPONENT)]
        sys.modules[package.__name__] = package
        cls.release = importlib.import_module(f"{package.__name__}.release_catalog")
        cls.filters = importlib.import_module(f"{package.__name__}.shared_recipe_filters")
        cls.logic = importlib.import_module(f"{package.__name__}.recipe_logic")
        cls.index = importlib.import_module(f"{package.__name__}.catalog_search_index")
        cls.presentation = importlib.import_module(f"{package.__name__}.catalog_presentation")
        cls.payload = cls.release.load_release_catalog()

    def test_every_reviewed_ingredient_label_is_available_to_query_translation(self):
        aliases = self.payload["_runtimeSearchIndex"]["catalogQueryAliases"]
        for language, labels in self.presentation.labels().items():
            for canonical, label in labels.items():
                self.assertIn(self.index.normalize_search_text(canonical), aliases[language][self.index.normalize_search_text(label)], (language, label))

    def test_different_dishes_and_ingredients_find_their_english_matches_in_selected_catalogs(self):
        index = self.payload["_runtimeSearchIndex"]
        pairs = [("νιόκι", "gnocchi"), ("κινόα", "quinoa"), ("κουνουπίδι", "cauliflower"),
            ("γλυκιά πάπρικα", "sweet paprika"), ("μουσακάς", "moussaka"), ("σπαράγγια", "asparagus"),
            ("κολοκύθα", "pumpkin"), ("ράμεν", "ramen"), ("μελιτζάνα", "aubergine"),
            ("φακές", "lentils"), ("ρεβίθια", "chickpeas"), ("ριζότο ντομάτα", "risotto tomato")]
        for language in LANGUAGES:
            allowed = index["recipeLanguages"][language]
            for localized, canonical in pairs:
                def ids(query):
                    return set(self.index.search_index(index, query, language="el", allowed_indices=allowed, size=20000)["indices"])
                self.assertEqual(ids(localized), ids(canonical), (language, localized))

    def test_ingredient_picker_searches_source_languages_and_retains_ui_labels(self):
        for queries, name in [(("ρύζι", "rice", "arroz"), "Ρύζι"), (("κουνουπίδι", "cauliflower", "chou-fleur"), "Κουνουπίδι")]:
            for query in queries:
                rows = self.release.ingredient_choices("el", query)
                self.assertTrue(any(row["name"] == name for row in rows), query)
                self.assertTrue(all(row["displayLanguage"] == "el" for row in rows))
        self.assertEqual(self.release.ingredient_choices("el", "ανύπαρκτο συστατικό"), [])

    def test_new_bilingual_catalog_entries_work_without_a_query_whitelist(self):
        payload = {"ingredients": [{"id": "teff", "canonicalName": "Teff pasta"}], "recipes": [
            {"canonicalName": "Teff pudding", "variants": [{"variantId": "new", "language": "de", "title": "Teffpudding", "ingredients": [{"ingredientId": "teff"}]}]}]}
        aliases = self.index.prepare_catalog_query_aliases(payload, {"el": {"teff pasta": "Ζυμαρικά τεφ"}})
        index = self.index.prepare_search_index(self.index.compile_search_index(payload))
        index["catalogQueryAliases"] = aliases
        for query in ("τεφ", "ζυμαρικά τεφ", "Teffpudding"):
            self.assertEqual(self.index.search_index(index, query, language="el")["indices"], [0])
        self.assertEqual(self.index.search_index(index, "τεφ ανύπαρκτο", language="el")["indices"], [])

    def test_generic_family_rules_preserve_distinct_covers_titles_and_yield_dimensions(self):
        def recipe(ident, quantity=200, servings=4, title="Garden supper", cover="same", unit="servings"):
            return {"groupingFunctionalId": ident, "canonicalName": title, "variants": [{"variantId": ident,
                "cover": cover, "servings": servings, "yield": {"unit": unit},
                "ingredients": [{"ingredientId": "carrot", "quantity": quantity, "unit": "g"}]}]}
        payload = {"recipes": [recipe("a"), recipe("b", 100, 2), recipe("c", 300),
            recipe("d", cover="different"), recipe("e", title="Different supper"), recipe("f", unit="g")],
            "_runtimeIngredientById": {"carrot": {"canonicalName": "Carrot"}}}
        self.presentation.prepare_families(payload)
        self.assertEqual(list(payload["_runtimeDisplayFamilyMembers"].values()), [[0, 1, 2], [3], [4], [5]])
        self.assertEqual(payload["_runtimeRegionalFamilies"], {0})
        payload["recipes"].pop(2)
        self.presentation.prepare_families(payload)
        self.assertEqual(payload["_runtimeRegionalFamilies"], set(), "Proportionally scaled servings must not become different editions")

    def search(self, query, languages=LANGUAGES, process=None, **kwargs):
        with patch.object(socket, "socket", side_effect=AssertionError("offline query used network")):
            return self.release.search_release_recipes(query, language="el", configured_language="de", country="DE",
                catalog_languages=languages, group_families=True, filter_rows=process or self.vegetarian, **kwargs)

    def vegetarian(self, rows):
        safe = []
        for row in rows:
            row["match"] = self.logic.score_recipe(row, {"diet": "vegetarian", "houseIngredients": []})
            if row["match"]["safe"]:
                safe.append(row)
        return self.filters.apply_filters(safe, {"mealTypes": ["soup"]})

    def test_greek_accent_case_and_phrases_return_the_same_two_recipe_cards(self):
        expected = self.search("ramen")
        self.assertEqual(expected["page"]["totalElements"], 2)
        self.assertEqual(expected["rawMatchedPublications"], 13)
        self.assertEqual(sorted(row["publicationCount"] for row in expected["items"]), [1, 5])
        for query in ("Ράμεν", "ΡΑΜΕΝ", "ΡΆΜΕΝ", "ραμεν", "ράμεν με λαχανικά"):
            result = self.search(query)
            self.assertEqual({row["displayFamilyId"] for row in result["items"]}, {row["displayFamilyId"] for row in expected["items"]}, query)
        self.assertEqual(self.search("Ράμεν")["resolvedQuery"], "ramen")
        self.assertEqual(self.search("ράμεν ανύπαρκτο")["items"], [])

    def test_selected_catalogs_and_pagination_do_not_restore_duplicates(self):
        first = self.search("Ράμεν", size=1)
        second = self.search("ramen", size=1, page=1)
        self.assertEqual(first["page"]["totalElements"], 2)
        self.assertNotEqual(first["items"][0]["displayFamilyId"], second["items"][0]["displayFamilyId"])
        for codes in (["de", "en"], ["es", "it"], ["de"], ["fr"]):
            result = self.search("Ράμεν", languages=codes)
            self.assertEqual(len(result["items"]), 1)
            self.assertLessEqual(set(result["items"][0]["availableLanguages"]), set(codes))

    def test_every_regional_publication_and_serving_remains_selectable(self):
        row = next(row for row in self.search("ramen", languages=None)["items"] if row.get("regionalPublications"))
        self.assertEqual(row["publicationCount"], 10)
        options = [option for language in row["languageVariants"] for option in language["servingVariants"]]
        self.assertEqual(len(options), 30)
        self.assertEqual(len({option["displayVariantId"] for option in options}), 30)
        german = next(language for language in row["languageVariants"] if language["language"] == "de")
        self.assertEqual(len(german["servingVariants"]), 6)
        self.assertEqual({option["publicationNumber"] for option in german["servingVariants"]}, {1, 2})
        for variant in ("316542", "326387", "331208", "324778", "325003"):
            grouped = self.release.recipe_by_variant(variant, language="el", configured_language="de", country="DE", group_families=True)
            original = self.release.recipe_by_variant(variant, language=grouped["language"], configured_language="de", country="DE", group_families=False)
            self.assertEqual(grouped["displayVariantId"], variant)
            for key in ("ingredients", "catalogNutrition", "sendVariantId", "sendGroupingFunctionalId"):
                self.assertEqual(grouped.get(key), original.get(key), (variant, key))

    def test_a_nonmatching_default_publication_does_not_hide_a_matching_language(self):
        # Rice pasta is in the Spanish edition but not the default German one.
        def process(rows):
            return self.filters.apply_filters(self.vegetarian(rows), {"ingredients": ["k:M_FOOD_337"]})
        result = self.search("Ράμεν", process=process)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["language"], "es")
        self.assertEqual(result["items"][0]["availableLanguages"], ["es"])
        self.assertEqual(result["items"][0]["displayVariantId"], "325003")

    def test_even_identical_food_proportions_are_filtered_per_original_publication(self):
        result = self.search("rice", process=lambda rows: [row for row in rows
            if row["canonicalName"] == "Rice" and row["language"] == "es"])
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["availableLanguages"], ["es"])

    def test_distinct_french_recipe_stays_separate_and_meat_fish_stay_filtered(self):
        all_rows = self.search("ramen", languages=None)["items"]
        self.assertEqual(len(all_rows), 2)
        self.assertEqual(len({row["cover"] for row in all_rows}), 2)
        self.assertEqual({row["canonicalName"] for row in all_rows}, {"Vegetable ramen"})
        # The real Polish recipe has canonical "Prawns", plural, and must not
        # become a vegetarian suggestion just because its source text is Polish.
        shrimp = self.release.recipe_by_variant("566361", language="pl", configured_language="de", country="DE")
        self.assertFalse(self.logic.dietary_flags(shrimp)["vegetarian"])
        self.assertTrue(self.logic.dietary_flags(shrimp)["pescatarian"])


if __name__ == "__main__":
    unittest.main()
