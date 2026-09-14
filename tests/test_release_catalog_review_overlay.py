from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "apply_release_catalog_reviews_v2.py"
spec = importlib.util.spec_from_file_location("apply_release_catalog_reviews_v2", SCRIPT)
assert spec and spec.loader
overlay = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = overlay
spec.loader.exec_module(overlay)


class ReleaseCatalogReviewOverlayTests(unittest.TestCase):
    def test_reviewed_provider_food_and_keyless_tasks_are_removed(self):
        prep = {
            "schemaVersion": 2,
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {
                    "key": "M_FOOD_589",
                    "usedByRecipe": True,
                    "translationTaskId": "food-task",
                }
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "ar",
                    "sourceName": "المياه",
                    "translationTaskId": "keyless-task",
                    "localSyntheticIngredientId": "local:ar:water",
                }
            ],
        }
        queue = {
            "schemaVersion": 2,
            "kind": "cook4me-local-translation-queue",
            "tasks": [
                {"taskId": "food-task", "type": "provider_food_english"},
                {"taskId": "keyless-task", "type": "unkeyed_ingredient"},
                {"taskId": "title-task", "type": "recipe_title_english"},
            ],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        food = reviewed["providerFoods"][0]
        self.assertEqual("Edamame", food["canonicalEnglishName"])
        self.assertNotIn("translationTaskId", food)
        keyless = reviewed["unkeyedIngredients"][0]
        self.assertEqual("Water", keyless["canonicalEnglishName"])
        self.assertEqual("food", keyless["classification"])
        self.assertEqual("local:ar:water", keyless["localSyntheticIngredientId"])
        self.assertNotIn("translationTaskId", keyless)
        self.assertEqual(["title-task"], [row["taskId"] for row in remaining["tasks"]])
        self.assertEqual(0, remaining["summary"]["providerFoodEnglish"])
        self.assertEqual(0, remaining["summary"]["unkeyedIngredient"])
        self.assertEqual(1, remaining["summary"]["recipeTitleEnglish"])

    def test_review_overlay_never_promotes_keyless_candidate_to_provider_identity(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [{"key": "M_FOOD_677", "canonicalEnglishName": "Water", "usedByRecipe": True}],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "de",
                    "sourceName": "Wasser",
                    "exactProviderFoodKeyCandidate": "M_FOOD_677",
                    "localSyntheticIngredientId": "local:de:water",
                }
            ],
        }
        queue = {"kind": "cook4me-local-translation-queue", "tasks": []}
        reviewed, _remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertEqual("local:de:water", row["localSyntheticIngredientId"])
        self.assertEqual("M_FOOD_677", row["exactProviderFoodKeyCandidate"])
        self.assertNotIn("providerFoodKey", row)


    def test_numbered_keyless_review_file_is_loaded_with_provenance(self):
        review_path = ROOT / "tools" / "release_catalog_reviewed_keyless_ingredients_zz_01.v1.json"
        review_path.write_text(
            '{"schemaVersion":1,"kind":"cook4me-reviewed-keyless-ingredient-semantics",'
            '"items":[{"language":"zz","source":"Proof food","english":"Proof food",'
            '"classification":"food","confidence":"high"}]}\n',
            encoding="utf-8",
        )
        try:
            reviews = overlay._keyless_reviews()
            row = reviews[("zz", overlay._norm("Proof food"))]
            self.assertEqual("Proof food", row["english"])
            self.assertEqual("food", row["classification"])
            self.assertEqual(review_path.name, row["reviewFile"])
        finally:
            review_path.unlink(missing_ok=True)

    def test_conflicting_numbered_keyless_reviews_fail_closed(self):
        first = ROOT / "tools" / "release_catalog_reviewed_keyless_ingredients_zz_01.v1.json"
        second = ROOT / "tools" / "release_catalog_reviewed_keyless_ingredients_zz_02.v1.json"
        first.write_text(
            '{"schemaVersion":1,"kind":"cook4me-reviewed-keyless-ingredient-semantics",'
            '"items":[{"language":"zz","source":"Ambiguous","english":"Cream",'
            '"classification":"food","confidence":"high"}]}\n',
            encoding="utf-8",
        )
        second.write_text(
            '{"schemaVersion":1,"kind":"cook4me-reviewed-keyless-ingredient-semantics",'
            '"items":[{"language":"zz","source":"Ambiguous","english":"Cream",'
            '"classification":"equipment","confidence":"high"}]}\n',
            encoding="utf-8",
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "conflicting keyless review"):
                overlay._keyless_reviews()
        finally:
            first.unlink(missing_ok=True)
            second.unlink(missing_ok=True)


    def test_same_language_ambiguous_provider_keys_resolve_only_on_full_consensus(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {"key": "M_FOOD_A", "canonicalEnglishName": "Cream", "translations": []},
                {"key": "M_FOOD_B", "canonicalEnglishName": "Cream", "translations": []},
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "pl",
                    "sourceName": "Śmietana",
                    "ambiguousProviderFoodKeyCandidates": ["M_FOOD_A", "M_FOOD_B"],
                    "translationTaskId": "keyless-task",
                    "localSyntheticIngredientId": "local:pl:cream",
                }
            ],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertEqual("Cream", row["canonicalEnglishName"])
        self.assertEqual("food", row["classification"])
        self.assertEqual(["M_FOOD_A", "M_FOOD_B"], row["semanticProviderFoodKeyCandidates"])
        self.assertNotIn("providerFoodKey", row)
        self.assertEqual([], remaining["tasks"])
        self.assertEqual(1, reviewed["summary"]["providerFoodConsensusKeylessSemanticsApplied"])

    def test_same_language_consensus_fails_closed_when_any_candidate_is_unresolved(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {"key": "M_FOOD_A", "canonicalEnglishName": "Cream", "translations": []},
                {"key": "M_FOOD_B", "translations": []},
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "pl",
                    "sourceName": "Śmietana",
                    "ambiguousProviderFoodKeyCandidates": ["M_FOOD_A", "M_FOOD_B"],
                    "translationTaskId": "keyless-task",
                }
            ],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertNotIn("canonicalEnglishName", row)
        self.assertEqual(["keyless-task"], [item["taskId"] for item in remaining["tasks"]])
        self.assertEqual(0, reviewed["summary"]["providerFoodConsensusKeylessSemanticsApplied"])

    def test_same_language_consensus_fails_closed_on_conflicting_meanings(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {"key": "M_FOOD_A", "canonicalEnglishName": "Cream", "translations": []},
                {"key": "M_FOOD_B", "canonicalEnglishName": "Sour cream", "translations": []},
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "pl",
                    "sourceName": "Śmietana",
                    "ambiguousProviderFoodKeyCandidates": ["M_FOOD_A", "M_FOOD_B"],
                    "translationTaskId": "keyless-task",
                }
            ],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertNotIn("canonicalEnglishName", row)
        self.assertEqual(["keyless-task"], [item["taskId"] for item in remaining["tasks"]])
        self.assertEqual(0, reviewed["summary"]["providerFoodConsensusKeylessSemanticsApplied"])

    def test_english_global_exact_provider_label_can_resolve_semantics_without_identity(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {
                    "key": "M_FOOD_A",
                    "canonicalEnglishName": "Cream",
                    "translations": [{"language": "fr", "name": "cream"}],
                },
                {
                    "key": "M_FOOD_B",
                    "canonicalEnglishName": "Cream",
                    "translations": [{"language": "de", "name": "cream"}],
                },
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "en",
                    "sourceName": "cream",
                    "translationTaskId": "keyless-task",
                    "localSyntheticIngredientId": "local:en:cream",
                }
            ],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertEqual("Cream", row["canonicalEnglishName"])
        self.assertEqual("food", row["classification"])
        self.assertEqual("local:en:cream", row["localSyntheticIngredientId"])
        self.assertNotIn("providerFoodKey", row)
        self.assertEqual([], remaining["tasks"])


    def test_unique_exact_provider_food_candidate_proves_food_not_identity(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {
                    "key": "M_FOOD_WATER",
                    "canonicalEnglishName": "Water",
                    "translations": [{"language": "de", "name": "Wasser"}],
                }
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "de",
                    "sourceName": "Wasser",
                    "exactProviderFoodKeyCandidate": "M_FOOD_WATER",
                    "localSyntheticIngredientId": "local:de:water",
                    "translationTaskId": "keyless-task",
                }
            ],
            "recipeGroups": [],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertEqual("Water", row["canonicalEnglishName"])
        self.assertEqual("food", row["classification"])
        self.assertEqual("local:de:water", row["localSyntheticIngredientId"])
        self.assertNotIn("providerFoodKey", row)
        self.assertTrue(row["semanticIdentityPreserved"])
        self.assertEqual([], remaining["tasks"])

    def test_unique_exact_candidate_stays_open_until_provider_english_is_resolved(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {
                    "key": "M_FOOD_UNKNOWN",
                    "translations": [{"language": "de", "name": "Unbekannt"}],
                }
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "de",
                    "sourceName": "Unbekannt",
                    "exactProviderFoodKeyCandidate": "M_FOOD_UNKNOWN",
                    "localSyntheticIngredientId": "local:de:unknown",
                    "translationTaskId": "keyless-task",
                }
            ],
            "recipeGroups": [],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertNotIn("classification", row)
        self.assertNotIn("providerFoodKey", row)
        self.assertEqual(["keyless-task"], [task["taskId"] for task in remaining["tasks"]])


if __name__ == "__main__":
    unittest.main()
