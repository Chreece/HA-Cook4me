"""Transactional nutrition and recipe-cost-cache regressions."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"
PKG = "cook4me_nutrition_cache_v211"
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
    module.Store = object
    sys.modules[module.__name__] = module
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


nutrition = load("nutrition")
cost_cache = load("recipe_cost_cache")


class Storage:
    def __init__(self, initial=None):
        self.saved = deepcopy(initial)
        self.fail = False
        self.block_next = False
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.writes = 0

    async def async_save(self, data):
        snapshot = deepcopy(data)
        self.writes += 1
        if self.block_next:
            self.block_next = False
            self.started.set()
            await self.release.wait()
        if self.fail:
            raise OSError("disk full")
        self.saved = snapshot


PROFILE = {
    "basisQuantity": 100,
    "basisUnit": "g",
    "values": {"energyKcal": 350, "protein": 7},
}
INGREDIENT = {"key": "rice", "name": "Rice"}


def nutrition_store(data=None):
    store = nutrition.Cook4MeNutritionStore.__new__(nutrition.Cook4MeNutritionStore)
    store._store = Storage(data or {"generic": {}, "stockLots": {}})
    store._data = deepcopy(data or {"generic": {}, "stockLots": {}})
    store._loaded = True
    store._mutation_lock = asyncio.Lock()
    return store


class NutritionTransactionTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_generic_write_is_not_visible(self):
        store = nutrition_store()
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_set_generic("k:rice", INGREDIENT, PROFILE)
        self.assertEqual(store.generic, {})

    async def test_cancelled_generic_write_rolls_back_memory(self):
        store = nutrition_store()
        store._store.block_next = True
        task = asyncio.create_task(
            store.async_set_generic("k:rice", INGREDIENT, PROFILE)
        )
        await store._store.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(store.generic, {})

    async def test_failed_exact_lot_append_is_not_visible(self):
        store = nutrition_store()
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_add_stock_lot(
                INGREDIENT,
                quantity=500,
                unit="g",
                nutrition=PROFILE,
                product_name="Rice package",
            )
        self.assertEqual(store.stock_lots, {})

    async def test_concurrent_generic_writes_preserve_both(self):
        store = nutrition_store()
        store._store.block_next = True
        first = asyncio.create_task(
            store.async_set_generic("k:rice", INGREDIENT, PROFILE)
        )
        await store._store.started.wait()
        second = asyncio.create_task(
            store.async_set_generic(
                "k:carrot",
                {"key": "carrot", "name": "Carrot"},
                {**PROFILE, "values": {"energyKcal": 40}},
            )
        )
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        store._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(set(store.generic), {"k:rice", "k:carrot"})
        self.assertEqual(set(store._store.saved["generic"]), {"k:rice", "k:carrot"})

    async def test_failed_reconcile_restores_removed_exact_lot(self):
        seeded = nutrition_store()
        await seeded.async_add_stock_lot(
            INGREDIENT, quantity=500, unit="g", nutrition=PROFILE
        )
        before = seeded.stock_lots
        seeded._store.fail = True
        with self.assertRaises(OSError):
            await seeded.async_reconcile_inventory([])
        self.assertEqual(seeded.stock_lots, before)

    async def test_failed_consumption_restores_exact_lot_quantity(self):
        store = nutrition_store()
        await store.async_add_stock_lot(
            INGREDIENT, quantity=500, unit="g", nutrition=PROFILE
        )
        before = store.stock_lots
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_consume_report(
                {
                    "deductedLots": [
                        {
                            "identity": "k:rice",
                            "quantity": 100,
                            "unit": "g",
                            "bestBefore": "",
                        }
                    ]
                }
            )
        self.assertEqual(store.stock_lots, before)


class Hass:
    async def async_add_executor_job(self, function):
        return function()


class CostStore:
    settings = {"currency": "EUR", "country": "DE", "autoGlobalPrices": False}
    _data = {"references": {}}


def cache_store():
    bridge = SimpleNamespace(
        hass=Hass(), entry=SimpleNamespace(entry_id="entry")
    )
    cache = cost_cache.Cook4MeRecipeCostCache.__new__(
        cost_cache.Cook4MeRecipeCostCache
    )
    cache._hass = bridge.hass
    cache._lock = asyncio.Lock()
    cache._store = Storage({"entries": {}})
    cache._loaded = True
    cache._data = {"entries": {}}
    return cache


def recipe(ident):
    return {
        "variantFunctionalId": ident,
        "servings": 2,
        "ingredients": [],
    }


class RecipeCostCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original = cost_cache.calculate_recipe_cost
        self.calls = 0

        def calculate(_recipe, _inventory, _store, **_kwargs):
            self.calls += 1
            return {
                "totalsByCurrency": {"EUR": float(self.calls)},
                "ingredients": [],
            }

        cost_cache.calculate_recipe_cost = calculate

    def tearDown(self):
        cost_cache.calculate_recipe_cost = self.original

    async def test_failed_cache_save_does_not_create_memory_hit(self):
        cache = cache_store()
        cache._store.fail = True
        with self.assertRaises(OSError):
            await cache.async_cost(
                recipe("one"), [], CostStore(), currency="EUR", country="DE"
            )
        self.assertEqual(cache._data["entries"], {})

    async def test_cancelled_cache_write_does_not_publish_entry(self):
        cache = cache_store()
        cache._store.block_next = True
        task = asyncio.create_task(
            cache.async_cost(
                recipe("one"), [], CostStore(), currency="EUR", country="DE"
            )
        )
        await cache._store.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(cache._data["entries"], {})

    async def test_successful_retry_becomes_a_real_cache_hit(self):
        cache = cache_store()
        cache._store.fail = True
        with self.assertRaises(OSError):
            await cache.async_cost(
                recipe("one"), [], CostStore(), currency="EUR", country="DE"
            )
        cache._store.fail = False
        first = await cache.async_cost(
            recipe("one"), [], CostStore(), currency="EUR", country="DE"
        )
        second = await cache.async_cost(
            recipe("one"), [], CostStore(), currency="EUR", country="DE"
        )
        self.assertFalse(first["costCacheHit"])
        self.assertTrue(second["costCacheHit"])
        self.assertEqual(self.calls, 2)
        self.assertEqual(cache._data, cache._store.saved)

    async def test_overlapping_cache_writes_preserve_both_keys(self):
        cache = cache_store()
        cache._store.block_next = True
        first = asyncio.create_task(
            cache.async_cost(
                recipe("one"), [], CostStore(), currency="EUR", country="DE"
            )
        )
        await cache._store.started.wait()
        second = asyncio.create_task(
            cache.async_cost(
                recipe("two"), [], CostStore(), currency="EUR", country="DE"
            )
        )
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        cache._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(len(cache._data["entries"]), 2)
        self.assertEqual(cache._data, cache._store.saved)


if __name__ == "__main__":
    unittest.main()
