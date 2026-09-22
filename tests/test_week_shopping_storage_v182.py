from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/"custom_components"/"cook4me"


def load_modules():
    package=types.ModuleType("cook4me_week_shopping_v182")
    package.__path__=[str(PKG)]
    sys.modules[package.__name__]=package

    ha=types.ModuleType("homeassistant")
    ha_core=types.ModuleType("homeassistant.core")
    ha_helpers=types.ModuleType("homeassistant.helpers")
    ha_storage=types.ModuleType("homeassistant.helpers.storage")
    ha_core.HomeAssistant=object
    class Store:
        def __init__(self,*_args,**_kwargs): pass
        def __class_getitem__(cls,_item): return cls
    ha_storage.Store=Store
    sys.modules["homeassistant"]=ha
    sys.modules["homeassistant.core"]=ha_core
    sys.modules["homeassistant.helpers"]=ha_helpers
    sys.modules["homeassistant.helpers.storage"]=ha_storage

    today=types.ModuleType(f"{package.__name__}.today_logic")
    today.recipe_identity=lambda recipe: str((recipe or {}).get("id") or "")
    sys.modules[today.__name__]=today

    recipe_languages=types.ModuleType(f"{package.__name__}.recipe_languages")
    recipe_languages.language_options=lambda:[{"code":code} for code in ("de","el","en","fr")]
    sys.modules[recipe_languages.__name__]=recipe_languages

    release=types.ModuleType(f"{package.__name__}.release_catalog")
    def identities(raw):
        values=raw.get("_testIdentities") if isinstance(raw,dict) else None
        if values:
            return tuple(values)
        key=str((raw or {}).get("key") or (raw or {}).get("foodKey") or (raw or {}).get("ingredientId") or (raw or {}).get("id") or "")
        return (f"k:{key}",) if key else ()
    release.ingredient_stock_identities=identities
    def display_name(item,language):
        key=str((item or {}).get("key") or (item or {}).get("foodKey") or "")
        if key in {"skyr-recipe","skyr-storage"}:
            return {"el":"Σκάιρ","de":"Skyr Natur","en":"Skyr"}.get(language,"Skyr")
        return str((item or {}).get("name") or "")
    release.ingredient_display_name=display_name
    sys.modules[release.__name__]=release

    def load(name):
        spec=importlib.util.spec_from_file_location(
            f"{package.__name__}.{name}",PKG/f"{name}.py"
        )
        module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    inventory=load("inventory")
    stock_allocation=load("stock_allocation")
    meal=load("meal_lifecycle")
    shopping=load("shopping_presentation")
    return inventory,stock_allocation,meal,shopping


class WeekShoppingStorageV182Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory,cls.allocation,cls.meal,cls.shopping=load_modules()

    def test_recipe_ingredient_id_matches_scanned_lot_semantic_sibling(self):
        slots=[{
            "id":"2026-09-22:breakfast",
            "date":"2026-09-22",
            "mealType":"breakfast",
            "selected":True,
            "recipe":{
                "title":"Skyr breakfast",
                "ingredients":[{
                    "ingredientId":"skyr-recipe",
                    "name":"Skyr",
                    "quantity":100,
                    "unit":"g",
                    "_testIdentities":["k:skyr-recipe","k:skyr-storage"],
                }],
            },
        }]
        inventory=[{
            "key":"product-skyr-natur",
            "name":"Skyr Natur",
            "unit":"g",
            "lots":[{
                "id":"lot-skyr",
                "quantity":400,
                "ingredientLinks":[{"key":"skyr-storage","name":"Skyr Natur"}],
            }],
        }]
        requirements=self.meal.planned_requirements(slots)
        self.assertEqual(requirements[0]["identity"],"k:skyr-recipe")
        self.assertEqual(
            set(requirements[0]["identities"]),
            {"k:skyr-recipe","k:skyr-storage"},
        )
        status=self.meal.reservation_status(slots,inventory)
        self.assertEqual(status["shortages"],[])
        self.assertEqual(status["items"][0]["available"],100)
        self.assertEqual(self.meal.shopping_delta(slots,inventory),[])

    def test_ingredient_id_is_not_dropped_to_name_identity(self):
        row=self.meal._ingredient({
            "ingredientId":"provider-skyr-id",
            "name":"Skyr",
            "quantity":100,
            "unit":"g",
        })
        self.assertEqual(row["key"],"provider-skyr-id")
        self.assertEqual(self.inventory.inventory_identity(row),"k:provider-skyr-id")

    def test_ui_market_original_shopping_name_order(self):
        rows=self.shopping.shopping_rows(
            [{"identity":"k:skyr-recipe","name":"Skyr","quantity":100,"unit":"g"}],
            "el",
            "DE",
            (),
            "de",
        )
        self.assertEqual(rows[0]["name"],"Σκάιρ (Skyr Natur; Skyr)")
        self.assertEqual(rows[0]["shoppingDisplayName"],rows[0]["name"])
        self.assertEqual(rows[0]["uiLanguage"],"el")
        self.assertEqual(rows[0]["supermarketLanguage"],"de")
        self.assertEqual(rows[0]["quantity"],100)
        self.assertEqual(rows[0]["unit"],"g")

    def test_week_api_accepts_explicit_display_and_supermarket_languages(self):
        source=(PKG/"websocket_v20.py").read_text(encoding="utf-8")
        self.assertIn('vol.Optional("display_language"): str',source)
        self.assertIn('vol.Optional("supermarket_language"): str',source)
        self.assertIn('msg.get("display_language") or msg.get("ui_language")',source)
        self.assertIn('state["shoppingDelta"] = await hass.async_add_executor_job(',source)

    def test_main_shopping_api_uses_same_language_contract(self):
        source=(PKG/"websocket_v11.py").read_text(encoding="utf-8")
        self.assertIn('vol.Optional("display_language"): str',source)
        self.assertIn('vol.Optional("supermarket_language"): str',source)
        self.assertIn('msg.get("display_language") or msg.get("ui_language")',source)


if __name__=="__main__":
    unittest.main()
