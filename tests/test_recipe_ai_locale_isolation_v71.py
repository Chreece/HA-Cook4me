"""AI recipe translation must never serialize source language/country metadata."""
from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
from typing import Any
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "cook4me"
MARKER = "DO_NOT_SEND_SOURCE_COUNTRY_OR_LANGUAGE"


def isolated_functions(filename, names):
    """Load source functions without importing Home Assistant service modules."""
    path = COMPONENT / filename
    tree = ast.parse(path.read_text(encoding="utf-8"))
    requested = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in requested} != set(names):
        raise AssertionError(f"Missing production translation helpers in {filename}")
    module = ast.fix_missing_locations(ast.Module(body=requested, type_ignores=[]))
    namespace = {"json": json, "Any": Any}
    exec(compile(module, str(path), "exec"), namespace)
    return namespace


def new_translation():
    path = COMPONENT / "recipe_translation.py"
    spec = importlib.util.spec_from_file_location("cook4me_translation_text_only_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class RecipeAiLocaleIsolationTests(unittest.TestCase):
    def setUp(self):
        self.recipe = {
            "title": "Lentil soup",
            "language": "de-DE",
            "sourceLanguage": MARKER,
            "country": MARKER,
            "market": "GS_" + MARKER,
            "recipeLanguage": {"code": "de", "country": MARKER},
            "selectedLanguage": "de",
            "languageVariants": [{"language": MARKER, "country": MARKER}],
            "deviceSourceMarket": MARKER,
            "displayCountry": MARKER,
            "steps": [
                {"instruction": "Add 1 litre water", "language": MARKER,
                 "country": MARKER, "programName": "Pressure cooking"},
                {"description": "Simmer for 10 minutes", "sourceCountry": MARKER},
            ],
            "ingredients": [{"name": "Lentils", "quantity": 200, "unit": "g",
                             "language": MARKER, "country": MARKER}],
            "match": {"missingIngredients": ["Lentils"]},
        }

    def test_new_prompt_is_title_and_cooking_steps_only(self):
        t = new_translation()
        prompt = t.translation_prompt(self.recipe, "el-GR")
        self.assertIn("language code el-GR", prompt)
        self.assertNotIn(MARKER, prompt)
        self.assertNotIn("de-DE", prompt)
        self.assertNotIn("GS_", prompt)
        payload = json.loads(prompt.split("Input: ", 1)[1])
        self.assertEqual(payload, {
            "id": "0", "title": "Lentil soup",
            "steps": ["Add 1 litre water", "Simmer for 10 minutes"],
        })

    def test_nested_language_objects_are_never_stringified(self):
        t = new_translation()
        recipe = {
            **self.recipe,
            "title": {"value": "Soup", "language": MARKER},
            "steps": [
                {"instruction": {"text": "Stir", "country": MARKER},
                 "description": "Stir gently"},
                {"instructions": ["Add 2 eggs", {"text": "Heat", "country": MARKER},
                                  "Serve"]},
                {"text": {"value": "Do not serialize", "country": MARKER}},
            ],
        }
        prompt = t.translation_prompt(recipe, "en")
        self.assertNotIn(MARKER, prompt)
        self.assertEqual(json.loads(prompt.split("Input: ", 1)[1]), {
            "id": "0", "title": "",
            "steps": ["Stir gently", "Add 2 eggs\nServe", ""],
        })
        self.assertEqual(t.step_text(None), "")

    def test_legacy_translation_payload_excludes_structured_metadata(self):
        legacy = isolated_functions("websocket_v5.py", (
            "_plain_translation_text", "_clean_string_list", "_translation_payload"
        ))
        payload = legacy["_translation_payload"](self.recipe)
        self.assertEqual(payload, {
            "title": "Lentil soup",
            "ingredients": ["200 g Lentils"],
            "steps": ["Add 1 litre water", "Simmer for 10 minutes"],
            "missing": ["Lentils"],
        })
        nested = {
            **self.recipe,
            "title": {"value": "Soup", "country": MARKER},
            "ingredients": [{"name": {"value": "Egg", "country": MARKER},
                             "quantity": {"value": 2, "country": MARKER},
                             "unit": {"value": "pieces", "country": MARKER}}],
            "steps": [{"instruction": {"value": "Boil", "country": MARKER},
                       "programName": "Pressure"}],
            "match": {"missingIngredients": [{"name": "Egg", "country": MARKER},
                                            "Water"]},
        }
        safe = legacy["_translation_payload"](nested)
        self.assertNotIn(MARKER, json.dumps(safe))
        self.assertEqual(safe, {"title": "", "ingredients": [], "steps": ["Pressure"],
                                "missing": ["Water"]})

    def test_v7_legacy_ai_prompt_uses_the_sanitized_payload(self):
        legacy = isolated_functions("websocket_v5.py", (
            "_plain_translation_text", "_clean_string_list", "_translation_payload"
        ))
        v7 = isolated_functions("websocket_v7.py", ("_translation_prompt",))
        payload = {"id": "0", **legacy["_translation_payload"](self.recipe)}
        prompt = v7["_translation_prompt"]([payload], "el")
        self.assertNotIn(MARKER, prompt)
        self.assertNotIn("de-DE", prompt)
        self.assertEqual(json.loads(prompt.split("Input: ", 1)[1])["recipes"], [payload])

    def test_active_endpoint_keeps_locale_metadata_out_of_ai_request(self):
        endpoint = (COMPONENT / "websocket_v31.py").read_text(encoding="utf-8")
        self.assertIn("instructions=translation_prompt(part, language)", endpoint)
        self.assertIn("recipe = msg[\"recipe\"]", endpoint)
        # Original source metadata still returns to HA so recipe/device actions
        # keep their IDs, language, market and proof; only the AI input is reduced.
        self.assertIn("translated = apply_saved_translation(recipe, saved, language)", endpoint)


if __name__ == "__main__":
    unittest.main()
