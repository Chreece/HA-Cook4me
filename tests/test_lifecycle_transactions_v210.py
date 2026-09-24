"""Transactional meal-lifecycle persistence regressions."""
from __future__ import annotations

import ast
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"
PKG = "cook4me_lifecycle_v210"
package = ModuleType(PKG)
package.__path__ = [str(COMPONENT)]
sys.modules[PKG] = package

stock_allocation = ModuleType(PKG + ".stock_allocation")
stock_allocation.allocate_stock = lambda _stock, reqs: [None for _ in reqs]
sys.modules[stock_allocation.__name__] = stock_allocation

inventory = ModuleType(PKG + ".inventory")
inventory.convert_amount = lambda amount, source, target: float(amount) if source == target else None
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


def load():
    path = COMPONENT / "meal_lifecycle.py"
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
    module = ModuleType(PKG + ".meal_lifecycle")
    module.__package__ = PKG
    module.__file__ = str(path)
    module.DOMAIN = "cook4me"
    module.Store = object
    sys.modules[module.__name__] = module
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


life = load()


class Storage:
    def __init__(self, initial):
        self.saved = deepcopy(initial)
        self.fail = False
        self.block_next = False
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def async_save(self, data):
        snapshot = deepcopy(data)
        if self.block_next:
            self.block_next = False
            self.started.set()
            await self.release.wait()
        if self.fail:
            raise OSError("disk full")
        self.saved = snapshot


def recipe(name="Meal", ident="r1"):
    return {
        "id": ident,
        "title": name,
        "language": "en",
        "ingredients": [{"key": "rice", "name": "Rice", "quantity": 100, "unit": "g"}],
        "steps": [{"instruction": "Cook"}],
    }


def slot(ident="s1", stamp="2026-09-24", name="Meal"):
    return {
        "id": ident,
        "date": stamp,
        "mealType": "dinner",
        "selected": True,
        "recipe": recipe(name, "recipe-" + ident),
    }


def base_data():
    return {
        "weekStart": "2026-09-21",
        "slots": [life._slot(slot())],
        "leftovers": [{
            "id": "left-1",
            "mealHistoryId": "meal-1",
            "title": "Leftovers",
            "servings": 2.0,
            "originalServings": 2.0,
            "weightGrams": 400.0,
            "nutrition": {"totals": {"protein": 20.0}},
            "costByCurrency": {"EUR": 4.0},
            "recipe": recipe(),
        }],
        "feedback": {},
        "substitutions": {},
        "mealCosts": {},
        "settings": {
            "mealTypes": ["breakfast", "lunch", "dinner"],
            "weekdayMealTypes": {key: ["breakfast", "lunch", "dinner"] for key in life._WEEKDAY_KEYS},
            "leftoversFirst": True,
            "avoidRecentDays": 7,
            "nutritionTargets": {},
        },
    }


def store():
    obj = life.Cook4MeMealLifecycleStore.__new__(life.Cook4MeMealLifecycleStore)
    obj._data = base_data()
    obj._store = Storage(obj._data)
    obj._loaded = True
    obj._weekly_mutation_lock = asyncio.Lock()
    obj._persistence_mutation_lock = asyncio.Lock()
    return obj


class FailureRollbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_week_replace_keeps_previous_week(self):
        s = store()
        before = s.snapshot()
        s._store.fail = True
        with self.assertRaises(OSError):
            await s.async_replace_week("2026-09-28", [slot("new", "2026-09-28", "New")])
        self.assertEqual(s.snapshot(), before)

    async def test_failed_selection_keeps_previous_selection(self):
        s = store()
        s._store.fail = True
        with self.assertRaises(OSError):
            await s.async_select_slots(["s1"], False)
        self.assertTrue(s.slots[0]["selected"])

    async def test_failed_leftover_consumption_keeps_food_and_amount(self):
        s = store()
        before = s.leftovers
        s._store.fail = True
        with self.assertRaises(OSError):
            await s.async_consume_leftover("left-1", 1)
        self.assertEqual(s.leftovers, before)

    async def test_failed_weight_update_keeps_previous_weight(self):
        s = store()
        s._store.fail = True
        with self.assertRaises(OSError):
            await s.async_set_leftover_weight("left-1", 250)
        self.assertEqual(s.leftovers[0]["weightGrams"], 400)

    async def test_failed_feedback_does_not_appear(self):
        s = store()
        s._store.fail = True
        with self.assertRaises(OSError):
            await s.async_set_feedback(recipe(), rating=5, notes="great")
        self.assertEqual(s._data["feedback"], {})

    async def test_failed_meal_cost_does_not_appear(self):
        s = store()
        s._store.fail = True
        with self.assertRaises(OSError):
            await s.async_record_meal_cost("meal-1", {"totalsByCurrency": {"EUR": 4}})
        self.assertEqual(s._data["mealCosts"], {})

    async def test_failed_substitution_does_not_appear(self):
        s = store()
        s._store.fail = True
        with self.assertRaises(OSError):
            await s.async_approve_substitution(
                {"key": "rice", "name": "Rice"},
                {"key": "bulgur", "name": "Bulgur"},
            )
        self.assertEqual(s._data["substitutions"], {})

    async def test_cancelled_write_rolls_back_memory(self):
        s = store()
        before = s.snapshot()
        s._store.block_next = True
        task = asyncio.create_task(s.async_upsert_slot(slot("s2", name="Second")))
        await s._store.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(s.snapshot(), before)


class ConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_concurrent_slot_writes_keep_both(self):
        s = store()
        s._store.block_next = True
        first = asyncio.create_task(s.async_upsert_slot(slot("s2", name="Second")))
        await s._store.started.wait()
        second = asyncio.create_task(s.async_upsert_slot(slot("s3", name="Third")))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        s._store.release.set()
        await asyncio.gather(first, second)
        ids = {row["id"] for row in s.slots}
        self.assertEqual(ids, {"s1", "s2", "s3"})
        self.assertEqual({row["id"] for row in s._store.saved["slots"]}, ids)

    async def test_leftover_weight_and_feedback_do_not_interleave_storage(self):
        s = store()
        s._store.block_next = True
        first = asyncio.create_task(s.async_set_leftover_weight("left-1", 300))
        await s._store.started.wait()
        second = asyncio.create_task(s.async_set_feedback(recipe(), rating=4))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        s._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(s.leftovers[0]["weightGrams"], 300)
        self.assertIn("id:r1", s._data["feedback"])

    async def test_weekly_mutation_lock_can_wrap_durable_mutation_without_deadlock(self):
        s = store()
        async with s.weekly_mutation():
            await asyncio.wait_for(
                s.async_replace_week("2026-09-28", [slot("new", "2026-09-28")]),
                timeout=1,
            )
        self.assertEqual(s._data["weekStart"], "2026-09-28")


class SuccessTests(unittest.IsolatedAsyncioTestCase):
    async def test_successful_leftover_consumption_updates_memory_and_disk(self):
        s = store()
        consumed = await s.async_consume_leftover_weight("left-1", 100)
        self.assertEqual(consumed["remainingGrams"], 300)
        self.assertEqual(s.leftovers[0]["weightGrams"], 300)
        self.assertEqual(s._store.saved["leftovers"][0]["weightGrams"], 300)

    async def test_successful_settings_write_is_durable(self):
        s = store()
        result = await s.async_set_settings(leftovers_first=False, avoid_recent_days=14)
        self.assertFalse(result["leftoversFirst"])
        self.assertEqual(result["avoidRecentDays"], 14)
        self.assertEqual(s._store.saved["settings"], result)


if __name__ == "__main__":
    unittest.main()
