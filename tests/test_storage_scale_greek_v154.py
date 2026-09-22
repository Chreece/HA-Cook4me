from pathlib import Path
import importlib.util
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


def load_module(name, relative):
    path=ROOT/"custom_components"/"cook4me"/relative
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class StorageScaleGreekV154Tests(unittest.TestCase):
    def test_v154_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v154.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v174",panel)
        self.assertIn("cook4me-panel-v174.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.1",panel)
        self.assertIn("?v=2026.9.22.1",panel)
        self.assertIn('"version": "2026.9.22.1"',manifest)
        self.assertIn("cook4me-panel-v153.js?v=2026.9.21.18",ui)

    def test_storage_kinds_include_real_kitchen_locations(self):
        storage=load_module("cook4me_storage_locations_v154_test","storage_locations.py")
        expected={"fridge","freezer","pantry","cupboard","shelf","drawer","countertop","cellar","other"}
        self.assertEqual(storage.KINDS,expected)
        rows=storage.normalize_locations([
            {"id":"counter","name":"Kitchen counter","kind":"countertop"},
            {"id":"drawer1","name":"Spice drawer","kind":"drawer"},
        ])
        self.assertEqual([row["kind"] for row in rows],["countertop","drawer"])

    def test_container_id_is_exact_lot_metadata(self):
        inventory=load_module("cook4me_inventory_v154_test","inventory.py")
        rows=inventory.add_inventory_item(
            [],
            {"key":"rice","name":"Rice"},
            quantity=350,
            unit="g",
            lot_metadata={
                "storage":"countertop",
                "storageLocationId":"counter",
                "containerId":"bowl-1",
                "productName":"Rice jar",
            },
        )
        self.assertEqual(len(rows),1)
        lot=rows[0]["lots"][0]
        self.assertEqual(lot["storage"],"countertop")
        self.assertEqual(lot["storageLocationId"],"counter")
        self.assertEqual(lot["containerId"],"bowl-1")
        self.assertNotIn("containerId",rows[0])

    def test_storage_ui_counts_and_edits_exact_items(self):
        ui=(FRONTEND/"cook4me-panel-v154.js").read_text(encoding="utf-8")
        self.assertIn("_v154PlaceItems(locationId)",ui)
        self.assertIn("lot?.storageLocationId",ui)
        self.assertIn("v154-place-count",ui)
        self.assertIn("editItems:'Edit items'",ui)
        self.assertIn("data-v154-edit-lot",ui)
        self.assertIn("this._v112EditLot(button.dataset.v154EditLot)",ui)
        for kind in ("cupboard","shelf","drawer","countertop","cellar"):
            self.assertIn(f"['{kind}'",ui)
        self.assertIn("Πάγκος κουζίνας",ui)

    def test_product_editor_reuses_smart_scale_container_store(self):
        ui=(FRONTEND/"cook4me-panel-v154.js").read_text(encoding="utf-8")
        base=(FRONTEND/"cook4me-panel-v78.js").read_text(encoding="utf-8")
        backend=(ROOT/"custom_components"/"cook4me"/"websocket_v33.py").read_text(encoding="utf-8")
        inventory=(ROOT/"custom_components"/"cook4me"/"inventory.py").read_text(encoding="utf-8")
        self.assertIn("this._v116Scale?.containers||[]",ui)
        self.assertIn("containerId:'',deductContainer:false",ui)
        self.assertIn("data-v154-container",ui)
        self.assertIn("data-v154-deduct",ui)
        self.assertIn("'containerId'",base)
        self.assertIn('"containerId"',backend)
        self.assertIn("smart_scale_store_for_bridge",backend)
        self.assertIn('"containerId"',inventory)

    def test_weighing_can_optionally_deduct_saved_container(self):
        ui=(FRONTEND/"cook4me-panel-v154.js").read_text(encoding="utf-8")
        self.assertIn("_v154ApplyContainerTare",ui)
        self.assertIn("tareGrams",ui)
        self.assertIn("_v116UseDraftWeight()",ui)
        self.assertIn("_v154OpenWeigh(row,lotId)",ui)
        self.assertIn("Deduct container from weight",ui)
        self.assertIn("Αφαίρεση βάρους δοχείου",ui)
        self.assertIn("cook4me/v37/inventory_reweigh",ui)

    def test_ninth_greek_audit_market_names(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        labels=data["labels"]
        expected={
            "aburaage":"Aburaage (λεπτό τηγανητό τόφου)",
            "shiso leaf":"Φύλλο shiso",
            "gochugaru":"Gochugaru (κορεάτικο τσίλι)",
            "konjac noodle":"Shirataki / konjac noodles",
            "shichimi togarashi":"Shichimi togarashi (ιαπωνικό μείγμα 7 μπαχαρικών)",
            "ichimi chili pepper":"Ichimi togarashi (ιαπωνικό τσίλι)",
            "sansho pepper":"Sansho (ιαπωνικό πιπέρι)",
            "yuzu kosho":"Yuzu kosho (πάστα γιούζου και τσίλι)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)
        self.assertGreaterEqual(len(labels),383)
        self.assertGreaterEqual(len(data["searchAliases"]),192)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
