from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOGIC_PATH = ROOT / "custom_components" / "cook4me" / "recipe_logic.py"

spec = importlib.util.spec_from_file_location("cook4me_recipe_logic_v251_test", LOGIC_PATH)
assert spec is not None and spec.loader is not None
logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logic)


def profile(diet: str, *, allergies=(), avoid=()):
    return {
        "diet": diet,
        "allergies": list(allergies),
        "avoid": list(avoid),
        "pantry": [],
        "preferences": [],
        "habitTerms": [],
    }


def recipe(*ingredients: str):
    return {
        "title": "Diet substitution matrix test",
        "ingredients": [{"name": name} for name in ingredients],
    }


class AllDietSubstitutionTests(unittest.TestCase):
    def assert_adapted(self, diet, rows, expected_keys):
        match = logic.score_recipe(recipe(*rows), profile(diet))
        self.assertFalse(match["safe"])
        self.assertTrue(match["eligibleWithSubstitutions"], (diet, rows, match))
        self.assertTrue(match["requiresSubstitutions"])
        self.assertTrue(match["substitutionCoverageComplete"])
        self.assertEqual(
            [row["ingredientIndex"] for row in match["substitutions"]],
            list(range(len(rows))),
        )
        self.assertEqual(
            [row["replacement"]["key"] for row in match["substitutions"]],
            expected_keys,
        )
        return match

    def test_pescatarian_meat_gelatin_rennet_and_lard(self):
        self.assert_adapted(
            "pescatarian",
            ["Chicken", "Gelatin", "Animal rennet", "Lard"],
            ["tofu", "agar", "microbial_rennet", "oil"],
        )

    def test_vegetarian_fish_meat_gelatin_and_isinglass(self):
        self.assert_adapted(
            "vegetarian",
            ["Salmon", "Beef", "Gelatin", "Isinglass"],
            ["tofu", "tofu", "agar", "bentonite"],
        )

    def test_vegan_mixed_recipe_gets_replacement_for_every_conflict(self):
        self.assert_adapted(
            "vegan",
            [
                "Chicken",
                "Salmon",
                "Milk",
                "Cream",
                "Butter",
                "Yogurt",
                "Honey",
                "Cheese",
                "Egg",
                "Egg whites",
                "Whey",
                "Gelatin",
                "Animal rennet",
            ],
            [
                "tofu",
                "tofu",
                "oat_milk",
                "oat_cream",
                "oil",
                "soy_yogurt",
                "sweetener",
                "soy_cheese",
                "flax_egg",
                "aquafaba",
                "pea_protein",
                "agar",
                "microbial_rennet",
            ],
        )

    def test_milk_falls_back_across_gluten_and_soy_restrictions(self):
        match = logic.score_recipe(
            recipe("Milk"),
            profile("vegan", allergies=("gluten", "soy")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "rice_milk")

    def test_cream_falls_back_across_gluten_and_soy_restrictions(self):
        match = logic.score_recipe(
            recipe("Cream"),
            profile("vegan", allergies=("gluten", "soy")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "coconut_cream")

    def test_yogurt_falls_back_when_soy_is_blocked(self):
        match = logic.score_recipe(
            recipe("Yogurt"),
            profile("vegan", allergies=("soy",)),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "coconut_yogurt")

    def test_fish_sauce_falls_back_when_soy_and_gluten_are_blocked(self):
        match = logic.score_recipe(
            recipe("Fish sauce"),
            profile("vegetarian", allergies=("soy", "gluten")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "coconut_aminos")

    def test_stock_falls_back_when_celery_is_blocked(self):
        match = logic.score_recipe(
            recipe("Chicken stock"),
            profile("vegetarian", allergies=("celery",)),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "mushroom_stock")

    def test_cheese_falls_back_across_soy_and_nut_restrictions(self):
        match = logic.score_recipe(
            recipe("Cheese"),
            profile("vegan", allergies=("soy", "nuts")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "nutritional_yeast")

    def test_omnivore_does_not_create_diet_substitutions(self):
        match = logic.score_recipe(recipe("Chicken", "Milk", "Egg"), profile("omnivore"))
        self.assertTrue(match["safe"])
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"], [])

    def test_non_diet_restrictions_still_block_adaptation(self):
        match = logic.score_recipe(
            recipe("Chicken"),
            profile("vegetarian", avoid=("tofu", "mushrooms", "chickpeas")),
        )
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertFalse(match["substitutionCoverageComplete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
