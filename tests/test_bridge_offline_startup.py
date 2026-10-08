"""Regression tests: cloud state must never block Cook4Me offline HA startup.

Extract the real bridge lifecycle methods from the source tree; no Home
Assistant instance, credentials, MQTT connection, or third-party modules are
needed to exercise their asyncio behaviour.
"""
from __future__ import annotations

import ast
import asyncio
import logging
from pathlib import Path
import time
from types import ModuleType
from unittest import IsolatedAsyncioTestCase, main
from unittest.mock import AsyncMock, patch

SOURCE = Path(__file__).resolve().parents[1] / "custom_components/cook4me/bridge.py"
BRIDGE_LOGGER = logging.getLogger("cook4me.bridge.startup_test")


def load_bridge():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    original = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Cook4MeBridge"
    )
    wanted = {
        "async_start", "_warn_if_initial_state_missing", "async_stop",
        "_run_forever", "_drain_stderr",
    }
    methods = [
        node for node in original.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name in wanted
    ]
    assert {node.name for node in methods} == wanted
    cls = ast.ClassDef(
        name="Cook4MeBridge", bases=[], keywords=[], body=methods,
        decorator_list=[],
    )
    module_ast = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
    namespace = {
        "__file__": str(SOURCE),
        "asyncio": asyncio,
        "logging": logging,
        "pathlib": __import__("pathlib"),
        "json": __import__("json"),
        "time": time,
        "_LOGGER": BRIDGE_LOGGER,
    }
    exec(compile(module_ast, str(SOURCE), "exec"), namespace)
    return namespace["Cook4MeBridge"]


Bridge = load_bridge()


class FakeHass:
    def async_create_background_task(self, coro, name):
        return asyncio.create_task(coro, name=name)


class FakeHub:
    async def async_load(self):
        return None


def bridge_fixture():
    bridge = Bridge.__new__(Bridge)
    bridge.hass = FakeHass()
    bridge.recipe_hub = FakeHub()
    bridge._first_state = asyncio.Event()
    bridge._background_tasks = set()
    bridge._client_processes = set()
    bridge._proc = None
    bridge._task = None
    bridge._initial_state_monitor = None
    bridge._stopping = False
    bridge._watcher_stage = "not_started"
    bridge._last_watcher_exit_code = None
    bridge._last_reconnect_warning = 0
    bridge._base_cmd = lambda: ["python", "-u", "vendor-placeholder"]
    bridge._env = lambda: {}
    bridge._stop_process = AsyncMock()
    bridge._mark_disconnected = lambda: None
    return bridge


class Reader:
    def __init__(self, *rows):
        self.rows = iter(rows)

    async def readline(self):
        return next(self.rows, b"")


class FakeProcess:
    def __init__(self):
        self.stdout = Reader()
        self.stderr = Reader()
        self.returncode = 1

    async def wait(self):
        return self.returncode


class StartupRegressionTests(IsolatedAsyncioTestCase):
    async def test_start_loads_offline_without_waiting_for_first_mqtt_state(self):
        bridge = bridge_fixture()
        bridge._run_forever = lambda: asyncio.Event().wait()
        await asyncio.wait_for(bridge.async_start(), timeout=0.3)
        self.assertFalse(bridge._first_state.is_set())
        self.assertFalse(bridge._task.done())
        self.assertFalse(bridge._initial_state_monitor.done())
        await bridge.async_stop()
        self.assertTrue(bridge._stopping)
        self.assertIsNone(bridge._task)
        self.assertIsNone(bridge._initial_state_monitor)

    async def test_missing_state_warns_but_does_not_fail(self):
        bridge = bridge_fixture()
        bridge._watcher_stage = "authentication"
        bridge._last_watcher_exit_code = 1
        with self.assertLogs(BRIDGE_LOGGER, level="WARNING") as captured:
            await bridge._warn_if_initial_state_missing(timeout=0.001)
        message = "\n".join(captured.output)
        self.assertIn("initial cloud state missing", message)
        self.assertIn("stage=authentication", message)
        self.assertFalse(bridge._first_state.is_set())

    async def test_first_state_satisfies_monitor(self):
        bridge = bridge_fixture()
        bridge._first_state.set()
        await asyncio.wait_for(
            bridge._warn_if_initial_state_missing(timeout=0.001), timeout=0.3
        )

    async def test_watcher_retries_even_after_two_no_state_exits(self):
        bridge = bridge_fixture()
        attempts = []
        original_sleep = asyncio.sleep

        async def fake_spawn(*args, **kwargs):
            attempts.append(args)
            if len(attempts) == 3:
                bridge._stopping = True
            return FakeProcess()

        async def instant_sleep(_seconds):
            await original_sleep(0)

        with patch.object(asyncio, "create_subprocess_exec", fake_spawn), \
             patch.object(asyncio, "sleep", instant_sleep):
            with self.assertLogs(BRIDGE_LOGGER, level="WARNING") as captured:
                await asyncio.wait_for(bridge._run_forever(), timeout=1)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(bridge._last_watcher_exit_code, 1)
        self.assertIn("exited 2 times", "\n".join(captured.output))

    async def test_progress_diagnostics_redact_vendor_error_payloads(self):
        bridge = bridge_fixture()
        stream = Reader(
            b"COOK4ME_BOOT_PHASE=mqtt_initial_state\n",
            b"MQTT reconnect   : TimeoutError: wss://signed-example?secret=abc123\n",
            b"extra error contains secret=abc123\n",
        )
        with self.assertLogs(BRIDGE_LOGGER, level="WARNING") as captured:
            await bridge._drain_stderr(stream)
        self.assertEqual(bridge._watcher_stage, "mqtt_initial_state")
        joined = "\n".join(captured.output)
        self.assertIn("TimeoutError", joined)
        self.assertNotIn("secret=abc123", joined)


if __name__ == "__main__":
    main()
