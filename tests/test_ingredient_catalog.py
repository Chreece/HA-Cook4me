from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
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

    package = types.ModuleType("cook4me_ingredient_test")
    package.__path__ = []
    const = types.ModuleType("cook4me_ingredient_test.const")
    const.DOMAIN = "cook4me"
    sys.modules["cook4me_ingredient_test"] = package
    sys.modules["cook4me_ingredient_test.const"] = const

    spec = importlib.util.spec_from_file_location(
        "cook4me_ingredient_test.ingredient_catalog",
        ROOT / "custom_components/cook4me/ingredient_catalog.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class IngredientCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_canonical_food_name_wins_over_recipe_amount(self):
        self.assertEqual(
            self.module.catalog_ingredient_name(
                {
                    "foodName": "Kartoffeln",
                    "applicationDescription": "200 g Kartoffeln, gewürfelt",
                    "quantity": 200.0,
                    "unit": "g",
                }
            ),
            "Kartoffeln",
        )

    def test_structured_amount_cleanup_is_language_independent(self):
        cases = [
            ({"name": "200 g Kartoffeln", "quantity": 200.0, "unit": "g"}, "Kartoffeln"),
            ({"name": "2 c. à soupe huile d'olive", "quantity": 2, "unit": "c. à soupe"}, "huile d'olive"),
            ({"name": "1,5 kg patatas", "quantity": 1.5, "unit": "kg"}, "patatas"),
            ({"name": "٢ مل زيت", "quantity": 2, "unit": "مل"}, "زيت"),
            ({"name": "2 大さじ しょうゆ", "quantity": 2, "unit": "大さじ"}, "しょうゆ"),
            ({"name": "½ TL Salz", "quantity": 0.5, "unit": "TL"}, "Salz"),
            ({"name": "2 Eier", "quantity": 2}, "Eier"),
        ]
        for item, expected in cases:
            with self.subTest(item=item):
                self.assertEqual(self.module.catalog_ingredient_name(item), expected)

    def test_recipe_catalog_dedupes_after_amount_cleanup(self):
        recipes = [
            {
                "ingredients": [
                    {
                        "foodKey": "M_FOOD_1",
                        "name": "200 g Kartoffeln",
                        "quantity": 200,
                        "unit": "g",
                    },
                    {
                        "foodKey": "M_FOOD_1",
                        "name": "500 g Kartoffeln",
                        "quantity": 500,
                        "unit": "g",
                    },
                ]
            }
        ]
        self.assertEqual(
            self.module.catalog_items_from_recipes(recipes),
            [{"key": "M_FOOD_1", "name": "Kartoffeln"}],
        )

    def test_free_text_fallback_removes_unicode_numeric_amount(self):
        self.assertEqual(self.module.catalog_ingredient_name("٣ طماطم"), "طماطم")
        self.assertEqual(self.module.catalog_ingredient_name("3 tomates"), "tomates")

    def test_unicode_normalization_keeps_non_latin_food_names(self):
        self.assertEqual(self.module._norm("زيت"), "زيت")
        self.assertEqual(self.module._norm("しょうゆ"), "しょうゆ")
        self.assertEqual(self.module._norm("Żółta papryka"), "zołta papryka")

    def test_recipe_fallback_rejects_keyless_recipe_prose(self):
        recipes = [
            {
                "ingredients": [
                    {"name": "Runde Backform, mit Backpapier ausgelegt, 13 cm"},
                    {"applianceDescription": "Backpapier"},
                    {"name": "Förmchen aus Porzellan, 150 ml"},
                    {"name": "Hübsche Schälchen oder kleine tiefe Teller"},
                    {"foodName": "Salz", "name": "Salz und Pfeffer, zum Würzen"},
                ]
            }
        ]
        self.assertEqual(
            self.module.catalog_items_from_recipes(recipes),
            [{"name": "Salz"}],
        )

    def test_same_food_identity_collapses_preparation_prose(self):
        recipes = [
            {
                "ingredients": [
                    {"foodKey": "M_FOOD_10", "name": "Lachsfilet (à 100 g)"},
                    {"foodKey": "M_FOOD_10", "name": "Lachsfilet"},
                    {"foodKey": "M_FOOD_11", "name": "Mungobohnen, bereits 12 Stunden eingeweicht"},
                    {"foodKey": "M_FOOD_12", "name": "Crème Double, über den Butter-Schoko-Mix gegeben"},
                    {"foodKey": "M_FOOD_13", "name": "Salatköpfe, gewaschen und Außenblätter entfernt"},
                    {"foodKey": "M_FOOD_14", "name": "Weiße Fischfilets (400 g) (z.B. Lotte oder Kabeljau)"},
                ]
            }
        ]
        self.assertEqual(
            self.module.catalog_items_from_recipes(recipes),
            [
                {"key": "M_FOOD_12", "name": "Crème Double"},
                {"key": "M_FOOD_10", "name": "Lachsfilet"},
                {"key": "M_FOOD_11", "name": "Mungobohnen"},
                {"key": "M_FOOD_13", "name": "Salatköpfe"},
                {"key": "M_FOOD_14", "name": "Weiße Fischfilets"},
            ],
        )

    def test_final_catalog_dedupes_same_clean_name_across_different_keys(self):
        rows = self.module._clean_catalog_rows(
            [
                {"key": "M_FOOD_A", "name": "Olivenöl"},
                {"key": "M_FOOD_B", "name": "Olivenöl"},
                {"name": "Olivenöl"},
            ]
        )
        self.assertEqual(rows, [{"key": "M_FOOD_A", "name": "Olivenöl"}])


if __name__ == "__main__":
    unittest.main()
