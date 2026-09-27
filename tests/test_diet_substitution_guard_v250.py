from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
LOGIC_PATH = ROOT / "custom_components" / "cook4me" / "recipe_logic.py"

spec = importlib.util.spec_from_file_location("cook4me_recipe_logic_v250_test", LOGIC_PATH)
assert spec is not None and spec.loader is not None
logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logic)


class VegetarianFishSubstitutionGuardTests(unittest.TestCase):
    def profile(self, diet="vegetarian"):
        return {
            "diet": diet,
            "allergies": [],
            "avoid": [],
            "pantry": [],
            "preferences": [],
            "habitTerms": [],
        }

    def test_fish_suggestion_has_concrete_replacement_and_complete_coverage(self):
        recipe = {
            "title": "Cod with vegetables",
            "ingredients": [
                {"name": "Cod"},
                {"name": "Carrots"},
            ],
        }
        match = logic.score_recipe(recipe, self.profile())

        self.assertFalse(match["safe"])
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertTrue(match["requiresSubstitutions"])
        self.assertTrue(match["substitutionCoverageComplete"])
        self.assertEqual([row["ingredientIndex"] for row in match["substitutions"]], [0])
        self.assertTrue(match["substitutions"][0]["replacement"]["name"])

    def test_every_fish_row_requires_its_own_replacement(self):
        recipe = {
            "title": "Fish duo",
            "ingredients": [
                {"name": "Cod"},
                {"name": "Salmon"},
                {"name": "Potatoes"},
            ],
        }
        match = logic.score_recipe(recipe, self.profile())

        self.assertTrue(match["substitutionCoverageComplete"])
        self.assertEqual(
            {row["ingredientIndex"] for row in match["substitutions"]},
            {0, 1},
        )
        incomplete = match["substitutions"][:1]
        self.assertFalse(
            logic.diet_substitution_coverage(
                recipe,
                diet="vegetarian",
                substitutions=incomplete,
                violations=["diet:vegetarian"],
            )
        )

    def test_unresolved_explicit_fish_conflict_cannot_be_suggested(self):
        recipe = {
            "title": "Provider protein recipe",
            "ingredients": [
                {
                    "name": "Protein",
                    "diets": {"vegetarian": "incompatible"},
                }
            ],
        }
        match = logic.score_recipe(recipe, self.profile())

        self.assertFalse(match["safe"])
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertFalse(match["requiresSubstitutions"])
        self.assertFalse(match["substitutionCoverageComplete"])
        self.assertEqual(match["substitutions"], [])

    def test_allergy_or_avoid_violation_cannot_be_hidden_by_diet_substitution(self):
        recipe = {
            "title": "Cod with soy",
            "ingredients": [{"name": "Cod"}],
        }
        profile = self.profile()
        profile["avoid"] = ["tofu", "mushrooms", "chickpeas"]
        match = logic.score_recipe(recipe, profile)

        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertFalse(match["substitutionCoverageComplete"])

    def test_final_ranking_and_active_runtime_require_the_coverage_marker(self):
        ranking = (ROOT / "custom_components" / "cook4me" / "websocket_v13.py").read_text(encoding="utf-8")
        panel = (ROOT / "custom_components" / "cook4me" / "panel.py").read_text(encoding="utf-8")
        active = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v180.js").read_text(encoding="utf-8")

        self.assertIn('get("substitutionCoverageComplete") is not True', ranking)
        self.assertIn("runtime-v250", panel)
        self.assertIn("DietSubstitutionGuardMixin", active)


if __name__ == "__main__":
    unittest.main(verbosity=2)
