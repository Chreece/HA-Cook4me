from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "snapshot_release_catalog_keyless_queue_v59.py"
spec = importlib.util.spec_from_file_location("snapshot_release_catalog_keyless_queue_v59", SCRIPT)
assert spec and spec.loader
snapshotter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = snapshotter
spec.loader.exec_module(snapshotter)


class ReleaseCatalogKeylessQueueSnapshotTests(unittest.TestCase):
    def test_snapshot_filters_keyless_and_ranks_by_occurrence(self):
        queue = {
            "schemaVersion": 4,
            "kind": "cook4me-local-translation-queue",
            "tasks": [
                {
                    "taskId": "k-low",
                    "type": "unkeyed_ingredient",
                    "sourceLanguage": "de",
                    "sourceText": "Zutat B",
                    "occurrenceCount": 2,
                    "needsTranslation": True,
                    "requestedClassification": ["food", "equipment", "other", "ambiguous"],
                },
                {
                    "taskId": "title",
                    "type": "recipe_title_english",
                    "sourceLanguage": "de",
                    "sourceText": "Ignore me",
                },
                {
                    "taskId": "k-high",
                    "type": "unkeyed_ingredient",
                    "sourceLanguage": "fr",
                    "sourceText": "Ingrédient",
                    "occurrenceCount": 12,
                    "needsTranslation": True,
                    "requestedClassification": ["food"],
                    "sourceFieldCounts": {"foodName": 12},
                },
                {
                    "taskId": "k-mid",
                    "type": "unkeyed_ingredient",
                    "sourceLanguage": "en",
                    "sourceText": "baking mold",
                    "occurrenceCount": 5,
                    "needsTranslation": False,
                    "requestedClassification": ["food", "equipment", "other", "ambiguous"],
                },
            ],
        }
        payload, summary, batches = snapshotter.snapshot(queue, batch_size=2)
        self.assertEqual(["k-high", "k-mid", "k-low"], [row["taskId"] for row in payload["tasks"]])
        self.assertEqual(3, payload["taskCount"])
        self.assertEqual(19, payload["occurrenceCount"])
        self.assertEqual(2, payload["batchCount"])
        self.assertEqual(2, summary["translationNeeded"])
        self.assertEqual(1, summary["providerStructuredFoodClassification"])
        self.assertEqual({"de": 1, "en": 1, "fr": 1}, summary["remainingByLanguage"])
        self.assertEqual({"de": 2, "en": 5, "fr": 12}, summary["remainingOccurrencesByLanguage"])
        self.assertEqual(["k-high", "k-mid"], [row["taskId"] for row in batches[0]["tasks"]])
        self.assertEqual(["k-low"], [row["taskId"] for row in batches[1]["tasks"]])

    def test_equal_occurrences_have_stable_language_and_text_order(self):
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [
                {"taskId": "2", "type": "unkeyed_ingredient", "sourceLanguage": "fr", "sourceText": "Beta", "occurrenceCount": 3},
                {"taskId": "1", "type": "unkeyed_ingredient", "sourceLanguage": "de", "sourceText": "Zulu", "occurrenceCount": 3},
                {"taskId": "0", "type": "unkeyed_ingredient", "sourceLanguage": "de", "sourceText": "alpha", "occurrenceCount": 3},
            ],
        }
        payload, _summary, _batches = snapshotter.snapshot(queue, batch_size=100)
        self.assertEqual(["0", "1", "2"], [row["taskId"] for row in payload["tasks"]])

    def test_nonpositive_batch_size_is_rejected(self):
        queue = {"kind": "cook4me-local-translation-queue", "tasks": []}
        with self.assertRaises(ValueError):
            snapshotter.snapshot(queue, batch_size=0)

    def test_wrong_queue_kind_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "cook4me-local-translation-queue"):
            snapshotter.snapshot({"kind": "wrong", "tasks": []})


if __name__ == "__main__":
    unittest.main()
