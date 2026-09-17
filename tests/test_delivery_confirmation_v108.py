"""Real confirmation polling: late reports, bounded reads and cancellation."""
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

spec = importlib.util.spec_from_file_location('confirmation_v108', Path(__file__).resolve().parents[1] / 'custom_components/cook4me/delivery_confirmation.py')
confirmation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(confirmation)


class ConfirmationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bridge = SimpleNamespace(data={'connected': True}, _run_client_json=AsyncMock(return_value={}))
        self.bridge._publish = Mock(side_effect=lambda state: setattr(self.bridge, 'data', state))

    async def wait(self, **kwargs):
        return await confirmation.wait_for_recipe(self.bridge, 'chosen', timeout=kwargs.pop('timeout', .16),
                                                  poll_interval=.02, check_interval=.002, **kwargs)

    async def test_default_confirmation_budget_is_ninety_seconds(self):
        self.assertEqual(confirmation.CONFIRMATION_TIMEOUT, 90)
        self.bridge.data['variantFunctionalId'] = 'chosen'
        self.assertTrue(await confirmation.wait_for_recipe(self.bridge, 'chosen'))
        self.bridge._run_client_json.assert_not_awaited()

    async def test_late_live_confirmation_interrupts_and_reaps_a_slow_read(self):
        started, stopped = asyncio.Event(), asyncio.Event()
        async def read(*args, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        self.bridge._run_client_json.side_effect = read
        task = asyncio.create_task(self.wait())
        await asyncio.wait_for(started.wait(), .5)
        await asyncio.sleep(.035)
        self.bridge.data = {'connected': True, 'variantFunctionalId': 'chosen'}
        self.assertTrue(await asyncio.wait_for(task, .5))
        self.assertTrue(stopped.is_set())
        self.bridge._run_client_json.assert_awaited_once()

    async def test_repeated_readback_confirms_when_watch_stream_is_delayed(self):
        self.bridge._run_client_json.side_effect = [RuntimeError('temporary'), {'variantFunctionalId': 'old'},
                                                  {'connected': True, 'variantFunctionalId': 'chosen'}]
        self.assertTrue(await self.wait())
        self.assertEqual(self.bridge._run_client_json.await_count, 3)
        self.bridge._publish.assert_called_once_with({'connected': True, 'variantFunctionalId': 'chosen'})
        self.assertTrue(all(call.args == ('state',) for call in self.bridge._run_client_json.await_args_list))

    async def test_deadline_cancels_outstanding_read_without_resending(self):
        stopped = asyncio.Event()
        async def read(*args, **kwargs):
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        self.bridge._run_client_json.side_effect = read
        self.assertFalse(await asyncio.wait_for(self.wait(timeout=.07), .5))
        self.assertTrue(stopped.is_set())
        self.bridge._run_client_json.assert_awaited_once()
        self.assertLessEqual(self.bridge._run_client_json.await_args.kwargs['timeout'], .07)

    async def test_cancellation_cleans_up_read_task(self):
        started, stopped = asyncio.Event(), asyncio.Event()
        async def read(*args, **kwargs):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                stopped.set()
        self.bridge._run_client_json.side_effect = read
        task = asyncio.create_task(self.wait())
        await asyncio.wait_for(started.wait(), .5)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(stopped.is_set())

    async def test_desired_shadow_ack_and_disconnected_stale_recipe_are_not_confirmation(self):
        self.bridge.data = {'connected': False, 'variantFunctionalId': 'chosen'}
        self.bridge._run_client_json.return_value = {'connected': False, 'variantFunctionalId': 'chosen',
            'desired': {'recipe': {'variant': {'functionalId': 'chosen'}}}, 'accepted': True}
        self.assertFalse(await self.wait(timeout=.06))
        self.bridge._publish.assert_not_called()
        self.bridge.data = {'connected': True, 'shadowRecipe': {'variant': {'functionalId': 'chosen'}}}
        self.bridge._run_client_json.return_value = {'connected': True, 'desired': {'variantFunctionalId': 'chosen'}}
        self.assertFalse(await self.wait(timeout=.06))

    async def test_slow_read_cannot_overwrite_newer_live_cooking_or_disconnect(self):
        for changed in ({'connected': False}, {'connected': True, 'variantFunctionalId': 'newer', 'phase': 'cooking'}):
            with self.subTest(changed=changed):
                self.bridge.data = {'connected': True}
                async def read(*args, **kwargs):
                    self.bridge.data = dict(changed)
                    await asyncio.sleep(.005)
                    return {'connected': True, 'variantFunctionalId': 'chosen'}
                self.bridge._run_client_json.side_effect = read
                # Only one read starts before the deadline.
                self.assertFalse(await self.wait(timeout=.035))
                self.assertEqual(self.bridge.data, changed)
                self.bridge._publish.assert_not_called()


class DefinitionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'custom_components/cook4me/vendor/cook4me_recipe_definition.py'
        spec = importlib.util.spec_from_file_location('recipe_definition_test', path)
        cls.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(cls.module)

    def test_program_structure_is_preserved_for_every_group_without_claiming_compatibility(self):
        raw = {'access_token': 'SECRET', 'applianceGroups': [{'reference': {'key': 'GROUP_A'}}, {'reference': {'key': 'GROUP_B'}}],
            'steps': [{'fid': {'functionalId': 'step'}, 'type': {'key': 'COOKING'}, 'applicationDescription': 'text',
                'sequences': [{'applianceGroup': {'key': 'GROUP_A'}, 'operations': [{'program': {'key': 'PRESSURE'}, 'parameters': [{'key': 'DURATION', 'value': 900}]}]},
                              {'applianceGroup': {'key': 'GROUP_B'}, 'operations': [{'program': None, 'parameters': None}]}]}]}
        out = self.module.definition_summary(raw)
        self.assertEqual(out['firmwareCompatibility'], 'unknown')
        self.assertEqual(out['applianceGroups'], ['GROUP_A', 'GROUP_B'])
        self.assertEqual(out['steps'][0]['sequences'][0]['operations'][0]['parameterKeys'], ['DURATION'])
        self.assertEqual(out['steps'][0]['sequences'][1]['operations'][0]['nullFields'], ['parameters', 'program'])
        self.assertNotIn('SECRET', str(out))

    def test_malformed_or_missing_collections_do_not_break_recipe_loading(self):
        for raw in ({}, {'steps': None, 'applianceGroups': 2}, {'steps': [None, {'sequences': 5}]},
                    {'steps': [{'sequences': [{'operations': True}, None]}]}):
            self.assertEqual(self.module.definition_summary(raw)['firmwareCompatibility'], 'unknown')


import test_runtime_audit_v74 as runtime
import importlib


class DiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    setUp = runtime.AuditTests.setUp
    asyncTearDown = runtime.AuditTests.asyncTearDown

    async def test_diagnostics_are_entry_scoped_and_do_not_export_account_or_household_data(self):
        self.bridge.data = {'connected': True, 'uiFirmware': 'example', 'variantFunctionalId': 'selected',
                            'recipeTitle': 'private title', 'password': 'SECRET'}
        self.bridge.entry.data.update(email='SECRET', password='SECRET', language='el', country='GR')
        self.bridge.record_recipe_delivery('resolving', 'selected')
        self.bridge.record_recipe_delivery('resolved', 'selected', {'groupingFunctionalId': 'group', 'recipeFunctionalId': 'selected',
            'ingredients': ['private pantry'], 'headers': {'Authorization': 'SECRET'}})
        self.bridge.record_recipe_delivery('unconfirmed', 'selected')
        self.hass.data['cook4me'] = {'bridges': {'one': self.bridge, 'two': runtime.NS(data={'password': 'OTHER_SECRET'})}}
        module = importlib.import_module(runtime.PREFIX + '.diagnostics')
        result = await module.async_get_config_entry_diagnostics(self.hass, self.bridge.entry)
        self.assertEqual(result['configuredLocale']['language'], 'el')
        self.assertEqual(result['lastRecipeDelivery']['phase'], 'unconfirmed')
        self.assertEqual(result['lastRecipeDelivery']['recipe']['recipeFunctionalId'], 'selected')
        self.assertNotIn('SECRET', str(result)); self.assertNotIn('private', str(result))
        result['lastRecipeDelivery']['events'].clear()
        self.assertEqual(len(self.bridge._last_recipe_delivery['events']), 3)


    async def test_opening_any_recipe_refreshes_legacy_structure_once_without_sending(self):
        from copy import deepcopy
        self.hass.config = runtime.NS(path=lambda *parts: '/config/' + '/'.join(parts))
        old = {'recipeFunctionalId': 'arbitrary-id', 'groupingFunctionalId': 'group', 'ingredients': ['rice'], 'steps': []}
        fresh = {**old, 'deliveryDefinition': {'schemaVersion': 1, 'steps': [], 'firmwareCompatibility': 'unknown'}}
        stored = {'raw': old}
        cache = runtime.NS(get=lambda *args: stored['raw'], async_mark_checked=AsyncMock(),
                           async_set=AsyncMock(side_effect=lambda kind, key, value: stored.update(raw=value)))
        call = AsyncMock(return_value=fresh)
        ns = {'__package__': runtime.PREFIX, 'deepcopy': deepcopy, '_text': str,
              'recipe_languages': runtime.NS(country_for_language=lambda language, fallback: fallback),
              'v7': runtime.NS(_cache_for=AsyncMock(return_value=cache)),
              'v9': runtime.NS(_async_catalog_call=call), '_detail_sync': None,
              '_device_country': lambda b: 'GR', '_app_version': lambda b: 'test',
              'release_catalog_summary': lambda: {'catalogVersion': 'test'}, 'stable_cache_key': lambda *args: 'key'}
        runtime.functions('websocket_v30.py', {'_recipe_detail'}, ns)
        kwargs = dict(variant_id='arbitrary-id', language='el', refresh=False, coordinator=runtime.NS(progress=Mock()), operation={})
        await ns['_recipe_detail'](self.hass, self.bridge, **kwargs)
        await ns['_recipe_detail'](self.hass, self.bridge, **kwargs)
        call.assert_awaited_once()
        self.assertEqual(self.bridge._last_inspected_recipe['recipeFunctionalId'], 'arbitrary-id')
        self.assertEqual(self.bridge._last_inspected_recipe['definition']['firmwareCompatibility'], 'unknown')
        self.assertIsNone(getattr(self.bridge, '_last_recipe_delivery', None))


if __name__ == '__main__':
    unittest.main()
