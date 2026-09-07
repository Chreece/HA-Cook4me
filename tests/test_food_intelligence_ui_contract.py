from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
V24 = (ROOT / "custom_components/cook4me/frontend/cook4me-panel-v24.js").read_text(encoding="utf-8")
V25 = (ROOT / "custom_components/cook4me/frontend/cook4me-panel-v25.js").read_text(encoding="utf-8")


class FoodIntelligenceUIContractTests(unittest.TestCase):
    def test_recommendations_include_quantity_and_nutrition_goal_controls(self):
        self.assertIn('cook4me/v17/recommend', V24)
        self.assertIn('nutritionGoal', V24)
        self.assertIn('quantityShortages', V24)
        self.assertIn('quantityCoverage', V24)

    def test_stock_batches_expose_storage_opened_provenance_and_date_scan(self):
        for token in ('data-stock-lot-storage', 'data-stock-lot-opened', 'data-stock-lot-use-days', 'provenance', 'TextDetector'):
            self.assertIn(token, V24)

    def test_meal_history_and_per_person_allocations_are_present(self):
        self.assertIn('householdMembers', V24)
        self.assertIn('data-meal-member', V24)
        self.assertIn('allocations', V24)
        self.assertIn('cook4me/v17/food_state', V24)

    def test_local_date_and_unknown_shortages_are_preserved(self):
        self.assertIn('getFullYear()', V25)
        self.assertIn('const unknown=base.filter', V25)
        self.assertNotIn('toISOString().slice(0,10)', V25)


if __name__ == "__main__":
    unittest.main()
