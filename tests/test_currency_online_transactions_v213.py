"""Currency and online-cache persistence race regressions."""
from __future__ import annotations

import ast
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"
PKG = "cook4me_currency_online_v213"
package = ModuleType(PKG)
package.__path__ = [str(COMPONENT)]
sys.modules[PKG] = package

locks = {}
helpers = ModuleType(PKG + ".store_helpers")
@asynccontextmanager
async def store_load_lock(bridge, name):
    lock = locks.setdefault((id(bridge), name), asyncio.Lock())
    async with lock:
        yield
helpers.store_load_lock = store_load_lock
sys.modules[helpers.__name__] = helpers


def load(name):
    path = COMPONENT / (name + ".py")
    tree = ast.parse(path.read_text())
    tree.body = [
        node for node in tree.body
        if not (
            isinstance(node, ast.ImportFrom)
            and (
                (node.module or "").startswith("homeassistant")
                or node.module == "const"
            )
        )
    ]
    module = ModuleType(PKG + "." + name)
    module.__package__ = PKG
    module.__file__ = str(path)
    module.DOMAIN = "cook4me"
    module.HomeAssistant = object
    module.Store = object
    sys.modules[module.__name__] = module
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


currency = load("currency_fx")
online = load("online_cache")


class Storage:
    def __init__(self, initial=None):
        self.initial = deepcopy(initial)
        self.saved = deepcopy(initial)
        self.fail = False
        self.block_next = False
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def async_load(self):
        return deepcopy(self.initial)

    async def async_save(self, data):
        snapshot = deepcopy(data)
        if self.block_next:
            self.block_next = False
            self.started.set()
            await self.release.wait()
        if self.fail:
            raise OSError("disk full")
        self.saved = snapshot


class CostStore:
    def __init__(self, currency_code="EUR"):
        self._settings = {"currency": currency_code}
        self.fail = False
        self.calls = []

    @property
    def settings(self):
        return deepcopy(self._settings)

    async def async_set_settings(self, *, currency=None, **_kwargs):
        self.calls.append(currency)
        if self.fail:
            raise OSError("cost settings unavailable")
        if currency is not None:
            self._settings["currency"] = str(currency)
        return self.settings


class Hass:
    def __init__(self):
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.block_next = False

    async def async_add_executor_job(self, function):
        if self.block_next:
            self.block_next = False
            self.started.set()
            await self.release.wait()
        return function()


def currency_store(pref=None, rates=None):
    obj = currency.Cook4MeCurrencyFxStore.__new__(currency.Cook4MeCurrencyFxStore)
    obj.hass = Hass()
    obj.entry_id = "entry"
    obj._data = {
        "preference": deepcopy(pref or {"initialized": True, "mode": "fixed", "currency": "EUR"}),
        "rates": deepcopy(rates or {}),
    }
    obj._store = Storage(obj._data)
    obj._loaded = True
    obj._lock = asyncio.Lock()
    obj._rates_lock = asyncio.Lock()
    return obj


def online_store(rows=None):
    obj = online.Cook4MeOnlineCache.__new__(online.Cook4MeOnlineCache)
    obj.hass = object()
    obj.entry_id = "entry"
    obj._rows = deepcopy(rows or {})
    obj._store = Storage({"rows": obj._rows})
    obj._loaded = True
    obj._lock = asyncio.Lock()
    return obj


class CurrencyPreferenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_cost_store_failure_does_not_change_saved_preference(self):
        store = currency_store()
        costs = CostStore("EUR")
        costs.fail = True
        before = store.preference
        with self.assertRaises(OSError):
            await store.async_set_preference(
                mode="fixed", currency="USD", language="en-US", cost_store=costs
            )
        self.assertEqual(store.preference, before)

    async def test_preference_storage_failure_rolls_cost_currency_back(self):
        store = currency_store()
        costs = CostStore("EUR")
        store._store.fail = True
        before = store.preference
        with self.assertRaises(OSError):
            await store.async_set_preference(
                mode="fixed", currency="USD", language="en-US", cost_store=costs
            )
        self.assertEqual(store.preference, before)
        self.assertEqual(costs.settings["currency"], "EUR")
        self.assertEqual(costs.calls, ["USD", "EUR"])

    async def test_successful_preference_updates_both_stores(self):
        store = currency_store()
        costs = CostStore("EUR")
        selected = await store.async_set_preference(
            mode="fixed", currency="USD", language="en-US", cost_store=costs
        )
        self.assertEqual(selected, "USD")
        self.assertEqual(store.preference["currency"], "USD")
        self.assertEqual(costs.settings["currency"], "USD")
        self.assertEqual(store._data, store._store.saved)

    async def test_initial_resolution_storage_failure_rolls_cost_currency_back(self):
        store = currency_store(
            pref={"initialized": False, "mode": "auto", "currency": ""}
        )
        costs = CostStore("")
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_resolve_currency("el-GR", costs)
        self.assertFalse(store.preference["initialized"])
        self.assertEqual(costs.settings["currency"], "")


class CurrencyRateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original = currency.fetch_ecb_daily_rates

    def tearDown(self):
        currency.fetch_ecb_daily_rates = self.original

    async def test_failed_rate_storage_keeps_previous_rates(self):
        old = {
            "date": "2026-09-23",
            "fetchedAt": "2026-09-23T00:00:00+00:00",
            "source": "ecb_reference_rates",
            "rates": {"EUR": 1.0, "USD": 1.2},
        }
        store = currency_store(rates=old)
        store._store.fail = True
        currency.fetch_ecb_daily_rates = lambda: {
            "ok": True, "date": "2026-09-24", "rates": {"EUR": 1.0, "USD": 1.3}
        }
        with self.assertRaises(OSError):
            await store.async_rates(force=True)
        self.assertEqual(store._data["rates"], old)

    async def test_concurrent_rate_and_preference_commit_preserve_both(self):
        store = currency_store()
        costs = CostStore("EUR")
        store.hass.block_next = True
        currency.fetch_ecb_daily_rates = lambda: {
            "ok": True, "date": "2026-09-24", "rates": {"EUR": 1.0, "USD": 1.3}
        }
        rates_task = asyncio.create_task(store.async_rates(force=True))
        await store.hass.started.wait()
        pref_task = asyncio.create_task(store.async_set_preference(
            mode="fixed", currency="USD", language="en-US", cost_store=costs
        ))
        await pref_task
        store.hass.release.set()
        await rates_task
        self.assertEqual(store.preference["currency"], "USD")
        self.assertEqual(store._data["rates"]["rates"]["USD"], 1.3)
        self.assertEqual(store._data, store._store.saved)


class OnlineCacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_record_keeps_previous_row(self):
        old = {
            "one": {
                "value": {"old": True}, "fingerprint": "x", "source": "online",
                "checkedAt": 1.0, "updatedAt": 1.0, "accessedAt": 1.0, "lastError": "",
            }
        }
        store = online_store(old)
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_record("one", {"new": True})
        self.assertEqual(store._rows, old)

    async def test_failed_failure_marker_keeps_previous_check_metadata(self):
        old = {
            "one": {
                "value": {"old": True}, "fingerprint": "x", "source": "online",
                "checkedAt": 1.0, "updatedAt": 1.0, "accessedAt": 1.0, "lastError": "",
            }
        }
        store = online_store(old)
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_record_failure("one", "network")
        self.assertEqual(store._rows, old)

    async def test_cancelled_record_rolls_back(self):
        store = online_store()
        store._store.block_next = True
        task = asyncio.create_task(store.async_record("one", {"value": 1}))
        await store._store.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(store._rows, {})

    async def test_concurrent_records_preserve_both(self):
        store = online_store()
        store._store.block_next = True
        first = asyncio.create_task(store.async_record("one", {"value": 1}))
        await store._store.started.wait()
        second = asyncio.create_task(store.async_record("two", {"value": 2}))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        store._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(set(store._rows), {"one", "two"})
        self.assertEqual(set(store._store.saved["rows"]), {"one", "two"})


class OnlineCacheFirstLoadTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_first_access_constructs_one_cache(self):
        constructed = 0
        started = asyncio.Event()
        release = asyncio.Event()

        class BarrierStore:
            def __init__(self, *_args):
                nonlocal constructed
                constructed += 1
            async def async_load(self):
                started.set()
                await release.wait()
                return {"rows": {}}
            async def async_save(self, _data):
                pass

        original = online.Store
        online.Store = BarrierStore
        bridge = SimpleNamespace(hass=object(), entry=SimpleNamespace(entry_id="entry"))
        try:
            first = asyncio.create_task(online.online_cache_for_bridge(bridge))
            await started.wait()
            second = asyncio.create_task(online.online_cache_for_bridge(bridge))
            await asyncio.sleep(0)
            self.assertFalse(second.done())
            release.set()
            one, two = await asyncio.gather(first, second)
            self.assertIs(one, two)
            self.assertEqual(constructed, 1)
        finally:
            online.Store = original


if __name__ == "__main__":
    unittest.main()
