from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
BATCH_DIR = TOOLS / "release_catalog_keyless_phase3_batches_v59"


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
    def _source_batch(self, part: int) -> dict:
        path = BATCH_DIR / (
            f"release_catalog_pending_keyless_phase3_{part:03d}_source_v59.json"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_batch_001_has_exact_review_for_every_queued_source_label(self):
        batch = self._source_batch(1)
        self.assertEqual(batch["kind"], "cook4me-keyless-ingredient-review-source-batch-v59")
        self.assertEqual(batch["part"], 1)
        self.assertEqual(batch["batchSize"], 100)

        reviews = apply_reviews._keyless_reviews()
        missing: list[tuple[str, str, str]] = []
        for task in batch.get("tasks") or []:
            language = apply_reviews._text(task.get("sourceLanguage")).lower()
            source = apply_reviews._text(task.get("sourceText"))
            key = (language, apply_reviews._norm(source))
            if key not in reviews:
                missing.append((str(task.get("taskId") or ""), language, source))

        self.assertEqual(
            missing,
            [],
            "Phase 3 batch 001 contains queued labels without an exact review; "
            f"first missing rows: {missing[:10]!r}",
        )

    def test_batch_001_reviews_do_not_assign_provider_identity(self):
        # The review overlay may translate/classify source-local labels, but it must
        # never promote one into an inferred SEB M_FOOD/provider identity.
        batch = self._source_batch(1)
        reviews = apply_reviews._keyless_reviews()
        for task in batch.get("tasks") or []:
            language = apply_reviews._text(task.get("sourceLanguage")).lower()
            source = apply_reviews._text(task.get("sourceText"))
            review = reviews[(language, apply_reviews._norm(source))]
            self.assertNotIn("foodKey", review)
            self.assertNotIn("providerIngredientId", review)
            self.assertNotIn("ingredientId", review)
            self.assertIn(review["classification"], {"food", "equipment", "other"})


if __name__ == "__main__":
    unittest.main()
