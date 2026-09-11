from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
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
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


overlay = _load(
    "cook4me_canonical_reviews_v60_test",
    TOOLS / "release_catalog_canonical_reviews_v60.py",
)
reviewed_builder = _load(
    "cook4me_reviewed_builder_v60_test",
    TOOLS / "build_release_catalog_v60_reviewed.py",
)
reviewed_pipeline = _load(
    "cook4me_reviewed_pipeline_v60_test",
    TOOLS / "run_release_catalog_v60_reviewed_pipeline.py",
)


def base_payload() -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "review-overlay-test",
        "complete": False,
        "source": {
            "auditedCatalogCount": 1,
            "catalogs": [
                {
                    "language": "hr",
                    "country": "HR",
                    "market": "GS_HR",
                    "state": "POPULATED",
                    "uniqueVariants": 1,
                    "hydratedVariants": 1,
                    "failedDetails": 0,
                }
            ],
            "failedDetailCount": 0,
            "unresolvedCanonicalIngredientNames": 1,
            "unresolvedCanonicalRecipeNames": 1,
            "nutritionResolvedCount": 0,
            "nutritionRequiredForComplete": False,
            "semanticCoverageComplete": True,
            "providerIngredientIdentityPreserved": True,
            "providerIngredientIdentityInferred": False,
            "keylessSourceLocalIdentity": True,
            "semanticConceptProviderIdentity": False,
            "secretsPersisted": False,
        },
        "ingredients": [
            {
                "id": "M_FOOD_589",
                "key": "M_FOOD_589",
                "canonicalName": "枝豆",
                "canonicalNameSourceLanguage": "ja",
                "canonicalEnglishNeedsReview": True,
                "translations": {"ja": "枝豆"},
            }
        ],
        "recipes": [
            {
                "groupingFunctionalId": "GROUP_HR_TEST",
                "canonicalName": "Bijela juha od cvjetače",
                "canonicalEnglishNeedsReview": True,
                "variants": [
                    {
                        "variantId": "VAR_HR_TEST",
                        "recipeFunctionalId": "REC_HR_TEST",
                        "groupingFunctionalId": "GROUP_HR_TEST",
                        "title": "Bijela juha od cvjetače",
                        "originalTitle": "Bijela juha od cvjetače",
                        "language": "hr",
                        "originalLanguage": "hr",
                        "ingredients": [
                            {
                                "ingredientId": "M_FOOD_589",
                                "key": "M_FOOD_589",
                                "foodKey": "M_FOOD_589",
                                "originalName": "Edamame",
                            }
                        ],
                    }
                ],
            }
        ],
        "recipeDependencyIndex": {
            "k:M_FOOD_589": [0],
            "n:edamame": [0],
        },
        "searchIndex": {},
        "recipeSafetyIndex": {},
    }


class ReleaseCatalogCanonicalReviewsV60Tests(unittest.TestCase):
    def test_repository_review_bundle_loads_known_exact_evidence(self):
        bundle = overlay.load_review_bundle()
        self.assertEqual(bundle.provider_foods["M_FOOD_589"]["english"], "Edamame")
        title = bundle.recipe_titles[("hr", overlay._norm("Bijela juha od cvjetače"))]
        self.assertEqual(title["english"], "White cauliflower soup")
        self.assertEqual(
            bundle.entry_titles["2774772"]["englishTitle"],
            "Beef skewers with teriyaki sauce",
        )

    def test_reviewed_fallbacks_become_canonical_without_changing_identity(self):
        value = base_payload()
        result = reviewed_builder.apply_capture_canonical_reviews(value)
        self.assertTrue(result["complete"])
        self.assertEqual(result["source"]["unresolvedCanonicalIngredientNames"], 0)
        self.assertEqual(result["source"]["unresolvedCanonicalRecipeNames"], 0)
        self.assertEqual(result["source"]["reviewedProviderFoodEnglishApplied"], 1)
        self.assertEqual(result["source"]["exactRecipeTitleReviewsApplied"], 1)
        self.assertFalse(result["source"]["canonicalReviewProviderIdentityChanged"])
        self.assertFalse(result["source"]["canonicalReviewRecipeGroupingChanged"])

        ingredient = result["ingredients"][0]
        self.assertEqual(ingredient["id"], "M_FOOD_589")
        self.assertEqual(ingredient["key"], "M_FOOD_589")
        self.assertEqual(ingredient["canonicalName"], "Edamame")
        self.assertEqual(ingredient["translations"]["ja"], "枝豆")
        self.assertEqual(ingredient["translations"]["en"], "Edamame")
        self.assertNotIn("canonicalEnglishNeedsReview", ingredient)

        group = result["recipes"][0]
        self.assertEqual(group["groupingFunctionalId"], "GROUP_HR_TEST")
        self.assertEqual(group["canonicalName"], "White cauliflower soup")
        self.assertEqual(group["variants"][0]["variantId"], "VAR_HR_TEST")
        self.assertEqual(
            group["variants"][0]["originalTitle"], "Bijela juha od cvjetače"
        )
        self.assertNotIn("canonicalEnglishNeedsReview", group)
        self.assertEqual(result["searchIndex"]["recipeCount"], 1)
        self.assertEqual(result["recipeSafetyIndex"]["recipeCount"], 1)

    def test_group_id_review_resolves_fallback_by_provider_identity_only(self):
        value = base_payload()
        value["recipes"][0]["groupingFunctionalId"] = "2774772"
        value["recipes"][0]["variants"][0]["groupingFunctionalId"] = "2774772"
        value["recipes"][0]["variants"][0]["title"] = "Provider native label"
        value["recipes"][0]["variants"][0]["originalTitle"] = "Provider native label"
        result = reviewed_builder.apply_capture_canonical_reviews(value)
        group = result["recipes"][0]
        self.assertEqual(group["groupingFunctionalId"], "2774772")
        self.assertEqual(group["canonicalName"], "Beef skewers with teriyaki sauce")
        self.assertEqual(result["source"]["entryMealTitleReviewsApplied"], 1)
        self.assertEqual(result["source"]["exactRecipeTitleReviewsApplied"], 0)

    def test_authoritative_provider_english_conflict_fails_closed(self):
        value = base_payload()
        ingredient = value["ingredients"][0]
        ingredient["canonicalName"] = "Different authoritative English"
        ingredient.pop("canonicalEnglishNeedsReview")
        ingredient.pop("canonicalNameSourceLanguage")
        with self.assertRaisesRegex(RuntimeError, "authoritative English"):
            reviewed_builder.apply_capture_canonical_reviews(value)

    def test_unreviewed_fallback_stays_unresolved_and_capture_incomplete(self):
        value = base_payload()
        value["ingredients"][0]["id"] = "M_FOOD_NOT_REVIEWED_TEST"
        value["ingredients"][0]["key"] = "M_FOOD_NOT_REVIEWED_TEST"
        value["recipes"][0]["canonicalName"] = "Totally unreviewed provider title"
        value["recipes"][0]["variants"][0]["title"] = "Totally unreviewed provider title"
        value["recipes"][0]["variants"][0]["originalTitle"] = (
            "Totally unreviewed provider title"
        )
        result = reviewed_builder.apply_capture_canonical_reviews(value)
        self.assertFalse(result["complete"])
        self.assertEqual(result["source"]["unresolvedCanonicalIngredientNames"], 1)
        self.assertEqual(result["source"]["unresolvedCanonicalRecipeNames"], 1)

    def test_reviewed_pipeline_defaults_to_reviewed_capture_builder(self):
        sentinel = object()
        captured: dict[str, object] = {}
        original = reviewed_pipeline.pipeline.run_pipeline

        def fake_pipeline(args, **kwargs):
            captured.update(kwargs)
            self.assertIs(args, sentinel)
            return {"readyForActivation": False}

        reviewed_pipeline.pipeline.run_pipeline = fake_pipeline
        try:
            result = reviewed_pipeline.run_pipeline(sentinel)
        finally:
            reviewed_pipeline.pipeline.run_pipeline = original
        self.assertFalse(result["readyForActivation"])
        self.assertIs(captured["build_func"], reviewed_pipeline.reviewed_builder.build)
        self.assertIs(
            captured["finalize_func"],
            reviewed_pipeline.reviewed_builder.apply_reviewed_nutrition,
        )


if __name__ == "__main__":
    unittest.main()
