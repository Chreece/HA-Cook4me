"""v218 stock/storage and nutrient-review regressions."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/"custom_components"/"cook4me"
FRONTEND=COMPONENT/"frontend"

def load_file(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

inventory=load_file("cook4me_inventory_v218",COMPONENT/"inventory.py")
locations=load_file("cook4me_locations_v218",COMPONENT/"storage_locations.py")

PKG="cook4me_resolution_v218"
package=ModuleType(PKG);package.__path__=[str(COMPONENT)];sys.modules[PKG]=package
def load_resolution():
    path=COMPONENT/"nutrition_resolution.py"
    tree=ast.parse(path.read_text())
    tree.body=[node for node in tree.body if not (
        isinstance(node,ast.ImportFrom)
        and ((node.module or "").startswith("homeassistant") or node.module=="const")
    )]
    module=ModuleType(PKG+".nutrition_resolution")
    module.__package__=PKG;module.__file__=str(path);module.DOMAIN="cook4me";module.HomeAssistant=object;module.Store=object
    sys.modules[module.__name__]=module
    exec(compile(tree,str(path),"exec"),module.__dict__)
    return module
resolution=load_resolution()

class Storage:
    async def async_save(self,_data): pass

class UnlimitedStockTests(unittest.TestCase):
    def test_unlimited_item_keeps_location_product_and_catalog_links(self):
        rows=inventory.add_inventory_item(
            [],
            {"key":"salt","name":"Salt"},
            unlimited=True,
            lot_metadata={
                "storage":"pantry",
                "storageLocationId":"spices",
                "productName":"Sea salt",
                "brand":"Test",
                "ingredientLinks":[
                    {"key":"salt","name":"Salt"},
                    {"key":"sea-salt","name":"Sea salt"},
                ],
            },
        )
        self.assertEqual(len(rows),1)
        row=rows[0]
        self.assertTrue(row["unlimited"])
        self.assertEqual(row["storageLocationId"],"spices")
        self.assertEqual(row["storage"],"pantry")
        self.assertEqual(row["productName"],"Sea salt")
        self.assertEqual({x["key"] for x in row["ingredientLinks"]},{"salt","sea-salt"})
        self.assertNotIn("lots",row)
        self.assertNotIn("quantity",row)
        self.assertEqual(inventory.normalize_inventory(rows),rows)

    def test_unlimited_product_matches_every_reviewed_catalog_link(self):
        rows=inventory.add_inventory_item(
            [],
            {"key":"salt","name":"Salt"},
            unlimited=True,
            lot_metadata={
                "storageLocationId":"spices",
                "storage":"pantry",
                "ingredientLinks":[{"key":"fine-salt","name":"Fine salt"}],
            },
        )
        found=inventory.stock_for_ingredient(rows,{"key":"fine-salt","name":"Fine salt"})
        self.assertIsNotNone(found)
        self.assertTrue(found["unlimited"])
        self.assertEqual(found["storageLocationId"],"spices")

    def test_existing_unlimited_item_merges_new_reviewed_catalog_links(self):
        rows=inventory.add_inventory_item(
            [{
                "key":"salt","name":"Salt","unlimited":True,
                "storageLocationId":"spices","storage":"pantry",
                "ingredientLinks":[{"key":"salt","name":"Salt"}],
            }],
            {"key":"salt","name":"Salt"},
            unlimited=True,
            lot_metadata={
                "storageLocationId":"spices",
                "storage":"pantry",
                "ingredientLinks":[{"key":"sea-salt","name":"Sea salt"}],
            },
        )
        self.assertEqual(
            {link["key"] for link in rows[0]["ingredientLinks"]},
            {"salt","sea-salt"},
        )
        found=inventory.stock_for_ingredient(
            rows,{"key":"sea-salt","name":"Sea salt"}
        )
        self.assertIsNotNone(found)
        self.assertTrue(found["unlimited"])

    def test_storage_place_cannot_be_deleted_while_unlimited_stock_uses_it(self):
        profile={
            "storageLocations":[{"id":"spices","name":"Spice shelf","kind":"shelf"}],
            "houseIngredients":[{
                "key":"salt","name":"Salt","unlimited":True,
                "storageLocationId":"spices","storage":"shelf",
            }],
        }
        with self.assertRaisesRegex(ValueError,"Move the stock"):
            locations.edit_location(profile,action="delete",identity="spices")

    def test_renaming_unlimited_storage_place_updates_storage_kind(self):
        profile={
            "storageLocations":[{"id":"spices","name":"Spice shelf","kind":"shelf"}],
            "houseIngredients":[{
                "key":"pepper","name":"Pepper","unlimited":True,
                "storageLocationId":"spices","storage":"shelf",
            }],
        }
        updated=locations.edit_location(
            profile,action="save",identity="spices",name="Spice drawer",kind="drawer"
        )
        self.assertEqual(updated["houseIngredients"][0]["storageLocationId"],"spices")
        self.assertEqual(updated["houseIngredients"][0]["storage"],"drawer")

    def test_scanner_unlimited_path_passes_reviewed_metadata(self):
        source=(COMPONENT/"recipe_hub.py").read_text()
        block=source[source.index("if unlimited:",source.index("async def async_scanner_add")):]
        self.assertIn("unlimited=True, best_before=best_before, lot_metadata=metadata",block[:3000])


class ResolutionRowsTests(unittest.TestCase):
    def _store(self,failures):
        store=resolution.Cook4MeNutritionResolutionStore.__new__(
            resolution.Cook4MeNutritionResolutionStore
        )
        store.hass=object();store.entry_id="entry";store._loaded=True
        store._data={"failures":deepcopy(failures)};store._store=Storage();store._lock=asyncio.Lock()
        return store

    def test_active_rows_exposes_reviewable_failure_details(self):
        store=self._store({
            "k:salt":{
                "identity":"k:salt","query":"salt","mode":"demo","reason":"ambiguous",
                "attemptedAt":"2026-09-24T08:00:00+00:00",
                "retryAt":"2026-10-24T08:00:00+00:00","confidence":0.92,
            },
            "k:expired":{
                "identity":"k:expired","query":"old","mode":"demo","reason":"TimeoutError",
                "attemptedAt":"2026-09-23T08:00:00+00:00",
                "retryAt":"2026-09-23T09:00:00+00:00",
            },
        })
        rows=store.active_rows(
            {"k:salt","k:expired"},mode="demo",
            now=datetime(2026,9,24,9,tzinfo=timezone.utc),
        )
        self.assertEqual([row["identity"] for row in rows],["k:salt"])
        self.assertEqual(rows[0]["reason"],"ambiguous")

    def test_custom_mode_still_shows_semantic_ambiguity(self):
        store=self._store({
            "k:salt":{
                "identity":"k:salt","query":"salt","mode":"demo","reason":"ambiguous",
                "attemptedAt":"2026-09-24T08:00:00+00:00",
                "retryAt":"2026-10-24T08:00:00+00:00",
            },
        })
        rows=store.active_rows(
            {"k:salt"},mode="custom",
            now=datetime(2026,9,24,9,tzinfo=timezone.utc),
        )
        self.assertEqual(len(rows),1)


class WiringTests(unittest.TestCase):
    def test_nutrition_routes_include_retry_and_manual_resolution(self):
        source=(COMPONENT/"websocket_v16.py").read_text()
        self.assertIn('cook4me/v16/nutrition_unresolved_retry',source)
        self.assertIn('cook4me/v16/nutrition_generic_set',source)
        self.assertIn('"unresolvedDetails"',source)
        self.assertIn('"genericFallbackCatalog": True',source)

    def test_v218_runtime_and_ui_mixin_are_active(self):
        panel=(COMPONENT/"panel.py").read_text()
        active=(FRONTEND/"cook4me-panel-v180.js").read_text()
        ux=(FRONTEND/"ux-fixes-v218.js").read_text()
        self.assertIn("/runtime-v225",panel)
        self.assertIn("&runtime=225",panel)
        self.assertIn("UXFixesMixin",active)
        self.assertIn("runtime-v225",active)
        self.assertIn("nutrition_unresolved_retry",ux)
        self.assertIn("nutrition_generic_set",ux)

    def test_more_no_longer_moves_to_full_new_row(self):
        css=(FRONTEND/"app-theme-v203.js").read_text()
        self.assertNotIn("details.ui203-more[open]{flex-basis:100%}",css)
        self.assertIn("details.ui203-more[open]{flex-basis:190px",css)

    def test_container_has_explicit_unuse_state(self):
        ui=(FRONTEND/"cook4me-panel-v117.js").read_text()
        bundle=(FRONTEND/"cook4me-panel-v126-bundle.js").read_text()
        for source in (ui,bundle):
            self.assertIn("unuse:'Unuse'",source)
            self.assertIn("unuse:'Ακύρωση χρήσης'",source)
            self.assertIn("active?'unused':'using'",source)

    def test_active_bundle_has_clarified_nutrition_fallback_labels(self):
        bundle=(FRONTEND/"cook4me-panel-v126-bundle.js").read_text()
        self.assertIn('nutritionSettings:"USDA fallback nutrition"',bundle)
        self.assertIn('cachedUnresolved:"USDA matches needing review"',bundle)

if __name__=="__main__":
    unittest.main()
