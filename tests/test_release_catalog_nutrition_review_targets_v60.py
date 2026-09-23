from __future__ import annotations

import importlib.util
import json
from pathlib import Path
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


identity_queue = _load(
    "cook4me_identity_nutrition_queue_target_test",
    TOOLS / "snapshot_release_catalog_nutrition_queue_v60.py",
)
compactor = _load(
    "cook4me_nutrition_review_target_compactor_test",
    TOOLS / "compact_release_catalog_nutrition_review_targets_v60.py",
)
target_resolver = _load(
    "cook4me_nutrition_review_target_resolver_test",
    TOOLS / "resolve_reviewed_release_catalog_nutrition_targets_v60.py",
)


def _identity_task(
    ingredient_id: str,
    canonical: str,
    *,
    kind: str,
    concept_id: str = "",
    usage: int = 1,
) -> dict:
    row = {
        "ingredientId": ingredient_id,
        "canonicalEnglishName": canonical,
        "identityKind": kind,
        "usageCount": usage,
        "usedByRecipe": True,
    }
    if kind == "source-local":
        row.update(
            {
                "conceptId": concept_id,
                "sourceLanguage": ingredient_id.split(":")[1],
                "reviewConfidence": "high",
                "semanticReviewFile": "review.v1.json",
            }
        )
    return row


def queue() -> dict:
    return {
        "schemaVersion": 1,
        "kind": "cook4me-release-catalog-nutrition-queue-v60",
        "catalogVersion": "v60-test",
        "nutritionBasisRequired": "per100g",
        "identityPolicy": {
            "providerIngredientIdsPreserved": True,
            "providerKeyMustMatchIngredientId": True,
            "providerIdentityInference": False,
            "sourceLocalFoodRequiresReviewedNutritionEligibility": True,
            "reviewedExactFdcProvenanceRequired": True,
            "legacyStructuralNutritionAccepted": False,
            "ambiguousExcluded": True,
            "equipmentAndOtherExcluded": True,
            "searchResultAutoAccepted": False,
        },
        "taskCount": 4,
        "tasks": [
            _identity_task("M_FOOD_TOMATO", "Tomato", kind="provider", usage=3),
            _identity_task(
                "local:de:tomato",
                "Tomato",
                kind="source-local",
                concept_id="concept:food:tomato",
                usage=2,
            ),
            _identity_task(
                "local:fr:tomate",
                "Tomato",
                kind="source-local",
                concept_id="concept:food:tomato",
                usage=4,
            ),
            _identity_task(
                "local:de:sea-salt",
                "Sea salt",
                kind="source-local",
                concept_id="concept:food:sea-salt",
                usage=1,
            ),
        ],
    }


def fdc_food(fdc_id: int, description: str = "Tomatoes, red, ripe, raw") -> dict:
    return {
        "fdcId": fdc_id,
        "description": description,
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
        ],
    }


class NutritionReviewTargetV60Tests(unittest.TestCase):
    def test_compactor_groups_only_source_local_semantic_concepts(self):
        targets, summary = compactor.compact(queue())
        self.assertEqual(summary["identityCount"], 4)
        self.assertEqual(summary["reviewTargetCount"], 3)
        self.assertEqual(summary["collapsedIdentityCount"], 1)
        self.assertEqual(summary["providerReviewTargetCount"], 1)
        self.assertEqual(summary["semanticConceptReviewTargetCount"], 2)

        by_id = {row["reviewTargetId"]: row for row in targets["targets"]}
        self.assertEqual(
            by_id["M_FOOD_TOMATO"]["memberIngredientIds"],
            ["M_FOOD_TOMATO"],
        )
        self.assertEqual(
            by_id["concept:food:tomato"]["memberIngredientIds"],
            ["local:de:tomato", "local:fr:tomate"],
        )
        self.assertEqual(
            by_id["concept:food:tomato"]["canonicalEnglishName"],
            "Tomato",
        )
        self.assertEqual(by_id["concept:food:tomato"]["usageCountSum"], 6)

    def test_compactor_fails_closed_on_non_high_source_local_review(self):
        value = queue()
        value["tasks"][1]["reviewConfidence"] = "medium"
        with self.assertRaisesRegex(RuntimeError, "not high-confidence"):
            compactor.compact(value)

    def test_compactor_fails_closed_on_concept_name_disagreement(self):
        value = queue()
        value["tasks"][2]["canonicalEnglishName"] = "Cherry tomato"
        with self.assertRaisesRegex(RuntimeError, "canonical-English mismatch"):
            compactor.compact(value)

    def test_target_resolver_fetches_concept_once_and_expands_exact_id_profiles(self):
        targets, _summary = compactor.compact(queue())
        reviews = {
            "concept:food:tomato": {
                "reviewTargetId": "concept:food:tomato",
                "reviewTargetKind": "semantic-concept",
                "canonicalEnglishName": "Tomato",
                "fdcId": 123,
                "confidence": "high",
                "reviewFile": "targets_001.v1.json",
            }
        }
        fetched: list[int] = []

        def fetcher(fdc_id: int) -> dict:
            fetched.append(fdc_id)
            return fdc_food(fdc_id)

        cache, pending = target_resolver.resolve(
            targets,
            {},
            reviews,
            fetcher=fetcher,
        )
        self.assertEqual(fetched, [123])
        for ingredient_id in ("local:de:tomato", "local:fr:tomate"):
            self.assertIn(ingredient_id, cache)
            self.assertEqual(cache[ingredient_id]["ingredientId"], ingredient_id)
            self.assertEqual(
                cache[ingredient_id]["nutritionReviewTargetId"],
                "concept:food:tomato",
            )
            self.assertEqual(
                cache[ingredient_id]["semanticConceptId"],
                "concept:food:tomato",
            )
            self.assertEqual(cache[ingredient_id]["sourceId"], 123)

        self.assertNotIn("M_FOOD_TOMATO", cache)
        self.assertEqual(pending["summary"]["resolvedNowReviewTargets"], 1)
        self.assertEqual(pending["summary"]["resolvedNowIdentities"], 2)
        self.assertEqual(pending["summary"]["pendingReviewTargetCount"], 2)
        self.assertEqual(pending["summary"]["pendingIdentityCount"], 2)

    def test_provider_target_remains_exact_and_never_merges_with_same_name_concept(self):
        targets, _summary = compactor.compact(queue())
        provider = next(
            row
            for row in targets["targets"]
            if row["reviewTargetId"] == "M_FOOD_TOMATO"
        )
        concept = next(
            row
            for row in targets["targets"]
            if row["reviewTargetId"] == "concept:food:tomato"
        )
        self.assertEqual(provider["reviewTargetKind"], "provider-identity")
        self.assertEqual(provider["memberIngredientIds"], ["M_FOOD_TOMATO"])
        self.assertEqual(concept["reviewTargetKind"], "semantic-concept")
        self.assertNotIn("M_FOOD_TOMATO", concept["memberIngredientIds"])

    def test_target_review_loader_requires_explicit_fail_closed_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "release_catalog_reviewed_nutrition_targets_001.v1.json"
            path.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "kind": "cook4me-reviewed-nutrition-target-source",
                        "policy": {
                            "searchResultAutoAccepted": False,
                            "exactFdcBindingRequired": True,
                            "semanticConceptGroupingReviewed": True,
                            "providerIdentityInference": False,
                        },
                        "items": [
                            {
                                "reviewTargetId": "concept:food:tomato",
                                "canonicalEnglishName": "Tomato",
                                "fdcId": 123,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            reviews = target_resolver.load_reviews(root)
            self.assertEqual(reviews["concept:food:tomato"]["fdcId"], 123)

            unsafe = root / "release_catalog_reviewed_nutrition_targets_002.v1.json"
            unsafe.write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "kind": "cook4me-reviewed-nutrition-target-source",
                        "policy": {
                            "searchResultAutoAccepted": True,
                            "exactFdcBindingRequired": True,
                            "semanticConceptGroupingReviewed": True,
                            "providerIdentityInference": False,
                        },
                        "items": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "unsafe policy"):
                target_resolver.load_reviews(root)

    def test_expanded_profiles_satisfy_existing_exact_identity_queue_contract(self):
        concept_id = "concept:food:tomato"
        catalog = {
            "schemaVersion": 1,
            "catalogVersion": "v60-test",
            "complete": True,
            "source": {"semanticCoverageComplete": True},
            "ingredients": [
                {
                    "id": "local:de:tomato",
                    "canonicalName": "Tomato",
                    "sourceLocalIdentity": True,
                    "conceptId": concept_id,
                    "classification": "food",
                    "nutritionEligible": True,
                    "needsSemanticConfirmation": False,
                    "sourceLanguage": "de",
                    "reviewConfidence": "high",
                    "semanticReviewFile": "review.v1.json",
                },
                {
                    "id": "local:fr:tomate",
                    "canonicalName": "Tomato",
                    "sourceLocalIdentity": True,
                    "conceptId": concept_id,
                    "classification": "food",
                    "nutritionEligible": True,
                    "needsSemanticConfirmation": False,
                    "sourceLanguage": "fr",
                    "reviewConfidence": "high",
                    "semanticReviewFile": "review.v1.json",
                },
            ],
            "recipeDependencyIndex": {
                "l:local:de:tomato": [0],
                "l:local:fr:tomate": [1],
            },
            "recipes": [],
        }
        identity_tasks, before = identity_queue.snapshot(catalog, {})
        self.assertEqual(before["pendingNutritionCount"], 2)

        targets, _ = compactor.compact(identity_tasks)
        reviews = {
            concept_id: {
                "reviewTargetId": concept_id,
                "reviewTargetKind": "semantic-concept",
                "canonicalEnglishName": "Tomato",
                "fdcId": 123,
                "confidence": "high",
                "reviewFile": "targets_001.v1.json",
            }
        }
        cache, pending = target_resolver.resolve(
            targets,
            {},
            reviews,
            fetcher=lambda fdc_id: fdc_food(fdc_id),
        )
        self.assertEqual(pending["summary"]["pendingReviewTargetCount"], 0)

        remaining, after = identity_queue.snapshot(catalog, cache)
        self.assertEqual(remaining["taskCount"], 0)
        self.assertEqual(after["resolvedNutritionCount"], 2)
        self.assertEqual(after["pendingNutritionCount"], 0)


if __name__ == "__main__":
    unittest.main()
