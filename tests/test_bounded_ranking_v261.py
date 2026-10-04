"""Regression coverage for bounded heavy ranking before exact nutrition."""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "cook4me"
NAME = "bounded_ranking_v261_test"

pkg = types.ModuleType(NAME)
pkg.__path__ = [str(COMP)]
sys.modules[NAME] = pkg


def module(name, **members):
    result = types.ModuleType(NAME + "." + name)
    vars(result).update(members)
    sys.modules[result.__name__] = result
    setattr(pkg, name, result)
    return result


def functions(path, names, namespace):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    body = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in names
    ]
    assert len(body) == len(names)
    for node in body:
        node.decorator_list = []
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])),
            str(path),
            "exec",
        ),
        namespace,
    )


def recipe_matches_meal_types(recipe, meals):
    return bool(set(recipe.get("mealTypes") or []) & set(meals or []))


module(
    "today_logic",
    recipe_identity=lambda recipe: str(recipe.get("displayFamilyId") or recipe.get("id") or ""),
    recipe_matches_meal_types=recipe_matches_meal_types,
)
module(
    "shared_recipe_filters",
    recipe_seasonally_available=lambda recipe, country, month: True,
)


class Hass:
    def __init__(self):
        self.config = types.SimpleNamespace(time_zone="Europe/Berlin")

    async def async_add_executor_job(self, function, *args):
        return function(*args)


async def resolved(value):
    return value


class NutritionStore:
    @property
    def generic(self):
        return {}

    @property
    def stock_lots(self):
        return {}


def normalized_filters(value):
    return {
        "maxCost": None,
        "diet": "vegetarian",
        "dietProfile": "household",
        "ingredients": [],
        "avoidRecentDays": 0,
        "seasonalIngredients": False,
        "mealTypes": ["breakfast", "dinner"],
        "onlyHome": False,
        "maxMissing": None,
        "preferExpiring": True,
        "nutritionGoal": "balanced",
        "calorieTolerance": 25,
        "currency": "EUR",
        **(value if isinstance(value, dict) else {}),
    }


def fake_apply_filters(
    rows,
    settings,
    *,
    ingredient_groups=None,
    cost=None,
    nutrition=None,
    recent=(),
    score_targets=True,
    progress=None,
    season_country="",
    season_month=None,
):
    result = []
    rows = list(rows)
    for completed, source in enumerate(rows, 1):
        row = deepcopy(source)
        if nutrition is not None:
            row["nutrition"] = nutrition(row)
            if progress and (completed == 1 or completed % 25 == 0):
                progress("nutrition", completed=completed - 1, total=len(rows))
        else:
            row["nutrition"] = deepcopy(row.get("catalogNutrition") or {})
        result.append(row)
    if nutrition is not None and progress:
        progress("nutrition", completed=len(rows), total=len(rows))
    return sorted(
        result,
        key=lambda row: float((row.get("match") or {}).get("score") or 0),
        reverse=True,
    )


class BoundedRankingTests(unittest.IsolatedAsyncioTestCase):
    async def test_9565_catalog_never_enters_one_full_heavy_ranking_pass(self):
        ranking_batches = []
        exact_calls = []
        progress_events = []

        def rank_filtered(bridge, rows, **kwargs):
            rows = list(rows)
            ranking_batches.append([row["id"] for row in rows])
            # Simulate a profile where the first 120 rotating candidates fail
            # diet/substitution safety. The scanner must continue in bounded
            # chunks until 192 usable candidates exist.
            return [
                deepcopy(row)
                for row in rows
                if int(row["id"]) >= 120
            ]

        module("websocket_v13", _rank_filtered=rank_filtered)
        module("websocket_v18", _recent_identities=lambda *args, **kwargs: set())
        module("costs", cost_store_for_bridge=lambda bridge: resolved(None))
        module("costing", calculate_recipe_cost=lambda *args, **kwargs: {})
        module(
            "meal_history",
            meal_history_store_for_bridge=lambda bridge: resolved(
                types.SimpleNamespace(recent=lambda limit: [])
            ),
        )
        module(
            "nutrition",
            nutrition_store_for_bridge=lambda bridge: resolved(NutritionStore()),
        )

        def calculate(recipe, house, *, generic, stock_lots):
            exact_calls.append(recipe["id"])
            return {
                "totals": {"protein": 20},
                "perServing": {"protein": 20},
                "coverage": 1.0,
            }

        module("nutrition_fefo", calculate_recipe_nutrition_fefo=calculate)
        module("diet_profiles", resolve_filters=lambda profile, filters: filters)
        module("recipe_suitability", meal_candidates=lambda rows: list(rows))

        ns = {
            "__name__": NAME + ".runtime",
            "__package__": NAME,
            "apply_filters": fake_apply_filters,
            "ingredient_aliases": lambda language: {},
            "normalize_filters": normalized_filters,
        }
        functions(
            COMP / "shared_recipe_runtime.py",
            {
                "_candidate_identity",
                "_bounded_suggestion_candidates",
                "_cheap_suggestion_prefilter",
                "processor",
            },
            ns,
        )

        bridge = types.SimpleNamespace(
            hass=Hass(),
            recipe_hub=types.SimpleNamespace(
                profile={"houseIngredients": []},
                habit_terms=[],
            ),
        )
        process = await ns["processor"](
            bridge,
            {},
            for_suggestions=True,
            exact_nutrition_limit=192,
            candidate_languages=["de", "fr"],
            progress=lambda phase, **values: progress_events.append(
                (phase, values)
            ),
        )

        rows = [
            {
                "id": str(index),
                "displayFamilyId": f"family-{index}",
                "language": "de" if index % 2 == 0 else "fr",
                "mealTypes": ["breakfast"] if index % 3 == 0 else ["dinner"],
                "match": {"score": 10000 - index},
                "catalogNutrition": {
                    "totals": {"protein": 10},
                    "coverage": 1.0,
                },
            }
            for index in range(9565)
        ]

        result = process(rows)

        self.assertEqual(len(result), 192)
        self.assertEqual(len(exact_calls), 192)
        self.assertTrue(ranking_batches)
        self.assertLessEqual(max(map(len, ranking_batches)), 32)
        self.assertLess(sum(map(len, ranking_batches)), 500)
        self.assertEqual(process.candidate_scanned_count, sum(map(len, ranking_batches)))
        self.assertEqual(
            len(process.candidate_history_delta),
            process.candidate_scanned_count,
        )
        self.assertIn("family-0", process.candidate_history_delta)

        ranking_totals = [
            int(values["total"])
            for phase, values in progress_events
            if phase == "ranking" and values.get("total") is not None
        ]
        self.assertTrue(ranking_totals)
        self.assertEqual(set(ranking_totals), {384})
        self.assertNotIn(9565, ranking_totals)
        ranking_completed = [
            int(values["completed"])
            for phase, values in progress_events
            if phase == "ranking" and values.get("completed") is not None
        ]
        self.assertTrue(any(value > 0 for value in ranking_completed))
        self.assertGreater(max(ranking_completed), 192)

        nutrition_totals = [
            int(values["total"])
            for phase, values in progress_events
            if phase == "nutrition" and values.get("total") is not None
        ]
        self.assertTrue(nutrition_totals)
        self.assertLessEqual(max(nutrition_totals), 192)

    async def test_rotation_history_moves_every_expensively_checked_family_forward(self):
        ranking_batches = []

        def rank_filtered(bridge, rows, **kwargs):
            rows = list(rows)
            ranking_batches.extend(row["displayFamilyId"] for row in rows)
            return [deepcopy(row) for row in rows]

        module("websocket_v13", _rank_filtered=rank_filtered)
        module("websocket_v18", _recent_identities=lambda *args, **kwargs: set())
        module("costs", cost_store_for_bridge=lambda bridge: resolved(None))
        module("costing", calculate_recipe_cost=lambda *args, **kwargs: {})
        module(
            "meal_history",
            meal_history_store_for_bridge=lambda bridge: resolved(
                types.SimpleNamespace(recent=lambda limit: [])
            ),
        )
        module("nutrition", nutrition_store_for_bridge=lambda bridge: resolved(NutritionStore()))
        module(
            "nutrition_fefo",
            calculate_recipe_nutrition_fefo=lambda *args, **kwargs: {
                "totals": {"protein": 1},
                "coverage": 1.0,
            },
        )
        module("diet_profiles", resolve_filters=lambda profile, filters: filters)
        module("recipe_suitability", meal_candidates=lambda rows: list(rows))

        ns = {
            "__name__": NAME + ".runtime_rotation",
            "__package__": NAME,
            "apply_filters": fake_apply_filters,
            "ingredient_aliases": lambda language: {},
            "normalize_filters": normalized_filters,
        }
        functions(
            COMP / "shared_recipe_runtime.py",
            {
                "_candidate_identity",
                "_bounded_suggestion_candidates",
                "_cheap_suggestion_prefilter",
                "processor",
            },
            ns,
        )
        bridge = types.SimpleNamespace(
            hass=Hass(),
            recipe_hub=types.SimpleNamespace(
                profile={"houseIngredients": []},
                habit_terms=[],
            ),
        )
        process = await ns["processor"](
            bridge,
            {},
            for_suggestions=True,
            exact_nutrition_limit=64,
            candidate_languages=["de"],
            candidate_history=[f"family-{i}" for i in range(64)],
        )
        rows = [
            {
                "id": str(index),
                "displayFamilyId": f"family-{index}",
                "language": "de",
                "mealTypes": ["breakfast", "dinner"],
                "match": {"score": 500 - index},
            }
            for index in range(500)
        ]
        process(rows)
        self.assertTrue(ranking_batches)
        self.assertTrue(all(int(value.split("-")[1]) >= 64 for value in ranking_batches))
        self.assertEqual(process.candidate_history_delta, ranking_batches)


class PreparedStockTests(unittest.TestCase):
    def test_ranking_prepares_inventory_once_per_rank_call(self):
        rank = (COMP / "websocket_v13.py").read_text(encoding="utf-8")
        quantity = (COMP / "food_intelligence.py").read_text(encoding="utf-8")
        expiry = (COMP / "inventory.py").read_text(encoding="utf-8")

        self.assertIn("normalized_house = normalize_inventory(house)", rank)
        self.assertIn("quantity_stock = coverage_stock(normalized_house)", rank)
        self.assertIn("prepared_stock=quantity_stock", rank)
        self.assertIn("prepared_inventory=normalized_house", rank)
        self.assertIn("prepared_stock: Any = None", quantity)
        self.assertIn("prepared_inventory: Any = None", expiry)


if __name__ == "__main__":
    unittest.main(verbosity=2)
