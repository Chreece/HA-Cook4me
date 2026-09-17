"""Original-edition requests require exact identity and observed appliance loading."""
import asyncio
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock, Mock

import test_runtime_audit_v74 as runtime
from build_cross_language_fixture_v106 import recipes


class OriginalLanguageSendTests(unittest.IsolatedAsyncioTestCase):
    setUp = runtime.AuditTests.setUp
    asyncTearDown = runtime.AuditTests.asyncTearDown

    @classmethod
    def setUpClass(cls):
        cls.recipes = recipes()

    async def prepare(self, recipe=None, loaded=True):
        self.meta = deepcopy(recipe or self.recipes[0])
        self.variant = self.meta['displayVariantId']
        self.bridge.data = {'connected': True}
        self.bridge.async_recipe_detail = AsyncMock(return_value=self.meta)
        self.bridge._run_client_json = AsyncMock(return_value={'accepted': True})
        self.bridge.recipe_hub.async_record_send = AsyncMock()
        self.wait = AsyncMock(return_value=loaded)
        ns = {'asyncio': asyncio, 'HomeAssistantError': runtime.HomeAssistantError,
              '_wait_for_loaded_variant': self.wait,
              '_REPLACEABLE_RECIPE_PHASES': {'idle', 'stopped', 'preparation', 'add_ingredient', 'done'}}
        runtime.functions('websocket_v12.py', {'_loaded_variant', '_recipe_phase', '_send_recipe_replaceable', '_send_recipe_replaceable_locked'}, ns)
        self.store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        send_ns = {'_text': lambda value: str(value or '').strip(),
                   'Cook4MeDietaryError': self.mod.Cook4MeDietaryError,
                   'recipe_book_store_for_bridge': AsyncMock(return_value=self.store),
                   'v12': runtime.NS(_send_recipe_replaceable=ns['_send_recipe_replaceable'])}
        runtime.functions('websocket_v25.py', {'_send_one_exact'}, send_ns)
        self.send = send_ns['_send_one_exact']
        self.request = {'sendVariantId': self.variant, 'sendOriginalLanguage': True, 'sendDiet': 'omnivore'}

    async def test_real_foreign_editions_send_exact_original_ids_and_preserve_recipe(self):
        for recipe in self.recipes:
            with self.subTest(language=recipe['language']):
                self.assertFalse(recipe.get('sendVariantId'))
                await self.prepare(recipe)
                before = deepcopy(self.meta)
                result = await self.send(self.bridge, self.request)
                self.assertTrue(result['sent'])
                self.assertTrue(result['result']['verified'])
                self.bridge.async_recipe_detail.assert_awaited_once_with(self.variant)
                self.bridge._run_client_json.assert_awaited_once_with('send-recipe', recipe['groupingFunctionalId'], self.variant, timeout=45)
                self.wait.assert_awaited_once_with(self.bridge, self.variant, timeout=90)
                self.assertEqual(self.meta, before)
                self.bridge.recipe_hub.async_record_send.assert_awaited_once()

    async def test_fresh_cooking_status_can_confirm_loading_after_delayed_watch(self):
        await self.prepare(loaded=False)
        from test_delivery_confirmation_v108 import confirmation
        async def real_wait(bridge, variant, timeout):
            return await confirmation.wait_for_recipe(bridge, variant, timeout=.2, poll_interval=.01, check_interval=.002)
        self.wait.side_effect = real_wait
        self.bridge._run_client_json.side_effect = [{'accepted': True}, {'connected': True, 'variantFunctionalId': self.variant}]
        result = await self.send(self.bridge, self.request)
        self.assertTrue(result['sent'])
        self.assertEqual(self.bridge.data['variantFunctionalId'], self.variant)

    async def test_cloud_acceptance_without_device_loading_is_not_success_or_queued(self):
        await self.prepare(loaded=False)
        previous = (await self.store.async_queue_send({'sendVariantId': 'unrelated'}, reason='device_busy'))['queued']
        self.bridge._run_client_json.side_effect = [{'accepted': True}, {'variantFunctionalId': 'other', 'desired': {'variantFunctionalId': self.variant}}]
        result = await self.send(self.bridge, self.request)
        self.assertEqual(result['reason'], 'device_confirmation_unavailable')
        self.assertTrue(result['accepted'])
        self.assertFalse(result['sent']); self.assertFalse(result['queued'])
        self.assertEqual(self.store.queued_send, previous)
        self.bridge.recipe_hub.async_record_send.assert_not_awaited()

    async def test_unconfirmed_mapped_replacement_is_not_queued_or_repeated(self):
        await self.prepare(loaded=False)
        self.bridge.data.update(recipeFunctionalId='old-group', variantFunctionalId='old', phase='preparation')
        self.request.pop('sendOriginalLanguage')
        result = await self.send(self.bridge, self.request)
        self.assertEqual(result['reason'], 'device_confirmation_unavailable')
        self.assertTrue(result['accepted']); self.assertFalse(result['sent']); self.assertFalse(result['queued'])
        self.assertIsNone(self.store.queued_send)
        self.bridge._run_client_json.assert_awaited_once_with('send-recipe', self.meta['groupingFunctionalId'], self.variant, timeout=45)
        self.bridge.recipe_hub.async_record_send.assert_not_awaited()

    async def test_offline_request_does_not_queue_an_unverified_language_override(self):
        await self.prepare()
        self.bridge.data = {'connected': False}
        result = await self.send(self.bridge, self.request)
        self.assertEqual(result['reason'], 'original_language_offline')
        self.assertIsNone(self.store.queued_send)
        self.bridge.async_recipe_detail.assert_not_awaited()
        self.bridge._run_client_json.assert_not_awaited()

    async def test_active_cooking_and_mismatched_identity_never_send(self):
        await self.prepare()
        self.bridge.data.update(recipeFunctionalId='busy-group', variantFunctionalId='busy', phase='cooking', active=True)
        result = await self.send(self.bridge, self.request)
        self.assertFalse(result['sent']); self.assertFalse(result['queued'])
        self.bridge._run_client_json.assert_not_awaited()
        self.bridge.data = {'connected': True}
        self.meta['recipeFunctionalId'] = 'different-edition'
        result = await self.send(self.bridge, self.request)
        self.assertIn('identity', result['error'])
        self.bridge._run_client_json.assert_not_awaited()

    async def test_dietary_guidance_remains_authoritative_without_blocking_original_language(self):
        await self.prepare()
        self.meta['ingredients'] = ['duck', 'gelatin']
        self.request.update(sendDiet='vegetarian', match={'safe': True}, ingredients=['forged safe food'])
        result = await self.send(self.bridge, self.request)
        self.assertTrue(result['sent'])
        self.assertTrue(result['result']['verified'])
        sent = result['result']['recipe']
        self.assertEqual(sent['ingredients'], ['duck', 'gelatin'])
        self.assertFalse(sent['match']['safe'])
        self.assertEqual(len(sent['match']['ingredientChanges']), 2)
        self.bridge._run_client_json.assert_awaited_once_with('send-recipe', self.meta['groupingFunctionalId'], self.variant, timeout=45)

    async def test_cloud_rejection_is_reported_without_an_automatic_retry(self):
        await self.prepare()
        self.bridge._run_client_json.side_effect = RuntimeError('Shadow recipe update rejected')
        result = await self.send(self.bridge, self.request)
        self.assertEqual(result['reason'], 'original_language_send_failed')
        self.assertFalse(result['queued'])
        self.assertIsNone(self.store.queued_send)
        self.wait.assert_not_awaited()

    async def test_cancellation_and_missing_identity_never_trigger_fallback_retries(self):
        await self.prepare()
        result = await self.send(self.bridge, {'sendOriginalLanguage': True})
        self.assertFalse(result['sent']); self.assertFalse(result['queued'])
        self.bridge._run_client_json.assert_not_awaited()
        self.bridge.async_recipe_detail.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.send(self.bridge, self.request)
        self.assertIsNone(self.store.queued_send)


if __name__ == '__main__':
    unittest.main()
