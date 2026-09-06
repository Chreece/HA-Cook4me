from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
logic_path = ROOT / "custom_components/cook4me/recipe_logic.py"
spec = importlib.util.spec_from_file_location("cook4me_recipe_logic", logic_path)
logic = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(logic)

vendor_path = ROOT / "custom_components/cook4me/vendor/cook4me_phonefree.py"
vspec = importlib.util.spec_from_file_location("cook4me_vendor", vendor_path)
vendor = importlib.util.module_from_spec(vspec)
assert vspec.loader is not None
vspec.loader.exec_module(vendor)

RAW = json.loads((ROOT / "tests/fixtures/pfifferling-recipe.json").read_text())
RECIPE = {
    "title": RAW["title"],
    "ingredients": vendor._extract_recipe_ingredients(RAW),
    "excludedFoods": vendor._extract_key_name_list(RAW, "excludedFoods"),
    "detectedExcludedFoods": vendor._extract_key_name_list(RAW, "detectedExcludedFoods"),
}


class RecipeLogicTests(unittest.TestCase):
    def test_pfifferling_is_vegetarian_not_vegan(self):
        flags = logic.dietary_flags(RECIPE)
        self.assertTrue(flags["vegetarian"])
        self.assertFalse(flags["vegan"])
        self.assertIn("DAIRY", flags["exclusionKeys"])

    def test_short_ei_token_does_not_match_reis_substring(self):
        recipe = {"ingredients": [{"name": "Reis"}]}
        flags = logic.dietary_flags(recipe)
        self.assertTrue(flags["vegan"])
        self.assertNotIn("ei", flags["nonVeganIngredientHits"])

    def test_fish_recipe_is_pescatarian_not_vegetarian(self):
        recipe = {"ingredients": [{"name": "Salmon"}, {"name": "rice"}]}
        flags = logic.dietary_flags(recipe)
        self.assertTrue(flags["pescatarian"])
        self.assertFalse(flags["vegetarian"])
        self.assertFalse(flags["vegan"])

    def test_backend_exclusion_can_gate_allergy(self):
        result = logic.score_recipe(RECIPE, {
            "diet": "omnivore",
            "allergies": ["Milchprodukte"],
            "avoid": [], "preferences": [], "pantry": [],
        })
        self.assertFalse(result["safe"])
        self.assertIn("allergy:Milchprodukte", result["violations"])

    def test_english_milk_alias_matches_backend_dairy_key(self):
        result = logic.score_recipe(RECIPE, {
            "diet": "omnivore", "allergies": ["milk"],
            "avoid": [], "preferences": [], "pantry": [],
        })
        self.assertFalse(result["safe"])
        self.assertIn("allergy:milk", result["violations"])

    def test_pantry_coverage_ignores_named_staples(self):
        result = logic.score_recipe(RECIPE, {
            "diet": "vegetarian", "allergies": [], "avoid": [], "preferences": [],
            "pantry": ["Arborio-Reis", "Schalotte", "Pfifferlinge", "Mascarpone", "Parmesan", "Petersilie", "Weißwein"],
        })
        self.assertTrue(result["safe"])
        self.assertGreaterEqual(result["pantryCoverage"], 0.95)
        self.assertNotIn("Wasser", result["missingIngredients"])
        self.assertNotIn("Olivenöl", result["missingIngredients"])
        self.assertNotIn("Salz", result["missingIngredients"])

    def test_category_allergy_matches_manual_ai_ingredient_synonym(self):
        recipe = {"ingredients": [{"name": "milk"}, {"name": "rice"}]}
        result = logic.score_recipe(recipe, {
            "diet": "omnivore", "allergies": ["dairy"], "avoid": [], "preferences": [], "pantry": []
        })
        self.assertFalse(result["safe"])
        self.assertIn("allergy:dairy", result["violations"])

    def test_manual_recipe_never_claims_sendability(self):
        r = logic.normalize_manual_recipe({
            "title": "My Soup",
            "ingredients": ["potato", "water"],
            "steps": ["Cook everything."],
        }, source="ai")
        self.assertEqual(r["source"], "ai")
        self.assertFalse(r["sendable"])
        self.assertIn("no proven SEB", r["sendRestriction"])


if __name__ == "__main__":
    unittest.main()
