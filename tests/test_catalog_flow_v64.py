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
PREFIX = "cook4me_flow_v64_test"
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


async def run_flow():
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
        v31 = importlib.import_module(f"{PREFIX}.websocket_v31")
        release = importlib.import_module(f"{PREFIX}.release_catalog")
        # Both endpoints must stay offline, including all enrichment work.
        import urllib.request
        with patch.object(urllib.request, "urlopen", side_effect=AssertionError("offline flow used network")):
            await hass.async_add_executor_job(release.load_release_catalog)
            connection = types.SimpleNamespace(send_result=lambda ident, result: responses.update({ident: result}))
            filters = {"languages": LANGUAGES, "mealTypes": MEALS, "diet": "vegetarian", "preferExpiring": True}
            await v31.ws_official_search(hass, connection, {"id": 1, "entry_id": "entry", "query": "ramen", "query_language": "el",
                "languages": LANGUAGES, "shared_filters": filters, "client_operation_id": "official-flow"})
            await v30.ws_today_suggest(hass, connection, {"id": 2, "entry_id": "entry", "languages": LANGUAGES, "ui_language": "el",
                "meal_types": MEALS, "shared_filters": filters, "group_by_meal_type": True, "meal_count": 8, "client_operation_id": "today-flow"})
            saved = bridge._today_plan_store.snapshot
            # No-stock filters must still exclude every recipe requiring stock.
            await v31.ws_official_search(hass, connection, {"id": 3, "query": "ramen", "query_language": "el", "languages": LANGUAGES,
                "shared_filters": {**filters, "onlyHome": True}})
    return {"official": responses[1], "today": responses[2], "stockOnly": responses[3], "saved": saved, "events": events, "profile": profile}


class CatalogFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flow = asyncio.run(run_flow())
        spec = importlib.util.spec_from_file_location("cook4me_flow_logic", COMPONENT / "today_logic.py")
        cls.logic = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.logic)

    def test_five_languages_all_meals_ramen_returns_safe_families(self):
        rows = self.flow["official"]["items"]
        self.assertGreater(len(rows), 0)
        self.assertEqual(len(rows), len({row["displayFamilyId"] for row in rows}))
        for row in rows:
            self.assertTrue(row["match"]["safe"])
            self.assertNotIn("lamb", row["canonicalName"].lower())
            self.assertEqual(row["mealTypes"], ["soup"])
        self.assertEqual(self.flow["stockOnly"]["items"], [])

    def test_today_returns_one_real_recipe_per_category_and_persists_it(self):
        result = self.flow["today"]
        self.assertGreater(result["candidateCount"], 100)
        self.assertEqual(set(row["todayMealType"] for row in result["items"]), set(MEALS)-{"snack"})
        self.assertEqual(result["emptyMealTypes"], ["snack"])
        self.assertEqual(len({row["displayFamilyId"] for row in result["items"]}), len(MEALS)-1)
        for row in result["items"]:
            self.assertTrue(self.logic.recipe_matches_meal_types(row, [row["todayMealType"]]))
            self.assertTrue(row["ingredients"])
        self.assertEqual([row["todayMealType"] for row in self.flow["saved"]["items"]], MEALS[:-1])
        self.assertEqual(self.flow["profile"], {"diet": "vegetarian", "houseIngredients": []})

    def test_one_operation_reports_actual_recipe_counts(self):
        events = [row for row in self.flow["events"] if row["operationId"] == "today-flow"]
        self.assertEqual(len({row["serverOperationId"] for row in events}), 1)
        self.assertEqual(sum(bool(row["done"]) for row in events), 1)
        self.assertTrue(events[-1]["done"])
        counts = [row for row in events if row["phase"] == "catalog_index" and row["total"]]
        self.assertGreater(counts[-1]["total"], 100)
        self.assertTrue(any(0 < row["completed"] < row["total"] for row in counts))

    def test_category_matching_handles_provider_categories_and_unknowns(self):
        self.assertTrue(self.logic.recipe_matches_meal_types({}, MEALS))
        self.assertFalse(self.logic.recipe_matches_meal_types({}, ["main"]))
        self.assertTrue(self.logic.recipe_matches_meal_types({"mealTypes": ["soup"]}, ["soup"]))
        row = {"source": "cook4me_release_catalog", "canonicalName": "Rice pudding", "ingredients": [{"name": "Rice"}]}
        self.assertTrue(self.logic.recipe_matches_meal_types(row, ["dessert"]))
        self.assertFalse(self.logic.recipe_matches_meal_types(row, ["main"]))
        row["courses"] = [{"key": "COURSE_BREAKFAST", "name": "Breakfast"}]
        self.assertTrue(self.logic.recipe_matches_meal_types(row, ["breakfast"]))
        self.assertFalse(self.logic.recipe_matches_meal_types(row, ["dessert"]))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--fixture":
        Path(sys.argv[2]).write_text(json.dumps(asyncio.run(run_flow()), ensure_ascii=False))
    else:
        unittest.main()
