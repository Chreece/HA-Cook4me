"""Recipe Hub and currency persistence/concurrency regressions."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
from types import ModuleType
from typing import Any
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"
PKG = "cook4me_hub_currency_v212"
package = ModuleType(PKG)
package.__path__ = [str(COMPONENT)]
sys.modules[PKG] = package

filters = ModuleType(PKG + ".shared_recipe_filters")
filters.merge_preferences = lambda old, patch: {**deepcopy(old or {}), **deepcopy(patch or {})}
sys.modules[filters.__name__] = filters


class Storage:
    def __init__(self, initial=None):
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


def validate_location(_profile, metadata):
    return deepcopy(metadata or {})


def add_inventory_item(rows, ingredient, quantity=None, unit="", unlimited=False, best_before="", lot_metadata=None):
    result = deepcopy(rows or [])
    result.append({
        "key": ingredient.get("key"),
        "name": ingredient.get("name"),
        "quantity": quantity,
        "unit": unit,
        "unlimited": unlimited,
        "bestBefore": best_before,
        "lots": [deepcopy(lot_metadata)] if lot_metadata else [],
    })
    return result


def update_inventory_item(rows, identity, **changes):
    result = deepcopy(rows or [])
    for row in result:
        if "k:" + str(row.get("key")) == identity:
            row.update(deepcopy(changes))
    return result


def remove_inventory_item(rows, identity):
    return [deepcopy(row) for row in rows or [] if "k:" + str(row.get("key")) != identity]


def recipe_consumption_items(_recipe, rows):
    return [{"identity": "k:rice", "quantity": 100, "unit": "g"}] if rows else []


def apply_consumption(rows, consumptions):
    result = deepcopy(rows or [])
    if result and consumptions:
        result[0]["quantity"] = max(0, float(result[0].get("quantity") or 0) - 100)
    return result, {"deductedLots": deepcopy(consumptions)}


def consumption_shortfalls(_consumptions, _report):
    return []


def restore_consumption(rows, _report):
    return deepcopy(rows), {"restored": True}


def normalize_manual_recipe(recipe, source="manual"):
    return {**deepcopy(recipe), "source": source}


def score_recipe(_recipe, profile):
    safe = profile.get("marker") != "blocked"
    return {"safe": safe, "violations": [] if safe else ["blocked profile"]}


def recipe_ingredient_names(recipe):
    return [str(row.get("name") or "") for row in recipe.get("ingredients") or []]


# Compile the exact production Recipe Hub methods, while replacing only the
# service/catalog helpers above.
hub_source = ast.parse((COMPONENT / "recipe_hub.py").read_text())
hub_class = next(node for node in hub_source.body if isinstance(node, ast.ClassDef) and node.name == "Cook4MeRecipeHub")
wanted = {
    "_commit",
    "async_set_profile",
    "async_inventory_add",
    "async_inventory_update",
    "async_inventory_remove",
    "async_prepare_consumption",
    "async_confirm_consumption",
    "async_revise_consumption",
    "async_clear_pending_consumption",
    "async_set_user_ui_preferences",
    "async_set_ui_preferences",
    "async_save_recipe",
    "async_delete_recipe",
    "async_record_send",
}
methods = [deepcopy(node) for node in hub_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted]
namespace = {
    "__name__": PKG + ".hub_methods",
    "__package__": PKG,
    "deepcopy": deepcopy,
    "Any": Any,
    "validate_location": validate_location,
    "add_inventory_item": add_inventory_item,
    "update_inventory_item": update_inventory_item,
    "remove_inventory_item": remove_inventory_item,
    "recipe_consumption_items": recipe_consumption_items,
    "apply_consumption": apply_consumption,
    "consumption_shortfalls": consumption_shortfalls,
    "restore_consumption": restore_consumption,
    "normalize_manual_recipe": normalize_manual_recipe,
    "score_recipe": score_recipe,
    "recipe_ingredient_names": recipe_ingredient_names,
    "uuid4": uuid4,
    "datetime": datetime,
    "timezone": timezone,
}
exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])), str(COMPONENT / "recipe_hub.py"), "exec"), namespace)


class Hub:
    def __init__(self):
        self._data = {
            "profile": {"marker": "allowed", "houseIngredients": [], "pantry": []},
            "recipes": [],
            "history": [],
            "uiPreferences": {"lastTab": "official"},
            "userUiPreferences": {},
            "pendingConsumption": None,
            "scannerReceipts": {},
            "receiptScannerReceipts": {},
        }
        self._store = Storage(self._data)
        self._lock = asyncio.Lock()

    @staticmethod
    def _normalize_profile(value):
        return deepcopy(value)

    @staticmethod
    def _normalize_ui_preferences(value):
        return deepcopy(value)

    @property
    def profile(self):
        return deepcopy(self._data["profile"])

    @property
    def recipes(self):
        return deepcopy(self._data["recipes"])

    @property
    def ui_preferences(self):
        return deepcopy(self._data["uiPreferences"])

    @property
    def pending_consumption(self):
        return deepcopy(self._data.get("pendingConsumption"))

    def user_ui_preferences(self, user_id):
        return deepcopy(self._data.get("userUiPreferences", {}).get(user_id, {}))

    def _scoring_profile(self):
        return deepcopy(self._data["profile"])


for name in wanted:
    setattr(Hub, name, namespace[name])


class HubDurabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_profile_save_keeps_previous_profile(self):
        hub = Hub()
        before = hub.profile
        hub._store.fail = True
        with self.assertRaises(OSError):
            await hub.async_set_profile({"marker": "new"})
        self.assertEqual(hub.profile, before)

    async def test_failed_inventory_add_does_not_create_stock(self):
        hub = Hub()
        hub._store.fail = True
        with self.assertRaises(OSError):
            await hub.async_inventory_add({"key": "rice", "name": "Rice"}, quantity=500, unit="g")
        self.assertEqual(hub.profile["houseIngredients"], [])

    async def test_failed_pending_consumption_does_not_appear(self):
        hub = Hub()
        hub._data["profile"]["houseIngredients"] = [{"key": "rice", "name": "Rice", "quantity": 500, "unit": "g"}]
        hub._store.saved = deepcopy(hub._data)
        hub._store.fail = True
        with self.assertRaises(OSError):
            await hub.async_prepare_consumption({"title": "Rice", "servings": 2})
        self.assertIsNone(hub.pending_consumption)

    async def test_failed_confirm_keeps_stock_and_pending_confirmation(self):
        hub = Hub()
        hub._data["profile"]["houseIngredients"] = [{"key": "rice", "name": "Rice", "quantity": 500, "unit": "g"}]
        hub._data["pendingConsumption"] = {"id": "pending", "ingredients": []}
        before = deepcopy(hub._data)
        hub._store.fail = True
        with self.assertRaises(OSError):
            await hub.async_confirm_consumption("pending", [{"identity": "k:rice", "quantity": 100, "unit": "g"}])
        self.assertEqual(hub._data, before)

    async def test_failed_recipe_save_and_delete_do_not_change_recipe_book(self):
        hub = Hub()
        hub._data["recipes"] = [{"id": "old", "title": "Old"}]
        hub._store.saved = deepcopy(hub._data)
        hub._store.fail = True
        with self.assertRaises(OSError):
            await hub.async_save_recipe({"id": "new", "title": "New"})
        self.assertEqual([row["id"] for row in hub.recipes], ["old"])
        with self.assertRaises(OSError):
            await hub.async_delete_recipe("old")
        self.assertEqual([row["id"] for row in hub.recipes], ["old"])

    async def test_failed_user_preferences_and_send_history_are_not_visible(self):
        hub = Hub()
        hub._store.fail = True
        with self.assertRaises(OSError):
            await hub.async_set_user_ui_preferences("user", {"lastTab": "week"})
        self.assertEqual(hub.user_ui_preferences("user"), {})
        with self.assertRaises(OSError):
            await hub.async_record_send({"title": "Meal", "ingredients": []})
        self.assertEqual(hub._data["history"], [])

    async def test_prepare_consumption_uses_stock_after_prior_locked_write(self):
        hub = Hub()
        hub._store.block_next = True
        first = asyncio.create_task(
            hub.async_inventory_add({"key": "rice", "name": "Rice"}, quantity=500, unit="g")
        )
        await hub._store.started.wait()
        second = asyncio.create_task(hub.async_prepare_consumption({"title": "Rice", "servings": 2}))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        hub._store.release.set()
        await first
        pending = await second
        self.assertIsNotNone(pending)
        self.assertEqual(pending["ingredients"][0]["identity"], "k:rice")

    async def test_ai_recipe_is_checked_against_profile_committed_before_it(self):
        hub = Hub()
        hub._store.block_next = True
        profile = asyncio.create_task(hub.async_set_profile({"marker": "blocked"}))
        await hub._store.started.wait()
        recipe_save = asyncio.create_task(hub.async_save_recipe({"id": "ai", "title": "AI"}, source="ai"))
        await asyncio.sleep(0)
        self.assertFalse(recipe_save.done())
        hub._store.release.set()
        await profile
        with self.assertRaisesRegex(ValueError, "blocked profile"):
            await recipe_save
        self.assertEqual(hub.recipes, [])

    async def test_concurrent_recipe_saves_preserve_both(self):
        hub = Hub()
        hub._store.block_next = True
        first = asyncio.create_task(hub.async_save_recipe({"id": "one", "title": "One"}))
        await hub._store.started.wait()
        second = asyncio.create_task(hub.async_save_recipe({"id": "two", "title": "Two"}))
        hub._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual({row["id"] for row in hub.recipes}, {"one", "two"})
        self.assertEqual({row["id"] for row in hub._store.saved["recipes"]}, {"one", "two"})


# Load the production currency store with Home Assistant imports removed.
currency_path = COMPONENT / "currency_fx.py"
currency_tree = ast.parse(currency_path.read_text())
currency_tree.body = [
    node for node in currency_tree.body
    if not (
        isinstance(node, ast.ImportFrom)
        and ((node.module or "").startswith("homeassistant") or node.module == "const")
    )
]
currency = ModuleType(PKG + ".currency_fx")
currency.__package__ = PKG
currency.__file__ = str(currency_path)
currency.DOMAIN = "cook4me"
currency.Store = object
sys.modules[currency.__name__] = currency
exec(compile(currency_tree, str(currency_path), "exec"), currency.__dict__)


class Hass:
    def __init__(self):
        self.result = {"ok": True, "date": "2026-09-24", "rates": {"EUR": 1.0, "USD": 1.2}}
    async def async_add_executor_job(self, _func):
        return deepcopy(self.result)


class CostStore:
    def __init__(self, currency_code=""):
        self.settings = {"currency": currency_code}
        self.calls = []
    async def async_set_settings(self, **values):
        self.calls.append(deepcopy(values))
        self.settings.update(values)


def currency_store():
    obj = currency.Cook4MeCurrencyFxStore.__new__(currency.Cook4MeCurrencyFxStore)
    obj.hass = Hass()
    obj._store = Storage({
        "preference": {"initialized": False, "mode": "auto", "currency": ""},
        "rates": {},
    })
    obj._data = deepcopy(obj._store.saved)
    obj._loaded = True
    obj._lock = asyncio.Lock()
    return obj


class CurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_initial_resolution_does_not_publish_preference(self):
        store = currency_store()
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_resolve_currency("de", CostStore(""))
        self.assertFalse(store.preference["initialized"])

    async def test_failed_manual_preference_keeps_previous_value(self):
        store = currency_store()
        store._data["preference"] = {"initialized": True, "mode": "fixed", "currency": "EUR"}
        store._store.saved = deepcopy(store._data)
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_set_preference(mode="fixed", currency="USD", language="en", cost_store=CostStore("EUR"))
        self.assertEqual(store.preference["currency"], "EUR")

    async def test_failed_rate_refresh_keeps_previous_rates(self):
        store = currency_store()
        old = {"date": "2026-09-23", "fetchedAt": "2026-09-23T00:00:00+00:00", "source": "ecb_reference_rates", "rates": {"EUR": 1.0, "USD": 1.1}}
        store._data["rates"] = deepcopy(old)
        store._store.saved = deepcopy(store._data)
        store._store.fail = True
        with self.assertRaises(OSError):
            await store.async_rates(force=True)
        self.assertEqual(store._data["rates"], old)

    async def test_initial_resolve_cannot_overwrite_later_explicit_preference(self):
        store = currency_store()
        store._store.block_next = True
        cost = CostStore("")
        first = asyncio.create_task(store.async_resolve_currency("de", cost))
        await store._store.started.wait()
        second = asyncio.create_task(store.async_set_preference(mode="fixed", currency="USD", language="en", cost_store=cost))
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        store._store.release.set()
        await first
        await second
        self.assertEqual(store.preference, {"initialized": True, "mode": "fixed", "currency": "USD"})
        self.assertEqual(store._store.saved["preference"]["currency"], "USD")


if __name__ == "__main__":
    unittest.main()
