"""Rolling planner dates, reservations and real WebSocket request handlers."""
import ast
import asyncio
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
import types
import unittest
from unittest.mock import AsyncMock

from test_meal_lifecycle_v20 import load_modules

ROOT = Path(__file__).resolve().parents[1]


def handler(name, namespace):
    # Execute the production handler with explicit boundary fakes, without HA.
    source = ROOT / "custom_components/cook4me/websocket_v20.py"
    tree = ast.parse(source.read_text())
    node = next(row for row in tree.body if isinstance(row, ast.AsyncFunctionDef) and row.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)
    return namespace[name]


class RollingWeekTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        *_, cls.lifecycle = load_modules()

    def store(self):
        return self.lifecycle.Cook4MeMealLifecycleStore(object(), "entry")

    def slot(self, stamp, amount=100):
        return {"id": stamp, "date": stamp, "mealType": "dinner", "recipe": {
            "id": stamp, "title": "Tomato soup", "servings": 1,
            "ingredients": [{"foodKey": "M_FOOD_TOMATO", "foodName": "Tomato", "quantity": amount, "unit": "g"}]}}

    def test_rolling_snapshot_preserves_saved_dates_and_excludes_old_reservations(self):
        store = self.store()
        slots = [self.slot(stamp) for stamp in ("2026-09-07", "2026-09-14", "2026-09-15", "2026-09-21", "2026-09-22")]
        asyncio.run(store.async_replace_week("2026-09-07", slots))
        original = deepcopy(store.slots)
        shown = store.snapshot([], start_date=date(2026, 9, 15))
        self.assertEqual(shown["weekStart"], "2026-09-15")
        self.assertEqual(shown["weekEnd"], "2026-09-21")
        self.assertEqual([row["date"] for row in shown["slots"]], ["2026-09-15", "2026-09-21"])
        self.assertEqual(shown["reservations"]["items"][0]["quantity"], 200)
        self.assertEqual(store.slots, original)
        self.assertEqual(store.snapshot()["weekStart"], "2026-09-07")

    def test_empty_plan_and_year_boundary_keep_a_seven_day_window(self):
        store = self.store()
        shown = store.snapshot([], start_date=date(2026, 12, 29))
        self.assertEqual((shown["weekStart"], shown["weekEnd"]), ("2026-12-29", "2027-01-04"))
        self.assertEqual(shown["slots"], [])
        self.assertEqual(shown["shoppingDelta"], [])

    def boundary(self, store):
        answers = {}
        bridge = types.SimpleNamespace(recipe_hub=types.SimpleNamespace(profile={"houseIngredients": [{"key": "M_FOOD_TOMATO", "name": "Tomato", "quantity": 10, "unit": "g"}]}))
        def fail(_connection, _msg, error):
            raise error
        namespace = {
            "legacy": types.SimpleNamespace(_bridge=lambda *_: bridge, _send_error=fail),
            "meal_lifecycle_store_for_bridge": AsyncMock(return_value=store),
            "_text": lambda value: str(value or "").strip(),
            "rolling_week_start": self.lifecycle.rolling_week_start,
            "dt_util": types.SimpleNamespace(now=lambda: datetime(2026, 9, 15, 1)),
            "v18": types.SimpleNamespace(_languages=lambda _bridge, raw: raw or ["de"]),
            "_generate_week": AsyncMock(return_value={"slotCount": 21}),
            "_state": AsyncMock(return_value={"weekStart": "2026-09-15"}),
            "_shopping_add": AsyncMock(return_value={"added": []}),
        }
        return namespace, types.SimpleNamespace(send_result=lambda key, value: answers.update({key: value})), answers

    def test_generation_starts_on_today_or_requested_future_day_without_monday_rounding(self):
        for raw, expected in [(None, "2026-09-15"), ("2026-09-07", "2026-09-15"), ("2026-09-22", "2026-09-22")]:
            namespace, connection, answers = self.boundary(self.store())
            call = handler("ws_week_generate", namespace)
            asyncio.run(call(None, connection, {"id": 1, "week_start": raw}))
            self.assertEqual(namespace["_generate_week"].await_args.kwargs["week_start"], expected)
            self.assertEqual(answers[1]["slotCount"], 21)

    def test_add_plan_shopping_only_uses_the_visible_seven_day_plan(self):
        store = self.store()
        asyncio.run(store.async_replace_week("2026-09-07", [self.slot("2026-09-07", 900), self.slot("2026-09-15", 100)]))
        namespace, connection, answers = self.boundary(store)
        call = handler("ws_week_add_shopping", namespace)
        asyncio.run(call(None, connection, {"id": 1}))
        rows = namespace["_shopping_add"].await_args.args[1]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["quantity"], 90)
        self.assertEqual(answers[1]["shoppingDelta"], rows)


if __name__ == "__main__":
    unittest.main()
