"""Exercise original-program delivery with server-checked diet replacements."""
import asyncio
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock

import test_runtime_audit_v74 as runtime


class DietSendTests(unittest.IsolatedAsyncioTestCase):
    setUp = runtime.AuditTests.setUp
    asyncTearDown = runtime.AuditTests.asyncTearDown

    async def prepare(self, ingredients=None):
        self.bridge.data = {"connected": True}
        self.meta = {"title": "Duck and prawns", "groupingFunctionalId": "original-group",
                     "recipeFunctionalId": "original-variant", "sendVariantId": "original-variant",
                     "ingredients": ingredients or ["duck", "prawns", "rice"],
                     "steps": [{"instruction": "Cook the duck and prawns"}]}
        self.bridge.async_recipe_detail = AsyncMock(side_effect=lambda _variant: deepcopy(self.meta))
        self.bridge._run_client_json = AsyncMock(return_value={"ok": True})
        self.bridge.recipe_hub.async_record_send = AsyncMock()
        self.store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        ns = {"asyncio": asyncio, "HomeAssistantError": runtime.HomeAssistantError,
              "_recipe_phase": lambda _bridge: "idle"}
        runtime.functions("websocket_v12.py", {"_send_recipe_replaceable", "_send_recipe_replaceable_locked"}, ns)
        self.send_ns = {"_text": lambda value: str(value or "").strip(),
                        "Cook4MeDietaryError": self.mod.Cook4MeDietaryError,
                        "recipe_book_store_for_bridge": AsyncMock(return_value=self.store),
                        "v12": runtime.NS(_send_recipe_replaceable=ns["_send_recipe_replaceable"])}
        runtime.functions("websocket_v25.py", {"_send_one_exact"}, self.send_ns)
        self.send = self.send_ns["_send_one_exact"]
        flush_ns = {"recipe_book_store_for_bridge": AsyncMock(return_value=self.store)}
        runtime.functions("websocket_v18.py", {"_flush_one_queued_send"}, flush_ns)
        self.flush = flush_ns["_flush_one_queued_send"]

    async def test_dashboard_sends_original_ids_and_instructions_with_every_replacement(self):
        await self.prepare()
        before = deepcopy(self.meta)
        result = await self.send(self.bridge, {"sendVariantId": "original-variant", "sendDiet": "vegetarian"})
        self.assertTrue(result["sent"])
        self.assertFalse(result["queued"])
        self.bridge._run_client_json.assert_awaited_once_with("send-recipe", "original-group", "original-variant", timeout=45)
        sent = result["result"]["recipe"]
        self.assertEqual(sent["ingredients"], before["ingredients"])
        self.assertEqual(sent["steps"], before["steps"])
        self.assertFalse(sent["match"]["safe"])
        self.assertEqual([row["ingredientIndex"] for row in sent["match"]["substitutions"]], [0, 1])
        self.assertEqual(self.bridge.recipe_hub.profile["diet"], "omnivore")

    async def test_partial_or_forged_replacements_never_send_or_replace_an_existing_queue(self):
        await self.prepare(["duck", "gelatin"])
        await self.store.async_queue_send({"sendVariantId": "previous"}, reason="busy")
        previous = self.store.queued_send
        # Neither submitted ingredients nor fabricated match flags may waive
        # the official gelatin ingredient's unresolved replacement.
        result = await self.send(self.bridge, {"sendVariantId": "original-variant", "sendDiet": "vegetarian",
            "ingredients": ["rice"], "match": {"safe": True, "eligibleWithSubstitutions": True}})
        self.assertFalse(result["sent"])
        self.assertFalse(result["queued"])
        self.assertEqual(result["reason"], "dietary_profile")
        self.assertEqual(self.store.queued_send, previous)
        self.bridge._run_client_json.assert_not_awaited()

    async def test_selected_diet_keeps_target_allergies_and_avoid_rules(self):
        await self.prepare()
        self.bridge.recipe_hub._data["profile"]["allergies"] = ["shellfish"]
        result = await self.send(self.bridge, {"sendVariantId": "original-variant", "sendDiet": "vegetarian"})
        self.assertFalse(result["sent"])
        self.assertFalse(result["queued"])
        self.bridge._run_client_json.assert_not_awaited()
        self.bridge.recipe_hub._data["profile"].update(allergies=["soy"], avoid=["mushrooms", "chickpeas"])
        with self.assertRaises(self.mod.Cook4MeDietaryError):
            await self.bridge.async_send_variant("original-variant", diet="vegetarian")
        self.bridge._run_client_json.assert_not_awaited()

    async def test_queue_persists_selected_diet_and_rechecks_current_allergies(self):
        await self.prepare()
        self.bridge.data = {"connected": False}
        result = await self.send(self.bridge, {"sendVariantId": "original-variant", "sendDiet": "vegetarian"})
        self.assertTrue(result["queued"])
        self.assertEqual(self.store._store.saved["queuedSend"]["diet"], "vegetarian")
        self.bridge.data = {"connected": True}
        self.bridge.recipe_hub._data["profile"]["allergies"] = ["shellfish"]
        await self.flush(self.bridge)
        self.bridge._run_client_json.assert_not_awaited()
        self.assertIsNotNone(self.store.queued_send)
        self.bridge.recipe_hub._data["profile"]["allergies"] = []
        await self.flush(self.bridge)
        self.bridge._run_client_json.assert_awaited_once_with("send-recipe", "original-group", "original-variant", timeout=45)
        checked = self.bridge.recipe_hub.async_record_send.await_args.args[0]
        self.assertEqual(checked["match"]["diet"], "vegetarian")
        self.assertEqual(len(checked["match"]["substitutions"]), 2)
        self.assertIsNone(self.store.queued_send)

    async def test_profile_send_uses_current_household_rules_without_override(self):
        await self.prepare()
        self.bridge.recipe_hub._data["profile"]["diet"] = "vegetarian"
        result = await self.bridge.async_send_variant("original-variant")
        self.assertTrue(result["recipe"]["match"]["requiresSubstitutions"])
        self.bridge._run_client_json.assert_awaited_once_with("send-recipe", "original-group", "original-variant", timeout=45)

    async def test_invalid_diet_cannot_be_queued_or_sent(self):
        await self.prepare()
        for diet in ("skip-checks", {}, []):
            with self.subTest(diet=diet):
                result = await self.send(self.bridge, {"sendVariantId": "original-variant", "sendDiet": diet})
                self.assertFalse(result["sent"])
                self.assertFalse(result["queued"])
                with self.assertRaises(self.mod.Cook4MeDietaryError):
                    await self.bridge.async_send_variant("original-variant", diet=diet)
        self.assertIsNone(self.store.queued_send)
        self.bridge._run_client_json.assert_not_awaited()

    async def test_unmodified_compatible_recipe_still_sends(self):
        await self.prepare(["rice", "carrot"])
        result = await self.send(self.bridge, {"sendVariantId": "original-variant", "sendDiet": "vegan"})
        self.assertTrue(result["sent"])
        self.assertTrue(result["result"]["recipe"]["match"]["safe"])
        self.bridge._run_client_json.assert_awaited_once_with("send-recipe", "original-group", "original-variant", timeout=45)


if __name__ == "__main__":
    unittest.main()
