"""Ingredient-complete dietary checks and advisory substitutions."""
from copy import deepcopy
import unittest
from test_recipe_logic import logic
import test_runtime_audit_v74 as runtime
import importlib
from unittest.mock import AsyncMock


class DietSubstitutionTests(unittest.TestCase):
    def check(self, ingredients, **profile):
        return logic.score_recipe({"ingredients": ingredients}, {"diet": "vegetarian", **profile})

    def test_missed_animal_foods_are_never_vegetarian(self):
        for name in ("Duck breast", "Veal stock", "Squid", "Anchovies", "Octopus", "Cod", "Trout", "Crab", "Scallops", "Lard", "Gelatin", "Bonito flakes", "Worcestershire sauce", "Chicken breasts"):
            with self.subTest(name=name):
                self.assertFalse(self.check([{"canonicalName": name, "name": "source label"}])["safe"])

    def test_every_conflicting_ingredient_gets_its_own_replacement(self):
        ingredients = [{"name": "Duck breast"}, {"name": "Prawns"}, {"name": "Chicken stock"}, {"name": "rice"}]
        before = deepcopy(ingredients)
        result = self.check(ingredients)
        self.assertFalse(result["safe"], "The original recipe remains incompatible")
        self.assertTrue(result["eligibleWithSubstitutions"])
        self.assertEqual([x["ingredientIndex"] for x in result["substitutions"]], [0, 1, 2])
        self.assertTrue(all(x["replacement"]["name"] for x in result["substitutions"]))
        self.assertEqual(ingredients, before)

    def test_incomplete_substitutions_and_recipe_level_conflicts_are_blocked(self):
        for recipe in ({"ingredients": [{"name": "Duck"}, {"name": "Gelatin"}]},
                       {"ingredients": [{"name": "Rice"}], "excludedFoods": ["MEAT"]},
                       {"ingredients": ["Duck"], "excludedFoods": ["GELATIN"]},
                       {"ingredients": ["Duck", {"name": "Unknown product", "diets": {"vegetarian": "incompatible"}}]},
                       {"ingredients": ["Duck", {"name": ""}]},
                       {"ingredients": []}):
            with self.subTest(recipe=recipe):
                result = logic.score_recipe(recipe, {"diet": "vegetarian"})
                self.assertFalse(result["safe"])
                self.assertFalse(result["eligibleWithSubstitutions"])

    def test_allergy_and_avoid_restrictions_cannot_be_waived(self):
        result = self.check(["duck", "shrimp"], allergies=["shellfish"])
        self.assertFalse(result["eligibleWithSubstitutions"])
        result = self.check(["duck"], allergies=["soy"], avoid=["mushroom", "chickpeas"])
        self.assertFalse(result["eligibleWithSubstitutions"])

    def test_no_cross_ingredient_phrases_and_food_name_is_checked(self):
        self.assertFalse(self.check([{"foodName": "Veal"}])["safe"])
        self.assertFalse(self.check(["coconut", "milk"], diet="vegan")["safe"])
        self.assertTrue(self.check(["coconut milk", "rice"], diet="vegan")["safe"])
        self.assertFalse(self.check(["coconut milk with chicken"], diet="vegan")["safe"])

    def test_vegan_requires_replacement_for_eggs_and_dairy_too(self):
        result = self.check(["prawns", "cream", "butter", "rice"], diet="vegan")
        self.assertTrue(result["eligibleWithSubstitutions"])
        self.assertEqual(len(result["substitutions"]), 3)
        self.assertFalse(result["safe"])
        self.assertTrue(self.check(["cream", "eggs"])["safe"])

    def test_pescatarian_allows_fish_but_not_meat(self):
        self.assertTrue(self.check(["cod", "prawns"], diet="pescatarian")["safe"])
        result = self.check(["duck", "cod"], diet="pescatarian")
        self.assertEqual([x["ingredientIndex"] for x in result["substitutions"]], [0])

    def test_plant_food_compounds_and_goat_cheese_are_not_meat(self):
        for name in ("Red kidney beans", "Butter beans", "Oyster mushrooms", "Lamb's lettuce"):
            self.assertTrue(self.check([name], diet="vegan")["safe"], name)
        self.assertTrue(self.check(["Goat cheese"])["safe"])
        self.assertFalse(self.check(["Goat cheese"], diet="vegan")["safe"])
        self.assertFalse(self.check(["Kidney beans with pork"])["safe"])

    def test_fake_client_substitutions_cannot_make_recipe_eligible(self):
        result = logic.score_recipe({"ingredients": ["gelatin"], "match": {"safe": True},
            "substitutions": [{"ingredientIndex": 0, "replacement": {"name": "rice"}}]}, {"diet": "vegetarian"})
        self.assertFalse(result["eligibleWithSubstitutions"])


class RuntimeDietTests(unittest.IsolatedAsyncioTestCase):
    setUp = runtime.AuditTests.setUp
    asyncTearDown = runtime.AuditTests.asyncTearDown

    async def test_original_cloud_recipe_can_send_with_complete_suggestions(self):
        self.bridge.recipe_hub._data["profile"]["diet"] = "vegetarian"
        self.bridge.data = {"connected": True}
        meta = {"title": "Duck and prawns", "groupingFunctionalId": "g", "recipeFunctionalId": "r", "ingredients": ["duck", "prawns"]}
        self.bridge.async_recipe_detail = AsyncMock(return_value=meta)
        self.bridge._run_client_json = AsyncMock()
        result = await self.bridge.async_send_variant("r")
        self.assertFalse(result["recipe"]["match"]["safe"])
        self.assertTrue(result["recipe"]["match"]["eligibleWithSubstitutions"])
        self.bridge._run_client_json.assert_awaited_once_with("send-recipe", "g", "r", timeout=45)

    async def test_selected_diet_and_cache_preserve_original_and_all_substitutions(self):
        recipe = {"title": "Duck and prawns", "ingredients": ["duck", "prawns"]}
        hub = self.bridge.recipe_hub
        self.assertTrue(hub.annotate(recipe)["match"]["safe"])
        checked = hub.annotate(recipe, diet="vegetarian")
        self.assertFalse(checked["match"]["safe"])
        self.assertTrue(checked["match"]["eligibleWithSubstitutions"])
        self.assertEqual(hub.profile["diet"], "omnivore")
        module = importlib.import_module(runtime.PREFIX + ".today_plan_store")
        compact = module.compact_today_recipe(checked)
        self.assertNotIn("ingredients", compact)
        for key in ("safe", "diet", "dietCheckVersion", "substitutions", "eligibleWithSubstitutions"):
            self.assertEqual(compact["match"][key], checked["match"][key])
        self.assertEqual(module.compact_today_recipe(compact), compact)

    async def test_unresolved_recipe_cannot_reserve_or_purchase_original_meat(self):
        module = importlib.import_module(runtime.PREFIX + ".meal_lifecycle")
        recipe = self.bridge.recipe_hub.annotate({"title": "Duck", "ingredients": [
            {"name": "duck", "quantity": 400, "unit": "g"}, {"name": "rice", "quantity": 100, "unit": "g"}]}, diet="vegetarian")
        slots = [{"id": "one", "date": "2026-09-16", "mealType": "dinner", "recipe": recipe}]
        self.assertEqual(module.planned_requirements(slots), [])
        self.assertEqual(module.shopping_delta(slots, []), [])


if __name__ == "__main__":
    unittest.main()
