"""Exercise actual telemetry handlers, permission checks and bridge listeners."""
import ast
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def functions(path, namespace):
    nodes = [node for node in ast.parse((ROOT / path).read_text()).body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != 'async_register']
    for node in nodes:
        node.decorator_list = []
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), namespace)


class TelemetryTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.listeners, self.events, self.results, self.errors = [], [], [], []
        self.bridge = NS(entry=NS(entry_id='one'), device_uuid='device1', available=True,
                         can_accept_recipe=False, loaded_recipe={'title': 'Rice', 'secret': 'not sent'},
                         data={'phase': 'warming', 'active': True, 'uiFirmware': '1.2',
                               'remainingTime': 90, 'credentials': 'secret', 'currentInstruction': 'Stir'})
        def add_listener(callback):
            self.listeners.append(callback)
            def remove():
                if callback in self.listeners:
                    self.listeners.remove(callback)
            return remove
        self.bridge.async_add_listener = add_listener
        self.denied = set()
        self.user = NS(is_active=True, permissions=NS(check_entity=lambda entity, policy: (entity, policy) not in self.denied))
        registry = NS(async_get=lambda hass: None,
                      async_entries_for_config_entry=lambda registry, entry: [NS(unique_id='device1_summary', entity_id='sensor.cooker')])
        self.registry_patch = patch.dict(sys.modules, {'homeassistant.helpers': NS(entity_registry=registry)})
        self.registry_patch.start(); self.addCleanup(self.registry_patch.stop)
        permissions = {'POLICY_READ': 'read', 'POLICY_CONTROL': 'control'}
        functions('custom_components/cook4me/device_settings.py', permissions)
        self.ns = {'device_read_access': permissions['device_read_access'],
                   'legacy': NS(_bridge=lambda *args: self.bridge, _send_error=lambda *args: self.errors.append(args))}
        functions('custom_components/cook4me/websocket_v32.py', self.ns)
        self.connection = NS(user=self.user, subscriptions={}, send_event=lambda *args: self.events.append(args),
                             send_result=lambda *args: self.results.append(args))

    async def subscribe(self):
        await self.ns['ws_device_state_subscribe'](NS(), self.connection, {'id': 42, 'entry_id': 'one'})

    async def test_initial_state_and_updates_without_cloud_requests(self):
        await self.subscribe()
        self.assertFalse(self.errors)
        self.assertEqual(self.results, [(42,)])
        self.assertEqual(self.events[0][1]['state']['phase'], 'warming')
        self.assertEqual(self.events[0][1]['state']['remainingTime'], 90)
        self.assertNotIn('credentials', self.events[0][1]['state'])
        self.assertEqual(self.events[0][1]['loadedRecipe'], {'title': 'Rice'})
        self.bridge.data['phase'] = 'cooking'
        self.listeners[0]()
        self.assertEqual(self.events[-1][1]['state']['phase'], 'cooking')
        self.assertEqual(self.events[0][1]['state']['phase'], 'warming', 'Prior snapshots must not mutate')
        self.bridge.available = False
        self.listeners[0]()
        self.assertFalse(self.events[-1][1]['connected'])
        callback = self.listeners[0]
        self.connection.subscriptions[42]()
        self.connection.subscriptions[42]()
        self.assertEqual(self.listeners, [])
        count = len(self.events); callback(); self.assertEqual(len(self.events), count)

    async def test_read_permission_suffices_without_control_permission(self):
        self.denied.add(('sensor.cooker', 'control'))
        await self.subscribe()
        self.assertFalse(self.errors)
        self.assertEqual(len(self.events), 1)

    async def test_denied_or_inactive_users_receive_no_telemetry(self):
        self.denied.add(('sensor.cooker', 'read'))
        await self.subscribe()
        self.assertEqual(len(self.errors), 1)
        self.assertEqual(self.listeners, []); self.assertEqual(self.events, [])
        self.denied.clear(); self.user.is_active = False
        await self.subscribe()
        self.assertEqual(len(self.errors), 2); self.assertEqual(self.events, [])

    async def test_permission_revocation_clears_state_and_removes_listener(self):
        await self.subscribe()
        callback = self.listeners[0]
        self.denied.add(('sensor.cooker', 'read')); callback()
        self.assertFalse(self.events[-1][1]['accessible'])
        self.assertEqual(self.events[-1][1]['state'], {})
        self.assertEqual(self.listeners, [])
        count = len(self.events); callback(); self.assertEqual(len(self.events), count)

    async def test_failed_initial_response_does_not_leak_listener(self):
        self.connection.send_result = lambda *args: (_ for _ in ()).throw(RuntimeError('closed'))
        await self.subscribe()
        self.assertEqual(self.listeners, []); self.assertEqual(len(self.errors), 1)


if __name__ == '__main__':
    unittest.main()
