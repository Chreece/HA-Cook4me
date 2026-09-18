from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "resolve_reviewed_release_catalog_nutrition_v59.py"
spec = importlib.util.spec_from_file_location("resolve_reviewed_release_catalog_nutrition_v59", SCRIPT)
assert spec and spec.loader
resolver = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = resolver
spec.loader.exec_module(resolver)


def queue():
    return {
        "kind": "cook4me-release-catalog-nutrition-queue-v59",
        "tasks": [
            {
                "ingredientId": "M_FOOD_TOMATO",
                "canonicalEnglishName": "Tomato",
                "identityKind": "provider",
                "usageCount": 20,
            },
            {
                "ingredientId": "local:de:salt",
                "canonicalEnglishName": "Sea salt",
                "identityKind": "local-keyless",
                "usageCount": 3,
            },
        ],
    }


def food(fdc_id: int = 170457):
    return {
        "fdcId": fdc_id,
        "description": "Tomatoes, red, ripe, raw, year round average",
        "dataType": "Foundation",
        "foodNutrients": [
            {"nutrientName": "Energy", "unitName": "KCAL", "value": 18.0},
            {"nutrientName": "Protein", "unitName": "G", "value": 0.88},
            {"nutrientName": "Carbohydrate, by difference", "unitName": "G", "value": 3.89},
            {"nutrientName": "Total lipid (fat)", "unitName": "G", "value": 0.2},
            {"nutrientName": "Fiber, total dietary", "unitName": "G", "value": 1.2},
            {"nutrientName": "Sodium, Na", "unitName": "MG", "value": 5.0},
        ],
    }


class ReviewedNutritionResolverTests(unittest.TestCase):
    def test_unreviewed_items_stay_pending_and_reviewed_exact_id_is_resolved(self):
        reviews = {
            "M_FOOD_TOMATO": {
                "ingredientId": "M_FOOD_TOMATO",
                "fdcId": 170457,
                "canonicalEnglishName": "Tomato",
                "confidence": "high",
                "reviewFile": "review.json",
            }
        }
        calls = []
        cache, pending = resolver.resolve(
            queue(),
            {},
            reviews,
            fetcher=lambda fdc_id: calls.append(fdc_id) or food(fdc_id),
        )
        self.assertEqual([170457], calls)
        profile = cache["M_FOOD_TOMATO"]
        self.assertEqual("per100g", profile["basis"])
        self.assertEqual(18.0, profile["values"]["energyKcal"])
        self.assertAlmostEqual(0.005, profile["values"]["sodium"])
        self.assertAlmostEqual(0.0125, profile["values"]["salt"])
        self.assertEqual(170457, profile["sourceId"])
        self.assertEqual("review.json", profile["reviewFile"])
        self.assertNotIn("apiKey", profile)
        self.assertEqual(1, pending["summary"]["resolvedNow"])
        self.assertEqual(1, pending["summary"]["missingReview"])
        self.assertEqual("local:de:salt", pending["pending"][0]["ingredientId"])
        self.assertFalse(pending["summary"]["secretsPersisted"])

    def test_existing_valid_profile_is_not_refetched(self):
        existing = {
            "M_FOOD_TOMATO": {
                "basis": "per100g",
                "values": {"energyKcal": 18.0},
            }
        }
        cache, pending = resolver.resolve(
            queue(),
            existing,
            {},
            fetcher=lambda _fdc_id: self.fail("fetcher must not run"),
        )
        self.assertEqual(1, pending["summary"]["alreadyResolved"])
        self.assertEqual(existing["M_FOOD_TOMATO"], cache["M_FOOD_TOMATO"])

    def test_review_name_mismatch_fails_closed(self):
        reviews = {
            "M_FOOD_TOMATO": {
                "ingredientId": "M_FOOD_TOMATO",
                "fdcId": 170457,
                "canonicalEnglishName": "Tomato sauce",
            }
        }
        with self.assertRaisesRegex(RuntimeError, "name mismatch"):
            resolver.resolve(queue(), {}, reviews, fetcher=lambda fdc_id: food(fdc_id))

    def test_returned_fdc_identity_must_match_reviewed_id(self):
        reviews = {
            "M_FOOD_TOMATO": {
                "ingredientId": "M_FOOD_TOMATO",
                "fdcId": 170457,
                "canonicalEnglishName": "Tomato",
            }
        }
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            resolver.resolve(queue(), {}, reviews, fetcher=lambda _fdc_id: food(999999))

    def test_nested_fdc_nutrient_shape_is_supported(self):
        nested = {
            "fdcId": 1,
            "description": "Example",
            "foodNutrients": [
                {"nutrient": {"name": "Energy", "unitName": "kcal"}, "amount": 25},
                {"nutrient": {"name": "Protein", "unitName": "g"}, "amount": 2.5},
            ],
        }
        profile = resolver.fdc_profile(nested)
        self.assertEqual(25.0, profile["values"]["energyKcal"])
        self.assertEqual(2.5, profile["values"]["protein"])

    def test_review_loader_accepts_numbered_files_and_rejects_conflicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "release_catalog_reviewed_nutrition_sources_01.v1.json").write_text(
                json.dumps({
                    "kind": "cook4me-reviewed-nutrition-source",
                    "items": [{
                        "ingredientId": "M_FOOD_TOMATO",
                        "fdcId": 170457,
                        "canonicalEnglishName": "Tomato",
                    }],
                }),
                encoding="utf-8",
            )
            reviews = resolver.load_reviews(root)
            self.assertEqual(170457, reviews["M_FOOD_TOMATO"]["fdcId"])
            self.assertEqual(
                "release_catalog_reviewed_nutrition_sources_01.v1.json",
                reviews["M_FOOD_TOMATO"]["reviewFile"],
            )
            (root / "release_catalog_reviewed_nutrition_sources_02.v1.json").write_text(
                json.dumps({
                    "kind": "cook4me-reviewed-nutrition-source",
                    "items": [{"ingredientId": "M_FOOD_TOMATO", "fdcId": 999999}],
                }),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "conflicting nutrition review"):
                resolver.load_reviews(root)

    def test_wrong_queue_kind_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "nutrition-queue"):
            resolver.resolve({"kind": "wrong"}, {}, {}, fetcher=lambda _: {})


if __name__ == "__main__":
    unittest.main()
