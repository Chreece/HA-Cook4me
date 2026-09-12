from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "snapshot_release_catalog_title_queue_v59.py"
spec = importlib.util.spec_from_file_location("snapshot_release_catalog_title_queue_v59", SCRIPT)
assert spec and spec.loader
snapshotter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = snapshotter
spec.loader.exec_module(snapshotter)


class ReleaseCatalogTitleQueueSnapshotterTests(unittest.TestCase):
    def test_only_title_tasks_are_sorted_grouped_and_batched(self):
        queue = {
            "kind": "cook4me-local-translation-queue",
            "generatedAt": "2026-09-10T00:00:00+00:00",
            "tasks": [
                {"taskId": "z", "type": "unkeyed_ingredient", "sourceLanguage": "de", "sourceText": "Z"},
                {"taskId": "pl-b", "type": "recipe_title_english", "sourceLanguage": "pl", "sourceText": "Żurek"},
                {"taskId": "fr-a", "type": "recipe_title_english", "sourceLanguage": "fr", "sourceText": "Aubergine"},
                {"taskId": "pl-a", "type": "recipe_title_english", "sourceLanguage": "pl", "sourceText": "Barszcz"},
            ],
        }
        payload, summary, batches = snapshotter.snapshot(
            queue, source_queue="queue.json", batch_size=1
        )
        self.assertEqual(3, payload["recipeTitleTasksRemaining"])
        self.assertEqual({"fr": 1, "pl": 2}, payload["remainingByLanguage"])
        self.assertEqual(["fr-a", "pl-a", "pl-b"], [row["taskId"] for row in payload["tasks"]])
        self.assertEqual(3, summary["batchCount"])
        self.assertEqual({"fr_01.json", "pl_01.json", "pl_02.json"}, set(batches))
        self.assertEqual("pl-a", batches["pl_01.json"]["tasks"][0]["taskId"])
        self.assertTrue(payload["providerIdentityUnchanged"])

    def test_duplicate_title_task_ids_fail_closed(self):
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [
                {"taskId": "same", "type": "recipe_title_english", "sourceLanguage": "fr", "sourceText": "A"},
                {"taskId": "same", "type": "recipe_title_english", "sourceLanguage": "pl", "sourceText": "B"},
            ],
        }
        with self.assertRaisesRegex(RuntimeError, "duplicate task IDs"):
            snapshotter.snapshot(queue, source_queue="queue.json", batch_size=50)

    def test_missing_required_review_fields_fail_closed(self):
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [
                {"taskId": "x", "type": "recipe_title_english", "sourceLanguage": "fr", "sourceText": ""}
            ],
        }
        with self.assertRaisesRegex(RuntimeError, "missing sourceText"):
            snapshotter.snapshot(queue, source_queue="queue.json", batch_size=50)

    def test_invalid_queue_kind_and_batch_size_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "expected cook4me-local-translation-queue"):
            snapshotter.snapshot({}, source_queue="queue.json", batch_size=50)
        with self.assertRaisesRegex(ValueError, "batch_size"):
            snapshotter.snapshot(
                {"kind": "cook4me-local-translation-queue", "tasks": []},
                source_queue="queue.json",
                batch_size=0,
            )


if __name__ == "__main__":
    unittest.main()
