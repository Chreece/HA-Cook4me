"""Cancellation, failed persistence and speech regressions from the v75 audit."""
import asyncio
from copy import deepcopy
import time
import unittest
from unittest.mock import AsyncMock, patch

import test_runtime_audit_v74 as runtime
import test_device_announcements_v72 as speech


class DeliveryAudit(unittest.IsolatedAsyncioTestCase):
    setUp = runtime.AuditTests.setUp
    asyncTearDown = runtime.AuditTests.asyncTearDown

    def queue_flush(self, store):
        ns = {'recipe_book_store_for_bridge': AsyncMock(return_value=store)}
        runtime.functions('websocket_v18.py', {'_flush_one_queued_send'}, ns)
        return ns['_flush_one_queued_send']

    async def test_cancel_or_replace_during_metadata_does_not_send_old_recipe(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        self.bridge.data = {'connected': True}
        self.bridge._profile_match_or_raise = lambda meta: meta
        self.bridge._run_client_json = AsyncMock(return_value={'accepted': True})
        self.bridge.recipe_hub.async_record_send = AsyncMock()
        for replacement in (None, 'new'):
            with self.subTest(replacement=replacement):
                self.bridge._run_client_json.reset_mock()
                await store.async_queue_send({'sendVariantId': 'old'}, reason='offline')
                started, release = asyncio.Event(), asyncio.Event()
                async def detail(variant):
                    started.set()
                    await release.wait()
                    return {'groupingFunctionalId': 'group', 'recipeFunctionalId': variant}
                self.bridge.async_recipe_detail = detail
                task = asyncio.create_task(self.queue_flush(store)(self.bridge))
                await asyncio.wait_for(started.wait(), 1)
                if replacement:
                    await store.async_queue_send({'sendVariantId': replacement}, reason='offline')
                else:
                    await store.async_clear_queue()
                release.set()
                await asyncio.wait_for(task, 1)
                self.bridge._run_client_json.assert_not_awaited()
                self.assertEqual((store.queued_send or {}).get('variantId'), replacement)

    async def test_current_queued_recipe_sends_and_clears_queue(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        await store.async_queue_send({'sendVariantId': 'current'}, reason='offline')
        self.bridge.data = {'connected': True}
        self.bridge.async_recipe_detail = AsyncMock(return_value={
            'groupingFunctionalId': 'group', 'recipeFunctionalId': 'current'})
        self.bridge._profile_match_or_raise = lambda meta: meta
        self.bridge._run_client_json = AsyncMock(return_value={'accepted': True})
        self.bridge.recipe_hub.async_record_send = AsyncMock()
        await self.queue_flush(store)(self.bridge)
        self.bridge._run_client_json.assert_awaited_once_with('send-recipe', 'group', 'current', timeout=45)
        self.assertIsNone(store.queued_send)

    async def test_cancel_while_waiting_for_send_lock_does_not_dispatch(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        await store.async_queue_send({'sendVariantId': 'old'}, reason='offline')
        self.bridge.data = {'connected': True}
        self.bridge.async_recipe_detail = AsyncMock(return_value={
            'groupingFunctionalId': 'group', 'recipeFunctionalId': 'old'})
        self.bridge._profile_match_or_raise = lambda meta: meta
        self.bridge._run_client_json = AsyncMock(return_value={'accepted': True})
        self.bridge.recipe_hub.async_record_send = AsyncMock()
        await self.bridge._send_lock.acquire()
        task = asyncio.create_task(self.queue_flush(store)(self.bridge))
        await asyncio.sleep(0)
        await store.async_clear_queue()
        self.bridge._send_lock.release()
        await asyncio.wait_for(task, 1)
        self.bridge._run_client_json.assert_not_awaited()

    async def test_storage_failure_keeps_committed_book_and_queue(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        await store.async_toggle('favorites', {'id': 'saved', 'title': 'Saved'})
        await store.async_queue_send({'sendVariantId': 'saved'}, reason='offline')
        actions = {
            'favorite': lambda: store.async_toggle('favorites', {'id': 'new'}),
            'queue': lambda: store.async_queue_send({'sendVariantId': 'new'}, reason='offline'),
            'clear': store.async_clear_queue,
            'remove_local': lambda: store.async_remove_local_recipe('saved'),
        }
        for name, action in actions.items():
            with self.subTest(action=name):
                before = store.snapshot()
                with patch.object(store._store, 'async_save', AsyncMock(side_effect=OSError('disk unavailable'))):
                    with self.assertRaises(OSError):
                        await action()
                self.assertEqual(store.snapshot(), before)

    async def test_pending_or_cancelled_save_is_not_visible_as_committed(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        await store.async_queue_send({'sendVariantId': 'saved'}, reason='offline')
        before = store.snapshot()
        started = asyncio.Event()
        async def save(value):
            started.set()
            await asyncio.Event().wait()
        with patch.object(store._store, 'async_save', save):
            task = asyncio.create_task(store.async_queue_send({'sendVariantId': 'new'}, reason='offline'))
            await asyncio.wait_for(started.wait(), 1)
            during = store.snapshot()
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.assertEqual(during, before)
        self.assertEqual(store.snapshot(), before)


class AnnouncementAudit(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = speech.AnnouncementTests.asyncSetUp
    user = speech.AnnouncementTests.user
    data = speech.AnnouncementTests.data
    prefs = speech.AnnouncementTests.prefs
    save = speech.AnnouncementTests.save
    publish = speech.AnnouncementTests.publish
    add_listener = speech.AnnouncementTests.add_listener
    update_entity = speech.AnnouncementTests.update_entity

    async def test_broken_status_subscriber_does_not_stop_speech_or_other_users(self):
        await self.save()
        await self.save('bob', players=['media_player.living'])
        updates = []
        def broken(status):
            raise ConnectionError('browser disconnected')
        self.manager.listeners['alice'] = [broken, updates.append]
        await self.publish(variantFunctionalId='r', recipeTitle='Soup')
        self.assertEqual(self.hass.services.async_call.await_count, 2)
        self.assertEqual(updates[-1]['state'], 'done')
        self.assertEqual(self.manager.status['bob']['state'], 'done')

    async def test_slow_state_announcement_is_skipped_after_disconnect_or_recipe_change(self):
        await self.save(ai='ai_task.local', language='en_US')
        for change in ({'connected': False}, {'variantFunctionalId': 'new'}):
            with self.subTest(change=change):
                self.hass.services.async_call.reset_mock()
                self.bridge.data = self.data(active=True, phase='cooking', variantFunctionalId='old')
                async def generate(*args, **kwargs):
                    self.bridge.data.update(change)
                    return speech.NS(data={'text': 'Cooking'})
                self.generate.side_effect = generate
                self.manager.cache.clear()
                self.manager.queue.append(([('state', 'cooking')], deepcopy(self.bridge.data), time.monotonic()))
                await self.manager.run()
                self.hass.services.async_call.assert_not_awaited()

    async def test_entity_migration_cannot_overwrite_concurrent_speech_preferences(self):
        self.registry.rows.append(speech.NS(entry_id='entry1', entity_id='binary_sensor.connected',
            unique_id='device1_connected', platform='cook4me', disabled_by=None))
        self.states['sensor.cook4me_state'] = speech.NS(state='idle', attributes={})
        self.states['binary_sensor.connected'] = speech.NS(state='on', attributes={})
        entered, release = asyncio.Event(), asyncio.Event()
        writes = []
        async def persist(value):
            if not entered.is_set():
                entered.set()
                await release.wait()
            writes.append(deepcopy(value))
        self.settings.store.async_save = persist
        migrate = asyncio.create_task(self.settings.async_consolidate_entities())
        await asyncio.wait_for(entered.wait(), 1)
        save = asyncio.create_task(self.save())
        await asyncio.sleep(0)
        release.set()
        await asyncio.wait_for(asyncio.gather(migrate, save), 1)
        self.assertTrue(self.settings.for_user('alice')['enabled'])
        self.assertTrue(self.settings.data['entitiesConsolidated'])
        self.assertTrue(writes[-1]['users']['alice']['enabled'])
        self.assertTrue(writes[-1]['entitiesConsolidated'])


if __name__ == '__main__':
    unittest.main()
