"""Exercise ingredient clicks with HA's synchronous async_response scheduler."""
import asyncio
from functools import wraps
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch


class IngredientEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.prefix = "cook4me_ingredient_v80_test"
        package = types.ModuleType(self.prefix)
        package.__path__ = [str(Path(__file__).resolve().parents[1] / "custom_components/cook4me")]
        identity = lambda value: value
        self.tasks, self.results, self.errors = [], [], []

        def async_response(function):
            @wraps(function)
            def schedule(hass, connection, msg):
                async def handle():
                    try:
                        await function(hass, connection, msg)
                    except Exception as error:
                        self.errors.append((msg["id"], type(error).__name__, str(error)))
                self.tasks.append(asyncio.create_task(handle()))
                # This is deliberately NOT an awaitable, just like HA.
            return schedule

        self.bridge = types.SimpleNamespace(entry=types.SimpleNamespace(data={"country": "DE"}),
            recipe_hub=types.SimpleNamespace(profile={}, recipes=[]))
        self.connection = types.SimpleNamespace(send_result=lambda ident, result: self.results.append((ident, result)))
        async def executor(function, *args):
            return function(*args)
        self.hass = types.SimpleNamespace(async_add_executor_job=executor)
        self.legacy = types.SimpleNamespace(_bridge=lambda *_: self.bridge,
            _send_error=lambda conn, msg, exc: self.errors.append((msg["id"], type(exc).__name__, str(exc))))
        self.cloud = AsyncMock(side_effect=AssertionError("Ingredient popup must stay offline"))
        modules = {
            self.prefix: package,
            "homeassistant.core": types.SimpleNamespace(HomeAssistant=object, callback=identity),
            "homeassistant.components": types.SimpleNamespace(ai_task=object, websocket_api=types.SimpleNamespace(
                websocket_command=lambda _: identity, async_response=async_response)),
            "homeassistant.util": types.SimpleNamespace(dt=object),
            "voluptuous": types.SimpleNamespace(Required=lambda value, **_: value, Optional=lambda value, **_: value,
                All=lambda *args: None, Any=lambda *args: None, In=lambda _: None, Coerce=lambda _: None, Range=lambda **kwargs: None),
            f"{self.prefix}.websocket": self.legacy,
            f"{self.prefix}.websocket_v5": types.SimpleNamespace(),
            f"{self.prefix}.websocket_v10": types.SimpleNamespace(_search_with_diagnostic=self.cloud),
            f"{self.prefix}.websocket_v11": types.SimpleNamespace(_device_language=lambda _: "de"),
            f"{self.prefix}.websocket_v13": types.SimpleNamespace(),
            f"{self.prefix}.websocket_v30": types.SimpleNamespace(),
            f"{self.prefix}.barcode": types.SimpleNamespace(confident_match=identity, suggest_catalog_matches=identity),
            f"{self.prefix}.request_coordinator": types.SimpleNamespace(request_coordinator=None),
            f"{self.prefix}.nutrition": types.SimpleNamespace(nutrition_store_for_bridge=AsyncMock(
                return_value=types.SimpleNamespace(get_generic=lambda _: None, stock_lots={}))),
            f"{self.prefix}.nutrition_fefo": types.SimpleNamespace(calculate_recipe_nutrition_fefo=identity),
            f"{self.prefix}.meal_history": types.SimpleNamespace(meal_history_store_for_bridge=AsyncMock(
                return_value=types.SimpleNamespace(recent=lambda _: []))),
            f"{self.prefix}.recipe_book": types.SimpleNamespace(recipe_book_store_for_bridge=AsyncMock(
                return_value=types.SimpleNamespace(snapshot=lambda: {}))),
        }
        self.patch = patch.dict(sys.modules, modules)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.v18 = importlib.import_module(f"{self.prefix}.websocket_v18")
        self.v31 = importlib.import_module(f"{self.prefix}.websocket_v31")

    async def drain(self):
        position = 0
        while position < len(self.tasks):
            pending = self.tasks[position:]
            position = len(self.tasks)
            await asyncio.gather(*pending)

    async def test_current_and_legacy_click_each_send_exactly_one_success(self):
        for index, handler in enumerate((self.v31.ws_ingredient_info, self.v18.ws_ingredient_info), 1):
            self.assertIsNone(handler(self.hass, self.connection, {"id": index,
                "ingredient": {"foodKey": "M_FOOD_246", "foodName": "Olive oil"},
                "language": "el", "include_official_usage": False}))
            await self.drain()
        self.assertEqual(self.errors, [])
        self.assertEqual([ident for ident, _ in self.results], [1, 2])
        for _, result in self.results:
            self.assertEqual(result["ingredientInfoContract"], "offline-ingredient-info-v62")
            self.assertEqual(result["catalogNutrition"]["values"]["energyKcal"], 884)
        self.cloud.assert_not_awaited()

    async def test_unknown_ingredient_returns_empty_details_without_internal_error(self):
        self.v31.ws_ingredient_info(self.hass, self.connection,
            {"id": 3, "ingredient": {"key": "unknown", "name": "Unknown"}, "include_official_usage": False})
        await self.drain()
        self.assertEqual(self.errors, [])
        self.assertEqual(len(self.results), 1)
        self.assertIsNone(self.results[0][1]["catalogNutrition"])

    async def test_missing_device_sends_one_error_without_scheduling_another_handler(self):
        self.legacy._bridge = lambda *_: (_ for _ in ()).throw(ValueError("Device unavailable"))
        self.v31.ws_ingredient_info(self.hass, self.connection, {"id": 4, "ingredient": {"name": "Rice"}})
        await self.drain()
        self.assertEqual(self.results, [])
        self.assertEqual(self.errors, [(4, "ValueError", "Device unavailable")])


if __name__ == "__main__":
    unittest.main()
