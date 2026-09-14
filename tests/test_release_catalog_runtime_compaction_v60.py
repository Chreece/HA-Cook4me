from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import catalog_search_index as search  # noqa: E402
import compact_release_catalog_runtime_v60 as compactor  # noqa: E402
import release_catalog_v60_core as runtime  # noqa: E402
import reviewed_nutrition_v60 as reviewed_nutrition  # noqa: E402


def payload() -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "runtime-compact-test",
        "complete": True,
        "source": {
            "semanticCoverageComplete": True,
        },
        "ingredients": [
            {
                "id": "M_FOOD_1",
                "key": "M_FOOD_1",
                "canonicalName": "Rice",
                "translations": {"en": "Rice", "el": "Ρύζι", "it": "Riso"},
                "aliases": {"en": ["Rice"], "el": ["Ρύζι"], "it": ["Riso"]},
                "nutrition": {
                    "basis": "per100g",
                    "values": {"energyKcal": 130.0, "protein": 2.7},
                    "source": "usda_fdc",
                    "sourceId": 1,
                    "dataType": "SR Legacy",
                    "ingredientId": "M_FOOD_1",
                    "reviewedCanonicalEnglishName": "Rice",
                    "reviewFile": "review.json",
                    "nutritionReviewTargetId": "M_FOOD_1",
                    "nutritionReviewTargetKind": "provider-identity",
                    "sourceDescription": "Rice, cooked",
                    "reviewConfidence": "exact",
                    "reviewNotes": "maintenance-only audit note",
                    "sourceReferenceDataset": "SR Legacy",
                    "sourceReferenceReleaseDate": "2018-04",
                    "sourceReferenceJsonSha256": "b" * 64,
                    "sourceReferenceManifestSha256": "a" * 64,
                },
            },
            {
                "id": "local:el:tomato",
                "conceptId": "concept:food:tomato",
                "canonicalName": "Tomato",
                "translations": {"en": "Tomato", "el": "Ντομάτα"},
                "aliases": {"en": ["Tomato"], "el": ["Ντομάτα"]},
                "classification": "food",
                "sourceLocalIdentity": True,
                "providerIdentityAssigned": False,
                "nutritionEligible": True,
                "dietEligible": True,
                "allergenEligible": True,
                "needsSemanticConfirmation": False,
            },
        ],
        "recipes": [
            {
                "groupingFunctionalId": "GROUP_RISOTTO",
                "canonicalName": "Tomato risotto",
                "canonicalEnglishReviewFile": "review.json",
                "canonicalEnglishSource": "reviewed",
                "canonicalEnglishConfidence": "exact",
                "variants": [
                    {
                        "variantId": "IT_RISOTTO",
                        "recipeFunctionalId": "IT_RISOTTO",
                        "groupingFunctionalId": "GROUP_RISOTTO",
                        "language": "it",
                        "originalLanguage": "it",
                        "title": "Risotto al pomodoro",
                        "originalTitle": "Risotto al pomodoro",
                        "servings": 2,
                        "nutrition": {"legacy": True},
                        "calculatedNutritionV60": {"large": "duplicate"},
                        "ingredients": [
                            {
                                "ingredientId": "M_FOOD_1",
                                "key": "M_FOOD_1",
                                "canonicalName": "Rice",
                                "originalName": "100 g Riso Arborio",
                                "originalLanguage": "it",
                                "semanticSourceName": "Riso Arborio",
                                "semanticIdentityState": "reviewed",
                                "quantity": 100,
                                "unit": "g",
                                "unitKey": "G",
                            },
                            {
                                "ingredientId": "local:el:tomato",
                                "conceptId": "concept:food:tomato",
                                "canonicalName": "Tomato",
                                "originalName": "50 g Pomodoro",
                                "originalLanguage": "it",
                                "semanticSourceName": "Pomodoro",
                                "semanticIdentityState": "reviewed",
                                "classification": "food",
                                "sourceLocalIdentity": True,
                                "providerIdentityAssigned": False,
                                "quantity": 50,
                                "unit": "g",
                                "unitKey": "G",
                            },
                        ],
                    }
                ],
            }
        ],
    }


class RuntimeCatalogCompactionTests(unittest.TestCase):
    def setUp(self):
        self.compact, self.summary = compactor.compact(payload())

    def test_compaction_preserves_recipe_variant_and_global_identity_counts(self):
        self.assertEqual(self.summary["recipeGroups"], 1)
        self.assertEqual(self.summary["variants"], 1)
        self.assertEqual(self.summary["ingredients"], 2)
        self.assertEqual(len(self.compact["recipes"]), 1)
        self.assertEqual(len(self.compact["recipes"][0]["variants"]), 1)
        self.assertEqual(len(self.compact["ingredients"]), 2)

    def test_recipe_lines_keep_identity_quantity_unit_but_drop_global_duplicates(self):
        variant = self.compact["recipes"][0]["variants"][0]
        provider, local = variant["ingredients"]
        self.assertEqual(provider["ingredientId"], "M_FOOD_1")
        self.assertEqual(provider["key"], "M_FOOD_1")
        self.assertEqual(provider["quantity"], 100)
        self.assertEqual(provider["unit"], "g")
        self.assertNotIn("originalName", provider)
        self.assertNotIn("semanticSourceName", provider)
        self.assertNotIn("canonicalName", provider)
        self.assertEqual(local["ingredientId"], "local:el:tomato")
        self.assertEqual(local["quantity"], 50)
        self.assertNotIn("conceptId", local)
        self.assertNotIn("originalLanguage", local)
        self.assertNotIn("nutrition", variant)
        self.assertNotIn("calculatedNutritionV60", variant)

    def test_only_clean_semantic_wording_is_folded_into_global_search_labels(self):
        self.assertEqual(self.summary["preservedUniqueRecipeLineAliases"], 2)
        rice = next(row for row in self.compact["ingredients"] if row["id"] == "M_FOOD_1")
        tomato = next(
            row for row in self.compact["ingredients"] if row["id"] == "local:el:tomato"
        )
        self.assertIn("Riso Arborio", rice["aliases"]["it"])
        self.assertEqual(tomato["translations"]["it"], "Pomodoro")
        prepared = search.prepare_search_index(self.compact["searchIndex"])
        self.assertEqual(search.search_index(prepared, "arborio", size=10)["indices"], [0])
        # Raw provider wording embeds quantity and must not become a search alias.
        self.assertEqual(search.search_index(prepared, "100", size=10)["indices"], [])

    def test_reviewed_nutrition_keeps_minimum_reusable_proof_and_global_reference_receipt(self):
        rice = next(row for row in self.compact["ingredients"] if row["id"] == "M_FOOD_1")
        profile = rice["nutrition"]
        self.assertTrue(
            reviewed_nutrition.is_reviewed_profile(
                profile,
                ingredient_id="M_FOOD_1",
                canonical_name="Rice",
            )
        )
        self.assertEqual(profile["sourceId"], 1)
        self.assertEqual(profile["nutritionReviewTargetId"], "M_FOOD_1")
        self.assertNotIn("reviewNotes", profile)
        self.assertNotIn("sourceDescription", profile)
        self.assertNotIn("sourceReferenceManifestSha256", profile)
        source = self.compact["source"]
        self.assertEqual(source["reviewedNutritionReferenceManifestSha256"], "a" * 64)
        self.assertEqual(
            source["reviewedNutritionReferenceDatasets"],
            [
                {
                    "dataType": "SR Legacy",
                    "releaseDate": "2018-04",
                    "jsonSha256": "b" * 64,
                }
            ],
        )
        self.assertGreater(self.summary["strippedNutritionMaintenanceFields"], 0)

    def test_prefix_typeahead_works_without_persisted_prefix_postings(self):
        compiled = self.compact["searchIndex"]
        self.assertEqual(compiled["prefixPostings"], {})
        self.assertFalse(compiled["stats"]["prefixPostingsPersisted"])
        prepared = search.prepare_search_index(compiled)
        result = search.search_index(prepared, "riso", size=10)
        self.assertEqual(result["indices"], [0])

    def test_greek_risotto_and_global_ingredient_alias_survive_line_dedup(self):
        prepared = search.prepare_search_index(self.compact["searchIndex"])
        self.assertEqual(
            search.search_index(prepared, "ριζότο", language="el", size=10)["indices"],
            [0],
        )
        self.assertEqual(
            search.search_index(prepared, "ντομάτα", language="el", size=10)["indices"],
            [0],
        )

    def test_runtime_recipe_nutrition_is_calculated_from_global_profiles(self):
        data = self.compact
        lookup = {}
        for ingredient in data["ingredients"]:
            lookup[ingredient["id"]] = ingredient
            if ingredient.get("key"):
                lookup[ingredient["key"]] = ingredient
        data["_runtimeIngredientById"] = lookup
        runtime._prepare_fast_indexes(data)
        row = {
            "groupSize": 2,
            "ingredients": [
                {
                    "ingredientId": "M_FOOD_1",
                    "key": "M_FOOD_1",
                    "quantity": 100,
                    "unit": "g",
                }
            ],
        }
        result = runtime._enrich_recipe_row(data, row)
        nutrition = result["calculatedNutritionV60"]
        self.assertTrue(nutrition["fullyCovered"])
        self.assertEqual(nutrition["totals"]["energyKcal"], 130.0)
        self.assertEqual(nutrition["perServing"]["energyKcal"], 65.0)
        self.assertEqual(result["nutrition"], nutrition)


if __name__ == "__main__":
    unittest.main()
