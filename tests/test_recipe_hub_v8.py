from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


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
    # recipe_hub's normalization functions do not need a real HA runtime.
    ha = types.ModuleType("homeassistant")
    ha_core = types.ModuleType("homeassistant.core")
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_storage = types.ModuleType("homeassistant.helpers.storage")
    ha_core.HomeAssistant = object

    class Store:
        def __class_getitem__(cls, _item):
            return cls

    ha_storage.Store = Store
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.storage"] = ha_storage

    package = types.ModuleType("cook4me_hub_test")
    package.__path__ = []
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
    def test_apk_search_body_repeats_language_market_constraints(self):
        module = load_search_module()
        body = module.app_search_body("de", "GS_DE")
        filters = {row["field"]: row for row in body["fieldFilters"]}
        self.assertEqual(filters["lang.key"]["values"], ["de"])
        self.assertEqual(filters["market.key"]["values"], ["GS_DE"])
        self.assertEqual(filters["id.sourceSystem.key"]["values"], ["PRO"])
        self.assertEqual(filters["privacyLevel.key"]["values"], ["COMMUNITY", "PUBLIC"])
        self.assertEqual(
            filters["classifications.key_FOOD_COOKING"]["values"],
            ["IS_FOOD_COOKING"],
        )
        self.assertEqual(filters["classifications.key_FOOD_COOKING"]["type"], "inclusion")
        self.assertIn("resourceMedias", body["fieldList"])
        self.assertIn("title", body["fieldList"])
        self.assertIn("yield.quantity", body["fieldList"])

    def test_ui_preferences_remember_global_and_per_recipe_selections(self):
        module = load_recipe_hub_module()
        normalized = module.Cook4MeRecipeHub._normalize_ui_preferences(
            {
                "catalogLanguage": "DE-de",
                "translateResults": False,
                "lastTab": "recommend",
                "recipeLanguageSelections": {"g:500": "it"},
                "recipeServingSelections": {"g:500": "6"},
            }
        )
        self.assertEqual(normalized["catalogLanguage"], "de")
        self.assertFalse(normalized["translateResults"])
        self.assertEqual(normalized["lastTab"], "recommend")
        self.assertEqual(normalized["recipeLanguageSelections"], {"g:500": "it"})
        self.assertEqual(normalized["recipeServingSelections"], {"g:500": "6"})


if __name__ == "__main__":
    unittest.main()
