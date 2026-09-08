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
    helpers = types.ModuleType("homeassistant.helpers")
    storage = types.ModuleType("homeassistant.helpers.storage")
    core.HomeAssistant = object

    class Store:
        def __init__(self, *args, **kwargs):
            self.saved = None

        def __class_getitem__(cls, _item):
            return cls

        async def async_load(self):
            return None

        async def async_save(self, data):
            self.saved = data

    storage.Store = Store
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.storage"] = storage

    package_name = "cook4me_online_cache_test"
    package = types.ModuleType(package_name)
    package.__path__ = []
    const = types.ModuleType(f"{package_name}.const")
    const.DOMAIN = "cook4me"
    sys.modules[package_name] = package
    sys.modules[f"{package_name}.const"] = const

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.online_cache",
        ROOT / "custom_components/cook4me/online_cache.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FakeHass:
    def __init__(self):
        self.data = {}


class OnlineCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_minimum_recheck_age_is_one_day(self):
        self.assertEqual(self.mod._MIN_CHECK_AGE, 86400)

    def test_cached_value_is_not_checked_before_one_day(self):
        async def run():
            store = self.mod.Cook4MeOnlineCache(FakeHass(), "entry")
            store._loaded = True
            clock = [1_000_000.0]
            original = self.mod.time.time
            self.mod.time.time = lambda: clock[0]
            calls = 0
            try:
                async def fetch():
                    nonlocal calls
                    calls += 1
                    return {"version": 1}

                first = await store.async_get_or_revalidate("x", fetch)
                clock[0] += 86399
                second = await store.async_get_or_revalidate("x", fetch)
                return calls, first, second
            finally:
                self.mod.time.time = original

        calls, first, second = asyncio.run(run())
        self.assertEqual(calls, 1)
        self.assertTrue(first["checkedOnline"])
        self.assertTrue(second["cacheHit"])
        self.assertFalse(second["checkedOnline"])
        self.assertEqual(second["value"], {"version": 1})

    def test_unchanged_daily_check_preserves_updated_timestamp(self):
        async def run():
            store = self.mod.Cook4MeOnlineCache(FakeHass(), "entry")
            store._loaded = True
            clock = [2_000_000.0]
            original = self.mod.time.time
            self.mod.time.time = lambda: clock[0]
            try:
                async def fetch():
                    return {"version": 1}

                first = await store.async_get_or_revalidate("x", fetch)
                first_updated = first["updatedAt"]
                clock[0] += 86400
                second = await store.async_get_or_revalidate("x", fetch)
                return first_updated, second
            finally:
                self.mod.time.time = original

        first_updated, second = asyncio.run(run())
        self.assertTrue(second["checkedOnline"])
        self.assertFalse(second["changed"])
        self.assertEqual(second["updatedAt"], first_updated)

    def test_changed_upstream_replaces_value_only_after_daily_boundary(self):
        async def run():
            store = self.mod.Cook4MeOnlineCache(FakeHass(), "entry")
            store._loaded = True
            clock = [3_000_000.0]
            original = self.mod.time.time
            self.mod.time.time = lambda: clock[0]
            value = {"version": 1}
            try:
                async def fetch():
                    return dict(value)

                first = await store.async_get_or_revalidate("x", fetch)
                value["version"] = 2
                clock[0] += 100
                early = await store.async_get_or_revalidate("x", fetch)
                clock[0] += 86400
                changed = await store.async_get_or_revalidate("x", fetch)
                return first, early, changed
            finally:
                self.mod.time.time = original

        first, early, changed = asyncio.run(run())
        self.assertEqual(early["value"], {"version": 1})
        self.assertFalse(early["checkedOnline"])
        self.assertEqual(changed["value"], {"version": 2})
        self.assertTrue(changed["changed"])
        self.assertNotEqual(changed["updatedAt"], first["updatedAt"])

    def test_failed_daily_recheck_keeps_stale_and_throttles_retry(self):
        async def run():
            store = self.mod.Cook4MeOnlineCache(FakeHass(), "entry")
            store._loaded = True
            clock = [4_000_000.0]
            original = self.mod.time.time
            self.mod.time.time = lambda: clock[0]
            calls = 0
            failing = False
            try:
                async def fetch():
                    nonlocal calls
                    calls += 1
                    if failing:
                        raise RuntimeError("offline")
                    return {"version": 1}

                await store.async_get_or_revalidate("x", fetch)
                failing = True
                clock[0] += 86400
                failed = await store.async_get_or_revalidate("x", fetch)
                clock[0] += 60
                throttled = await store.async_get_or_revalidate("x", fetch)
                return calls, failed, throttled
            finally:
                self.mod.time.time = original

        calls, failed, throttled = asyncio.run(run())
        self.assertEqual(calls, 2)
        self.assertEqual(failed["value"], {"version": 1})
        self.assertIn("offline", failed["lastError"])
        self.assertFalse(throttled["checkedOnline"])
        self.assertEqual(throttled["value"], {"version": 1})


if __name__ == "__main__":
    unittest.main()
