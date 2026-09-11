from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import compile_release_catalog_semantics_v60 as semantics  # noqa: E402
import reoverlay_captured_release_catalog_v60 as overlay  # noqa: E402


def semantic_payload() -> dict:
    review = {
        "schemaVersion": 1,
        "kind": "cook4me-reviewed-keyless-ingredient-semantics",
        "items": [
            {
                "language": "de",
                "source": "Neue Zutat",
                "english": "New ingredient",
                "classification": "food",
                "confidence": "high",
            }
        ],
    }
    return semantics.compile_semantic_concepts([("fixture.v1.json", review)])


def fixture() -> dict:
    local_id = semantics.source_local_ingredient_id("de", "Neue Zutat")
    return {
        "schemaVersion": 1,
        "catalogVersion": overlay.CAPTURE3_VERSION,
        "complete": False,
        "source": {
            "auditedCatalogCount": 0,
            "failedDetailCount": 0,
            "providerIngredientIdentityPreserved": True,
            "providerIngredientIdentityInferred": False,
            "secretsPersisted": False,
            "nutritionRequiredForComplete": False,
        },
        "ingredients": [
            {
                "id": "M_FOOD_1",
                "key": "M_FOOD_1",
                "canonicalName": "Acqua",
                "canonicalNameSourceLanguage": "it",
                "canonicalEnglishNeedsReview": True,
                "translations": {"it": "Acqua"},
            },
            {
                "id": local_id,
                "canonicalName": "Neue Zutat",
                "translations": {"de": "Neue Zutat"},
                "aliases": {"de": ["Neue Zutat"]},
                "classification": "ambiguous",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
                "canonicalEnglishNeedsReview": True,
                "nutritionEligible": False,
                "dietEligible": False,
                "allergenEligible": False,
                "needsSemanticConfirmation": True,
            },
        ],
        "recipes": [
            {
                "groupingFunctionalId": "G1",
                "canonicalName": "Recipe",
                "variants": [
                    {
                        "variantId": "V1",
                        "groupingFunctionalId": "G1",
                        "originalTitle": "Rezept",
                        "originalLanguage": "de",
                        "ingredients": [
                            {
                                "ingredientId": local_id,
                                "originalName": "Neue Zutat",
                                "originalLanguage": "de",
                                "semanticSourceName": "Neue Zutat",
                                "quantity": 1,
                                "unit": "g",
                            },
                            {
                                "ingredientId": "M_FOOD_1",
                                "key": "M_FOOD_1",
                                "originalName": "Acqua",
                                "originalLanguage": "it",
                                "quantity": 1,
                                "unit": "g",
                            },
                        ],
                    }
                ],
            }
        ],
    }


def write_review_root(root: Path) -> None:
    (root / "release_catalog_reviewed_provider_food_english.v2.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "kind": "cook4me-reviewed-provider-food-english",
                "items": {
                    "M_FOOD_1": {"english": "Water", "confidence": "high"}
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "release_catalog_reviewed_recipe_titles.v1.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "kind": "cook4me-reviewed-recipe-title-english",
                "items": [],
            }
        ),
        encoding="utf-8",
    )
    (root / "release_catalog_reviewed_entry_meal_overrides.v1.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "kind": "cook4me-reviewed-entry-meal-overrides",
                "items": {},
            }
        ),
        encoding="utf-8",
    )


class OfflineCaptureReviewReoverlayV60Tests(unittest.TestCase):
    def run_overlay(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_review_root(root)
            return overlay.apply_offline_review_overlay(
                payload,
                review_root=root,
                semantic_payload=semantic_payload(),
            )

    def test_stale_source_globals_are_rebuilt_and_provider_review_is_applied_offline(self):
        payload = fixture()
        before = deepcopy(payload)
        result = self.run_overlay(payload)
        self.assertEqual(payload, before)

        rows = {row["id"]: row for row in result["ingredients"]}
        local_id = semantics.source_local_ingredient_id("de", "Neue Zutat")
        local = rows[local_id]
        self.assertEqual(local["canonicalName"], "New ingredient")
        self.assertTrue(local["conceptId"].startswith("concept:"))
        self.assertEqual(local["classification"], "food")
        self.assertFalse(local["providerIdentityAssigned"])
        self.assertNotIn("canonicalEnglishNeedsReview", local)

        provider = rows["M_FOOD_1"]
        self.assertEqual(provider["id"], "M_FOOD_1")
        self.assertEqual(provider["key"], "M_FOOD_1")
        self.assertEqual(provider["canonicalName"], "Water")
        self.assertNotIn("canonicalEnglishNeedsReview", provider)

        source = result["source"]
        self.assertTrue(source["semanticCoverageComplete"])
        self.assertEqual(source["unresolvedKeylessRecipeLineCount"], 0)
        self.assertEqual(source["unresolvedCanonicalIngredientNames"], 0)
        self.assertEqual(source["unresolvedCanonicalRecipeNames"], 0)
        self.assertTrue(source["offlineReviewReoverlayApplied"])
        self.assertFalse(source["offlineReviewReoverlayProviderCalls"])
        self.assertFalse(source["offlineReviewReoverlayNutritionCalls"])
        self.assertEqual(source["offlineReviewReoverlaySourceLocalGlobalsRebuilt"], 1)
        self.assertEqual(source["offlineReviewReoverlayProviderIdentityCount"], 1)

    def test_orphan_source_local_global_fails_closed(self):
        payload = fixture()
        orphan = semantics.source_local_ingredient_id("de", "Verwaiste Zutat")
        payload["ingredients"].append(
            {
                "id": orphan,
                "canonicalName": "Verwaiste Zutat",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
            }
        )
        with self.assertRaisesRegex(RuntimeError, "global/recipe identity sets differ"):
            self.run_overlay(payload)

    def test_changed_phase3_source_evidence_fails_closed(self):
        payload = fixture()
        payload["recipes"][0]["variants"][0]["ingredients"][0][
            "semanticSourceName"
        ] = "Andere Zutat"
        with self.assertRaisesRegex(RuntimeError, "identity/source mismatch"):
            self.run_overlay(payload)

    def test_wrong_capture_version_fails_closed(self):
        payload = fixture()
        payload["catalogVersion"] = "other-capture"
        with self.assertRaisesRegex(RuntimeError, "catalogVersion mismatch"):
            self.run_overlay(payload)


if __name__ == "__main__":
    unittest.main()
