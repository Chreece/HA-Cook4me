"""Final persistent-store audit: shared catalog schema and nutrition resolution."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"
PKG = "cook4me_final_store_v215"
package = ModuleType(PKG)
package.__path__ = [str(COMPONENT)]
sys.modules[PKG] = package


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


catalog = load("ingredient_catalog")
resolution = load("nutrition_resolution")


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


def catalog_store(initial=None):
    obj = catalog.Cook4MeIngredientCatalogCache.__new__(
        catalog.Cook4MeIngredientCatalogCache
    )
    obj._store = Storage(initial or {})
    obj._data = {}
    obj._lock = asyncio.Lock()
    return obj


class SharedCatalogSchemaTests(unittest.IsolatedAsyncioTestCase):
    async def test_old_v28_checkedAt_schema_survives_canonical_load(self):
        now = catalog.time.time()
        old = {
            "el": {
                "checkedAt": now,
                "updatedAt": now - 10,
                "source": "v28",
                "items": [{"key": "rice", "name": "Ρύζι"}],
            }
        }
        store = catalog_store(old)
        await store.async_load()
        row = store.get("el")
        self.assertIsNotNone(row)
        self.assertEqual(row["source"], "v28")
        self.assertEqual(row["checkedAt"], now)
        self.assertEqual(row["updatedAt"], now - 10)

    async def test_old_v11_timestamp_schema_gets_v28_metadata_without_rewrite(self):
        now = catalog.time.time()
        old = {
            "de": {
                "timestamp": now,
                "source": "v11",
                "items": [{"key": "rice", "name": "Reis"}],
            }
        }
        store = catalog_store(old)
        await store.async_load()
        row = store.get("de")
        self.assertEqual(row["checkedAt"], now)
        self.assertEqual(row["updatedAt"], now)
        self.assertEqual(store._store.saved, old)

    async def test_unchanged_catalog_advances_check_time_but_preserves_update_time(self):
        now = catalog.time.time()
        store = catalog_store({
            "en": {
                "timestamp": now - 100,
                "checkedAt": now - 100,
                "updatedAt": now - 100,
                "source": "same",
                "items": [{"key": "rice", "name": "Rice"}],
            }
        })
        await store.async_load()
        before = store.get("en")["updatedAt"]
        await store.async_set(
            "en", [{"key": "rice", "name": "Rice"}], source="same"
        )
        after = store.get("en")
        self.assertEqual(after["updatedAt"], before)
        self.assertGreaterEqual(after["checkedAt"], before)

    async def test_changed_catalog_advances_update_time(self):
        now = catalog.time.time()
        store = catalog_store({
            "en": {
                "timestamp": now - 100,
                "checkedAt": now - 100,
                "updatedAt": now - 100,
                "source": "same",
                "items": [{"key": "rice", "name": "Rice"}],
            }
        })
        await store.async_load()
        before = store.get("en")["updatedAt"]
        await store.async_set(
            "en", [{"key": "rice", "name": "Rice"}, {"key": "carrot", "name": "Carrot"}],
            source="same",
        )
        self.assertGreater(store.get("en")["updatedAt"], before)


class V28CanonicalCacheTests(unittest.IsolatedAsyncioTestCase):
    async def _functions(self, fake_v11):
        source_path = COMPONENT / "websocket_v28.py"
        tree = ast.parse(source_path.read_text())
        wanted = {"_catalog_store", "_cached_catalog", "_save_catalog"}
        functions = [
            deepcopy(node) for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name in wanted
        ]
        ns = {
            "__name__": PKG + ".v28_test",
            "__package__": PKG,
            "v11": fake_v11,
            "deepcopy": deepcopy,
            "_clean_catalog_rows": lambda rows: deepcopy(rows),
            "_now": lambda: 1000.0,
            "_MIN_CHECK_AGE": 86400,
            "Any": object,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[])),
                str(source_path),
                "exec",
            ),
            ns,
        )
        return ns

    async def test_v28_has_no_second_homeassistant_store_writer(self):
        source = (COMPONENT / "websocket_v28.py").read_text()
        self.assertNotIn("homeassistant.helpers.storage import Store", source)
        self.assertNotIn("_CATALOG_STORE_VERSION", source)

    async def test_v28_reads_and_writes_the_exact_v11_cache_object(self):
        class FakeCache:
            def __init__(self):
                self.rows = {}
            def get(self, language):
                row = self.rows.get(language)
                return deepcopy(row) if row else None
            async def async_set(self, language, items, *, source):
                self.rows[language] = {
                    "timestamp": 1000.0,
                    "checkedAt": 1000.0,
                    "updatedAt": 1000.0,
                    "source": source,
                    "items": deepcopy(items),
                }

        cache = FakeCache()
        calls = 0
        async def get_cache(_bridge):
            nonlocal calls
            calls += 1
            return cache

        ns = await self._functions(SimpleNamespace(_cache=get_cache))
        bridge = object()
        result = await ns["_save_catalog"](
            bridge, "el", [{"key": "rice", "name": "Ρύζι"}], "canonical"
        )
        self.assertEqual(cache.rows["el"]["items"][0]["name"], "Ρύζι")
        self.assertEqual(result["source"], "canonical")
        cached = await ns["_cached_catalog"](bridge, "el")
        self.assertEqual(cached["items"], result["items"])
        self.assertGreaterEqual(calls, 2)


def resolution_store(initial=None):
    obj = resolution.Cook4MeNutritionResolutionStore.__new__(
        resolution.Cook4MeNutritionResolutionStore
    )
    obj.hass = object()
    obj.entry_id = "entry"
    obj._data = deepcopy(initial or {"failures": {}})
    obj._store = Storage(obj._data)
    obj._loaded = True
    obj._lock = asyncio.Lock()
    return obj


class NutritionResolutionTransactionTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_failure_record_is_not_published(self):
        store = resolution_store()
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_record_failure(
                "k:rice",
                query="rice",
                mode="demo",
                reason="TimeoutError",
                now=datetime(2026, 9, 24, tzinfo=timezone.utc),
            )
        self.assertEqual(store.failure_count, 0)

    async def test_failed_clear_keeps_existing_failure(self):
        old = {
            "failures": {
                "k:rice": {
                    "identity": "k:rice",
                    "query": "rice",
                    "mode": "demo",
                    "reason": "TimeoutError",
                    "attemptedAt": "2026-09-24T00:00:00+00:00",
                    "retryAt": "2026-09-25T00:00:00+00:00",
                }
            }
        }
        store = resolution_store(old)
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_clear("k:rice")
        self.assertEqual(store._data, old)

    async def test_cancelled_record_is_not_published(self):
        store = resolution_store()
        store._store.block_next = True
        task = asyncio.create_task(store.async_record_failure(
            "k:rice",
            query="rice",
            mode="demo",
            reason="TimeoutError",
            now=datetime(2026, 9, 24, tzinfo=timezone.utc),
        ))
        await store._store.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(store.failure_count, 0)

    async def test_concurrent_failures_preserve_both_identities(self):
        store = resolution_store()
        store._store.block_next = True
        first = asyncio.create_task(store.async_record_failure(
            "k:rice", query="rice", mode="demo", reason="TimeoutError",
            now=datetime(2026, 9, 24, tzinfo=timezone.utc),
        ))
        await store._store.started.wait()
        second = asyncio.create_task(store.async_record_failure(
            "k:carrot", query="carrot", mode="demo", reason="TimeoutError",
            now=datetime(2026, 9, 24, tzinfo=timezone.utc),
        ))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        store._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(set(store._data["failures"]), {"k:rice", "k:carrot"})
        self.assertEqual(set(store._store.saved["failures"]), {"k:rice", "k:carrot"})


if __name__ == "__main__":
    unittest.main()
