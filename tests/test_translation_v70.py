"""Exercise the real translation endpoint across hydrated recipe copies."""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import importlib
import json
import sys
import types
import unittest
from unittest.mock import AsyncMock, patch

import test_recipe_cards_v66 as cards

SOURCE = {"title": "Quinoa-Feta-Salat mit Melone", "language": "de", "displayVariantId": "salad-de-4",
    "sendVariantId": "device-edition", "ingredients": [{"name": "Wassermelone", "quantity": 200, "unit": "g"}],
    "steps": [{"functionalId": "s0", "stepIndex": 0, "instruction": "Zutaten vorbereiten."},
        {"functionalId": "s1", "stepIndex": 1, "instruction": "Wassermelone in 3cm große Würfel schneiden."}]}
TITLE = "Σαλάτα κινόα με φέτα και καρπούζι"
TEXTS = ["Ετοιμάστε τα υλικά.", "Κόψτε το καρπούζι σε κύβους 3 εκ."]


class FullscreenTranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = types.ModuleType(cards.PREFIX)
        package.__path__ = [str(cards.ROOT / "custom_components/cook4me")]
        sys.modules.setdefault(cards.PREFIX, package)
        cls.fixture = cards.RecipeCardDataTests()
        cls.translation = importlib.import_module(f"{cards.PREFIX}.recipe_translation")

    @contextmanager
    def handlers(self, generate):
        # Ingredient localization is covered by v66/v68; this fixture isolates
        # the actual translation handler, prompt, cache key and validators.
        with patch.dict(sys.modules, {f"{cards.PREFIX}.recipe_presentation": types.SimpleNamespace(
            present_recipe=lambda recipe, language: deepcopy(recipe))}):
            with self.fixture.handlers(AsyncMock(), generate=generate) as context:
                yield context

    def result(self, texts=TEXTS, title=TITLE):
        return types.SimpleNamespace(data={"recipes": [{"id": "0", "title": title, "steps": texts}]})

    def request(self, ws, connection, recipe, id=1):
        asyncio.run(ws.ws_recipe_translation(None, connection,
            {"id": id, "recipe": recipe, "target_language": "el", "client_operation_id": "translate-test"}))

    def test_cache_reuses_success_between_fullscreen_and_card_in_both_orders(self):
        hydrated = deepcopy(SOURCE)
        hydrated["ingredients"][0].update(displayName="Καρπούζι", displayLanguage="el", originalName="Wassermelone")
        hydrated["match"] = {"missingIngredients": ["200 g Wassermelone"]}
        hydrated["steps"][0]["applianceDescription"] = "Device display metadata"
        for first, second in [(SOURCE, hydrated), (hydrated, SOURCE)]:
            generate = AsyncMock(side_effect=[self.result(), AssertionError("Unnecessary second translation")])
            with self.handlers(generate) as (ws, connection, answers):
                self.request(ws, connection, first)
                self.request(ws, connection, second, 2)
                self.assertTrue(answers[1]["available"])
                self.assertTrue(answers[2]["available"])
                self.assertEqual(generate.await_count, 1)
                self.assertEqual(answers[2]["recipe"]["steps"][1]["functionalId"], "s1")
                self.assertEqual(answers[2]["recipe"]["ingredients"][0]["quantity"], 200)

    def test_short_output_is_retried_without_guessing_dropped_step_positions(self):
        generate = AsyncMock(side_effect=[self.result([TEXTS[1]]), self.result([TEXTS[0]]), self.result([TEXTS[1]])])
        with self.handlers(generate) as (ws, connection, answers):
            self.request(ws, connection, SOURCE)
            self.assertTrue(answers[1]["available"])
            self.assertEqual([s["instruction"] for s in answers[1]["recipe"]["steps"]], TEXTS)
            self.assertEqual(generate.await_count, 3)
            for call, step in zip(generate.await_args_list[1:], SOURCE["steps"]):
                payload = json.loads(call.kwargs["instructions"].split("Input: ", 1)[1])
                self.assertEqual(payload["steps"], [step["instruction"]])
                self.assertEqual(call.kwargs["entity_id"], "ai_task.local")

    def test_only_invalid_step_is_retried_and_current_recipe_evidence_is_retained(self):
        bad = [TEXTS[0], TEXTS[1].replace("3", "30")]
        generate = AsyncMock(side_effect=[self.result(bad), self.result([TEXTS[1]])])
        with self.handlers(generate) as (ws, connection, answers):
            self.request(ws, connection, SOURCE)
            result = answers[1]["recipe"]
            self.assertEqual(generate.await_count, 2)
            self.assertEqual(result["sendVariantId"], SOURCE["sendVariantId"])
            self.assertEqual(result["steps"][1]["originalInstruction"], SOURCE["steps"][1]["instruction"])
            self.assertEqual(result["steps"][1]["stepIndex"], 1)
            self.assertEqual(SOURCE["title"], "Quinoa-Feta-Salat mit Melone")

    def test_failed_retry_never_returns_or_caches_partial_translation(self):
        bad = [TEXTS[0], TEXTS[1].replace("3", "30")]
        generate = AsyncMock(side_effect=[self.result(bad), self.result([bad[1]]), self.result()])
        with self.handlers(generate) as (ws, connection, answers):
            self.request(ws, connection, SOURCE)
            self.assertEqual(answers[1]["reason"], "incomplete_translation")
            self.assertNotIn("recipe", answers[1])
            self.request(ws, connection, SOURCE, 2)
            self.assertTrue(answers[2]["available"])
            self.assertEqual(generate.await_count, 3)

    def test_cache_fingerprint_tracks_source_text_language_and_target(self):
        key = self.translation.text_translation_cache_key(SOURCE, "el")
        for field, value in [("title", "Different salad"), ("language", "en"), ("steps", ["Cook for 5 minutes."])]:
            self.assertNotEqual(key, self.translation.text_translation_cache_key({**SOURCE, field: value}, "el"))
        self.assertNotEqual(key, self.translation.text_translation_cache_key(SOURCE, "de"))
        self.assertEqual(key, self.translation.text_translation_cache_key({**SOURCE, "sendVariantId": "another-device"}, "el"))

    def test_missing_instructions_never_calls_ai(self):
        generate = AsyncMock(side_effect=AssertionError("No instructions to translate"))
        with self.handlers(generate) as (ws, connection, answers):
            self.request(ws, connection, {**SOURCE, "steps": []})
            self.assertEqual(answers[1]["reason"], "instructions_unavailable")
            generate.assert_not_awaited()

    def test_existing_saved_translation_is_adopted(self):
        generate = AsyncMock(side_effect=AssertionError("Should reuse legacy translation"))
        with self.handlers(generate) as (ws, connection, answers):
            cache_module = importlib.import_module(f"{cards.PREFIX}.recipe_cache")
            # The fixture store is the real endpoint's cache boundary.
            v7 = sys.modules[f"{cards.PREFIX}.websocket_v7"]
            cache = v7._cache_for.return_value
            legacy_key = cache_module.translation_cache_key(SOURCE, "el")
            asyncio.run(cache.async_set("translation", legacy_key, {"title": TITLE, "steps": TEXTS}))
            self.request(ws, connection, SOURCE)
            self.assertTrue(answers[1]["available"])
            generate.assert_not_awaited()


if __name__ == "__main__":
    if "--translate" in sys.argv:
        FullscreenTranslationTests.setUpClass()
        case = FullscreenTranslationTests()
        recipe = json.load(sys.stdin)
        # Simulate an incomplete local-model response, then faithful single-step
        # replies. Handler, prompt, cache key and validators are production.
        generate = AsyncMock(side_effect=[case.result([TEXTS[1]]), case.result([TEXTS[0]]), case.result([TEXTS[1]])])
        with case.handlers(generate) as (ws, connection, answers):
            case.request(ws, connection, recipe)
            print(json.dumps({**answers[1], "testAiCalls": generate.await_count}, ensure_ascii=False))
    else:
        unittest.main()
