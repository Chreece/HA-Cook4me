"""Recipe card data, explicit instruction loading and local translation."""
import asyncio
from contextlib import asynccontextmanager, contextmanager
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "cook4me_cards_v66_test"


class RecipeCardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = types.ModuleType(PREFIX)
        package.__path__ = [str(ROOT / "custom_components/cook4me")]
        sys.modules[PREFIX] = package
        cls.release = importlib.import_module(f"{PREFIX}.release_catalog")
        cls.presentation = importlib.import_module(f"{PREFIX}.recipe_presentation")
        cls.translation = importlib.import_module(f"{PREFIX}.recipe_translation")
        cls.release.load_release_catalog()

    @contextmanager
    def handlers(self, fetch, local=True, generate=None):
        identity = lambda value: value
        api = types.SimpleNamespace(websocket_command=lambda _: identity, async_response=identity)
        @asynccontextmanager
        async def operation(*args, **kwargs):
            yield object()
        coordinator = types.SimpleNamespace(operation=operation)
        bridge = types.SimpleNamespace(entry=types.SimpleNamespace(entry_id="entry"),
            recipe_hub=types.SimpleNamespace(annotate=deepcopy), can_accept_recipe=False)
        cache = {}
        async def save(kind, key, value):
            cache[(kind, key)] = deepcopy(value)
        store = types.SimpleNamespace(get=lambda kind, key: cache.get((kind, key)), async_set=save)
        modules = {
            "homeassistant.core": types.SimpleNamespace(HomeAssistant=object, callback=identity),
            "homeassistant.components": types.SimpleNamespace(websocket_api=api, ai_task=types.SimpleNamespace(async_generate_data=generate)),
            "homeassistant.helpers.storage": types.SimpleNamespace(Store=object),
            "voluptuous": types.SimpleNamespace(Required=lambda v, **_: v, Optional=lambda v, **_: v,
                All=lambda *args: None, Coerce=lambda _: None, Range=lambda **_: None),
            f"{PREFIX}.websocket": types.SimpleNamespace(_bridge=lambda *_: bridge,
                _send_error=lambda *args: (_ for _ in ()).throw(AssertionError(str(args)))),
            f"{PREFIX}.websocket_v30": types.SimpleNamespace(_device_language=lambda _: "de",
                _device_country=lambda _: "DE", _recipe_detail=fetch),
            f"{PREFIX}.websocket_v7": types.SimpleNamespace(_cache_for=AsyncMock(return_value=store),
                _translation_prompt=lambda rows, language: json.dumps({"recipes": rows, "target": language})),
            f"{PREFIX}.websocket_v5": types.SimpleNamespace(_translation_payload=deepcopy, _parse_ai_json=lambda value: value),
            f"{PREFIX}.local_ai": types.SimpleNamespace(translation_capabilities=lambda _: {"localAiTaskEntityId": "ai_task.local" if local else None}),
            f"{PREFIX}.request_coordinator": types.SimpleNamespace(request_coordinator=AsyncMock(return_value=coordinator)),
        }
        sys.modules.pop(f"{PREFIX}.websocket_v31", None)
        with patch.dict(sys.modules, modules):
            ws = importlib.import_module(f"{PREFIX}.websocket_v31")
            answers = {}
            connection = types.SimpleNamespace(send_result=lambda key, row: answers.__setitem__(key, row))
            yield ws, connection, answers

    def test_ingredient_ui_names_keep_originals_and_all_nutrient_identity(self):
        original = self.release.recipe_by_variant("316542", language="de", configured_language="de", country="DE", group_families=True)
        shown = self.presentation.present_recipe(original, "el")
        carrot = next(row for row in shown["ingredients"] if row.get("key") == "M_FOOD_79")
        self.assertEqual(carrot["displayName"], "Καρότο")
        self.assertEqual(carrot["originalName"], "Karotten")
        for source, target in zip(original["ingredients"], shown["ingredients"]):
            for key, value in source.items():
                self.assertEqual(target[key], value)
        self.assertEqual(shown["catalogNutrition"], original["catalogNutrition"])
        self.assertEqual(shown["sendVariantId"], original["sendVariantId"])

    def test_summary_does_not_request_instructions_implicitly(self):
        fetch = AsyncMock(side_effect=AssertionError("Unexpected provider request"))
        with self.handlers(fetch) as (ws, connection, answers):
            asyncio.run(ws.ws_recipe_detail(None, connection, {"id": 1, "variant_id": "316542", "language": "de", "ui_language": "el"}))
            self.assertTrue(answers[1]["offline"])
            self.assertEqual(answers[1]["ingredients"][1]["displayName"], "Καρότο")
            fetch.assert_not_awaited()

    def test_expansion_loads_exact_instructions_without_copying_other_identity(self):
        steps = [{"functionalId": "exact-step", "stepIndex": 0, "instruction": "Prepare the ingredients."}]
        fetch = AsyncMock(return_value={"displayVariantId": "316542", "steps": steps,
            "sendVariantId": "wrong", "ingredients": [], "cacheHit": True, "checkedOnline": False})
        with self.handlers(fetch) as (ws, connection, answers):
            asyncio.run(ws.ws_recipe_detail(None, connection, {"id": 1, "variant_id": "316542", "language": "de", "ui_language": "el", "include_instructions": True}))
            result = answers[1]
            self.assertEqual(result["steps"], steps)
            self.assertEqual(result["sendVariantId"], "316542")
            self.assertEqual(len(result["ingredients"]), 10)
            self.assertTrue(result["instructionsCacheHit"])
            self.assertEqual(fetch.await_args.kwargs["variant_id"], "316542")
            self.assertFalse(fetch.await_args.kwargs["refresh"])

    def test_missing_or_wrong_instructions_are_reported_without_fabricating_steps(self):
        for fetch in (AsyncMock(side_effect=ConnectionError("offline")), AsyncMock(return_value={"displayVariantId": "different", "steps": ["Wrong instructions"]})):
            with self.handlers(fetch) as (ws, connection, answers):
                asyncio.run(ws.ws_recipe_detail(None, connection, {"id": 1, "variant_id": "316542", "language": "de", "include_instructions": True}))
                self.assertEqual(answers[1]["instructionsStatus"], "unavailable")
                self.assertFalse(answers[1].get("steps"))
                self.assertEqual(answers[1]["sendVariantId"], "316542")

    def test_cached_summary_without_steps_can_fetch_full_instructions(self):
        fetch = AsyncMock(side_effect=[{"displayVariantId": "316542", "cacheHit": True},
            {"displayVariantId": "316542", "steps": ["Prepare the ingredients"], "checkedOnline": True}])
        with self.handlers(fetch) as (ws, connection, answers):
            asyncio.run(ws.ws_recipe_detail(None, connection, {"id": 1, "variant_id": "316542", "language": "de", "include_instructions": True}))
            self.assertEqual(answers[1]["instructionsStatus"], "ready")
            self.assertTrue(fetch.await_args.kwargs["refresh"])

    def test_translation_is_complete_or_unavailable_and_preserves_instruction_numbers(self):
        recipe = {"title": "Rice", "canonicalName": "Rice", "language": "en", "displayVariantId": "original",
            "ingredients": [{"ingredientId": "rice", "quantity": 200}], "steps": [
                {"functionalId": "one", "instruction": "Prepare the ingredients."},
                {"functionalId": "two", "instruction": "Pressure cooking."}]}
        saved = self.translation.bundled_translation(recipe, "el")
        translated = self.translation.apply_saved_translation(recipe, saved, "el")
        self.assertEqual(translated["title"], "Ρύζι")
        self.assertEqual(translated["steps"][1]["instruction"], "Μαγείρεμα υπό πίεση")
        self.assertEqual(translated["steps"][1]["functionalId"], "two")
        self.assertEqual(translated["ingredients"], recipe["ingredients"])
        self.assertEqual(translated["language"], "en")
        recipe["steps"][1]["instruction"] = "Cook for 5 minutes at 110 degrees."
        self.assertIsNone(self.translation.bundled_translation(recipe, "el"))
        self.assertIsNone(self.translation.apply_saved_translation(recipe, saved, "el"))

    def test_translation_requires_local_ai_even_for_bundled_text(self):
        generate = AsyncMock(side_effect=AssertionError("Unexpected AI call"))
        recipe = {"title": "Rice", "language": "en", "ingredients": [], "steps": ["Prepare the ingredients.", "Serve."]}
        for local in (False, True):
            with self.handlers(AsyncMock(), local=local, generate=generate) as (ws, connection, answers):
                asyncio.run(ws.ws_recipe_translation(None, connection, {"id": 1, "recipe": recipe, "target_language": "el"}))
                self.assertEqual(answers[1]["available"], local)
                if local:
                    self.assertEqual(answers[1]["recipe"]["title"], "Ρύζι")
        generate.assert_not_awaited()

    def test_explicit_translation_pins_local_entity_caches_and_rejects_changed_numbers(self):
        recipe = {"title": "New soup", "language": "en", "ingredients": [],
            "steps": [{"instruction": "Cook for 5 minutes.", "functionalId": "original-step"}]}
        generate = AsyncMock(return_value=types.SimpleNamespace(data={"recipes": [
            {"id": "0", "title": "Νέα σούπα", "steps": ["Μαγειρέψτε για 5 λεπτά."]}]}))
        with self.handlers(AsyncMock(), generate=generate) as (ws, connection, answers):
            for key in (1, 2):
                asyncio.run(ws.ws_recipe_translation(None, connection, {"id": key, "recipe": recipe, "target_language": "el"}))
                self.assertTrue(answers[key]["available"])
                self.assertEqual(answers[key]["recipe"]["steps"][0]["functionalId"], "original-step")
            self.assertEqual(generate.await_count, 1)
            self.assertEqual(generate.await_args.kwargs["entity_id"], "ai_task.local")
        generate.return_value.data["recipes"][0]["steps"] = ["Μαγειρέψτε για 50 λεπτά."]
        with self.handlers(AsyncMock(), generate=generate) as (ws, connection, answers):
            asyncio.run(ws.ws_recipe_translation(None, connection, {"id": 1, "recipe": recipe, "target_language": "el"}))
            self.assertFalse(answers[1]["available"])

    def test_local_capability_uses_platform_provenance_and_live_availability(self):
        const = types.SimpleNamespace(AITaskEntityFeature=types.SimpleNamespace(GENERATE_DATA=1),
            DATA_COMPONENT="component", DATA_PREFERENCES="preferences")
        sys.modules.pop(f"{PREFIX}.local_ai", None)
        resolver = importlib.import_module(f"{PREFIX}.local_ai")
        def entity(name, platform, available=True, features=1):
            return types.SimpleNamespace(entity_id=name, platform=types.SimpleNamespace(platform_name=platform),
                available=available, supported_features=features)
        entities = [entity("ai_task.ollama_named_but_cloud", "openai_conversation"),
            entity("ai_task.local", "ollama"), entity("ai_task.unavailable", "ollama", False),
            entity("ai_task.no_data", "ollama", features=0)]
        states = {row.entity_id: types.SimpleNamespace(state="ready") for row in entities}
        hass = types.SimpleNamespace(data={"component": types.SimpleNamespace(entities=entities),
            "preferences": types.SimpleNamespace(gen_data_entity_id=entities[0].entity_id)}, states=states)
        with patch.dict(sys.modules, {"homeassistant.components.ai_task.const": const}):
            result = resolver.translation_capabilities(hass)
            self.assertEqual(result["localAiTaskEntityId"], "ai_task.local")
            self.assertNotIn(entities[0].entity_id, result["localAiTaskEntityIds"])
            states["ai_task.local"].state = "unknown"
            self.assertTrue(resolver.translation_capabilities(hass)["localAiTaskAvailable"],
                "An unused AI Task has no last-activity timestamp")
            states["ai_task.local"].state = "unavailable"
            self.assertFalse(resolver.translation_capabilities(hass)["localAiTaskAvailable"])
            hass.data = {}
            self.assertFalse(resolver.translation_capabilities(hass)["localAiTaskAvailable"])


if __name__ == "__main__":
    unittest.main()
