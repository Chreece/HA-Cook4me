from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components/cook4me/recipe_metrics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_recipe_metrics_v60_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class RecipeMetricsV60Tests(unittest.TestCase):
    def _tomato_de(self, quantity=200, unit="g"):
        return {
            "conceptId": "concept:food:tomato",
            "ingredientId": "local:de:tomato",
            "canonicalName": "Tomato",
            "name": "Tomate",
            "quantity": quantity,
            "unit": unit,
        }

    def _tomato_el(self, quantity=100, unit="g"):
        return {
            "conceptId": "concept:food:tomato",
            "ingredientId": "local:el:tomato",
            "canonicalName": "Tomato",
            "name": "Ντομάτα",
            "quantity": quantity,
            "unit": unit,
        }

    def test_nutrition_profile_is_shared_by_concept_across_languages(self):
        index = mod.build_nutrition_index(
            [
                {
                    "conceptId": "concept:food:tomato",
                    "canonicalName": "Tomato",
                    "nutrition": {
                        "basis": "per100g",
                        "values": {"energyKcal": 18, "protein": 0.9},
                        "source": "reviewed-test",
                    },
                }
            ]
        )
        de = mod.ingredient_nutrition(self._tomato_de(), index)
        el = mod.ingredient_nutrition(self._tomato_el(), index)
        self.assertEqual(de["energyKcal"], 36)
        self.assertEqual(el["energyKcal"], 18)

    def test_recipe_nutrition_is_vector_sum_with_coverage(self):
        index = mod.build_nutrition_index(
            [
                {
                    "conceptId": "concept:food:tomato",
                    "canonicalName": "Tomato",
                    "nutrition": {
                        "basisQuantity": 100,
                        "basisUnit": "g",
                        "values": {"energyKcal": 18, "protein": 0.9},
                    },
                },
                {
                    "key": "M_FOOD_RICE",
                    "canonicalName": "Rice",
                    "nutrition": {
                        "basis": "per100g",
                        "values": {"energyKcal": 360, "protein": 7},
                    },
                },
            ]
        )
        recipe = {
            "groupSize": 2,
            "ingredients": [
                self._tomato_de(200),
                {
                    "foodKey": "M_FOOD_RICE",
                    "name": "Reis",
                    "quantity": 100,
                    "unit": "g",
                },
            ],
        }
        result = mod.calculate_recipe_nutrition_fast(recipe, index)
        self.assertEqual(result["totals"]["energyKcal"], 396)
        self.assertEqual(result["perServing"]["energyKcal"], 198)
        self.assertEqual(result["coverage"], 1.0)
        self.assertTrue(result["fullyCovered"])

    def test_unknown_density_or_dimension_does_not_get_guessed(self):
        index = mod.build_nutrition_index(
            [
                {
                    "conceptId": "concept:food:tomato",
                    "nutrition": {
                        "basis": "per100g",
                        "values": {"energyKcal": 18},
                    },
                }
            ]
        )
        values = mod.ingredient_nutrition(self._tomato_de(200, "ml"), index)
        self.assertIsNone(values)

    def test_conflicting_profiles_for_same_concept_fail_closed(self):
        rows = [
            {
                "conceptId": "concept:food:test",
                "canonicalName": "Test",
                "nutrition": {"basis": "per100g", "values": {"energyKcal": 10}},
            },
            {
                "conceptId": "concept:food:test",
                "canonicalName": "Test",
                "nutrition": {"basis": "per100g", "values": {"energyKcal": 20}},
            },
        ]
        index = mod.build_nutrition_index(rows)
        self.assertNotIn("c:concept:food:test", index)

    def test_price_profile_applies_across_language_aliases_by_concept(self):
        prices = mod.build_price_index(
            [
                {
                    "conceptId": "concept:food:tomato",
                    "canonicalName": "Tomato",
                    "amount": 3.0,
                    "currency": "EUR",
                    "basisQuantity": 1,
                    "basisUnit": "kg",
                    "country": "DE",
                    "source": "manual",
                }
            ]
        )
        cost = mod.ingredient_cost(
            self._tomato_el(250),
            prices,
            currency="EUR",
            country="DE",
        )
        self.assertEqual(cost["amount"], 0.75)
        self.assertEqual(cost["currency"], "EUR")
        self.assertEqual(cost["identity"], "c:concept:food:tomato")

    def test_price_engine_never_converts_currency(self):
        prices = mod.build_price_index(
            [
                {
                    "conceptId": "concept:food:tomato",
                    "amount": 3,
                    "currency": "EUR",
                    "basisQuantity": 1,
                    "basisUnit": "kg",
                }
            ]
        )
        cost = mod.ingredient_cost(
            self._tomato_de(100), prices, currency="USD"
        )
        self.assertIsNone(cost)

    def test_recipe_cost_is_fast_identity_lookup_and_sum(self):
        prices = mod.build_price_index(
            [
                {
                    "conceptId": "concept:food:tomato",
                    "amount": 2,
                    "currency": "EUR",
                    "basisQuantity": 1,
                    "basisUnit": "kg",
                    "country": "DE",
                },
                {
                    "key": "M_FOOD_RICE",
                    "name": "Rice",
                    "amount": 4,
                    "currency": "EUR",
                    "basisQuantity": 1,
                    "basisUnit": "kg",
                    "country": "DE",
                },
            ]
        )
        recipe = {
            "groupSize": 2,
            "ingredients": [
                self._tomato_de(500),
                {
                    "foodKey": "M_FOOD_RICE",
                    "name": "Rice",
                    "quantity": 250,
                    "unit": "g",
                },
            ],
        }
        result = mod.calculate_recipe_cost_fast(
            recipe, prices, currency="EUR", country="DE"
        )
        self.assertEqual(result["totalsByCurrency"]["EUR"], 2.0)
        self.assertEqual(result["perServingByCurrency"]["EUR"], 1.0)
        self.assertEqual(result["coverage"], 1.0)
        self.assertFalse(result["currencyConversionApplied"])

    def test_dependency_index_targets_only_recipes_affected_by_price_or_nutrition_change(self):
        recipes = [
            {"ingredients": [self._tomato_de()]},
            {
                "ingredients": [
                    {
                        "key": "M_FOOD_RICE",
                        "name": "Rice",
                        "quantity": 100,
                        "unit": "g",
                    }
                ]
            },
            {
                "variants": [
                    {"ingredients": [self._tomato_el()]}
                ]
            },
        ]
        dependencies = mod.compile_recipe_dependency_index(recipes)
        affected = mod.affected_recipe_indices(
            dependencies,
            {"conceptId": "concept:food:tomato", "canonicalName": "Tomato"},
        )
        self.assertEqual(affected, (0, 2))
        rice = mod.affected_recipe_indices(
            dependencies,
            {"foodKey": "M_FOOD_RICE", "name": "Rice"},
        )
        self.assertEqual(rice, (1,))

    def test_legacy_name_price_reference_can_still_match_during_migration(self):
        prices = mod.build_price_index(
            [
                {
                    "identity": "n:tomato",
                    "amount": 2,
                    "currency": "EUR",
                    "basisQuantity": 1,
                    "basisUnit": "kg",
                }
            ]
        )
        cost = mod.ingredient_cost(self._tomato_de(100), prices, currency="EUR")
        self.assertEqual(cost["amount"], 0.2)


if __name__ == "__main__":
    unittest.main()
