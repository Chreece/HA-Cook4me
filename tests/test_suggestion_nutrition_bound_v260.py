"""Regression coverage for bounded Today/Week exact nutrition work."""
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
NAME = "suggestion_bound_v260_test"

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
    recipe_identity=lambda recipe: str(recipe.get("id") or ""),
    recipe_matches_meal_types=recipe_matches_meal_types,
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
        "ingredients": [],
        "avoidRecentDays": 0,
        "seasonalIngredients": False,
        "mealTypes": [],
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
    """Small filter double that exposes exactly when exact nutrition is invoked."""
    result = []
    rows = list(rows)
    for completed, source in enumerate(rows, 1):
        if source.get("eligible") is False:
            continue
        if settings.get("mealTypes") and not recipe_matches_meal_types(
            source, settings["mealTypes"]
        ):
            continue
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


class SuggestionBoundTests(unittest.IsolatedAsyncioTestCase):
    def test_rotation_keeps_quality_reserve_but_changes_full_catalog_window(self):
        ns = {"__name__": NAME + ".rotation", "__package__": NAME}
        functions(
            COMP / "shared_recipe_runtime.py",
            {"_bounded_suggestion_candidates"},
            ns,
        )
        rows = [
            {
                "id": str(index),
                "language": "de" if index % 2 == 0 else "fr",
                "mealTypes": ["breakfast"] if index % 3 == 0 else ["dinner"],
                "match": {"score": 2000 - index},
            }
            for index in range(1000)
        ]
        settings = {"mealTypes": ["breakfast", "dinner"]}
        first = ns["_bounded_suggestion_candidates"](
            rows, settings, ["de", "fr"], 100, rotation_keys=["first-plan"]
        )
        second = ns["_bounded_suggestion_candidates"](
            rows, settings, ["de", "fr"], 100, rotation_keys=["second-plan"]
        )
        first_ids = {row["id"] for row in first}
        second_ids = {row["id"] for row in second}

        self.assertEqual(len(first), 100)
        self.assertEqual(len(second), 100)
        self.assertNotEqual(first_ids, second_ids)
        # The strongest quarter remains in play every time.
        self.assertTrue({str(index) for index in range(25)}.issubset(first_ids))
        self.assertTrue({str(index) for index in range(25)}.issubset(second_ids))
        # Rotation reaches beyond a permanently fixed top-100 shortlist.
        self.assertTrue(any(int(value) >= 100 for value in first_ids))
        self.assertTrue(any(int(value) >= 100 for value in second_ids))

    async def test_9519_recipe_catalog_runs_exact_nutrition_only_for_shortlist(self):
        exact_calls = []
        progress_events = []

        module(
            "websocket_v13",
            _rank_filtered=lambda bridge, rows, **kwargs: sorted(
                rows,
                key=lambda row: float((row.get("match") or {}).get("score") or 0),
                reverse=True,
            ),
        )
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
            {"_bounded_suggestion_candidates", "processor"},
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
            {
                "mealTypes": ["breakfast", "dinner"],
                "diet": "vegetarian",
            },
            for_suggestions=True,
            exact_nutrition_limit=192,
            candidate_languages=["de", "fr"],
            rotation_keys=["prior-family-a", "prior-family-b"],
            progress=lambda phase, **values: progress_events.append(
                (phase, values)
            ),
        )

        rows = []
        for index in range(9519):
            rows.append(
                {
                    "id": str(index),
                    "eligible": index >= 50,
                    "language": "de" if index % 2 == 0 else "fr",
                    "mealTypes": ["breakfast"] if index % 3 == 0 else ["dinner"],
                    "match": {"score": 10000 - index},
                    "catalogNutrition": {
                        "totals": {"protein": 10},
                        "coverage": 1.0,
                    },
                }
            )

        result = process(rows)
        self.assertEqual(len(exact_calls), 192)
        self.assertEqual(len(result), 192)
        self.assertTrue(all(row["eligible"] for row in result))
        self.assertEqual(
            {row["language"] for row in result},
            {"de", "fr"},
        )
        self.assertEqual(
            {row["mealTypes"][0] for row in result},
            {"breakfast", "dinner"},
        )
        nutrition_totals = [
            int(values["total"])
            for phase, values in progress_events
            if phase == "nutrition" and values.get("total") is not None
        ]
        self.assertTrue(nutrition_totals)
        self.assertLessEqual(max(nutrition_totals), 192)
        self.assertTrue(
            any(int(recipe_id) >= 192 for recipe_id in exact_calls),
            "rotation never reached outside the old fixed top shortlist",
        )

    async def test_unbounded_processor_keeps_historical_exact_behavior(self):
        exact_calls = []
        module(
            "websocket_v13",
            _rank_filtered=lambda bridge, rows, **kwargs: list(rows),
        )
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
            return {"totals": {"protein": 1}, "coverage": 1.0}

        module("nutrition_fefo", calculate_recipe_nutrition_fefo=calculate)
        module("diet_profiles", resolve_filters=lambda profile, filters: filters)
        module("recipe_suitability", meal_candidates=lambda rows: list(rows))

        ns = {
            "__name__": NAME + ".runtime_unbounded",
            "__package__": NAME,
            "apply_filters": fake_apply_filters,
            "ingredient_aliases": lambda language: {},
            "normalize_filters": normalized_filters,
        }
        functions(
            COMP / "shared_recipe_runtime.py",
            {"_bounded_suggestion_candidates", "processor"},
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
            {"diet": "vegetarian"},
            for_suggestions=True,
        )
        rows = [
            {
                "id": str(index),
                "mealTypes": ["dinner"],
                "language": "de",
                "match": {"score": index},
            }
            for index in range(25)
        ]
        result = process(rows)
        self.assertEqual(len(result), 25)
        self.assertEqual(len(exact_calls), 25)


class WiringTests(unittest.TestCase):
    def test_today_and_week_opt_into_bounded_exact_nutrition(self):
        today = (COMP / "websocket_v30.py").read_text(encoding="utf-8")
        week = (COMP / "websocket_v20.py").read_text(encoding="utf-8")
        runtime = (COMP / "shared_recipe_runtime.py").read_text(encoding="utf-8")

        self.assertIn("_MAX_TODAY_EXACT_NUTRITION_CANDIDATES = 192", today)
        self.assertIn(
            "exact_nutrition_limit=_MAX_TODAY_EXACT_NUTRITION_CANDIDATES",
            today,
        )
        self.assertIn(
            "exact_nutrition_limit=_MAX_WEEK_CANDIDATES",
            week,
        )
        self.assertIn("nutrition=None", runtime)
        self.assertIn("_bounded_suggestion_candidates(", runtime)
        self.assertIn("rotation_keys=rotation_keys", runtime)
        self.assertIn("rotation_keys=rotation_keys", today)
        self.assertIn("rotation_keys=rotation_keys", week)

    def test_fefo_copies_only_relevant_lots_not_whole_store(self):
        source = (COMP / "nutrition_fefo.py").read_text(encoding="utf-8")
        self.assertNotIn("deepcopy(stock_lots", source)
        self.assertIn("dict(row)", source)
        self.assertIn("for owner, records in stock_lots.items()", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
