from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


queue_mod = _load(
    "cook4me_snapshot_reviewed_nutrition_v60_test",
    TOOLS / "snapshot_release_catalog_nutrition_queue_v60.py",
)
resolver = _load(
    "cook4me_resolve_reviewed_nutrition_v60_test",
    TOOLS / "resolve_reviewed_release_catalog_nutrition_v60.py",
)
builder = _load(
    "cook4me_build_release_catalog_v60_review_guard_test",
    TOOLS / "build_release_catalog_v60.py",
)


def catalog() -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "v60-test",
        "complete": True,
        "source": {
            "semanticCoverageComplete": True,
            "providerIngredientIdentityInferred": False,
        },
        "ingredients": [
            {
                "id": "M_FOOD_TOMATO",
                "key": "M_FOOD_TOMATO",
                "canonicalName": "Tomato",
            },
            {
                "id": "local:de:sea-salt",
                "canonicalName": "Sea salt",
                "sourceLocalIdentity": True,
                "conceptId": "concept:food:sea-salt",
                "classification": "food",
                "nutritionEligible": True,
                "needsSemanticConfirmation": False,
                "reviewConfidence": "high",
                "semanticReviewFile": "phase3_001.v1.json",
            },
            {
                "id": "local:pt:palitos",
                "canonicalName": "Sticks / toothpicks",
                "sourceLocalIdentity": True,
                "conceptId": "concept:ambiguous:palitos",
                "classification": "ambiguous",
                "nutritionEligible": False,
                "needsSemanticConfirmation": True,
            },
            {
                "id": "local:de:foil",
                "canonicalName": "Aluminium foil",
                "sourceLocalIdentity": True,
                "conceptId": "concept:equipment:foil",
                "classification": "equipment",
                "nutritionEligible": False,
                "needsSemanticConfirmation": False,
            },
        ],
        "recipeDependencyIndex": {
            "M_FOOD_TOMATO": [0, 2],
            "local:de:sea-salt": [1],
            "local:pt:palitos": [0],
        },
        "recipes": [{"groupingFunctionalId": "GROUP_1", "variants": []}],
    }


def fdc_food(fdc_id: int = 123) -> dict:
    return {
        "fdcId": fdc_id,
        "description": "Tomatoes, red, ripe, raw",
        "dataType": "Foundation",
        "foodNutrients": [
            {
                "nutrient": {"name": "Energy", "unitName": "kcal"},
                "amount": 18.0,
            },
            {
                "nutrient": {"name": "Protein", "unitName": "g"},
                "amount": 0.9,
            },
            {
                "nutrient": {"name": "Sodium, Na", "unitName": "mg"},
                "amount": 5.0,
            },
        ],
    }


class ReviewedNutritionV60Tests(unittest.TestCase):
    def test_queue_contains_only_proven_nutrition_eligible_food_identities(self):
        payload, summary = queue_mod.snapshot(catalog(), {})
        self.assertEqual(payload["kind"], "cook4me-release-catalog-nutrition-queue-v60")
        self.assertTrue(payload["identityPolicy"]["ambiguousExcluded"])
        self.assertFalse(payload["identityPolicy"]["providerIdentityInference"])
        self.assertEqual(
            [row["ingredientId"] for row in payload["tasks"]],
            ["M_FOOD_TOMATO", "local:de:sea-salt"],
        )
        self.assertEqual(summary["pendingNutritionCount"], 2)
        self.assertEqual(summary["excludedSourceLocalByClassification"]["ambiguous"], 1)
        self.assertEqual(summary["excludedSourceLocalByClassification"]["equipment"], 1)

    def test_existing_reviewed_cache_removes_only_that_identity_from_queue(self):
        cache = {
            "M_FOOD_TOMATO": {
                "basis": "per100g",
                "values": {"energyKcal": 18.0},
            }
        }
        payload, summary = queue_mod.snapshot(catalog(), cache)
        self.assertEqual(
            [row["ingredientId"] for row in payload["tasks"]],
            ["local:de:sea-salt"],
        )
        self.assertEqual(summary["resolvedNutritionCount"], 1)

    def test_queue_refuses_unreviewed_semantic_catalog(self):
        value = catalog()
        value["source"]["semanticCoverageComplete"] = False
        with self.assertRaisesRegex(RuntimeError, "semantic coverage"):
            queue_mod.snapshot(value, {})

    def test_resolver_fetches_only_explicit_reviewed_fdc_id(self):
        queue, _summary = queue_mod.snapshot(catalog(), {})
        reviews = {
            "M_FOOD_TOMATO": {
                "ingredientId": "M_FOOD_TOMATO",
                "canonicalEnglishName": "Tomato",
                "fdcId": 123,
                "confidence": "high",
                "reviewFile": "review.v1.json",
            }
        }
        fetched: list[int] = []

        def fetcher(fdc_id: int) -> dict:
            fetched.append(fdc_id)
            return fdc_food(fdc_id)

        cache, pending = resolver.resolve(queue, {}, reviews, fetcher=fetcher)
        self.assertEqual(fetched, [123])
        self.assertIn("M_FOOD_TOMATO", cache)
        self.assertNotIn("local:de:sea-salt", cache)
        self.assertEqual(pending["summary"]["resolvedNow"], 1)
        self.assertEqual(pending["summary"]["missingReview"], 1)
        self.assertEqual(pending["summary"]["pendingCount"], 1)
        self.assertFalse(pending["summary"]["searchResultsAutoAccepted"])
        self.assertFalse(pending["summary"]["secretsPersisted"])

    def test_resolver_rejects_fdc_identity_mismatch(self):
        queue, _summary = queue_mod.snapshot(catalog(), {})
        reviews = {
            "M_FOOD_TOMATO": {
                "ingredientId": "M_FOOD_TOMATO",
                "canonicalEnglishName": "Tomato",
                "fdcId": 123,
            }
        }
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            resolver.resolve(
                queue,
                {},
                reviews,
                fetcher=lambda _fdc_id: fdc_food(999),
            )

    def test_review_loader_requires_explicit_no_auto_accept_policy_when_policy_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "release_catalog_reviewed_nutrition_sources_001.v1.json"
            path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "kind": "cook4me-reviewed-nutrition-source",
                        "policy": {"searchResultAutoAccepted": True},
                        "items": [
                            {"ingredientId": "M_FOOD_TOMATO", "fdcId": 123}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "forbid auto acceptance"):
                resolver.load_reviews(root)

    def _assert_fuzzy_resolution_stops_before_v59_capture(self, build_call):
        args = SimpleNamespace(resolve_nutrition=True)
        original = builder._core.v59.build
        called = False

        def should_not_run(_args):
            nonlocal called
            called = True
            raise AssertionError("v59 capture must not run")

        builder._core.v59.build = should_not_run
        try:
            with self.assertRaisesRegex(RuntimeError, "automatic USDA/FDC search"):
                build_call(args)
        finally:
            builder._core.v59.build = original
        self.assertFalse(called)

    def test_v60_facade_rejects_legacy_fuzzy_nutrition_resolution_before_capture(self):
        self._assert_fuzzy_resolution_stops_before_v59_capture(builder.build)

    def test_v60_core_rejects_legacy_fuzzy_nutrition_resolution_before_capture(self):
        self._assert_fuzzy_resolution_stops_before_v59_capture(builder._core.build)


if __name__ == "__main__":
    unittest.main()
