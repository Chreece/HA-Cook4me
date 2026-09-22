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

    def test_semantic_sibling_ids_cover_stock_for_any_catalog_ingredient(self):
        cases=[
            ("dairy-recipe","dairy-storage","Cultured dairy",100,400,"g"),
            ("herb-recipe","herb-storage","Fresh herb",20,60,"g"),
            ("sauce-recipe","sauce-storage","Cooking sauce",75,250,"ml"),
        ]
        for recipe_id,storage_id,name,needed,stored,unit in cases:
            with self.subTest(name=name):
                slots=[{
                    "id":"2026-09-22:dinner",
                    "date":"2026-09-22",
                    "mealType":"dinner",
                    "selected":True,
                    "recipe":{
                        "title":"Generic recipe",
                        "ingredients":[{
                            "ingredientId":recipe_id,
                            "name":name,
                            "quantity":needed,
                            "unit":unit,
                            "_testIdentities":[f"k:{recipe_id}",f"k:{storage_id}"],
                        }],
                    },
                }]
                inventory=[{
                    "key":f"product-{storage_id}",
                    "name":name,
                    "unit":unit,
                    "lots":[{
                        "id":f"lot-{storage_id}",
                        "quantity":stored,
                        "ingredientLinks":[{"key":storage_id,"name":name}],
                    }],
                }]
                requirements=self.meal.planned_requirements(slots)
                self.assertEqual(requirements[0]["identity"],f"k:{recipe_id}")
                self.assertEqual(
                    set(requirements[0]["identities"]),
                    {f"k:{recipe_id}",f"k:{storage_id}"},
                )
                status=self.meal.reservation_status(slots,inventory)
                self.assertEqual(status["shortages"],[])
                self.assertEqual(status["items"][0]["available"],stored)
                self.assertEqual(status["items"][0]["reserved"],needed)
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
        self.assertEqual(rows[0]["displayUnit"],"γρ.")

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

    def test_production_identity_matching_has_no_skyr_special_case(self):
        for filename in ("meal_lifecycle.py","inventory.py","stock_allocation.py","release_catalog.py"):
            source=(PKG/filename).read_text(encoding="utf-8").casefold()
            self.assertNotIn("skyr",source,filename)
        release=(PKG/"release_catalog.py").read_text(encoding="utf-8")
        self.assertIn("_runtimeIngredientsByConcept",release)
        self.assertIn("sourceIngredientIds",release)

    def test_shopping_keeps_raw_unit_but_formats_display_unit_in_ui_language(self):
        rows=self.shopping.shopping_rows(
            [{"identity":"k:item","name":"Ingredient","quantity":2,"unit":"tbsp"}],
            "el","DE",(),"de",
        )
        self.assertEqual(rows[0]["unit"],"tbsp")
        self.assertEqual(rows[0]["displayUnit"],"κ.σ.")
        websocket=(PKG/"websocket_v20.py").read_text(encoding="utf-8")
        catalog=(PKG/"ingredient_catalog.py").read_text(encoding="utf-8")
        self.assertIn('row.get("displayUnit") or unit',websocket)
        self.assertIn('item.get("displayUnit") or item.get("unit")',catalog)


if __name__=="__main__":
    unittest.main()
