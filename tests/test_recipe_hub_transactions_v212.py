"""Transactional Recipe Hub persistence regressions."""
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
PKG = "cook4me_recipe_hub_v212"
package = ModuleType(PKG)
package.__path__ = [str(COMPONENT)]
sys.modules[PKG] = package

food = ModuleType(PKG + ".food_intelligence")
food.recipe_quantity_feasibility = lambda *_args, **_kwargs: {
    "quantityCoverage": 1.0, "confidence": "quantity", "items": [],
    "shortages": [], "unknown": [], "fullyAvailable": True,
}
sys.modules[food.__name__] = food

catalog = ModuleType(PKG + ".ingredient_catalog")
catalog.enrich_match_with_house_keys = lambda _recipe, match, _house: deepcopy(match)
sys.modules[catalog.__name__] = catalog

inventory = ModuleType(PKG + ".inventory")
inventory.DEFAULT_EXPIRY_WARNING_DAYS = 7
inventory.inventory_identity = lambda row: (
    "k:" + str(row.get("key")) if isinstance(row, dict) and row.get("key") else ""
)
inventory.normalize_inventory = lambda rows: deepcopy(rows or [])
def add_inventory_item(rows, ingredient, *, quantity=None, unit="", unlimited=False, best_before="", lot_metadata=None):
    result = deepcopy(rows or [])
    result.append({
        "key": ingredient.get("key"), "name": ingredient.get("name", ""),
        "quantity": quantity, "unit": unit, "unlimited": unlimited,
        "lots": ([{"id": (lot_metadata or {}).get("id", "lot"), "quantity": quantity,
                    "bestBefore": best_before}] if not unlimited else []),
    })
    return result
inventory.add_inventory_item = add_inventory_item
inventory.update_inventory_item = lambda rows, identity, **kwargs: deepcopy(rows or [])
inventory.remove_inventory_item = lambda rows, identity: [
    deepcopy(row) for row in rows or [] if inventory.inventory_identity(row) != identity
]
def apply_consumption(rows, requests):
    result = deepcopy(rows or [])
    if result:
        result[0]["quantity"] = max(0, float(result[0].get("quantity") or 0) - 1)
    return result, {"deducted": deepcopy(requests), "deductedLots": []}
inventory.apply_consumption = apply_consumption
inventory.consumption_shortfalls = lambda *_args: []
inventory.restore_consumption = lambda rows, _report: (deepcopy(rows or []), {"restored": True})
inventory.recipe_consumption_items = lambda _recipe, _house: [
    {"identity": "k:rice", "name": "Rice", "quantity": 1, "unit": "g"}
]
inventory.recipe_expiry_priority = lambda *_args, **_kwargs: {"priority": 0, "ingredients": []}
sys.modules[inventory.__name__] = inventory

logic = ModuleType(PKG + ".recipe_logic")
logic.normalize_manual_recipe = lambda recipe, source="manual": {**deepcopy(recipe), "source": source}
logic.normalize_text = lambda value: str(value or "").strip().casefold()
logic.recipe_ingredient_names = lambda recipe: [
    str(row.get("name") or "") for row in recipe.get("ingredients") or [] if isinstance(row, dict)
]
logic.score_recipe = lambda *_args, **_kwargs: {"safe": True, "score": 1}
sys.modules[logic.__name__] = logic

locations = ModuleType(PKG + ".storage_locations")
locations.normalize_locations = lambda rows: deepcopy(rows or [])
locations.edit_location = lambda profile, **_change: deepcopy(profile)
locations.validate_location = lambda _profile, metadata: deepcopy(metadata or {})
sys.modules[locations.__name__] = locations

diet = ModuleType(PKG + ".diet_profiles")
def normalize_profiles(profile):
    return {
        "household": {
            "diet": str(profile.get("diet") or "omnivore"),
            "excludedTerms": list(profile.get("avoid") or []),
            "excludedIngredients": [],
        },
        "members": [],
    }
diet.normalize_profiles = normalize_profiles
diet.normalize_diet = lambda value: deepcopy(value)
diet.text_list = lambda value: list(value or []) if isinstance(value, list) else []
diet.scoring_profile = lambda profile, _filters: deepcopy(profile)
sys.modules[diet.__name__] = diet

shared = ModuleType(PKG + ".shared_recipe_filters")
shared.normalize_preferences = lambda value: deepcopy(value or {})
shared.merge_preferences = lambda old, patch: {**deepcopy(old or {}), **deepcopy(patch or {})}
sys.modules[shared.__name__] = shared


def load():
    path = COMPONENT / "recipe_hub.py"
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
    module = ModuleType(PKG + ".recipe_hub")
    module.__package__ = PKG
    module.__file__ = str(path)
    module.DOMAIN = "cook4me"
    module.HomeAssistant = object
    module.Store = object
    module.dt_util = SimpleNamespace(now=lambda: datetime.now(timezone.utc))
    sys.modules[module.__name__] = module
    exec(compile(tree, str(path), "exec"), module.__dict__)
    return module


hubmod = load()


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


def base_data():
    return {
        "profile": {
            "diet": "vegetarian",
            "allergies": [],
            "avoid": [],
            "preferences": [],
            "householdMembers": [],
            "dietProfiles": normalize_profiles({"diet": "vegetarian"}),
            "excludedIngredients": [],
            "houseIngredients": [{"key": "rice", "name": "Rice", "quantity": 10, "unit": "g", "lots": []}],
            "pantry": ["Rice"],
            "storageLocations": [],
            "scannerAiTaskEntityId": "",
        },
        "recipes": [{"id": "saved", "title": "Saved", "source": "manual"}],
        "history": [],
        "uiPreferences": {
            "catalogLanguage": "auto", "translateResults": True,
            "lastTab": "official", "nutritionGoal": "balanced",
            "recipeLanguageSelections": {}, "recipeServingSelections": {},
        },
        "userUiPreferences": {"user": {"lastTab": "today"}},
        "pendingConsumption": None,
    }


def hub():
    obj = hubmod.Cook4MeRecipeHub.__new__(hubmod.Cook4MeRecipeHub)
    obj.hass = object()
    obj.entry_id = "entry"
    obj._data = base_data()
    obj._store = Storage(obj._data)
    obj._lock = asyncio.Lock()
    return obj


class FailedWriteRollbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_profile_save_keeps_previous_profile(self):
        h = hub()
        before = h.profile
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_set_profile({"preferences": ["spicy"]})
        self.assertEqual(h.profile, before)

    async def test_failed_inventory_add_keeps_previous_stock(self):
        h = hub()
        before = h.profile
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_inventory_add(
                {"key": "carrot", "name": "Carrot"}, quantity=2, unit="g"
            )
        self.assertEqual(h.profile, before)

    async def test_failed_prepare_consumption_does_not_publish_pending_confirmation(self):
        h = hub()
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_prepare_consumption(
                {"title": "Meal", "servings": 2, "ingredients": [{"name": "Rice"}]}
            )
        self.assertIsNone(h.pending_consumption)

    async def test_failed_confirm_consumption_keeps_stock_and_pending_request(self):
        h = hub()
        pending = await h.async_prepare_consumption(
            {"title": "Meal", "servings": 2, "ingredients": [{"name": "Rice"}]}
        )
        before = h.snapshot()
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_confirm_consumption(
                pending["id"], [{"identity": "k:rice", "quantity": 1, "unit": "g"}]
            )
        self.assertEqual(h.snapshot(), before)

    async def test_failed_user_preference_save_keeps_previous_user_preferences(self):
        h = hub()
        before = h.user_ui_preferences("user")
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_set_user_ui_preferences("user", {"lastTab": "week"})
        self.assertEqual(h.user_ui_preferences("user"), before)

    async def test_failed_global_ui_preference_save_keeps_previous_preferences(self):
        h = hub()
        before = h.ui_preferences
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_set_ui_preferences({"catalogLanguage": "el"})
        self.assertEqual(h.ui_preferences, before)

    async def test_failed_recipe_save_does_not_create_memory_only_recipe(self):
        h = hub()
        before = h.recipes
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_save_recipe({"title": "New recipe", "ingredients": []})
        self.assertEqual(h.recipes, before)

    async def test_failed_recipe_delete_keeps_recipe(self):
        h = hub()
        before = h.recipes
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_delete_recipe("saved")
        self.assertEqual(h.recipes, before)

    async def test_failed_send_history_write_does_not_affect_habit_history(self):
        h = hub()
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_record_send(
                {"title": "Rice", "ingredients": [{"name": "Rice"}]}
            )
        self.assertEqual(h.snapshot()["history"], [])

    async def test_cancelled_ui_preference_write_rolls_back(self):
        h = hub()
        before = h.ui_preferences
        h._store.block_next = True
        task = asyncio.create_task(
            h.async_set_ui_preferences({"catalogLanguage": "el"})
        )
        await h._store.started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(h.ui_preferences, before)


class ConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_second_mutation_waits_and_preserves_first_success(self):
        h = hub()
        h._store.block_next = True
        first = asyncio.create_task(
            h.async_set_user_ui_preferences("user", {"lastTab": "week"})
        )
        await h._store.started.wait()
        second = asyncio.create_task(
            h.async_save_recipe({"title": "Concurrent", "ingredients": []})
        )
        await asyncio.sleep(0)
        self.assertFalse(second.done())
        h._store.release.set()
        await asyncio.gather(first, second)
        self.assertEqual(h.user_ui_preferences("user")["lastTab"], "week")
        self.assertIn("Concurrent", [row["title"] for row in h.recipes])
        self.assertEqual(h.snapshot(), h._store.saved)

    async def test_failed_second_mutation_does_not_roll_back_first_success(self):
        h = hub()
        await h.async_set_ui_preferences({"catalogLanguage": "el"})
        durable = h.snapshot()
        h._store.fail = True
        with self.assertRaises(OSError):
            await h.async_save_recipe({"title": "Should fail", "ingredients": []})
        self.assertEqual(h.snapshot(), durable)


class StagedPathsRemainValidTests(unittest.IsolatedAsyncioTestCase):
    async def test_storage_location_staged_path_still_publishes_after_save(self):
        h = hub()
        result = await h.async_storage_location(action="save", name="Desk", kind="other")
        self.assertEqual(result, h.profile)
        self.assertEqual(h.snapshot(), h._store.saved)


if __name__ == "__main__":
    unittest.main()
