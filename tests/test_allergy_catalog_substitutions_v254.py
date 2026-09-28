from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, COMPONENT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


logic = load("cook4me_recipe_logic_v254_test", "recipe_logic.py")
subs = load("cook4me_ingredient_substitutions_v254_test", "ingredient_substitutions.py")
intelligence = load("cook4me_ingredient_intelligence_v254_test", "ingredient_intelligence.py")


def target(identifier, name, *, allergens=None):
    row = {
        "id": identifier,
        "conceptId": f"concept:food:{identifier}",
        "canonicalName": name,
        "classification": "food",
    }
    if allergens:
        row["intelligence"] = {
            "allergens": {key: "present" for key in allergens}
        }
    return row


TARGETS = [
    target("tofu", "Tofu"),
    target("mushrooms", "Mushrooms"),
    target("chickpeas", "Chickpeas"),
    target("veg-stock", "Vegetable stock"),
    target("veg-stock-cube", "Vegetable stock cube"),
    target("water", "Water"),
    target("coconut-cream", "Coconut cream"),
    target("soy-cream", "Soy cream"),
    target("soy-milk", "Soy milk"),
    target("soy-milk-unsweet", "Unsweetened soy milk"),
    target("rice-milk", "Rice milk"),
    target("olive-oil", "Olive oil"),
    target("coconut-oil", "Coconut oil"),
    target("maple", "Maple syrup"),
    target("agave", "Agave syrup"),
    target("sugar", "Sugar"),
    target("soy-sauce", "Soy sauce"),
    target("agar", "Agar-agar"),
    target("pectin", "Pectin"),
    target("cornstarch", "Cornstarch"),
    target("lemon", "Lemon juice"),
    target("citric", "Citric acid"),
    target("flax", "Ground flaxseed"),
]


def profile(diet="omnivore", *, allergies=(), avoid=()):
    return {
        "diet": diet,
        "allergies": list(allergies),
        "avoid": list(avoid),
        "pantry": [],
        "preferences": [],
        "habitTerms": [],
    }


class AllergyCatalogSubstitutionTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            target("milk", "Milk", allergens=("milk", "lactose")),
            target("egg", "Egg", allergens=("egg",)),
            target("wheat-flour", "Wheat flour", allergens=("gluten",)),
            target("almond", "Almond", allergens=("tree_nut",)),
            target("provider-soy", "Provider protein", allergens=("soy",)),
            target("sulfite-additive", "Preservative", allergens=("sulfites",)),
            target("fish-sauce", "Fish sauce", allergens=("fish",)),
            target("chicken-stock", "Chicken stock"),
            target("egg-white", "Egg white", allergens=("egg",)),
        ]
        self.payload = {"ingredients": [*TARGETS, *self.sources]}
        self.summary = subs.enrich_catalog_substitutions(self.payload)
        self.by_id = {row["id"]: row for row in self.payload["ingredients"]}

    def test_allergy_overlay_uses_stable_application_allergen_keys(self):
        catalog = subs.load_substitution_catalog()
        supported = set(intelligence.ALLERGEN_KEYS)
        for row in catalog.get("sourceProfiles") or []:
            for key in row.get("triggerAllergens") or []:
                self.assertIn(key, supported)
        for row in catalog.get("candidates", {}).values():
            for key in row.get("allergens") or []:
                self.assertIn(key, supported)
        self.assertEqual(catalog["unsupportedAllergySubstitutions"], ["sulfites"])
        self.assertGreater(self.summary["allergySourceProfiles"], 0)
        self.assertGreater(self.summary["allergyIngredientCount"], 0)

    def test_specific_catalog_profiles_beat_generic_allergy_or_protein_fallbacks(self):
        self.assertEqual(
            [row["key"] for row in self.by_id["fish-sauce"]["substitutions"]],
            ["soy_sauce", "coconut_aminos"],
        )
        self.assertEqual(
            [row["key"] for row in self.by_id["chicken-stock"]["substitutions"]],
            ["vegetable_stock", "vegetable_stock_cube", "water"],
        )
        self.assertEqual(
            [row["key"] for row in self.by_id["egg-white"]["substitutions"]],
            ["aquafaba", "ground_flaxseed_water", "cornstarch_water"],
        )

    def test_plant_milks_do_not_inherit_dairy_allergy_triggers(self):
        for identifier in ("soy-milk", "soy-milk-unsweet", "rice-milk"):
            with self.subTest(identifier=identifier):
                row = self.by_id[identifier]
                self.assertNotIn("milk", row.get("substitutionAllergens") or [])
                self.assertNotIn("lactose", row.get("substitutionAllergens") or [])

    def test_milk_allergy_can_use_catalog_replacements_on_omnivore_profile(self):
        milk = self.by_id["milk"]
        self.assertEqual(milk["substitutionAllergens"], ["milk", "lactose"])
        match = logic.score_recipe(
            {"title": "Milk sauce", "ingredients": [milk]},
            profile(allergies=("milk",)),
        )
        self.assertFalse(match["safe"])
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["violations"], ["allergy:milk"])
        row = match["substitutions"][0]
        self.assertEqual(row["reasons"], ["allergy:milk"])
        self.assertEqual(
            [candidate["key"] for candidate in row["alternatives"]],
            ["soy_milk", "rice_milk", "unsweetened_soy_milk"],
        )

    def test_allergy_candidate_is_filtered_by_second_allergy(self):
        milk = self.by_id["milk"]
        match = logic.score_recipe(
            {"title": "Milk sauce", "ingredients": [milk]},
            profile(allergies=("milk", "soy")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(
            [candidate["key"] for candidate in match["substitutions"][0]["alternatives"]],
            ["rice_milk"],
        )

    def test_one_row_can_cover_combined_diet_and_allergy_conflicts(self):
        milk = self.by_id["milk"]
        match = logic.score_recipe(
            {"title": "Milk sauce", "ingredients": [milk]},
            profile("vegan", allergies=("milk", "soy")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertTrue(match["substitutionCoverageComplete"])
        self.assertEqual(
            match["substitutions"][0]["reasons"],
            ["diet:vegan", "allergy:milk"],
        )
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "rice_milk")

    def test_saved_profile_excluded_term_in_avoid_still_uses_allergy_trigger(self):
        milk = self.by_id["milk"]
        match = logic.score_recipe(
            {"title": "Milk sauce", "ingredients": [milk]},
            profile(avoid=("milk",)),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["violations"], ["avoid:milk"])
        self.assertEqual(match["substitutions"][0]["reasons"], ["avoid:milk"])

    def test_explicit_allergen_evidence_works_without_name_guessing(self):
        source = self.by_id["provider-soy"]
        self.assertIn("soy", source["substitutionAllergens"])
        match = logic.score_recipe(
            {"title": "Provider recipe", "ingredients": [source]},
            profile(allergies=("soy",)),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["violations"], ["allergy:soy"])
        self.assertEqual(
            [candidate["key"] for candidate in match["substitutions"][0]["alternatives"]],
            ["chickpeas", "mushrooms", "pea_protein"],
        )

    def test_gluten_and_tree_nut_profiles_mount_catalog_owned_candidates(self):
        wheat = logic.score_recipe(
            {"title": "Batter", "ingredients": [self.by_id["wheat-flour"]]},
            profile(allergies=("gluten",)),
        )
        self.assertTrue(wheat["eligibleWithSubstitutions"])
        self.assertEqual(
            [candidate["key"] for candidate in wheat["substitutions"][0]["alternatives"]],
            ["rice_flour", "cornstarch"],
        )

        almond = logic.score_recipe(
            {"title": "Nut sauce", "ingredients": [self.by_id["almond"]]},
            profile(allergies=("tree_nut",)),
        )
        self.assertTrue(almond["eligibleWithSubstitutions"])
        self.assertEqual(
            [candidate["key"] for candidate in almond["substitutions"][0]["alternatives"]],
            ["sunflower_seed_butter"],
        )

    def test_candidate_with_conflicting_allergen_is_removed(self):
        soy_sauce = self.by_id["soy-sauce"]
        self.assertIn("soy", soy_sauce["substitutionAllergens"])
        match = logic.score_recipe(
            {"title": "Sauce", "ingredients": [soy_sauce]},
            profile(allergies=("soy", "tree_nut")),
        )
        # Coconut aminos is reviewed as tree-nut-containing in the substitution
        # catalog, so a soy+tree-nut profile must not be offered that swap.
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertFalse(match["substitutionCoverageComplete"])

    def test_unsupported_allergen_fails_closed_even_with_catalog_evidence(self):
        source = self.by_id["sulfite-additive"]
        match = logic.score_recipe(
            {"title": "Preserved food", "ingredients": [source]},
            profile(allergies=("sulfites",)),
        )
        self.assertFalse(match["safe"])
        self.assertEqual(match["violations"], ["allergy:sulfites"])
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertFalse(match["substitutionCoverageComplete"])
        self.assertEqual(match["substitutions"], [])

    def test_multiple_conflicting_ingredients_each_require_a_replacement(self):
        recipe = {
            "title": "Custard",
            "ingredients": [self.by_id["milk"], self.by_id["egg"]],
        }
        match = logic.score_recipe(
            recipe,
            profile("vegan", allergies=("milk", "egg")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(
            [row["ingredientIndex"] for row in match["substitutions"]],
            [0, 1],
        )
        self.assertTrue(all(row["alternatives"] for row in match["substitutions"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
