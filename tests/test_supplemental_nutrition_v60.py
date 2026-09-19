from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import reviewed_nutrition_v60 as reviewed_nutrition  # noqa: E402
import supplemental_nutrition_v60 as supplemental  # noqa: E402


TARGET_ID = "concept:food:6e7ef7c7e15c50a5372e"
INGREDIENT_ID = "local:pl:689d81de9b8a8d52f1cb"


def queue() -> dict:
    return {
        "kind": "cook4me-release-catalog-nutrition-review-targets-v60",
        "targets": [
            {
                "reviewTargetId": TARGET_ID,
                "reviewTargetKind": "semantic-concept",
                "canonicalEnglishName": "Psyllium husks",
                "semanticConceptId": TARGET_ID,
                "memberIngredientIds": [INGREDIENT_ID],
            }
        ],
    }


class SupplementalNutritionV60Tests(unittest.TestCase):
    def test_committed_psyllium_review_is_exact_and_network_free(self):
        reviews = supplemental.load_reviews(TOOLS)
        self.assertIn(TARGET_ID, reviews)
        review = reviews[TARGET_ID]
        self.assertEqual(review["source"], "official_food_table")
        self.assertEqual(review["sourceId"], "NO:05.465")
        self.assertEqual(review["scientificName"], "Plantago ovata")
        self.assertEqual(review["values"]["fiber"], 78.0)
        self.assertEqual(review["values"]["energyKcal"], 206.0)
        self.assertEqual(review["memberIngredientIds"], [INGREDIENT_ID])

        cache, summary = supplemental.seed_cache(queue(), {}, review_root=TOOLS)
        self.assertEqual(summary["supplementalResolvedNowReviewTargets"], 1)
        self.assertEqual(summary["supplementalResolvedNowIdentities"], 1)
        self.assertFalse(summary["networkRequestsPerformed"])
        self.assertFalse(summary["searchResultsAutoAccepted"])
        profile = cache[INGREDIENT_ID]
        self.assertTrue(
            reviewed_nutrition.is_reviewed_profile(
                profile,
                ingredient_id=INGREDIENT_ID,
                canonical_name="Psyllium husks",
            )
        )
        self.assertEqual(profile["source"], "official_food_table")
        self.assertEqual(profile["sourceId"], "NO:05.465")
        self.assertEqual(profile["values"]["sodium"], 0.074)
        self.assertEqual(profile["values"]["salt"], 0.185)

    def test_supplemental_review_never_applies_to_a_different_target(self):
        other = queue()
        other["targets"][0]["reviewTargetId"] = "concept:food:other"
        other["targets"][0]["semanticConceptId"] = "concept:food:other"
        cache, summary = supplemental.seed_cache(other, {}, review_root=TOOLS)
        self.assertEqual(cache, {})
        self.assertEqual(summary["applicableSupplementalReviewTargetCount"], 0)
        self.assertEqual(summary["supplementalResolvedNowIdentities"], 0)


    def test_montbeliard_official_table_replaces_only_exact_holds(self):
        reviews = supplemental.load_reviews(TOOLS)
        cases = [
            ("M_FOOD_447", ["M_FOOD_447"], "Montbéliard sausage"),
            (
                "concept:food:5ba728d548d5b048a95c",
                ["local:hr:b7365ee791f2d1b91b1b"],
                "Montbéliard sausages",
            ),
        ]
        for target_id, members, canonical in cases:
            with self.subTest(target_id=target_id):
                review = reviews[target_id]
                self.assertTrue(review["replacesHeldNutritionBinding"])
                self.assertEqual(review["sourceId"], "FR-CIQUAL:30105")
                self.assertEqual(review["sourceFoodName"], "Saucisse de Montbéliard")
                target_kind = review["reviewTargetKind"]
                target = {
                    "reviewTargetId": target_id,
                    "reviewTargetKind": target_kind,
                    "canonicalEnglishName": canonical,
                    "memberIngredientIds": members,
                }
                if target_kind == "semantic-concept":
                    target["semanticConceptId"] = target_id
                cache, summary = supplemental.seed_cache(
                    {
                        "kind": "cook4me-release-catalog-nutrition-review-targets-v60",
                        "targets": [target],
                    },
                    {},
                    review_root=TOOLS,
                )
                self.assertEqual(summary["supplementalResolvedNowReviewTargets"], 1)
                self.assertEqual(summary["supplementalResolvedNowIdentities"], len(members))
                for ingredient_id in members:
                    profile = cache[ingredient_id]
                    self.assertTrue(profile["nutritionHoldReplacementApproved"])
                    self.assertEqual(profile["nutritionHoldReplacementTargetId"], target_id)
                    self.assertIsNone(
                        reviewed_nutrition.holds.profile_hold(
                            profile, ingredient_id=ingredient_id
                        )
                    )
                    self.assertTrue(
                        reviewed_nutrition.is_reviewed_profile(
                            profile,
                            ingredient_id=ingredient_id,
                            canonical_name=canonical,
                        )
                    )

    def test_source_fingerprint_drift_is_rejected(self):
        source = TOOLS / "release_catalog_reviewed_supplemental_nutrition_targets_001.v1.json"
        value = json.loads(source.read_text(encoding="utf-8"))
        value["items"][0]["values"]["fiber"] = 77.0
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / source.name
            path.write_text(
                json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RuntimeError, "source evidence drift"):
                supplemental.load_reviews(Path(tmp))

    def test_unreviewed_official_food_table_shape_is_not_enough(self):
        profile = {
            "basis": "per100g",
            "values": {"energyKcal": 206.0},
            "source": "official_food_table",
            "sourceId": "NO:05.465",
            "dataType": "Norwegian Food Composition Table",
            "ingredientId": INGREDIENT_ID,
            "reviewedCanonicalEnglishName": "Psyllium husks",
            "reviewFile": "review.json",
        }
        self.assertFalse(
            reviewed_nutrition.is_reviewed_profile(
                profile,
                ingredient_id=INGREDIENT_ID,
                canonical_name="Psyllium husks",
            )
        )


if __name__ == "__main__":
    unittest.main()
