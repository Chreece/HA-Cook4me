from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "cook4me_today_logic_test",
        ROOT / "custom_components/cook4me/today_logic.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TodayLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_meal_type_filter_uses_backend_taxonomy(self):
        recipe = {
            "courses": [{"key": "COURSE_SALAD", "name": "Salat"}],
            "occasions": [],
        }
        self.assertTrue(self.module.recipe_matches_meal_types(recipe, ["salad"]))
        self.assertFalse(self.module.recipe_matches_meal_types(recipe, ["breakfast"]))
        self.assertTrue(self.module.recipe_matches_meal_types(recipe, []))

    def test_meal_type_multichoice_is_or_semantics(self):
        recipe = {"courses": [{"key": "DESSERT", "name": "Dessert"}]}
        self.assertTrue(
            self.module.recipe_matches_meal_types(recipe, ["starter", "dessert"])
        )

    def test_calorie_target_rewards_close_recipe(self):
        close = self.module.calorie_target_bonus(
            {"coverage": 1.0, "perServing": {"energyKcal": 510}},
            500,
            tolerance_fraction=0.25,
        )
        far = self.module.calorie_target_bonus(
            {"coverage": 1.0, "perServing": {"energyKcal": 900}},
            500,
            tolerance_fraction=0.25,
        )
        self.assertGreater(close["bonus"], 20)
        self.assertEqual(far["bonus"], 0)
        self.assertEqual(close["delta"], 10)

    def test_calorie_target_refuses_low_coverage(self):
        row = self.module.calorie_target_bonus(
            {"coverage": 0.3, "perServing": {"energyKcal": 500}},
            500,
        )
        self.assertEqual(row["bonus"], 0)

    def test_diversity_can_prefer_distinct_second_meal(self):
        rows = [
            {
                "title": "A",
                "groupingFunctionalId": "1",
                "match": {"score": 100},
                "ingredients": [
                    {"foodKey": "RICE"},
                    {"foodKey": "TOFU"},
                ],
            },
            {
                "title": "B",
                "groupingFunctionalId": "2",
                "match": {"score": 99},
                "ingredients": [
                    {"foodKey": "RICE"},
                    {"foodKey": "TOFU"},
                ],
            },
            {
                "title": "C",
                "groupingFunctionalId": "3",
                "match": {"score": 95},
                "ingredients": [
                    {"foodKey": "LENTIL"},
                    {"foodKey": "TOMATO"},
                ],
            },
        ]
        chosen = self.module.select_diverse(rows, 2, enabled=True)
        self.assertEqual([row["title"] for row in chosen], ["A", "C"])
        self.assertEqual(chosen[1]["match"]["todayDiversityPenalty"], 0)

    def test_recipe_identity_prefers_grouping(self):
        self.assertEqual(
            self.module.recipe_identity(
                {"groupingFunctionalId": "abc", "recipeFunctionalId": "variant"}
            ),
            "groupingFunctionalId:abc",
        )


if __name__ == "__main__":
    unittest.main()
