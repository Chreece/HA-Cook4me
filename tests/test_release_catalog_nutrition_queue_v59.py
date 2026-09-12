from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "snapshot_release_catalog_nutrition_queue_v59.py"
spec = importlib.util.spec_from_file_location("snapshot_release_catalog_nutrition_queue_v59", SCRIPT)
assert spec and spec.loader
snapshotter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = snapshotter
spec.loader.exec_module(snapshotter)


def reviewed_prep():
    return {
        "kind": "cook4me-release-assembly-prep",
        "providerFoods": [
            {
                "key": "M_FOOD_USED",
                "canonicalEnglishName": "Used food",
                "usageCount": 10,
                "usedByRecipe": True,
            },
            {
                "key": "M_FOOD_UNUSED",
                "canonicalEnglishName": "Unused food",
                "usageCount": 0,
                "usedByRecipe": False,
            },
        ],
        "unkeyedIngredients": [
            {
                "sourceLanguage": "de",
                "sourceName": "Lokales Essen",
                "canonicalEnglishName": "Local food",
                "classification": "food",
                "localSyntheticIngredientId": "local:de:food",
                "occurrenceCount": 4,
            },
            {
                "sourceLanguage": "de",
                "sourceName": "Folie",
                "canonicalEnglishName": "Foil",
                "classification": "equipment",
                "localSyntheticIngredientId": "local:de:foil",
                "occurrenceCount": 20,
            },
        ],
    }


class ReleaseCatalogNutritionQueueTests(unittest.TestCase):
    def test_food_identities_only_are_queued_and_ranked_by_use(self):
        payload, summary = snapshotter.snapshot(reviewed_prep(), {})
        self.assertEqual(
            ["M_FOOD_USED", "local:de:food", "M_FOOD_UNUSED"],
            [row["ingredientId"] for row in payload["tasks"]],
        )
        self.assertNotIn("local:de:foil", [row["ingredientId"] for row in payload["tasks"]])
        self.assertEqual(3, summary["foodIdentityCount"])
        self.assertEqual(3, summary["pendingNutritionCount"])
        self.assertEqual(2, summary["usedPendingCount"])
        self.assertEqual(1, summary["unusedProviderPendingCount"])
        local = payload["tasks"][1]
        self.assertEqual("local-keyless", local["identityKind"])
        self.assertEqual("de", local["sourceLanguage"])

    def test_valid_per100g_profile_is_skipped(self):
        nutrition = {
            "M_FOOD_USED": {
                "basis": "per100g",
                "values": {"energyKcal": 10.0},
            }
        }
        payload, summary = snapshotter.snapshot(reviewed_prep(), nutrition)
        self.assertEqual(1, summary["resolvedNutritionCount"])
        self.assertEqual(2, summary["pendingNutritionCount"])
        self.assertNotIn("M_FOOD_USED", [row["ingredientId"] for row in payload["tasks"]])

    def test_empty_or_wrong_basis_profile_is_not_resolved(self):
        nutrition = {
            "M_FOOD_USED": {"basis": "perServing", "values": {"energyKcal": 10.0}},
            "M_FOOD_UNUSED": {"basis": "per100g", "values": {}},
        }
        _payload, summary = snapshotter.snapshot(reviewed_prep(), nutrition)
        self.assertEqual(0, summary["resolvedNutritionCount"])
        self.assertEqual(3, summary["pendingNutritionCount"])

    def test_unresolved_food_semantics_are_reported_not_silently_queued(self):
        prep = reviewed_prep()
        prep["unkeyedIngredients"][0]["translationTaskId"] = "pending"
        payload, summary = snapshotter.snapshot(prep, {})
        self.assertEqual(1, summary["unresolvedSemanticFoodCount"])
        self.assertNotIn("local:de:food", [row["ingredientId"] for row in payload["tasks"]])

    def test_wrong_prep_kind_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "cook4me-release-assembly-prep"):
            snapshotter.snapshot({"kind": "wrong"}, {})


if __name__ == "__main__":
    unittest.main()
