from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import apply_post_activation_nutrition_eligibility_overrides_v60 as overlay  # noqa: E402
import build_release_catalog_v60 as builder  # noqa: E402


class ProviderNutritionEligibilityV60Tests(unittest.TestCase):
    def test_reviewed_provider_exclusions_are_exact_and_zero_use(self):
        rows = overlay._provider_override_rows()
        self.assertEqual(set(rows), {"M_FOOD_609", "M_FOOD_553", "M_FOOD_672"})
        self.assertEqual(rows["M_FOOD_609"]["canonicalEnglishName"], "Konjac")
        self.assertEqual(rows["M_FOOD_553"]["canonicalEnglishName"], "Sweet")
        self.assertEqual(rows["M_FOOD_672"]["canonicalEnglishName"], "Yuka")
        for ingredient_id, row in rows.items():
            self.assertEqual(row["ingredientId"], ingredient_id)
            self.assertTrue(row["reason"])
            self.assertEqual(
                row["reviewFile"],
                "release_catalog_reviewed_provider_nutrition_eligibility.v1.json",
            )

    def test_provider_is_eligible_until_explicit_reviewed_exclusion_exists(self):
        base = {
            "id": "M_FOOD_609",
            "key": "M_FOOD_609",
            "canonicalName": "Konjac",
        }
        self.assertTrue(builder._reviewed_nutrition_eligible(base, "M_FOOD_609"))

        reviewed = {
            **base,
            "nutritionEligible": False,
            "nutritionEligibilityReviewed": True,
            "nutritionEligibilityReviewFile":
                "release_catalog_reviewed_provider_nutrition_eligibility.v1.json",
        }
        self.assertFalse(builder._reviewed_nutrition_eligible(reviewed, "M_FOOD_609"))

    def test_unreviewed_false_flag_cannot_exclude_provider(self):
        row = {
            "id": "M_FOOD_609",
            "key": "M_FOOD_609",
            "canonicalName": "Konjac",
            "nutritionEligible": False,
        }
        self.assertTrue(builder._reviewed_nutrition_eligible(row, "M_FOOD_609"))


if __name__ == "__main__":
    unittest.main()
