from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "translate_release_catalog_local.py"
spec = importlib.util.spec_from_file_location("translate_release_catalog_local", SCRIPT)
assert spec and spec.loader
translate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = translate
spec.loader.exec_module(translate)


class LocalTranslationTests(unittest.TestCase):
    def test_model_selection_excludes_embeddings_and_keeps_gpu_headroom(self):
        models = [
            {
                "name": "nomic-embed-text:latest",
                "size": 300_000_000,
                "details": {"parameter_size": "137M"},
            },
            {
                "name": "qwen3:8b",
                "size": 5_000_000_000,
                "details": {"parameter_size": "8.2B"},
            },
            {
                "name": "qwen3:14b",
                "size": 9_000_000_000,
                "details": {"parameter_size": "14.8B"},
            },
            {
                "name": "huge:70b",
                "size": 40_000_000_000,
                "details": {"parameter_size": "70B"},
            },
        ]
        self.assertEqual("qwen3:14b", translate.select_model(models))

    def test_unkeyed_result_requires_supported_classification(self):
        task = {
            "taskId": "u1",
            "type": "unkeyed_ingredient",
            "sourceLanguage": "de",
            "sourceText": "Backform",
        }
        result = translate.validate_batch(
            [task],
            {
                "results": [
                    {
                        "taskId": "u1",
                        "canonicalEnglish": "baking mold",
                        "classification": "equipment",
                    }
                ]
            },
        )
        self.assertEqual("equipment", result[0]["classification"])
        with self.assertRaisesRegex(ValueError, "classification"):
            translate.validate_batch(
                [task],
                {
                    "results": [
                        {
                            "taskId": "u1",
                            "canonicalEnglish": "baking mold",
                            "classification": "probably equipment",
                        }
                    ]
                },
            )

    def test_recipe_title_result_cannot_change_identity(self):
        task = {
            "taskId": "r1",
            "type": "recipe_title_english",
            "sourceLanguage": "de",
            "sourceText": "Kartoffelsuppe",
        }
        result = translate.validate_batch(
            [task],
            {"results": [{"taskId": "r1", "canonicalEnglish": "Potato soup"}]},
        )
        self.assertEqual(
            {"taskId": "r1", "canonicalEnglish": "Potato soup"}, result[0]
        )
        self.assertNotIn("groupingFunctionalId", result[0])
        self.assertNotIn("providerFoodKey", result[0])

    def test_cache_is_bound_to_model_and_task_hash(self):
        task = {
            "taskId": "r1",
            "type": "recipe_title_english",
            "sourceLanguage": "de",
            "sourceText": "Kartoffelsuppe",
        }
        result = {"taskId": "r1", "canonicalEnglish": "Potato soup"}
        with tempfile.TemporaryDirectory() as tmp:
            conn = translate._open_db(Path(tmp) / "cache.sqlite3")
            try:
                translate._store(conn, task, "model-a", result)
                self.assertEqual(result, translate._cached(conn, task, "model-a"))
                self.assertIsNone(translate._cached(conn, task, "model-b"))
                changed = dict(task, sourceText="Andere Suppe")
                self.assertIsNone(translate._cached(conn, changed, "model-a"))
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
