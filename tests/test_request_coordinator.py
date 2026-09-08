from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    ha = types.ModuleType("homeassistant")
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = core

    package_name = "cook4me_request_coordinator_test"
    package = types.ModuleType(package_name)
    package.__path__ = []
    const = types.ModuleType(f"{package_name}.const")
    const.DOMAIN = "cook4me"
    sys.modules[package_name] = package
    sys.modules[f"{package_name}.const"] = const

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.request_coordinator",
        ROOT / "custom_components/cook4me/request_coordinator.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeHass:
    def __init__(self):
        self.data = {}


class RequestCoordinatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_operations_never_overlap(self):
        async def run():
            coord = self.mod.Cook4MeRequestCoordinator(FakeHass())
            events = []
            active = 0
            max_active = 0

            async def worker(name, delay):
                nonlocal active, max_active
                async with coord.operation(name, name):
                    active += 1
                    max_active = max(max_active, active)
                    events.append(f"{name}-start")
                    await asyncio.sleep(delay)
                    events.append(f"{name}-end")
                    active -= 1

            first = asyncio.create_task(worker("a", 0.03))
            await asyncio.sleep(0.005)
            second = asyncio.create_task(worker("b", 0.001))
            await asyncio.gather(first, second)
            return events, max_active

        events, max_active = asyncio.run(run())
        self.assertEqual(max_active, 1)
        self.assertEqual(events, ["a-start", "a-end", "b-start", "b-end"])

    def test_nested_operation_is_reentrant(self):
        async def run():
            coord = self.mod.Cook4MeRequestCoordinator(FakeHass())
            async with coord.operation("outer", "Outer") as outer:
                async with coord.operation("inner", "Inner") as inner:
                    return outer["id"], inner["id"], coord.snapshot

        outer_id, inner_id, snapshot = asyncio.run(run())
        self.assertEqual(outer_id, inner_id)
        self.assertTrue(snapshot["busy"])
        self.assertEqual(snapshot["running"]["kind"], "outer")

    def test_shared_hass_returns_same_global_coordinator(self):
        async def run():
            hass = FakeHass()
            first = await self.mod.request_coordinator(hass)
            second = await self.mod.request_coordinator(hass)
            return first is second

        self.assertTrue(asyncio.run(run()))


if __name__ == "__main__":
    unittest.main()
