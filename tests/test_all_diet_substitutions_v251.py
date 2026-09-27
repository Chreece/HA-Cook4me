from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
LOGIC_PATH = COMPONENT / "recipe_logic.py"
SUBS_PATH = COMPONENT / "ingredient_substitutions.py"

spec = importlib.util.spec_from_file_location("cook4me_recipe_logic_v251_test", LOGIC_PATH)
assert spec is not None and spec.loader is not None
logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logic)

sub_spec = importlib.util.spec_from_file_location("cook4me_substitutions_v251_test", SUBS_PATH)
assert sub_spec is not None and sub_spec.loader is not None
subs = importlib.util.module_from_spec(sub_spec)
sub_spec.loader.exec_module(subs)


def catalog_row(identifier: str, name: str) -> dict:
    return {
        "id": identifier,
        "conceptId": f"concept:food:{identifier}",
        "canonicalName": name,
        "name": name,
        "classification": "food",
    }


_TARGET_NAMES = (
    "Tofu",
    "Mushrooms",
    "Chickpeas",
    "Vegetable stock",
    "Vegetable stock cube",
    "Water",
    "Coconut cream",
    "Soy cream",
    "Soy milk",
    "Unsweetened soy milk",
    "Rice milk",
    "Olive oil",
    "Coconut oil",
    "Maple syrup",
    "Agave syrup",
    "Sugar",
    "Soy sauce",
    "Agar-agar",
    "Pectin",
    "Cornstarch",
    "Lemon juice",
    "Citric acid",
    "Ground flaxseed",
)
TARGETS = [
    catalog_row(f"target-{index}", name)
    for index, name in enumerate(_TARGET_NAMES)
]


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
    sources = [
        catalog_row(f"source-{index}-{logic.normalize_text(name)}", name)
        for index, name in enumerate(ingredients)
    ]
    payload = {
        "ingredients": [
            *(dict(row) for row in TARGETS),
            *sources,
        ]
    }
    summary = subs.enrich_catalog_substitutions(payload)
    if summary["missingProfiles"] or summary["unresolvedTargets"]:
        raise AssertionError(summary)
    return {
        "title": "Diet substitution matrix test",
        "ingredients": sources,
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
        self.assertEqual(match["substitutionSources"], ["ingredient_catalog"])
        return match

    def test_pescatarian_meat_gelatin_rennet_and_lard(self):
        self.assert_adapted(
            "pescatarian",
            ["Chicken", "Gelatin", "Animal rennet", "Lard"],
            ["tofu", "agar", "microbial_rennet", "olive_oil"],
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
                "soy_milk",
                "coconut_cream",
                "olive_oil",
                "plant_yogurt",
                "maple_syrup",
                "plant_cheese",
                "ground_flaxseed_water",
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
        self.assertEqual(
            match["substitutions"][0]["replacement"]["key"],
            "coconut_cream_lemon",
        )

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
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "water")

    def test_cheese_fails_closed_when_all_reviewed_candidates_are_uncertain_or_blocked(self):
        match = logic.score_recipe(
            recipe("Cheese"),
            profile("vegan", allergies=("soy", "nuts")),
        )
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertFalse(match["substitutionCoverageComplete"])

    def test_multilingual_derivatives_are_replaced(self):
        cases = [
            ("pescatarian", "Tierisches Lab", "microbial_rennet"),
            ("vegetarian", "Présure", "microbial_rennet"),
            ("vegetarian", "Ιχθυόκολλα", "bentonite"),
            ("vegan", "Molke", "pea_protein"),
            ("vegan", "Ορός γάλακτος", "pea_protein"),
            ("vegan", "Eiweiß", "aquafaba"),
            ("vegan", "Yema de huevo", "ground_flaxseed_water"),
        ]
        for diet, ingredient, expected in cases:
            with self.subTest(diet=diet, ingredient=ingredient):
                match = logic.score_recipe(recipe(ingredient), profile(diet))
                self.assertTrue(match["eligibleWithSubstitutions"], match)
                self.assertTrue(match["substitutionCoverageComplete"])
                self.assertEqual(match["substitutions"][0]["replacement"]["key"], expected)

    def test_omnivore_does_not_mount_diet_substitutions(self):
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
