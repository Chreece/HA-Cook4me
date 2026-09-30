"""Regression coverage for full-catalog rotation behind bounded exact nutrition."""
from __future__ import annotations

import ast
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "cook4me"
NAME = "candidate_rotation_v260_test"

pkg = types.ModuleType(NAME)
pkg.__path__ = [str(COMP)]
sys.modules[NAME] = pkg

today_logic = types.ModuleType(NAME + ".today_logic")
today_logic.recipe_identity = lambda row: str(row.get("id") or "")
today_logic.recipe_matches_meal_types = (
    lambda row, meals: bool(set(row.get("mealTypes") or []) & set(meals or []))
)
sys.modules[today_logic.__name__] = today_logic
setattr(pkg, "today_logic", today_logic)


def load_functions(path, names):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    body = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in names
    ]
    assert len(body) == len(names)
    namespace = {
        "__name__": NAME + ".runtime",
        "__package__": NAME,
    }
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])),
            str(path),
            "exec",
        ),
        namespace,
    )
    return namespace


class CandidateRotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ns = load_functions(
            COMP / "shared_recipe_runtime.py",
            {"_bounded_suggestion_candidates"},
        )

    def _rows(self, count=1200):
        return [
            {
                "id": f"recipe-{index}",
                "displayFamilyId": f"family-{index}",
                "language": "de" if index % 2 == 0 else "fr",
                "mealTypes": ["breakfast"] if index % 3 == 0 else ["dinner"],
                "match": {"score": count - index},
            }
            for index in range(count)
        ]

    def test_rotation_exposes_the_entire_eligible_catalog_over_time(self):
        rows = self._rows(1200)
        limit = 120
        # 30 anchors + 90 rotating rows per generation. Advance by exactly the
        # rotating window so repeated generations traverse the full remainder.
        seen = set()
        for cursor in range(0, 1170, 90):
            selected = self.ns["_bounded_suggestion_candidates"](
                rows,
                {"mealTypes": []},
                [],
                limit,
                rotation_cursor=cursor,
            )
            self.assertEqual(len(selected), limit)
            seen.update(row["displayFamilyId"] for row in selected)
        self.assertEqual(seen, {row["displayFamilyId"] for row in rows})

    def test_recent_suggestions_move_behind_unseen_candidates(self):
        rows = self._rows(500)
        recent = [{"familyId": f"family-{index}"} for index in range(80)]
        selected = self.ns["_bounded_suggestion_candidates"](
            rows,
            {"mealTypes": ["breakfast", "dinner"]},
            ["de", "fr"],
            120,
            rotation_cursor=0,
            recent_candidates=recent,
        )
        selected_ids = {row["displayFamilyId"] for row in selected}
        self.assertTrue(selected_ids)
        self.assertFalse(selected_ids & {f"family-{index}" for index in range(80)})

    def test_meal_and_language_coverage_survives_rotation(self):
        rows = self._rows(800)
        selected = self.ns["_bounded_suggestion_candidates"](
            rows,
            {"mealTypes": ["breakfast", "dinner"]},
            ["de", "fr"],
            96,
            rotation_cursor=517,
        )
        self.assertEqual({row["language"] for row in selected}, {"de", "fr"})
        self.assertEqual(
            {row["mealTypes"][0] for row in selected},
            {"breakfast", "dinner"},
        )

    def test_today_persists_cursor_and_week_derives_rotation_from_replaced_plan(self):
        today = (COMP / "websocket_v30.py").read_text(encoding="utf-8")
        store = (COMP / "today_plan_store.py").read_text(encoding="utf-8")
        week = (COMP / "websocket_v20.py").read_text(encoding="utf-8")
        self.assertIn('"candidateRotationCursor"', store)
        self.assertIn("candidate_rotation_cursor=rotation_cursor", today)
        self.assertIn("recent_candidates=suggestion_history", today)
        self.assertIn("_TODAY_CANDIDATE_ROTATION_STEP = 144", today)
        self.assertIn('rotation_seed = "|".join(sorted(recent_candidates))', week)
        self.assertIn("candidate_rotation_cursor=rotation_cursor", week)
        self.assertIn("recent_candidates=recent_candidates", week)


if __name__ == "__main__":
    unittest.main(verbosity=2)
