"""Non-blocking catalog startup regressions."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "cook4me"
PKG = "cook4me_catalog_startup_v257"

package = ModuleType(PKG)
package.__path__ = [str(COMP)]
sys.modules[PKG] = package


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(f"{PKG}.{name}", COMP / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    module.__package__ = PKG
    sys.modules[module.__name__] = module
    spec.loader.exec_module(module)
    return module


runtime = load("catalog_runtime", "catalog_runtime.py")


class FakeHass:
    def __init__(self):
        self.data = {}
        self.config = SimpleNamespace(config_dir=None)

    def async_create_background_task(self, coro, _name):
        return asyncio.create_task(coro)

    async def async_add_executor_job(self, func, *args):
        return func(*args)


class CatalogStartupSourceTests(unittest.TestCase):
    def test_domain_setup_schedules_but_does_not_await_catalog_warmup(self):
        source = (COMP / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("start_catalog_warmup(hass)", source)
        self.assertNotIn("await async_warm_release_catalog(hass)", source)
        self.assertNotIn("await hass.async_add_executor_job(warm_stock_catalog)", source)

    def test_readiness_check_cannot_cold_load_catalog(self):
        source = (COMP / "release_catalog.py").read_text(encoding="utf-8")
        ready = source[source.index("def release_catalog_ready()"):source.index("def release_catalog_summary()")]
        self.assertIn("load_release_catalog.cache_info().currsize == 0", ready)
        self.assertIn("return False", ready)
        self.assertLess(
            ready.index("load_release_catalog.cache_info().currsize == 0"),
            ready.index("payload = load_release_catalog()"),
        )

    def test_catalog_request_routes_await_shared_warmup(self):
        expected = {
            "websocket_v10.py": "await async_ensure_catalog_ready(hass)",
            "websocket_v11.py": "await async_ensure_catalog_ready(hass)",
            "websocket_v18.py": "await async_ensure_catalog_ready(hass)",
            "websocket_v33.py": "await async_ensure_catalog_ready(hass)",
        }
        for filename, marker in expected.items():
            with self.subTest(filename=filename):
                source = (COMP / filename).read_text(encoding="utf-8")
                self.assertIn(marker, source)

    def test_warmup_reports_stage_timings(self):
        source = (COMP / "catalog_runtime.py").read_text(encoding="utf-8")
        for marker in (
            "storageSeconds",
            "catalogSeconds",
            "stockSeconds",
            "ancillarySeconds",
            "totalSeconds",
            "background catalog warm-up finished",
        ):
            self.assertIn(marker, source)


class SharedTaskTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_waiter_does_not_cancel_shared_warmup(self):
        hass = FakeHass()
        started = asyncio.Event()
        release = asyncio.Event()

        async def warm():
            started.set()
            await release.wait()
            return True

        task = asyncio.create_task(warm())
        hass.data.setdefault(runtime.DOMAIN, {})[runtime.DATA_CATALOG_WARM_TASK] = task
        await started.wait()

        waiter = asyncio.create_task(runtime.async_ensure_catalog_ready(hass))
        await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter

        self.assertFalse(task.cancelled())
        self.assertFalse(task.done())
        release.set()
        self.assertTrue(await task)


if __name__ == "__main__":
    unittest.main(verbosity=2)
