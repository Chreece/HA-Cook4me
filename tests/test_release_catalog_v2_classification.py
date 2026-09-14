from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "classify_release_catalog_v2.py"
spec = importlib.util.spec_from_file_location("classify_release_catalog_v2", SCRIPT)
assert spec and spec.loader
classify = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = classify
spec.loader.exec_module(classify)


class ReleaseCatalogV2ClassificationTests(unittest.TestCase):
    def setUp(self):
        self.english = {
            "VEG": "carrot",
            "TOFU": "tofu",
            "EGG": "egg",
            "FISH": "salmon",
            "MEAT": "beef",
        }
        self.localized = {}

    def diet(self, ingredients, *, language="en", extra=None):
        detail = {"language": language, "ingredients": ingredients}
        if extra:
            detail.update(extra)
        return classify.classify_variant_diet(
            detail,
            self.english,
            self.localized,
        )

    def test_complete_plant_recipe_is_vegan_and_hierarchical(self):
        row = self.diet([{"foodKey": "VEG"}, {"foodKey": "TOFU"}])
        self.assertEqual("resolved", row["status"])
        self.assertEqual("vegan", row["primaryDiet"])
        self.assertEqual(["vegan", "vegetarian", "pescatarian"], row["dietTags"])
        self.assertTrue(row["vegan"])
        self.assertTrue(row["vegetarian"])
        self.assertTrue(row["pescatarian"])

    def test_egg_recipe_is_vegetarian(self):
        row = self.diet([{"foodKey": "VEG"}, {"foodKey": "EGG"}])
        self.assertEqual("vegetarian", row["primaryDiet"])
        self.assertEqual(["vegetarian", "pescatarian"], row["dietTags"])
        self.assertFalse(row["vegan"])
        self.assertTrue(row["vegetarian"])

    def test_fish_recipe_is_pescatarian(self):
        row = self.diet([{"foodKey": "FISH"}, {"foodKey": "VEG"}])
        self.assertEqual("pescatarian", row["primaryDiet"])
        self.assertEqual(["pescatarian"], row["dietTags"])
        self.assertFalse(row["vegetarian"])
        self.assertTrue(row["pescatarian"])

    def test_meat_resolves_omnivore_even_with_other_unresolved_line(self):
        row = self.diet([{"foodKey": "MEAT"}, {"cleanName": "mystery ingredient"}])
        self.assertEqual("resolved", row["status"])
        self.assertEqual("omnivore", row["primaryDiet"])
        self.assertEqual(["omnivore"], row["dietTags"])
        self.assertFalse(row["pescatarian"])

    def test_unresolved_keyless_line_blocks_positive_vegan_claim(self):
        row = self.diet([{"foodKey": "VEG"}, {"cleanName": "mystery ingredient"}])
        self.assertEqual("review_required", row["status"])
        self.assertIsNone(row["primaryDiet"])
        self.assertIsNone(row["vegan"])
        self.assertTrue(row["evidence"]["unresolved"])

    def test_structured_amount_and_unit_are_removed_before_label_matching(self):
        name, changed = classify.semantic_ingredient_name(
            {
                "applicationDescription": "250 millilitres d'eau",
                "quantity": 250,
                "unit": {"name": "millilitre", "pluralName": "millilitres", "abbreviation": "ml"},
            }
        )
        self.assertTrue(changed)
        self.assertEqual("eau", name)

    def test_unicode_exact_label_matching_keeps_non_latin_scripts(self):
        self.english["WATER"] = "Water"
        key = classify._label_norm("水")
        localized = {
            "ja": {key: {"WATER"}},
            classify._GLOBAL_LABELS: {key: {"WATER"}},
        }
        row = classify.classify_variant_diet(
            {"language": "ja", "ingredients": [{"cleanName": "水"}]},
            self.english,
            localized,
        )
        self.assertEqual("vegan", row["primaryDiet"])

    def test_global_exact_label_match_is_semantic_only_and_can_cross_recipe_language(self):
        self.english["WATER"] = "Water"
        key = classify._label_norm("eau")
        localized = {
            classify._GLOBAL_LABELS: {key: {"WATER"}},
        }
        name, source, resolved = classify._ingredient_english(
            {"cleanName": "eau"}, "uk", self.english, localized
        )
        self.assertTrue(resolved)
        self.assertEqual("Water", name)
        self.assertTrue(source.startswith("keyless:global-exact-label-semantic:"))

    def test_multiple_exact_candidates_are_safe_when_english_semantics_are_identical(self):
        self.english.update({"WATER1": "Water", "WATER2": "Water"})
        key = classify._label_norm("víz")
        localized = {
            "hu": {key: {"WATER1", "WATER2"}},
            classify._GLOBAL_LABELS: {key: {"WATER1", "WATER2"}},
        }
        name, _source, resolved = classify._ingredient_english(
            {"cleanName": "víz"}, "hu", self.english, localized
        )
        self.assertTrue(resolved)
        self.assertEqual("Water", name)

    def test_coconut_and_almond_milk_do_not_trigger_dairy(self):
        for name in ("Coconut milk", "Almond milk", "Soy milk", "Hazelnut milk"):
            self.english["PLANT"] = name
            row = self.diet([{"foodKey": "PLANT"}])
            self.assertEqual("vegan", row["primaryDiet"], name)

    def test_peanut_butter_is_not_dairy(self):
        self.english["PB"] = "Peanut butter"
        row = self.diet([{"foodKey": "PB"}])
        self.assertEqual("vegan", row["primaryDiet"])

    def test_kidney_beans_are_not_meat(self):
        for name in ("Kidney bean", "Red Kidney beans"):
            self.english["BEAN"] = name
            row = self.diet([{"foodKey": "BEAN"}])
            self.assertEqual("vegan", row["primaryDiet"], name)

    def test_oyster_mushrooms_are_not_seafood(self):
        self.english["MUSH"] = "Oyster mushrooms"
        row = self.diet([{"foodKey": "MUSH"}])
        self.assertEqual("vegan", row["primaryDiet"])

    def test_vegetable_stock_is_plant_safe_but_generic_stock_is_reviewed(self):
        self.english["STOCK"] = "Vegetable stock"
        self.assertEqual("vegan", self.diet([{"foodKey": "STOCK"}])["primaryDiet"])
        self.english["STOCK"] = "Stock"
        row = self.diet([{"foodKey": "STOCK"}])
        self.assertEqual("review_required", row["status"])
        self.assertIn("ambiguous:stock", row["evidence"]["unresolved"])

    def test_chicken_stock_is_meat_not_ambiguous_generic_stock(self):
        self.english["STOCK"] = "Chicken stock"
        row = self.diet([{"foodKey": "STOCK"}])
        self.assertEqual("omnivore", row["primaryDiet"])

    def test_parmesan_and_gruyere_are_nonvegan_even_without_word_cheese(self):
        for name in ("Parmesan", "Gruyère", "Mimolette", "Emmental"):
            self.english["DAIRY"] = name
            row = self.diet([{"foodKey": "DAIRY"}])
            self.assertEqual("vegetarian", row["primaryDiet"], name)

    def test_vegetarian_sausage_does_not_become_omnivore_or_vegan(self):
        self.english["VS"] = "Vegetarian sausage"
        row = self.diet([{"foodKey": "VS"}])
        self.assertEqual("review_required", row["status"])
        self.assertIsNone(row["primaryDiet"])

    def test_noisy_provider_categories_are_audit_only(self):
        row = self.diet(
            [{"foodKey": "VEG"}],
            extra={"excludedFoods": [{"key": "FISH"}, {"key": "DAIRY"}]},
        )
        self.assertEqual("vegan", row["primaryDiet"])
        self.assertEqual(["DAIRY", "FISH"], row["evidence"]["providerCategoryHints"])

    def test_provider_main_course_is_resolved_main(self):
        row = classify.classify_variant_meal(
            {"title": "Anything", "courses": ["MAIN_COURSE"]}
        )
        self.assertEqual("resolved", row["status"])
        self.assertEqual(["main"], row["mealTypes"])
        self.assertEqual("main", row["primaryMealType"])
        self.assertEqual("seb_courses_occasions", row["source"])

    def test_provider_starter_is_resolved_starter(self):
        row = classify.classify_variant_meal(
            {"title": "Anything", "courses": [{"key": "STARTER", "name": "Starter"}]}
        )
        self.assertEqual("resolved", row["status"])
        self.assertEqual(["starter"], row["mealTypes"])

    def test_title_soup_without_provider_taxonomy_remains_review_required(self):
        row = classify.classify_variant_meal({"title": "Tomato soup"})
        self.assertEqual("review_required", row["status"])
        self.assertEqual(["soup"], row["mealTypes"])
        self.assertEqual("soup", row["primaryMealType"])
        self.assertEqual("title_keyword_provisional", row["source"])


if __name__ == "__main__":
    unittest.main()
