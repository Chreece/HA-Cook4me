"""Per-ingredient recipe weighing v255 regressions."""
from copy import deepcopy
import ast
from pathlib import Path
import sys
import types
from typing import Any
import unittest

ROOT=Path(__file__).resolve().parents[1]
COMP=ROOT/"custom_components"/"cook4me"
PKG="weigh_v255"
pkg=types.ModuleType(PKG);pkg.__path__=[str(COMP)];sys.modules[PKG]=pkg
from weigh_v255 import inventory


class IngredientWeighingV255Tests(unittest.TestCase):
    def test_already_deducted_measurement_is_not_deducted_again_at_completion(self):
        stock=[{
            "key":"rice","name":"Rice","unit":"g",
            "lots":[{"id":"rice-lot","quantity":500}],
        }]
        recipe={"ingredients":[{
            "key":"rice","name":"Rice","quantity":125,"unit":"g",
            "scaleMeasured":True,"scaleStockDeducted":True,
        }]}
        self.assertEqual(inventory.recipe_consumption_items(recipe,stock),[])

    def test_reweigh_can_restore_previous_deduction_then_apply_replacement(self):
        original=[{
            "key":"rice","name":"Rice","unit":"g",
            "lots":[{"id":"rice-lot","quantity":500}],
        }]
        first,report=inventory.apply_consumption(
            original,[{"identity":"k:rice","quantity":100,"unit":"g","consume":True}]
        )
        self.assertEqual(first[0]["quantity"],400)
        restored,restore_report=inventory.restore_consumption(first,report)
        self.assertEqual(restored[0]["quantity"],500)
        self.assertTrue(restore_report["restored"])
        second,second_report=inventory.apply_consumption(
            restored,[{"identity":"k:rice","quantity":125,"unit":"g","consume":True}]
        )
        self.assertEqual(second[0]["quantity"],375)
        self.assertAlmostEqual(
            sum(row["quantity"] for row in second_report["deductedLots"]),125
        )

    def test_backend_contract_is_idempotent_and_marks_saved_deduction(self):
        hub=(COMP/"recipe_hub.py").read_text(encoding="utf-8")
        scale=(COMP/"smart_scale.py").read_text(encoding="utf-8")
        route=(COMP/"websocket_v37.py").read_text(encoding="utf-8")
        self.assertIn("weighedConsumptionReceipts",hub)
        self.assertIn("existing = receipts.get(request_id)",hub)
        self.assertLess(hub.index("restore_consumption(house, previous_report)"),
                        hub.index("apply_consumption(house, [request])"))
        self.assertIn('ingredient["scaleStockDeducted"] = stock_deducted',scale)
        self.assertIn('"deductionReport": deepcopy(deduction_report)',scale)
        self.assertIn('"cook4me/v37/ingredient_weight_commit"',route)
        self.assertIn("previous.get(\"deductionReport\")",route)
        self.assertIn("async_commit_weighed_ingredient",route)

    def test_immediate_and_final_reports_merge_for_meal_accounting(self):
        path=COMP/"websocket_v14.py"
        tree=ast.parse(path.read_text(encoding="utf-8"))
        node=next(item for item in tree.body
                  if isinstance(item,ast.FunctionDef)
                  and item.name=="_merge_consumption_reports")
        ns={"Any":Any}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),"exec"),ns)
        merged=ns["_merge_consumption_reports"](
            {"deducted":[{"identity":"k:rice"}],
             "deductedLots":[{"lotId":"a","quantity":100,"unit":"g"}]},
            {"deducted":[{"identity":"k:milk"}],
             "deductedLots":[{"lotId":"b","quantity":50,"unit":"g"}],
             "depleted":[{"identity":"k:milk"}]},
        )
        self.assertEqual([row["identity"] for row in merged["deducted"]],
                         ["k:rice","k:milk"])
        self.assertEqual([row["lotId"] for row in merged["deductedLots"]],["a","b"])
        self.assertEqual(merged["depleted"],[{"identity":"k:milk"}])

    def test_all_preweighed_recipe_still_creates_completion_confirmation(self):
        hub=(COMP/"recipe_hub.py").read_text(encoding="utf-8")
        self.assertIn("already_deducted = [",hub)
        self.assertIn("if not ingredients and not already_deducted:",hub)
        self.assertIn('"immediateWeighedDeduction": bool(already_deducted)',hub)

    def test_v255_runtime_wiring_keeps_global_runtime_scoped(self):
        panel=(COMP/"panel.py").read_text(encoding="utf-8")
        active=(COMP/"frontend"/"cook4me-panel-v180.js").read_text(encoding="utf-8")
        self.assertIn('/runtime-v249',panel)
        self.assertIn('runtime-v256',panel)
        self.assertIn('&runtime=249&diet=254&weigh=256',panel)
        self.assertIn("RecipeIngredientWeighingMixin",active)
        self.assertIn("runtime-v255",active)
        self.assertIn("data-cook4me-ui-revision','256",active)


if __name__=="__main__":
    unittest.main()
