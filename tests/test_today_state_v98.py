"""Real offline catalog -> shared filters -> Today/Official WebSocket results."""
import asyncio
from copy import deepcopy
from datetime import datetime
import importlib
import json
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/cook4me"
PREFIX = "cook4me_today_v98_test"
LANGUAGES = ["de", "en", "fr", "es", "it"]
MEALS = ["breakfast", "starter", "salad", "soup", "main", "side", "dessert", "snack"]


class MemoryStore:
    def __init__(self, *args):
        self.data = None
    async def async_load(self):
        return deepcopy(self.data)
    async def async_save(self, value):
        self.data = deepcopy(value)
    async def async_remove(self):
        self.data = None


async def run_today():
    package = types.ModuleType(PREFIX)
    package.__path__ = [str(COMPONENT)]
    identity = lambda value: value
    ws = types.SimpleNamespace(websocket_command=lambda _: identity, async_response=identity)
    modules = {
        PREFIX: package,
        "homeassistant.core": types.SimpleNamespace(HomeAssistant=object, callback=identity),
        "homeassistant.components": types.SimpleNamespace(websocket_api=ws),
        "homeassistant.helpers.storage": types.SimpleNamespace(Store=MemoryStore),
        "homeassistant.util": types.SimpleNamespace(dt=types.SimpleNamespace(now=datetime.now)),
        "voluptuous": types.SimpleNamespace(Required=lambda value, **_: value, Optional=lambda value, **_: value,
            All=lambda *args: None, Any=lambda *args: None, In=lambda _: None, Coerce=lambda _: None, Range=lambda **kwargs: None),
    }
    modules.update({f"{PREFIX}.websocket_v{n}": types.SimpleNamespace() for n in (5, 7, 9, 10, 18, 20, 28)})
    modules[f"{PREFIX}.websocket_v5"]._default_ai_task_entity_id = lambda _: None
    modules[f"{PREFIX}.websocket_v18"] = types.SimpleNamespace(
        _DIET_FILTERS=["profile", "omnivore", "vegetarian", "vegan"], _languages=lambda bridge, raw: raw,
        _recent_identities=lambda *args, **kwargs: set())
    events, responses = [], {}
    main_thread = threading.get_ident()
    def fire(kind, event):
        assert threading.get_ident() == main_thread, "HA progress fired from the executor thread"
        events.append(deepcopy(event))
    async def executor(function, *args):
        return await asyncio.to_thread(function, *args)
    hass = types.SimpleNamespace(async_add_executor_job=executor, data={}, bus=types.SimpleNamespace(async_fire=fire))
    profile = {"diet": "vegetarian", "houseIngredients": []}
    bridge = types.SimpleNamespace(hass=hass, entry=types.SimpleNamespace(entry_id="entry", data={"language": "de", "country": "DE"}),
        recipe_hub=types.SimpleNamespace(profile=profile, habit_terms=[], annotate=deepcopy),
        can_accept_recipe=False, loaded_recipe=None,
        _nutrition_store=types.SimpleNamespace(generic={}, stock_lots={}),
        _meal_history_store=types.SimpleNamespace(recent=lambda _: []))
    def fail(*args):
        raise AssertionError(str(args))
    modules[f"{PREFIX}.websocket"] = types.SimpleNamespace(_bridge=lambda *_: bridge, _send_error=fail)
    with patch.dict(sys.modules, modules):
        v30 = importlib.import_module(f"{PREFIX}.websocket_v30")
        release = importlib.import_module(f"{PREFIX}.release_catalog")
        # Both endpoints must stay offline, including all enrichment work.
        import urllib.request
        with patch.object(urllib.request, "urlopen", side_effect=AssertionError("offline flow used network")):
            await hass.async_add_executor_job(release.load_release_catalog)
            connection = types.SimpleNamespace(send_result=lambda ident, result: responses.update({ident: result}))
            languages = importlib.import_module(f"{PREFIX}.recipe_languages").language_options()
            languages = [row["code"] for row in languages]
            filters = {"languages": languages, "mealTypes": MEALS, "diet": "vegetarian", "dietProfile": "manual", "preferExpiring": True}
            plans = []
            for number in range(3):
                await v30.ws_today_suggest(hass, connection, {"id": number, "entry_id": "entry", "languages": languages, "ui_language": "el",
                    "meal_types": MEALS, "shared_filters": filters, "group_by_meal_type": True, "meal_count": 8})
                plans.append(responses[number])
                # Recreate the HA store to prove the next request reads durable history.
                previous_store = bridge._today_plan_store
                store = type(previous_store)(bridge)
                store._store.data = deepcopy(previous_store._store.data)
                await store.async_load()
                bridge._today_plan_store = store
            return {"plans": plans, "saved": store.snapshot, "filters": filters}

class TodayStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from test_today_multilang import load_package_module
        cls.selection = load_package_module("today_multilang", "today_multilang.py")

    def rows(self, size=5, language="en", category="main"):
        return [{"title": f"Recipe {i}", "displayFamilyId": f"family-{i}", "groupingFunctionalId": str(i),
                 "todayCatalogLanguage": language, "mealTypes": [category], "match": {"score": 100-i}}
                for i in range(size)]

    def test_rotation_exhausts_families_before_repeating_and_survives_compaction(self):
        rows = self.rows()
        original = deepcopy(rows)
        plan, families = {}, []
        for _ in range(7):
            plan = self.selection.select_today_categories(rows, ["main"], ["en"], plan.get("items", []), plan.get("suggestionHistory", []))
            families.append(plan["items"][0]["displayFamilyId"])
        self.assertEqual(len(set(families[:5])), 5)
        self.assertEqual(families[5:], families[:2])
        self.assertEqual(rows, original)

    def test_language_balance_and_editions_do_not_create_duplicate_meals(self):
        rows = self.rows(3)
        rows += [{**rows[0], "todayCatalogLanguage": "de", "groupingFunctionalId": "translated"}]
        rows += [{**row, "displayFamilyId": "de-"+row["displayFamilyId"], "todayCatalogLanguage": "de"} for row in self.rows(3)]
        plan, languages, families = {}, [], []
        for _ in range(6):
            plan = self.selection.select_today_categories(rows, ["main"], ["en", "de"], plan.get("items", []), plan.get("suggestionHistory", []))
            languages.append(plan["items"][0]["todayCatalogLanguage"])
            families.append(plan["items"][0]["displayFamilyId"])
        self.assertEqual(len(set(families)), 6)
        self.assertEqual(languages.count("de"), 3)
        self.assertEqual(languages.count("en"), 3)

    def test_previous_plan_migration_scarce_categories_and_bounded_history(self):
        rows = self.rows(3)
        plan = self.selection.select_today_categories(rows, ["main"], ["en"], [{**rows[0], "todayMealType": "main"}])
        self.assertNotEqual(plan["items"][0]["displayFamilyId"], "family-0")
        one = self.selection.select_today_categories(rows[:1], ["main", "snack"], ["en"], history=plan["suggestionHistory"])
        self.assertEqual(len(one["items"]), 1)
        self.assertEqual(one["emptyMealTypes"], ["snack"])
        self.assertEqual(len(self.selection.compact_suggestion_history([{"familyId":str(i)} for i in range(300)])), 256)
        empty = self.selection.select_today_categories([], ["main"], ["en"], history=plan["suggestionHistory"])
        self.assertEqual(empty["suggestionHistory"], plan["suggestionHistory"])
        self.assertFalse(empty["items"])

    def test_real_all_language_vegetarian_requests_rotate_and_persist_checked_cards(self):
        flow = asyncio.run(run_today())
        first = flow["plans"][0]
        self.assertGreater(first["candidateCount"], 100)
        families = [set(row["displayFamilyId"] for row in plan["items"]) for plan in flow["plans"]]
        self.assertFalse(families[0] & families[1])
        self.assertFalse((families[0] | families[1]) & families[2])
        for plan in flow["plans"]:
            self.assertEqual(len(plan["items"]), len(set(row["displayFamilyId"] for row in plan["items"])))
            for row in plan["items"]:
                self.assertEqual(row["match"]["diet"], "vegetarian")
                self.assertTrue(row["match"]["safe"] or row["match"]["eligibleWithSubstitutions"])
        self.assertEqual(len(flow["saved"]["suggestionHistory"]), sum(len(plan["items"]) for plan in flow["plans"]))
        for full, compact in zip(flow["plans"][-1]["items"], flow["saved"]["items"]):
            for key in ["diet", "dietCheckVersion", "dietRulesSignature", "safe", "substitutions"]:
                self.assertEqual(compact["match"].get(key), full["match"].get(key))
            self.assertNotIn("ingredients", compact)
        if output := __import__("os").environ.get("COOK4ME_TODAY_FIXTURE"):
            Path(output).write_text(json.dumps(flow, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
