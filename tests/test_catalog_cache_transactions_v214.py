"""Ingredient-catalog and recipe-cache transaction regressions."""
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
PKG = "cook4me_catalog_cache_v214"
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


catalog = load("ingredient_catalog")
recipe_cache = load("recipe_cache")


class Storage:
    def __init__(self, initial=None):
        self.initial = deepcopy(initial)
        self.saved = deepcopy(initial)
        self.fail = False
        self.block_next = False
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.delayed = None

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

    def async_delay_save(self, callback, _delay):
        self.delayed = callback


def catalog_store(data=None):
    obj = catalog.Cook4MeIngredientCatalogCache.__new__(
        catalog.Cook4MeIngredientCatalogCache
    )
    obj._data = deepcopy(data or {})
    obj._store = Storage(obj._data)
    obj._lock = asyncio.Lock()
    return obj


def recipe_store(data=None):
    obj = recipe_cache.Cook4MeRecipeCache.__new__(
        recipe_cache.Cook4MeRecipeCache
    )
    obj._data = deepcopy(data or {
        "search": {},
        "detail": {"one": {
            "value": {"title": "Meal"},
            "timestamp": 1.0,
            "checkedAt": 1.0,
            "updatedAt": 1.0,
            "accessedAt": 1.0,
            "fingerprint": "x",
            "lastError": "",
        }},
        "translation": {},
        "ui": {},
    })
    obj._store = Storage(obj._data)
    obj._lock = asyncio.Lock()
    return obj


ROWS_EN = [{"key": "rice", "name": "Rice"}]
ROWS_EL = [{"key": "rice", "name": "Ρύζι"}]


class IngredientCatalogTransactionTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_language_save_does_not_publish_new_catalog(self):
        store = catalog_store({
            "en": {"timestamp": 9999999999.0, "source": "seed", "items": ROWS_EN}
        })
        before = deepcopy(store._data)
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_set("el", ROWS_EL, source="test")
        self.assertEqual(store._data, before)

    async def test_cancelled_language_save_does_not_publish_new_catalog(self):
        store = catalog_store()
        store._store.block_next = True
        task = asyncio.create_task(store.async_set("el", ROWS_EL, source="test"))
        await store._store.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(store._data, {})

    async def test_concurrent_language_saves_preserve_both(self):
        store = catalog_store()
        store._store.block_next = True
        first = asyncio.create_task(store.async_set("en", ROWS_EN, source="test"))
        await store._store.started.wait()
        second = asyncio.create_task(store.async_set("el", ROWS_EL, source="test"))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        store._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(set(store._data), {"en", "el"})
        self.assertEqual(set(store._store.saved), {"en", "el"})


class IngredientCatalogFirstLoadTests(unittest.IsolatedAsyncioTestCase):
    async def test_websocket_cache_first_access_constructs_one_store(self):
        source = ast.parse((COMPONENT / "websocket_v11.py").read_text())
        fn = next(
            deepcopy(node) for node in source.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_cache"
        )

        constructed = 0
        started = asyncio.Event()
        release = asyncio.Event()

        class BarrierCache:
            def __init__(self, *_args):
                nonlocal constructed
                constructed += 1
            async def async_load(self):
                started.set()
                await release.wait()

        ns = {
            "__name__": PKG + ".v11_cache_test",
            "__package__": PKG,
            "Cook4MeIngredientCatalogCache": BarrierCache,
        }
        exec(
            compile(
                ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                str(COMPONENT / "websocket_v11.py"),
                "exec",
            ),
            ns,
        )
        bridge = SimpleNamespace(
            hass=object(), entry=SimpleNamespace(entry_id="entry")
        )
        first = asyncio.create_task(ns["_cache"](bridge))
        await started.wait()
        second = asyncio.create_task(ns["_cache"](bridge))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        release.set()
        one, two = await asyncio.gather(first, second)
        self.assertIs(one, two)
        self.assertEqual(constructed, 1)


class RecipeCacheClearTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_bucket_clear_keeps_previous_cache(self):
        store = recipe_store()
        before = deepcopy(store._data)
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_clear("detail")
        self.assertEqual(store._data, before)

    async def test_cancelled_full_clear_keeps_previous_cache(self):
        store = recipe_store()
        before = deepcopy(store._data)
        store._store.block_next = True
        task = asyncio.create_task(store.async_clear())
        await store._store.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(store._data, before)

    async def test_successful_clear_updates_memory_and_disk(self):
        store = recipe_store()
        await store.async_clear("detail")
        self.assertEqual(store._data["detail"], {})
        self.assertEqual(store._store.saved["detail"], {})

    async def test_delayed_set_behavior_is_unchanged(self):
        store = recipe_store({"search": {}, "detail": {}, "translation": {}, "ui": {}})
        await store.async_set("detail", "new", {"title": "Meal"})
        self.assertIsNotNone(store._store.delayed)
        delayed = store._store.delayed()
        self.assertIn("new", delayed["detail"])


if __name__ == "__main__":
    unittest.main()
