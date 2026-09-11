from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
BATCH_DIR = TOOLS / "release_catalog_keyless_phase3_batches_v59"
BATCH_GLOB = "release_catalog_pending_keyless_phase3_*_source_v59.json"


def _load_apply_module():
    path = TOOLS / "apply_release_catalog_reviews_v2.py"
    spec = importlib.util.spec_from_file_location(
        "cook4me_apply_release_reviews_batch_coverage_test", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


apply_reviews = _load_apply_module()


class Phase3BatchReviewCoverageV59Tests(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.paths = sorted(BATCH_DIR.glob(BATCH_GLOB))
        cls.batches = [json.loads(path.read_text(encoding="utf-8")) for path in cls.paths]
        cls.reviews = apply_reviews._keyless_reviews()

    def test_all_97_baseline_batches_are_present(self):
        self.assertEqual(len(self.paths), 97)
        self.assertEqual([batch.get("part") for batch in self.batches], list(range(1, 98)))
        self.assertTrue(
            all(
                batch.get("kind") == "cook4me-keyless-ingredient-review-source-batch-v59"
                for batch in self.batches
            )
        )
        self.assertEqual(sum(len(batch.get("tasks") or []) for batch in self.batches), 9658)

    def test_all_9658_baseline_tasks_have_exact_review_keys(self):
        missing: list[tuple[str, str, str, int]] = []
        for batch in self.batches:
            part = int(batch.get("part") or 0)
            for task in batch.get("tasks") or []:
                language = apply_reviews._text(task.get("sourceLanguage")).lower()
                source = apply_reviews._text(task.get("sourceText"))
                key = (language, apply_reviews._norm(source))
                if key not in self.reviews:
                    missing.append(
                        (str(task.get("taskId") or ""), language, source, part)
                    )

        self.assertEqual(
            missing,
            [],
            "Phase 3 baseline contains queued labels without an exact review",
        )

    def test_reviewed_phase3_tasks_never_assign_provider_identity(self):
        for batch in self.batches:
            for task in batch.get("tasks") or []:
                language = apply_reviews._text(task.get("sourceLanguage")).lower()
                source = apply_reviews._text(task.get("sourceText"))
                review = self.reviews.get((language, apply_reviews._norm(source)))
                if review is None:
                    # Exact coverage is asserted independently above so this test
                    # remains focused on identity safety for reviews that do load.
                    continue
                self.assertNotIn("foodKey", review)
                self.assertNotIn("providerIngredientId", review)
                self.assertNotIn("ingredientId", review)
                self.assertIn(review["classification"], {"food", "equipment", "other"})


if __name__ == "__main__":
    unittest.main()
