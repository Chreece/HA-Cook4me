"""Regression cases from the v74 lifecycle, queue and persistence audit."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import ANY, AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/cook4me'
PREFIX = 'cook4me_audit_v74'
NS = types.SimpleNamespace


class MemoryStore:
    def __init__(self, *args):
        self.saved = None
    async def async_load(self):
        return deepcopy(self.saved)
    async def async_save(self, value):
        self.saved = deepcopy(value)


class HomeAssistantError(Exception): pass
class ConfigEntryNotReady(HomeAssistantError): pass
class ConfigEntryAuthFailed(HomeAssistantError): pass


def functions(filename, names, namespace):
    nodes = [n for n in ast.parse((COMPONENT / filename).read_text()).body
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    for node in nodes:
        node.decorator_list = []
    tree = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), filename, 'exec'), namespace)
    return namespace


class AuditTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        package = types.ModuleType(PREFIX)
        package.__path__ = [str(COMPONENT)]
        modules = {
            PREFIX: package,
            'homeassistant.config_entries': NS(ConfigEntry=object),
            'homeassistant.core': NS(HomeAssistant=object, callback=lambda f:f),
            'homeassistant.exceptions': NS(HomeAssistantError=HomeAssistantError, ConfigEntryNotReady=ConfigEntryNotReady, ConfigEntryAuthFailed=ConfigEntryAuthFailed),
            'homeassistant.helpers.storage': NS(Store=MemoryStore),
            'homeassistant.util': NS(dt=NS(now=datetime.now)),
        }
        self.patcher = patch.dict(sys.modules, modules)
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        self.events = []
        self.hass = NS(data={}, bus=NS(async_fire=lambda kind, event:self.events.append(deepcopy(event))),
                       async_create_background_task=lambda coro, name:asyncio.create_task(coro, name=name))
        self.mod = importlib.import_module(PREFIX + '.bridge')
        self.bridge = self.mod.Cook4MeBridge(self.hass, NS(entry_id='one', data={'device_uuid':'device'}))
        self.bridge._env = lambda:{}
        self.bridge._base_cmd = lambda:['client']
        self.bookmod = importlib.import_module(PREFIX + '.recipe_book')
        self.coordmod = importlib.import_module(PREFIX + '.request_coordinator')

    async def asyncTearDown(self):
        await self.bridge.async_stop()

    async def test_startup_surfaces_watcher_failure_without_waiting_75_seconds(self):
        async def fail(): raise RuntimeError('watcher failed')
        self.bridge._run_forever = fail
        with self.assertRaisesRegex(ConfigEntryNotReady, 'watcher failed'):
            await asyncio.wait_for(self.bridge.async_start(), .5)
        self.assertTrue(self.bridge._stopping)
        self.assertIsNone(self.bridge._task)

    async def test_initial_timeout_cancels_the_watcher(self):
        self.bridge._run_forever = lambda:asyncio.sleep(60)
        with patch.object(self.mod.asyncio, 'wait', AsyncMock(return_value=(set(), set()))):
            with self.assertRaisesRegex(ConfigEntryNotReady, 'Timed out'):
                await self.bridge.async_start()
        self.assertTrue(self.bridge._stopping)
        self.assertIsNone(self.bridge._task)

    async def test_cancelled_real_client_process_is_reaped(self):
        self.bridge._base_cmd = lambda:[sys.executable, '-c', 'import time; time.sleep(60)']
        task = asyncio.create_task(self.bridge._run_client_json('probe'))
        for _ in range(100):
            if self.bridge._client_processes: break
            await asyncio.sleep(.01)
        self.assertTrue(self.bridge._client_processes)
        proc = next(iter(self.bridge._client_processes))
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertIsNotNone(proc.returncode)
        self.assertEqual(self.bridge._client_processes, set())

    async def test_watcher_disconnects_and_keeps_retrying_after_initial_success(self):
        real_sleep = asyncio.sleep
        processes = []
        class Process:
            def __init__(self, initial=False):
                self.returncode = 1
                self.stdout = NS(readline=AsyncMock(side_effect=[b'{"connected":true}\n', b''] if initial else [b'']), read=AsyncMock(return_value=b''))
                self.stderr = NS(readline=AsyncMock(return_value=b''), read=AsyncMock(return_value=b''))
            async def wait(self): return self.returncode
        async def spawn(*args, **kwargs):
            proc = Process(not processes); processes.append(proc); return proc
        async def delay(seconds): await real_sleep(0)
        states = []
        self.bridge.async_add_listener(lambda:states.append(self.bridge.available))
        with patch.object(self.mod.asyncio, 'create_subprocess_exec', spawn), patch.object(self.mod.asyncio, 'sleep', delay):
            task = asyncio.create_task(self.bridge._run_forever())
            for _ in range(150):
                if len(processes) >= 4 or task.done(): break
                await real_sleep(0)
            self.assertGreaterEqual(len(processes), 4)
            self.assertEqual(states[:2], [True, False])
            self.assertFalse(task.done())
            task.cancel(); await asyncio.gather(task, return_exceptions=True)

    async def test_process_cleanup_drains_full_output_pipes_promptly(self):
        proc = await asyncio.create_subprocess_exec(
            sys.executable, '-c',
            'import os,time; os.write(1,b"x"*1000000); time.sleep(60)',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            # Fill the unread pipe, so wait() alone cannot complete cleanup.
            for _ in range(100):
                if len(proc.stdout._buffer) > 131072:
                    break
                await asyncio.sleep(.01)
            self.assertGreater(len(proc.stdout._buffer), 131072)
            await asyncio.wait_for(self.bridge._stop_process(proc), 1)
            self.assertIsNotNone(proc.returncode)
            self.assertTrue(proc.stdout.at_eof())
        finally:
            if proc.returncode is None:
                proc.kill()
            await proc.communicate()

    async def test_unload_cancels_owned_metadata_and_completion_work(self):
        ended = asyncio.Event()
        async def work():
            try: await asyncio.sleep(60)
            finally: ended.set()
        task = self.bridge.async_create_task(work(), 'recipe metadata')
        await asyncio.sleep(0)
        await self.bridge.async_stop()
        self.assertTrue(task.cancelled()); self.assertTrue(ended.is_set())

    async def test_failed_listener_does_not_break_live_entities(self):
        self.bridge.async_add_listener(lambda:(_ for _ in ()).throw(ValueError('broken subscriber')))
        states = []
        self.bridge.async_add_listener(lambda:states.append(self.bridge.available))
        with self.assertLogs(self.mod._LOGGER, level='ERROR'):
            self.bridge._publish({'connected':True})
            self.bridge._mark_disconnected()
        self.assertEqual(states, [True, False])

    async def test_final_step_clears_the_previous_next_instruction(self):
        self.bridge._recipe_cache['v'] = {'steps':[{'functionalId':'last', 'instruction':'Serve'}]}
        self.bridge.data = {'variantFunctionalId':'v', 'stepFunctionalId':'last',
                            'nextInstruction':'Old step', 'nextStepFunctionalId':'last'}
        self.bridge._apply_recipe_metadata()
        self.assertEqual(self.bridge.data['currentInstruction'], 'Serve')
        self.assertNotIn('nextInstruction', self.bridge.data)
        self.assertNotIn('nextStepFunctionalId', self.bridge.data)

    async def test_platform_setup_failure_removes_bridge_and_listeners(self):
        cleanup = []
        self.bridge.async_start = AsyncMock()
        self.bridge.async_stop = AsyncMock(side_effect=lambda:cleanup.append('stop'))
        self.bridge._completion_listener_unsub = lambda:cleanup.append('completion')
        self.hass.config_entries = NS(async_forward_entry_setups=AsyncMock(side_effect=RuntimeError('platform failed')))
        settings = NS(async_load=AsyncMock(), async_consolidate_entities=AsyncMock())
        ns = {'__package__':PREFIX, 'Cook4MeBridge':lambda *args:self.bridge,
              'DOMAIN':'cook4me', 'DATA_BRIDGES':'bridges', 'PLATFORMS':[],
              '_register_completion_listener':lambda b:None, 'update_expiry_notification':lambda b:None,
              'register_daily_expiry_check':lambda b:lambda:cleanup.append('expiry'),
              'dismiss_expiry_notification':lambda b:cleanup.append('dismiss')}
        functions('__init__.py', {'async_setup_entry', '_async_cleanup_bridge'}, ns)
        with patch.dict(sys.modules, {PREFIX+'.device_settings':NS(DeviceSettings=lambda b:settings), PREFIX+'.announcements':NS(Announcements=object)}):
            with self.assertRaisesRegex(RuntimeError, 'platform failed'):
                await ns['async_setup_entry'](self.hass, self.bridge.entry)
        self.assertEqual(self.hass.data['cook4me']['bridges'], {})
        self.assertEqual(cleanup, ['completion', 'expiry', 'dismiss', 'stop'])

    async def test_child_task_cannot_inherit_its_parents_queue_lock(self):
        coord = self.coordmod.Cook4MeRequestCoordinator(self.hass)
        entered = []
        async def child():
            async with coord.operation('child', 'Child'): entered.append('child')
        async with coord.operation('parent', 'Parent'):
            task = asyncio.create_task(child())
            await asyncio.sleep(0)
            self.assertEqual(entered, [])
            self.assertEqual(coord.snapshot['waitingCount'], 1)
        await asyncio.wait_for(task, .5)
        self.assertEqual(entered, ['child'])

    async def test_cancelled_running_and_waiting_jobs_finish_progress(self):
        coord = self.coordmod.Cook4MeRequestCoordinator(self.hass)
        async def work(name):
            async with coord.operation(name, name, client_operation_id=name): await asyncio.sleep(60)
        active = asyncio.create_task(work('active')); await asyncio.sleep(0)
        waiting = asyncio.create_task(work('waiting')); await asyncio.sleep(0)
        waiting.cancel(); await asyncio.gather(waiting, return_exceptions=True)
        active.cancel(); await asyncio.gather(active, return_exceptions=True)
        terminal = [e for e in self.events if e['done']]
        self.assertEqual({e['operationId'] for e in terminal}, {'active', 'waiting'})
        self.assertTrue(all(e['phase']=='cancelled' for e in terminal))
        self.assertFalse(coord.snapshot['busy']); self.assertEqual(coord.snapshot['waitingCount'], 0)

    async def test_late_executor_progress_cannot_reopen_completed_job(self):
        coord = self.coordmod.Cook4MeRequestCoordinator(self.hass)
        async with coord.operation('search', 'Search', client_operation_id='one') as job: pass
        count = len(self.events)
        self.assertIsNone(coord.progress(job, 'ranking', completed=3, total=100))
        self.assertEqual(len(self.events), count)

    async def test_concurrent_first_book_load_returns_one_store_and_keeps_favorites(self):
        gate = asyncio.Event()
        loaded = []
        async def load(store):
            loaded.append(store); await gate.wait(); return None
        with patch.object(MemoryStore, 'async_load', load):
            first = asyncio.create_task(self.bookmod.recipe_book_store_for_bridge(self.bridge))
            second = asyncio.create_task(self.bookmod.recipe_book_store_for_bridge(self.bridge))
            await asyncio.sleep(0); gate.set()
            a, b = await asyncio.gather(first, second)
        self.assertIs(a, b); self.assertEqual(len(loaded), 1)
        await asyncio.gather(a.async_toggle('favorites', {'id':'a','title':'A'}), b.async_toggle('favorites', {'id':'b','title':'B'}))
        self.assertEqual({r['id'] for r in a.snapshot()['favorites']}, {'a','b'})
        self.assertEqual(len(a._store.saved['favorites']), 2)

    async def test_queued_send_does_not_clear_a_newer_request(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        await store.async_queue_send({'sendVariantId':'old','title':'Old'}, reason='offline')
        started, release = asyncio.Event(), asyncio.Event()
        async def send(variant, **kwargs):
            self.assertEqual(variant, 'old'); started.set(); await release.wait()
        bridge = NS(can_accept_recipe=True, async_send_variant=send)
        ns = {'recipe_book_store_for_bridge':AsyncMock(return_value=store)}
        functions('websocket_v18.py', {'_flush_one_queued_send'}, ns)
        task = asyncio.create_task(ns['_flush_one_queued_send'](bridge))
        await started.wait()
        await store.async_queue_send({'sendVariantId':'new','title':'New'}, reason='offline')
        release.set(); await task
        self.assertEqual(store.queued_send['variantId'], 'new')
        self.assertFalse(bridge._cook4me_queued_send_running)

    async def test_queue_flush_reserves_work_before_awaiting_store_load(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        await store.async_queue_send({'sendVariantId':'one'}, reason='offline')
        gate = asyncio.Event()
        async def load(bridge): await gate.wait(); return store
        bridge = NS(can_accept_recipe=True, async_send_variant=AsyncMock())
        ns = {'recipe_book_store_for_bridge':load}
        functions('websocket_v18.py', {'_flush_one_queued_send'}, ns)
        tasks = [asyncio.create_task(ns['_flush_one_queued_send'](bridge)) for _ in range(2)]
        await asyncio.sleep(0); gate.set(); await asyncio.gather(*tasks)
        bridge.async_send_variant.assert_awaited_once_with('one', still_current=ANY)

    async def test_offline_queue_preserves_selected_variant_identity(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        await store.async_queue_send({'selectedSendVariantId':'selected','searchVariantId':'search','variantFunctionalId':'old'}, reason='offline')
        self.assertEqual(store.queued_send['variantId'], 'selected')

    async def test_all_persistent_store_factories_share_concurrent_first_load(self):
        cases = [('nutrition','Cook4MeNutritionStore'), ('nutrition_resolution','Cook4MeNutritionResolutionStore'),
                 ('costs','Cook4MeCostStore'), ('currency_fx','Cook4MeCurrencyFxStore'),
                 ('meal_history','Cook4MeMealHistoryStore'), ('meal_lifecycle','Cook4MeMealLifecycleStore'),
                 ('today_plan_store','Cook4MeTodayPlanStore')]
        for filename, class_name in cases:
            with self.subTest(store=filename):
                gate, instances = asyncio.Event(), []
                class Store:
                    def __init__(self, *args): instances.append(self)
                    async def async_load(self): await gate.wait()
                name = next(n.name for n in ast.parse((COMPONENT/(filename+'.py')).read_text()).body
                            if isinstance(n, ast.AsyncFunctionDef) and n.name.endswith('store_for_bridge'))
                ns = {'__package__':PREFIX, class_name:Store}
                functions(filename+'.py', {name}, ns)
                bridge = NS(hass=self.hass, entry=NS(entry_id='one'))
                a = asyncio.create_task(ns[name](bridge)); b = asyncio.create_task(ns[name](bridge))
                await asyncio.sleep(0); gate.set(); first, second = await asyncio.gather(a,b)
                self.assertIs(first, second); self.assertEqual(len(instances), 1)

    async def test_failed_first_load_can_retry_without_retaining_half_loaded_store(self):
        with patch.object(MemoryStore, 'async_load', AsyncMock(side_effect=[OSError('disk temporarily unavailable'), None])):
            with self.assertRaises(OSError): await self.bookmod.recipe_book_store_for_bridge(self.bridge)
            store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        self.assertTrue(store._loaded)

    async def test_direct_send_does_not_clear_a_newer_queued_recipe(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        await store.async_queue_send({'sendVariantId':'previous'}, reason='busy')
        async def send(bridge, variant):
            await store.async_queue_send({'sendVariantId':'newer'}, reason='busy')
            return {'verified':True}
        ns = {'recipe_book_store_for_bridge':AsyncMock(return_value=store),
              '_text':lambda v:str(v or '').strip(), 'v12':NS(_send_recipe_replaceable=send)}
        functions('websocket_v25.py', {'_send_one_exact'}, ns)
        result = await ns['_send_one_exact'](NS(available=True), {'sendVariantId':'direct'})
        self.assertTrue(result['sent']); self.assertEqual(store.queued_send['variantId'], 'newer')

    async def test_failed_send_cannot_overwrite_a_newer_queue_or_cancellation(self):
        store = await self.bookmod.recipe_book_store_for_bridge(self.bridge)
        previous = (await store.async_queue_send({'sendVariantId':'old'}, reason='busy'))['queued']
        await store.async_queue_send({'sendVariantId':'new'}, reason='busy')
        result = await store.async_queue_send({'sendVariantId':'failed'}, reason='busy', expected=previous)
        self.assertTrue(result['superseded']); self.assertEqual(store.queued_send['variantId'], 'new')
        await store.async_clear_queue()
        result = await store.async_queue_send({'sendVariantId':'failed'}, reason='busy', expected=previous)
        self.assertTrue(result['superseded']); self.assertIsNone(store.queued_send)

    async def test_device_send_commands_are_serialized(self):
        gate = asyncio.Event(); commands = []
        async def command(*args, **kwargs):
            commands.append(args); await gate.wait(); return {'accepted':True}
        self.bridge.data = {'connected':True}
        self.bridge._run_client_json = command
        self.bridge._profile_match_or_raise = lambda meta:meta
        self.bridge.recipe_hub.async_record_send = AsyncMock()
        meta = {'groupingFunctionalId':'group','recipeFunctionalId':'variant'}
        tasks = [asyncio.create_task(self.bridge._async_send_resolved(meta)) for _ in range(2)]
        await asyncio.sleep(0); self.assertEqual(len(commands), 1)
        gate.set(); await asyncio.gather(*tasks)
        self.assertEqual(len(commands), 2)

    async def test_changing_recipe_cancels_the_old_metadata_request(self):
        cancelled = []
        async def metadata(recipe, variant):
            try: await asyncio.sleep(60)
            finally: cancelled.append(variant)
        self.bridge._async_fetch_recipe_metadata = metadata
        self.bridge._publish({'connected':True, 'recipeFunctionalId':'g', 'variantFunctionalId':'a'})
        await asyncio.sleep(0)
        self.bridge._publish({'connected':True, 'recipeFunctionalId':'g', 'variantFunctionalId':'b'})
        await asyncio.sleep(0)
        self.assertEqual(cancelled, ['a'])

    async def test_cached_recipe_idle_and_disconnect_cancel_obsolete_metadata(self):
        for next_state in (
            {'connected': True, 'recipeFunctionalId': 'g', 'variantFunctionalId': 'cached'},
            {'connected': True},
            {'connected': False, 'recipeFunctionalId': 'g', 'variantFunctionalId': 'a'},
        ):
            with self.subTest(next_state=next_state):
                self.bridge._recipe_cache['cached'] = {'steps': []}
                self.bridge._async_fetch_recipe_metadata = AsyncMock(side_effect=lambda *args: None)
                task = self.bridge.async_create_task(asyncio.sleep(60), 'obsolete metadata')
                self.bridge._recipe_metadata_task = task
                self.bridge._recipe_metadata_variant = 'a'
                self.bridge._publish(next_state)
                await asyncio.sleep(0)
                self.assertTrue(task.cancelled())
                self.bridge._async_fetch_recipe_metadata.assert_not_awaited()

    async def test_watcher_disconnect_cancels_metadata_without_a_new_packet(self):
        self.bridge.data = {'connected': True}
        task = self.bridge.async_create_task(asyncio.sleep(60), 'obsolete metadata')
        self.bridge._recipe_metadata_task = task
        self.bridge._recipe_metadata_variant = 'a'
        self.bridge._mark_disconnected()
        await asyncio.sleep(0)
        self.assertTrue(task.cancelled())

    async def test_completion_fallback_uses_finished_recipe_after_live_recipe_changes(self):
        original = {'variantFunctionalId':'old','recipeFunctionalId':'group-old','recipeTitle':'Finished soup','recipeIngredients':[{'name':'Rice'}]}
        async def detail(variant):
            self.bridge.data = {'variantFunctionalId':'new', 'recipeTitle':'Next dish'}
            raise OSError('offline')
        self.bridge.data = deepcopy(original)
        self.bridge.async_recipe_detail = detail
        self.bridge.recipe_hub.async_prepare_consumption = AsyncMock(return_value=None)
        ns = {'deepcopy':deepcopy}
        functions('__init__.py', {'_handle_recipe_completed'}, ns)
        await ns['_handle_recipe_completed'](self.bridge)
        recipe = self.bridge.recipe_hub.async_prepare_consumption.call_args.args[0]
        self.assertEqual(recipe['title'], 'Finished soup')
        self.assertEqual(recipe['variantFunctionalId'], 'old')
        self.assertEqual(recipe['ingredients'], original['recipeIngredients'])


if __name__ == '__main__': unittest.main()
