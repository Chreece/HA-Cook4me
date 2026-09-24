"""Persistence race regressions over the production store classes."""
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
PKG = "cook4me_persistence_v209"
package = ModuleType(PKG)
package.__path__ = [str(COMPONENT)]
sys.modules[PKG] = package

# Small service-boundary stubs. Production class/function bodies are executed
# unchanged; only Home Assistant and unrelated catalog helpers are replaced.
food = ModuleType(PKG + ".food_intelligence")
def allocate_meal_nutrition(_totals, servings, allocations):
    rows = []
    assigned = 0.0
    for raw in allocations or []:
        if not isinstance(raw, dict):
            continue
        amount = float(raw.get("servings") or 0)
        assigned += amount
        rows.append({"name": str(raw.get("name") or ""), "servings": amount, "nutrition": {}})
    return {
        "allocations": rows,
        "assignedServings": assigned if rows else servings,
        "unassignedServings": max(0.0, float(servings or 0) - assigned) if rows else 0.0,
    }
food.allocate_meal_nutrition = allocate_meal_nutrition
sys.modules[food.__name__] = food

inventory = ModuleType(PKG + ".inventory")
inventory.inventory_identity = lambda row: (
    "k:" + str(row.get("key")) if isinstance(row, dict) and row.get("key") else ""
)
inventory.normalize_inventory = lambda value: deepcopy(value or [])
sys.modules[inventory.__name__] = inventory

today_logic = ModuleType(PKG + ".today_logic")
today_logic.recipe_identity = lambda row: (
    "id:" + str(row.get("id")) if isinstance(row, dict) and row.get("id") else ""
)
sys.modules[today_logic.__name__] = today_logic

today_multilang = ModuleType(PKG + ".today_multilang")
today_multilang.compact_suggestion_history = lambda value: deepcopy(value or [])
sys.modules[today_multilang.__name__] = today_multilang

locks = {}
store_helpers = ModuleType(PKG + ".store_helpers")
@asynccontextmanager
async def store_load_lock(bridge, name):
    lock = locks.setdefault((id(bridge), name), asyncio.Lock())
    async with lock:
        yield
store_helpers.store_load_lock = store_load_lock
sys.modules[store_helpers.__name__] = store_helpers


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


today = load("today_plan_store")
history = load("meal_history")
scale = load("smart_scale")


class Storage:
    def __init__(self, initial=None):
        self.initial = deepcopy(initial)
        self.saved = deepcopy(initial)
        self.fail_save = False
        self.fail_remove = False
        self.block_next_save = False
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def async_load(self):
        return deepcopy(self.initial)

    async def async_save(self, data):
        snapshot = deepcopy(data)
        if self.block_next_save:
            self.block_next_save = False
            self.started.set()
            await self.release.wait()
        if self.fail_save:
            raise OSError("disk full")
        self.saved = snapshot

    async def async_remove(self):
        if self.fail_remove:
            raise OSError("disk full")
        self.saved = None


def today_store(old=None):
    store = today.Cook4MeTodayPlanStore.__new__(today.Cook4MeTodayPlanStore)
    store._store = Storage(old)
    store._loaded = True
    store._data = deepcopy(old)
    store._lock = asyncio.Lock()
    return store


def history_store(meals=None):
    store = history.Cook4MeMealHistoryStore.__new__(history.Cook4MeMealHistoryStore)
    store._store = Storage({"meals": deepcopy(meals or [])})
    store._loaded = True
    store._data = {"meals": deepcopy(meals or [])}
    store._lock = asyncio.Lock()
    return store


def scale_store(data=None):
    store = scale.Cook4MeSmartScaleStore.__new__(scale.Cook4MeSmartScaleStore)
    store._store = Storage(data or {"selectedEntityId": "", "containers": [], "sessions": {}})
    store._loaded = True
    store._data = deepcopy(data or {"selectedEntityId": "", "containers": [], "sessions": {}})
    store._lock = asyncio.Lock()
    return store


def plan(title):
    return {"date": "2026-09-24", "items": [{"id": title, "title": title}], "suggestionHistory": []}


class TodayStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_plan_save_never_publishes_phantom_plan(self):
        old = today.compact_today_result(plan("Old"))
        store = today_store(old)
        store._store.fail_save = True
        with self.assertRaises(OSError):
            await store.async_set(plan("New"))
        self.assertEqual(store.snapshot, old)

    async def test_failed_clear_keeps_last_durable_plan(self):
        old = today.compact_today_result(plan("Old"))
        store = today_store(old)
        store._store.fail_remove = True
        with self.assertRaises(OSError):
            await store.async_clear()
        self.assertEqual(store.snapshot, old)

    async def test_overlapping_plan_writes_commit_in_call_order(self):
        store = today_store(today.compact_today_result(plan("Seed")))
        store._store.block_next_save = True
        first = asyncio.create_task(store.async_set(plan("First")))
        await store._store.started.wait()
        second = asyncio.create_task(store.async_set(plan("Second")))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        store._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(store.snapshot["items"][0]["title"], "Second")
        self.assertEqual(store._store.saved["items"][0]["title"], "Second")


class MealHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_record_is_not_visible_in_history(self):
        store = history_store()
        store._store.fail_save = True
        with self.assertRaises(OSError):
            await store.async_record(recipe={"title": "Meal", "servings": 2}, nutrition={"totals": {"protein": 10}})
        self.assertEqual(store.recent(), [])

    async def test_failed_history_edit_keeps_previous_record(self):
        store = history_store()
        row = await store.async_record(recipe={"title": "Meal", "servings": 2}, nutrition={"totals": {"protein": 10}})
        before = store.get(row["id"])
        store._store.fail_save = True
        with self.assertRaises(OSError):
            await store.async_update(row["id"], allocations=[{"name": "Chris", "servings": 1}])
        self.assertEqual(store.get(row["id"]), before)

    async def test_concurrent_meals_are_not_lost(self):
        store = history_store()
        store._store.block_next_save = True
        first = asyncio.create_task(store.async_record(recipe={"title": "First", "servings": 1}, nutrition={"totals": {"protein": 1}}))
        await store._store.started.wait()
        second = asyncio.create_task(store.async_record(recipe={"title": "Second", "servings": 1}, nutrition={"totals": {"protein": 2}}))
        store._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual({row["title"] for row in store.recent()}, {"First", "Second"})
        self.assertEqual(len(store._store.saved["meals"]), 2)


class SmartScaleStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_scale_selection_keeps_previous_selection(self):
        store = scale_store({"selectedEntityId": "sensor.old", "containers": [], "sessions": {}})
        store._store.fail_save = True
        with self.assertRaises(OSError):
            await store.async_select_entity("sensor.new")
        self.assertEqual(store.selected_entity_id, "sensor.old")

    async def test_failed_container_save_does_not_create_container(self):
        store = scale_store()
        store._store.fail_save = True
        with self.assertRaises(OSError):
            await store.async_save_container("Bowl", 120)
        self.assertEqual(store.containers, [])

    async def test_failed_session_write_does_not_publish_measurement(self):
        store = scale_store()
        store._store.fail_save = True
        recipe = {"id": "r1", "title": "Recipe"}
        with self.assertRaises(OSError):
            await store.async_record_measurement(
                recipe, ingredient_index=0, ingredient={"key": "rice", "name": "Rice"}, grams=125
            )
        self.assertIsNone(store.session_for(recipe))

    async def test_concurrent_container_saves_preserve_both(self):
        store = scale_store()
        store._store.block_next_save = True
        first = asyncio.create_task(store.async_save_container("Bowl", 100))
        await store._store.started.wait()
        second = asyncio.create_task(store.async_save_container("Plate", 200))
        store._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual({row["name"] for row in store.containers}, {"Bowl", "Plate"})

    async def test_concurrent_measurements_preserve_different_ingredients(self):
        store = scale_store()
        store._store.block_next_save = True
        recipe = {"id": "r1", "title": "Recipe"}
        first = asyncio.create_task(store.async_record_measurement(
            recipe, ingredient_index=0, ingredient={"key": "rice", "name": "Rice"}, grams=125
        ))
        await store._store.started.wait()
        second = asyncio.create_task(store.async_record_measurement(
            recipe, ingredient_index=1, ingredient={"key": "carrot", "name": "Carrot"}, grams=80
        ))
        store._store.release.set()
        await asyncio.gather(first, second)
        rows = store.session_for(recipe)["measurements"]
        self.assertEqual({row["ingredientIndex"] for row in rows}, {0, 1})

    async def test_failed_session_clear_keeps_session(self):
        store = scale_store()
        recipe = {"id": "r1", "title": "Recipe"}
        await store.async_set_batch_weight(recipe, 700)
        store._store.fail_save = True
        with self.assertRaises(OSError):
            await store.async_clear_session(recipe)
        self.assertEqual(store.session_for(recipe)["batchWeightGrams"], 700)


class SmartScaleFirstLoadTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_first_access_returns_one_loaded_store(self):
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
                return {"selectedEntityId": "", "containers": [], "sessions": {}}
            async def async_save(self, _data):
                pass

        original = scale.Store
        scale.Store = BarrierStore
        bridge = SimpleNamespace(hass=object(), entry=SimpleNamespace(entry_id="entry"))
        try:
            first = asyncio.create_task(scale.smart_scale_store_for_bridge(bridge))
            await started.wait()
            second = asyncio.create_task(scale.smart_scale_store_for_bridge(bridge))
            await asyncio.sleep(0)
            self.assertFalse(second.done())
            release.set()
            one, two = await asyncio.gather(first, second)
            self.assertIs(one, two)
            self.assertIs(bridge._smart_scale_store, one)
            self.assertEqual(constructed, 1)
        finally:
            scale.Store = original


if __name__ == "__main__":
    unittest.main()
