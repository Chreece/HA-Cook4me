from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "custom_components/cook4me"


def load_search_module():
    package = types.ModuleType("cook4me_v8_test")
    package.__path__ = []
    vendor = types.ModuleType("cook4me_v8_test.vendor")
    vendor.__path__ = []
    catalog = types.ModuleType("cook4me_v8_test.vendor.cook4me_recipe_catalog")
    sys.modules["cook4me_v8_test"] = package
    sys.modules["cook4me_v8_test.vendor"] = vendor
    sys.modules["cook4me_v8_test.vendor.cook4me_recipe_catalog"] = catalog
    spec = importlib.util.spec_from_file_location(
        "cook4me_v8_test.recipe_search_v8",
        ROOT / "custom_components/cook4me/recipe_search_v8.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_recipe_hub_module():
    ha = types.ModuleType("homeassistant")
    ha_core = types.ModuleType("homeassistant.core")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_storage = types.ModuleType("homeassistant.helpers.storage")
    ha_util = types.ModuleType("homeassistant.util")
    ha_dt = types.ModuleType("homeassistant.util.dt")
    ha_core.HomeAssistant = object
    ha_dt.now = datetime.now
    ha_util.dt = ha_dt

    class Store:
        def __class_getitem__(cls, _item):
            return cls

    ha_storage.Store = Store
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.storage"] = ha_storage
    sys.modules["homeassistant.util"] = ha_util
    sys.modules["homeassistant.util.dt"] = ha_dt

    package = types.ModuleType("cook4me_hub_test")
    package.__path__ = [str(PACKAGE_DIR)]
    const = types.ModuleType("cook4me_hub_test.const")
    const.DOMAIN = "cook4me"
    logic = types.ModuleType("cook4me_hub_test.recipe_logic")
    logic.normalize_manual_recipe = lambda recipe, source="manual": dict(recipe)
    logic.normalize_text = lambda value: str(value or "").strip().casefold()
    logic.recipe_ingredient_names = lambda recipe: []
    logic.score_recipe = lambda recipe, profile: {"safe": True, "score": 0}
    sys.modules["cook4me_hub_test"] = package
    sys.modules["cook4me_hub_test.const"] = const
    sys.modules["cook4me_hub_test.recipe_logic"] = logic

    ingredient_spec = importlib.util.spec_from_file_location(
        "cook4me_hub_test.ingredient_catalog",
        ROOT / "custom_components/cook4me/ingredient_catalog.py",
    )
    ingredient_module = importlib.util.module_from_spec(ingredient_spec)
    sys.modules[ingredient_spec.name] = ingredient_module
    assert ingredient_spec.loader is not None
    ingredient_spec.loader.exec_module(ingredient_module)

    inventory_spec = importlib.util.spec_from_file_location(
        "cook4me_hub_test.inventory",
        ROOT / "custom_components/cook4me/inventory.py",
    )
    inventory_module = importlib.util.module_from_spec(inventory_spec)
    sys.modules[inventory_spec.name] = inventory_module
    assert inventory_spec.loader is not None
    inventory_spec.loader.exec_module(inventory_module)

    spec = importlib.util.spec_from_file_location(
        "cook4me_hub_test.recipe_hub",
        ROOT / "custom_components/cook4me/recipe_hub.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RecipeHubV8Tests(unittest.TestCase):
    def test_search_body_is_exact_standalone_proven_cookeo_contract(self):
        module = load_search_module()
        body = module.app_search_body("DE-de", "gs_de")
        self.assertEqual(module.SEARCH_CONTRACT, "standalone-proven-cookeo-brand-v5")
        self.assertEqual(
            body,
            {
                "fieldFilters": [
                    {"field": "lang.key", "values": ["de-de"]},
                    {"field": "market.key", "values": ["GS_DE"]},
                    {
                        "field": "applianceGroups.reference.key",
                        "values": ["APPLIANCE_GROUP_15"],
                    },
                    {"field": "topRecipe.type.key", "values": ["BRAND"]},
                ]
            },
        )
        serialized = str(body)
        self.assertNotIn("fieldList", serialized)
        self.assertNotIn("FOOD_COOKING", serialized)
        self.assertNotIn("privacyLevel", serialized)
        self.assertNotIn("id.sourceSystem", serialized)

    def test_ui_preferences_remember_global_and_per_recipe_selections(self):
        module = load_recipe_hub_module()
        normalized = module.Cook4MeRecipeHub._normalize_ui_preferences(
            {
                "catalogLanguage": "DE-de",
                "translateResults": False,
                "lastTab": "recommend",
                "nutritionGoal": "high_protein",
                "recipeLanguageSelections": {"g:500": "it"},
                "recipeServingSelections": {"g:500": "6"},
            }
        )
        self.assertEqual(normalized["catalogLanguage"], "de")
        self.assertFalse(normalized["translateResults"])
        self.assertEqual(normalized["lastTab"], "recommend")
        self.assertEqual(normalized["nutritionGoal"], "high_protein")
        self.assertEqual(normalized["recipeLanguageSelections"], {"g:500": "it"})
        self.assertEqual(normalized["recipeServingSelections"], {"g:500": "6"})

    def test_shopping_tab_is_a_persistable_recipe_hub_tab(self):
        module = load_recipe_hub_module()
        normalized = module.Cook4MeRecipeHub._normalize_ui_preferences(
            {"lastTab": "shopping"}
        )
        self.assertEqual(normalized["lastTab"], "shopping")

    def test_old_pantry_migrates_to_structured_house_inventory(self):
        module = load_recipe_hub_module()
        normalized = module.Cook4MeRecipeHub._normalize_profile(
            {"diet": "vegetarian", "pantry": ["Tomate", "Reis"]}
        )
        self.assertEqual(
            normalized["houseIngredients"],
            [{"name": "Tomate"}, {"name": "Reis"}],
        )
        self.assertEqual(normalized["pantry"], ["Tomate", "Reis"])

    def test_house_inventory_preserves_stable_food_keys(self):
        module = load_recipe_hub_module()
        normalized = module.Cook4MeRecipeHub._normalize_profile(
            {
                "houseIngredients": [
                    {"key": "M_FOOD_123", "name": "Fenchel"},
                    {"key": "M_FOOD_123", "name": "fenouil"},
                ]
            }
        )
        self.assertEqual(
            normalized["houseIngredients"],
            [{"key": "M_FOOD_123", "name": "Fenchel"}],
        )

    def test_house_inventory_preserves_quantity_unit_and_unlimited(self):
        module = load_recipe_hub_module()
        normalized = module.Cook4MeRecipeHub._normalize_profile(
            {
                "houseIngredients": [
                    {"key": "M_FOOD_1", "name": "Rice", "quantity": 750, "unit": "g"},
                    {"key": "M_FOOD_2", "name": "Water", "unlimited": True, "unit": "l"},
                ]
            }
        )
        self.assertEqual(normalized["houseIngredients"][0]["quantity"], 750)
        self.assertEqual(normalized["houseIngredients"][0]["unit"], "g")
        self.assertTrue(normalized["houseIngredients"][1]["unlimited"])

    def test_household_members_are_normalized_and_deduped(self):
        module = load_recipe_hub_module()
        normalized = module.Cook4MeRecipeHub._normalize_profile(
            {"householdMembers": ["Chris", "Alex", "Chris"]}
        )
        self.assertEqual(normalized["householdMembers"], ["Chris", "Alex"])


if __name__ == "__main__":
    unittest.main()
