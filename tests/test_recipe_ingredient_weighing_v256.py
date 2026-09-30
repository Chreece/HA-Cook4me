"""Recipe ingredient weighing v256 state/undo regressions."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
COMP=ROOT/"custom_components"/"cook4me"


class IngredientWeighingV256Tests(unittest.TestCase):
    def test_saved_weight_cancel_is_backend_reversible_and_idempotent(self):
        hub=(COMP/"recipe_hub.py").read_text(encoding="utf-8")
        scale=(COMP/"smart_scale.py").read_text(encoding="utf-8")
        route=(COMP/"websocket_v37.py").read_text(encoding="utf-8")

        self.assertIn("async def async_cancel_weighed_ingredient",hub)
        self.assertIn('receipt.get("cancelledAt") or receipt.get("supersededBy")',hub)
        self.assertIn("restore_consumption(house, report)",hub)
        self.assertIn('updated["cancelled"] = True',hub)
        self.assertIn("async def async_remove_measurement",scale)
        self.assertIn('"cook4me/v37/ingredient_weight_cancel"',route)
        self.assertIn("async_cancel_weighed_ingredient",route)
        self.assertIn("async_remove_measurement",route)

    def test_reweigh_marks_previous_receipt_superseded(self):
        hub=(COMP/"recipe_hub.py").read_text(encoding="utf-8")
        route=(COMP/"websocket_v37.py").read_text(encoding="utf-8")
        self.assertIn("previous_request_id",hub)
        self.assertIn('previous_receipt["supersededBy"] = request_id',hub)
        self.assertIn("previous_request_id=(",route)

    def test_v256_runtime_wiring_keeps_global_runtime_scoped(self):
        panel=(COMP/"panel.py").read_text(encoding="utf-8")
        active=(COMP/"frontend"/"cook4me-panel-v180.js").read_text(encoding="utf-8")
        self.assertIn('/runtime-v249',panel)
        self.assertRegex(
            panel,
            r'_PANEL_ELEMENT = "cook4me-recipe-hub-panel-v180-runtime-v\d+"',
        )
        self.assertIn('&runtime=249&diet=254&weigh=257&fullscreen=258',panel)
        self.assertIn("runtime-v256",active)
        self.assertIn("recipe-ingredient-weighing-v257.js",active)
        self.assertRegex(active,r"data-cook4me-ui-revision','\d+")


if __name__=="__main__":
    unittest.main(verbosity=2)
