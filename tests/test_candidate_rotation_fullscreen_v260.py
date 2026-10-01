"""Regression coverage for rotating candidate windows and fullscreen progress cleanup."""
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

today = types.ModuleType(NAME + ".today_logic")
today.recipe_identity = lambda row: str(row.get("id") or "")
today.recipe_matches_meal_types = lambda row, meals: bool(
    set(row.get("mealTypes") or []) & set(meals or [])
)
sys.modules[today.__name__] = today
setattr(pkg, "today_logic", today)


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


class RotationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ns = {"__name__": NAME + ".runtime", "__package__": NAME}
        functions(
            COMP / "shared_recipe_runtime.py",
            {
                "_candidate_identity",
                "compact_candidate_history",
                "_bounded_suggestion_candidates",
            },
            ns,
        )
        cls.identity = staticmethod(ns["_candidate_identity"])
        cls.compact = staticmethod(ns["compact_candidate_history"])
        cls.bound = staticmethod(ns["_bounded_suggestion_candidates"])

    @staticmethod
    def rows(count=500):
        meals = ["breakfast", "starter", "salad", "soup"]
        languages = ["de", "fr"]
        return [
            {
                "id": f"recipe-{index}",
                "displayFamilyId": f"family-{index}",
                "language": languages[index % len(languages)],
                "mealTypes": [meals[index % len(meals)]],
                "match": {"score": count - index},
            }
            for index in range(count)
        ]

    def test_bounded_window_traverses_every_eligible_family_before_recycling(self):
        rows = self.rows()
        settings = {"mealTypes": ["breakfast", "starter", "salad", "soup"]}
        history = []
        generations = []
        visited = set()

        for _ in range(10):
            batch = self.bound(
                rows,
                settings,
                ["de", "fr"],
                50,
                candidate_history=history,
            )
            ids = [self.identity(row) for row in batch]
            self.assertEqual(len(ids), 50)
            self.assertEqual(len(set(ids)), 50)
            self.assertTrue(visited.isdisjoint(ids))
            self.assertEqual({row["language"] for row in batch}, {"de", "fr"})
            self.assertEqual(
                {row["mealTypes"][0] for row in batch},
                {"breakfast", "starter", "salad", "soup"},
            )
            visited.update(ids)
            history = self.compact(history, batch)
            generations.append(ids)

        self.assertEqual(len(visited), 500)
        recycled = self.bound(
            rows,
            settings,
            ["de", "fr"],
            50,
            candidate_history=history,
        )
        self.assertEqual(
            {self.identity(row) for row in recycled},
            set(generations[0]),
        )

    def test_history_is_unique_recency_order_and_large_enough_for_full_catalog(self):
        rows = self.rows(300)
        first = self.compact([], rows[:200], maximum=12000)
        second = self.compact(first, rows[150:300], maximum=12000)
        self.assertEqual(len(second), 300)
        self.assertEqual(len(set(second)), 300)
        self.assertEqual(second[-1], "family-299")
        self.assertGreater(second.index("family-149"), -1)
        self.assertGreater(second.index("family-150"), second.index("family-149"))


class WiringTests(unittest.TestCase):
    def test_today_and_week_persist_candidate_rotation(self):
        today_ws = (COMP / "websocket_v30.py").read_text(encoding="utf-8")
        week_ws = (COMP / "websocket_v20.py").read_text(encoding="utf-8")
        today_store = (COMP / "today_plan_store.py").read_text(encoding="utf-8")
        lifecycle = (COMP / "meal_lifecycle.py").read_text(encoding="utf-8")

        self.assertIn('candidate_history=saved.get("candidateHistory", [])', today_ws)
        self.assertIn('"candidateHistory": candidate_history', today_ws)
        self.assertIn("_MAX_CANDIDATE_HISTORY = 12000", today_store)
        self.assertIn('"candidateHistory"] = candidate_history[-_MAX_CANDIDATE_HISTORY:]', today_store)

        self.assertIn('candidate_history=getattr(lifecycle, "candidate_history", [])', week_ws)
        self.assertIn('hasattr(lifecycle, "async_record_candidate_history")', week_ws)
        self.assertIn("async_record_candidate_history", week_ws)
        self.assertIn("def candidate_history(self)", lifecycle)
        self.assertIn("async def async_record_candidate_history", lifecycle)

    def test_fullscreen_progress_cards_are_not_removed_while_fullscreen_is_active(self):
        guard = (
            COMP / "frontend" / "fullscreen-progress-guard-v260.js"
        ).read_text(encoding="utf-8")
        panel = (COMP / "frontend" / "cook4me-panel-v180.js").read_text(encoding="utf-8")
        registration = (COMP / "panel.py").read_text(encoding="utf-8")

        self.assertIn("FullscreenProgressGuardMixin", panel)
        self.assertIn("runtime-v264", panel)
        self.assertIn("runtime-v264", registration)
        self.assertIn("progress=260", registration)
        self.assertIn("contain:layout paint style", guard)
        self.assertIn("v260-progress-hidden", guard)
        self.assertIn("_v260DeferredProgressCards", guard)
        self.assertIn("if(this._v260FullscreenActive())", guard)
        self.assertIn("queueMicrotask(()=>this._v260FlushDeferredJobCards())", guard)


if __name__ == "__main__":
    unittest.main(verbosity=2)
