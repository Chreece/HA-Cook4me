from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DELIVERY = ROOT / "custom_components" / "cook4me" / "delivery_queue.py"
spec = importlib.util.spec_from_file_location("cook4me_delivery_queue_v129", DELIVERY)
delivery = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(delivery)


class DeliveryQueueV129Tests(unittest.TestCase):
    def test_exact_active_variant_clears_pending_delivery(self):
        queued = {"variantId": "variant-42", "recipe": {"title": "Soup"}}
        state = {
            "variantFunctionalId": "variant-42",
            "recipeFunctionalId": "grouping-9",
            "phase": "cooking",
            "active": True,
        }
        self.assertTrue(delivery.queued_recipe_received(queued, state))

    def test_title_or_grouping_match_never_clears_wrong_variant(self):
        queued = {
            "variantId": "variant-42",
            "recipe": {"title": "Same title", "recipeFunctionalId": "variant-42"},
        }
        state = {
            "variantFunctionalId": "variant-77",
            "recipeFunctionalId": "variant-42",
            "recipeTitle": "Same title",
        }
        self.assertFalse(delivery.queued_recipe_received(queued, state))

    def test_loaded_recipe_wrapper_is_supported(self):
        queued = {"variantId": "variant-42"}
        state = {"loadedRecipe": {"recipeFunctionalId": "variant-42", "status": "preheating"}}
        self.assertTrue(delivery.queued_recipe_received(queued, state))

    def test_backend_queues_every_send_before_background_delivery(self):
        source = (ROOT / "custom_components" / "cook4me" / "websocket_v18.py").read_text(encoding="utf-8")
        book = (ROOT / "custom_components" / "cook4me" / "recipe_book.py").read_text(encoding="utf-8")
        self.assertIn('queued = await store.async_queue_send(recipe, reason=reason)', source)
        self.assertIn('bridge.async_create_task(', source)
        self.assertIn('_reconcile_queued_send(bridge, store)', source)
        self.assertIn('if queued.get("submittedAt"):', source)
        self.assertIn('async_mark_queue_submitted', source)
        self.assertIn('queued["reason"] = "waiting_for_device"', book)
        self.assertIn('queued["submittedAt"] = datetime.now(timezone.utc).isoformat()', book)

    def test_live_device_listener_reconciles_stale_queue(self):
        source = (ROOT / "custom_components" / "cook4me" / "websocket_v18.py").read_text(encoding="utf-8")
        init = (ROOT / "custom_components" / "cook4me" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn('def register_send_queue_listener(bridge)', source)
        self.assertIn('register_send_queue_listener(bridge)', init)
        self.assertIn('"_send_queue_listener_unsub"', init)
        self.assertIn('await _reconcile_queued_send(bridge, store)', source)

    def test_v129_ui_polls_only_while_delivery_is_pending(self):
        ui = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v129.js").read_text(encoding="utf-8")
        panel = (ROOT / "custom_components" / "cook4me" / "panel.py").read_text(encoding="utf-8")
        manifest = (ROOT / "custom_components" / "cook4me" / "manifest.json").read_text(encoding="utf-8")
        self.assertIn("_v129ScheduleQueueRefresh", ui)
        self.assertIn("},1000);", ui)
        self.assertIn("pendingWaiting", ui)
        v130 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v130.js").read_text(encoding="utf-8")
        v131 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v131.js").read_text(encoding="utf-8")
        v132 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v132.js").read_text(encoding="utf-8")
        v133 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v133.js").read_text(encoding="utf-8")
        v134 = (ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v134.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v157",panel)
        self.assertIn("cook4me-panel-v157.js",panel)
        self.assertIn('"version": "2026.9.21.22"', manifest)
        self.assertIn("if(!customElements.get(V133))await import('./cook4me-panel-v133.js?v=2026.9.20.7')", v134)
        self.assertIn("if(!customElements.get(V132))await import('./cook4me-panel-v132.js?v=2026.9.20.6')", v133)
        self.assertIn("if(!customElements.get(V131))await import('./cook4me-panel-v131.js?v=2026.9.20.5')", v132)
        self.assertIn("if(!customElements.get(V130))await import('./cook4me-panel-v130.js?v=2026.9.20.4')", v131)
        self.assertIn("if(!customElements.get(V129))await import('./cook4me-panel-v129.js?v=2026.9.20.3')", v130)


if __name__ == "__main__":
    unittest.main()
