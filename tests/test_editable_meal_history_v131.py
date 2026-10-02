from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
INV=ROOT/"custom_components"/"cook4me"/"inventory.py"
spec=importlib.util.spec_from_file_location("cook4me_inventory_v131",INV)
inventory=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(inventory)


class EditableMealHistoryV131Tests(unittest.TestCase):
    def test_consumption_round_trip_restores_exact_lot_and_metadata(self):
        after=[{
            "key":"lentils","name":"Lentils","unit":"g",
            "lots":[{
                "id":"lot-1","quantity":380,"bestBefore":"2026-10-01",
                "storage":"pantry","productName":"Brown lentils",
            }],
        }]
        report={"deductedLots":[{
            "identity":"k:lentils","name":"Lentils","lotId":"lot-1",
            "quantity":120,"unit":"g","bestBefore":"2026-10-01",
            "storage":"pantry","productName":"Brown lentils",
            "ingredientLinks":[{"key":"lentils","name":"Lentils"}],
        }]}
        restored,restore_report=inventory.restore_consumption(after,report)
        self.assertEqual(restored[0]["quantity"],500)
        lot=restored[0]["lots"][0]
        self.assertEqual(lot["id"],"lot-1")
        self.assertEqual(lot["storage"],"pantry")
        self.assertEqual(lot["productName"],"Brown lentils")
        # Existing lot metadata wins; recreated depleted lots preserve links.
        recreated,_=inventory.restore_consumption([],report)
        self.assertEqual(recreated[0]["lots"][0]["ingredientLinks"][0]["key"],"lentils")
        self.assertTrue(restore_report["restored"])

    def test_strict_shortfall_detects_amount_not_fully_deducted(self):
        stock=[{"key":"lentils","name":"Lentils","unit":"g","quantity":50}]
        request={"identity":"k:lentils","quantity":80,"unit":"g","consume":True}
        _after,report=inventory.apply_consumption(stock,[request])
        shortfalls=inventory.consumption_shortfalls([request],report)
        self.assertEqual(len(shortfalls),1)
        self.assertEqual(shortfalls[0]["requested"],80)
        self.assertEqual(shortfalls[0]["deducted"],50)

    def test_confirmed_consumption_falls_back_from_stale_or_small_lot(self):
        stock=[{
            "key":"paprika","name":"Paprika","unit":"g","quantity":30,
            "lots":[
                {"id":"old","quantity":10,"bestBefore":"2026-10-03"},
                {"id":"new","quantity":20,"bestBefore":"2026-11-03"},
            ],
        }]
        request={
            "identity":"k:paprika","quantity":25,"unit":"g","consume":True,
            "lotId":"old","fallbackFefo":True,
        }
        after,report=inventory.apply_consumption(stock,[request])
        self.assertEqual(report["deducted"][0]["quantity"],25)
        self.assertEqual(sum(row["quantity"] for row in report["deductedLots"]),25)
        self.assertEqual(after[0]["quantity"],5)
        self.assertEqual(after[0]["lots"][0]["id"],"new")
        self.assertEqual(after[0]["lots"][0]["quantity"],5)

        missing={**request,"lotId":"already-gone","quantity":5}
        after2,report2=inventory.apply_consumption(after,[missing])
        self.assertEqual(report2["deducted"][0]["quantity"],5)
        self.assertEqual(after2,[])
        self.assertEqual(report2["depleted"][0]["name"],"Paprika")

    def test_unlimited_stock_is_never_offered_as_recipe_consumption(self):
        stock=[
            {"key":"salt","name":"Salt","unit":"","unlimited":True},
            {"key":"paprika","name":"Paprika","unit":"g","quantity":20},
        ]
        recipe={"ingredients":[
            {"key":"salt","name":"Salt","quantity":1,"unit":"g"},
            {"key":"paprika","name":"Paprika","quantity":5,"unit":"g"},
        ]}
        rows=inventory.recipe_consumption_items(recipe,stock)
        self.assertEqual([row["identity"] for row in rows],["k:paprika"])
        self.assertFalse(any(row.get("stockUnlimited") for row in rows))

    def test_confirm_button_commits_available_stock_and_prompts_for_depleted_items(self):
        hub=(ROOT/"custom_components"/"cook4me"/"recipe_hub.py").read_text(encoding="utf-8")
        websocket=(ROOT/"custom_components"/"cook4me"/"websocket_v14.py").read_text(encoding="utf-8")
        ui=(ROOT/"custom_components"/"cook4me"/"frontend"/"cook4me-panel-v131.js").read_text(encoding="utf-8")
        panel=(ROOT/"custom_components"/"cook4me"/"panel.py").read_text(encoding="utf-8")
        self.assertIn("commit_available: bool = False",hub)
        self.assertIn('"fallbackFefo": True',hub)
        self.assertIn('report["shortfalls"] = shortfalls',hub)
        self.assertIn('vol.Optional("commit_available", default=False): bool',websocket)
        self.assertIn("commit_available=bool(msg.get(\"commit_available\"))",websocket)
        self.assertIn("commit_available:true",ui)
        self.assertIn("_v131PromptDepleted",ui)
        self.assertIn("cook4me/v11/shopping_add",ui)
        self.assertIn("if(row?.unlimited)continue",ui)
        self.assertIn("row?.stockUnlimited",ui)
        self.assertIn("runtime-v272",panel)

    def test_finished_notification_deep_links_to_consumption_editor(self):
        source=(ROOT/"custom_components"/"cook4me"/"__init__.py").read_text(encoding="utf-8")
        self.assertIn('editor_path = f"/cook4me?consumption={pending_id}"',source)
        self.assertIn("[Open consumption editor]",source)
        self.assertIn("exact storage ingredient or batch",source)

    def test_history_update_reverses_then_reapplies_real_stock(self):
        hub=(ROOT/"custom_components"/"cook4me"/"recipe_hub.py").read_text(encoding="utf-8")
        websocket=(ROOT/"custom_components"/"cook4me"/"websocket_v38.py").read_text(encoding="utf-8")
        history=(ROOT/"custom_components"/"cook4me"/"meal_history.py").read_text(encoding="utf-8")
        self.assertIn("restore_consumption(",hub)
        self.assertIn("async_revise_consumption",hub)
        self.assertIn("strict=True",websocket)
        self.assertIn("_requests_from_report",websocket)
        self.assertIn("Compensate inventory",websocket)
        self.assertIn("async def async_update(",history)
        self.assertIn('"editedAt"',history)

    def test_v131_ui_edits_people_storage_lot_and_amount(self):
        ui=(ROOT/"custom_components"/"cook4me"/"frontend"/"cook4me-panel-v131.js").read_text(encoding="utf-8")
        for token in (
            "data-v131-stock","data-v131-lot","data-v131-history-amount",
            "data-v131-allocation","cook4me/v38/history_update",
            "strict:true","_v131OpenHistoryEditor","v131-nutrient-gap",
        ):
            self.assertIn(token,ui)

    def test_v131_is_inherited_by_active_v138_and_v38_registered(self):
        panel=(ROOT/"custom_components"/"cook4me"/"panel.py").read_text(encoding="utf-8")
        manifest=(ROOT/"custom_components"/"cook4me"/"manifest.json").read_text(encoding="utf-8")
        ui=(ROOT/"custom_components"/"cook4me"/"frontend"/"cook4me-panel-v131.js").read_text(encoding="utf-8")
        v132=(ROOT/"custom_components"/"cook4me"/"frontend"/"cook4me-panel-v132.js").read_text(encoding="utf-8")
        v133=(ROOT/"custom_components"/"cook4me"/"frontend"/"cook4me-panel-v133.js").read_text(encoding="utf-8")
        v134=(ROOT/"custom_components"/"cook4me"/"frontend"/"cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn("async_register_websocket_v38",panel)
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn('/cook4me_static/2026.9.27.2/runtime-v249',panel)
        self.assertIn('"version": "2026.9.22.7"',manifest)
        self.assertIn("if(!customElements.get(V133))await import('./cook4me-panel-v133.js?v=2026.9.20.7')",v134)
        self.assertIn("if(!customElements.get(V132))await import('./cook4me-panel-v132.js?v=2026.9.20.6')",v133)
        self.assertIn("if(!customElements.get(V131))await import('./cook4me-panel-v131.js?v=2026.9.20.5')",v132)
        self.assertIn("if(!customElements.get(V130))await import('./cook4me-panel-v130.js?v=2026.9.20.4')",ui)


if __name__=="__main__":
    unittest.main()
