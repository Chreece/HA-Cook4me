"""Retry/idempotency regressions for leftover consumption transactions."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"
PKG = "cook4me_leftover_v216"
package = ModuleType(PKG)
package.__path__ = [str(COMPONENT)]
sys.modules[PKG] = package

food = ModuleType(PKG + ".food_intelligence")
food.allocate_meal_nutrition = lambda _totals, servings, _allocations: {
    "allocations": [],
    "assignedServings": servings,
    "unassignedServings": 0.0,
}
sys.modules[food.__name__] = food

inventory = ModuleType(PKG + ".inventory")
inventory.inventory_identity = lambda row: (
    "k:" + str(row.get("key")) if isinstance(row, dict) and row.get("key") else ""
)
inventory.normalize_inventory = lambda rows: deepcopy(rows or [])
inventory.convert_amount = lambda amount, source, target: (
    float(amount) if source == target else None
)
sys.modules[inventory.__name__] = inventory

stock = ModuleType(PKG + ".stock_allocation")
stock.allocate_stock = lambda _inventory, requests: [None for _ in requests]
sys.modules[stock.__name__] = stock

today = ModuleType(PKG + ".today_logic")
today.recipe_identity = lambda row: (
    "id:" + str(row.get("id")) if isinstance(row, dict) and row.get("id") else ""
)
sys.modules[today.__name__] = today


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


lifecycle = load("meal_lifecycle")
history = load("meal_history")


class Storage:
    def __init__(self, initial):
        self.saved = deepcopy(initial)
        self.calls = 0
        self.fail_on = set()

    async def async_save(self, data):
        self.calls += 1
        if self.calls in self.fail_on:
            raise OSError("simulated storage failure")
        self.saved = deepcopy(data)


def life_store():
    obj = lifecycle.Cook4MeMealLifecycleStore.__new__(
        lifecycle.Cook4MeMealLifecycleStore
    )
    obj._loaded = True
    obj._weekly_mutation_lock = asyncio.Lock()
    obj._persistence_mutation_lock = asyncio.Lock()
    obj._data = {
        "weekStart": "2026-09-21",
        "slots": [],
        "leftovers": [{
            "id": "left-1",
            "title": "Rice",
            "servings": 2.0,
            "originalServings": 2.0,
            "weightGrams": 400.0,
            "originalWeightGrams": 400.0,
            "nutrition": {"totals": {"protein": 20.0}},
            "costByCurrency": {"EUR": 4.0},
            "recipe": {"id": "recipe-1", "title": "Rice"},
        }],
        "feedback": {},
        "substitutions": {},
        "mealCosts": {},
        "leftoverOperations": {},
        "settings": {
            "mealTypes": ["breakfast", "lunch", "dinner"],
            "weekdayMealTypes": {
                key: ["breakfast", "lunch", "dinner"]
                for key in lifecycle._WEEKDAY_KEYS
            },
            "leftoversFirst": True,
            "avoidRecentDays": 7,
            "nutritionTargets": {},
        },
    }
    obj._store = Storage(obj._data)
    return obj


def history_store():
    obj = history.Cook4MeMealHistoryStore.__new__(
        history.Cook4MeMealHistoryStore
    )
    obj._loaded = True
    obj._lock = asyncio.Lock()
    obj._data = {"meals": []}
    obj._store = Storage(obj._data)
    return obj


async def record_with(store, consumed, record_id):
    return await store.async_record(
        recipe={
            "title": consumed.get("title"),
            "servings": consumed.get("servings"),
        },
        nutrition=consumed.get("nutrition") or {},
        consumption={},
        record_id=record_id,
    )


class HistoryIdentityTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_record_id_is_idempotent(self):
        store = history_store()
        first = await record_with(
            store,
            {"title": "Rice", "servings": 1, "nutrition": {"totals": {}}},
            "leftover-request-123456",
        )
        second = await record_with(
            store,
            {"title": "Changed title", "servings": 1, "nutrition": {"totals": {}}},
            "leftover-request-123456",
        )
        self.assertEqual(first, second)
        self.assertEqual(len(store.recent()), 1)


class LeftoverTransactionTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_after_final_save_failure_consumes_once(self):
        life = life_store()
        hist = history_store()

        # 1 = durable prepared intent, 2 = final lifecycle commit.
        life._store.fail_on = {2}
        with self.assertRaises(OSError):
            await life.async_consume_leftover_transaction(
                request_id="request-1234567890",
                leftover_id="left-1",
                amount=1,
                mode="servings",
                record_history=lambda consumed, record_id: record_with(
                    hist, consumed, record_id
                ),
                cost_source="leftover",
            )

        # The prepared intent is durable, but the leftover has not yet changed.
        self.assertEqual(life.leftovers[0]["servings"], 2.0)
        self.assertEqual(len(hist.recent()), 1)
        self.assertEqual(
            life._data["leftoverOperations"]["request-1234567890"]["status"],
            "prepared",
        )

        life._store.fail_on.clear()
        result = await life.async_consume_leftover_transaction(
            request_id="request-1234567890",
            leftover_id="left-1",
            amount=1,
            mode="servings",
            record_history=lambda consumed, record_id: record_with(
                hist, consumed, record_id
            ),
            cost_source="leftover",
        )

        self.assertEqual(result["consumed"]["servings"], 1.0)
        self.assertEqual(life.leftovers[0]["servings"], 1.0)
        self.assertEqual(len(hist.recent()), 1)
        self.assertEqual(
            life._data["leftoverOperations"]["request-1234567890"]["status"],
            "applied",
        )

    async def test_applied_retry_returns_same_result_without_new_history(self):
        life = life_store()
        calls = 0

        async def recorder(consumed, record_id):
            nonlocal calls
            calls += 1
            return {"id": record_id, "title": consumed.get("title")}

        first = await life.async_consume_leftover_transaction(
            request_id="request-abcdefghijkl",
            leftover_id="left-1",
            amount=1,
            mode="servings",
            record_history=recorder,
            cost_source="leftover",
        )
        second = await life.async_consume_leftover_transaction(
            request_id="request-abcdefghijkl",
            leftover_id="left-1",
            amount=1,
            mode="servings",
            record_history=recorder,
            cost_source="leftover",
        )
        self.assertEqual(first, second)
        self.assertEqual(calls, 1)
        self.assertEqual(life.leftovers[0]["servings"], 1.0)

    async def test_same_request_id_with_different_amount_is_rejected(self):
        life = life_store()
        hist = history_store()
        life._store.fail_on = {2}
        with self.assertRaises(OSError):
            await life.async_consume_leftover_transaction(
                request_id="request-different-01",
                leftover_id="left-1",
                amount=1,
                mode="servings",
                record_history=lambda consumed, record_id: record_with(
                    hist, consumed, record_id
                ),
                cost_source="leftover",
            )
        life._store.fail_on.clear()
        with self.assertRaisesRegex(ValueError, "different amount"):
            await life.async_consume_leftover_transaction(
                request_id="request-different-01",
                leftover_id="left-1",
                amount=0.5,
                mode="servings",
                record_history=lambda consumed, record_id: record_with(
                    hist, consumed, record_id
                ),
                cost_source="leftover",
            )
        self.assertEqual(life.leftovers[0]["servings"], 2.0)

    async def test_new_request_is_blocked_while_previous_intent_is_pending(self):
        life = life_store()
        hist = history_store()
        life._store.fail_on = {2}
        with self.assertRaises(OSError):
            await life.async_consume_leftover_transaction(
                request_id="request-pending-0001",
                leftover_id="left-1",
                amount=1,
                mode="servings",
                record_history=lambda consumed, record_id: record_with(
                    hist, consumed, record_id
                ),
                cost_source="leftover",
            )
        life._store.fail_on.clear()
        with self.assertRaisesRegex(ValueError, "previous leftover action"):
            await life.async_consume_leftover_transaction(
                request_id="request-pending-0002",
                leftover_id="left-1",
                amount=1,
                mode="servings",
                record_history=lambda consumed, record_id: record_with(
                    hist, consumed, record_id
                ),
                cost_source="leftover",
            )

    async def test_weight_retry_scales_once(self):
        life = life_store()
        hist = history_store()
        life._store.fail_on = {2}
        with self.assertRaises(OSError):
            await life.async_consume_leftover_transaction(
                request_id="request-weight-000001",
                leftover_id="left-1",
                amount=100,
                mode="weight",
                record_history=lambda consumed, record_id: record_with(
                    hist, consumed, record_id
                ),
                cost_source="leftover_scale",
            )
        life._store.fail_on.clear()
        result = await life.async_consume_leftover_transaction(
            request_id="request-weight-000001",
            leftover_id="left-1",
            amount=100,
            mode="weight",
            record_history=lambda consumed, record_id: record_with(
                hist, consumed, record_id
            ),
            cost_source="leftover_scale",
        )
        self.assertEqual(result["consumed"]["grams"], 100.0)
        self.assertEqual(life.leftovers[0]["weightGrams"], 300.0)
        self.assertEqual(life.leftovers[0]["servings"], 1.5)
        self.assertEqual(len(hist.recent()), 1)


if __name__ == "__main__":
    unittest.main()
