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

    def diet(self, ingredients):
        return classify.classify_variant_diet(
            {"language": "en", "ingredients": ingredients},
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
