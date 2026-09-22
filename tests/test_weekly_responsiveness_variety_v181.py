from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/"custom_components"/"cook4me"


def _load_variety():
    package=types.ModuleType("cook4me_weekly_v181_test")
    package.__path__=[str(PKG)]
    sys.modules[package.__name__]=package
    presentation=types.ModuleType(f"{package.__name__}.catalog_presentation")
    presentation.clean_name=lambda value: str(value or "").strip()
    presentation.name_key=lambda value: " ".join(str(value or "").lower().split())
    sys.modules[presentation.__name__]=presentation
    today=types.ModuleType(f"{package.__name__}.today_logic")
    today.recipe_identity=lambda recipe: str((recipe or {}).get("id") or (recipe or {}).get("title") or "")
    sys.modules[today.__name__]=today
    spec=importlib.util.spec_from_file_location(
        f"{package.__name__}.weekly_variety",PKG/"weekly_variety.py"
    )
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WeeklyResponsiveVarietyV181Tests(unittest.TestCase):
    def test_changed_python_sources_parse(self):
        for name in (
            "websocket_v20.py","websocket_v36.py","meal_lifecycle.py",
            "weekly_plan.py","recipe_cost_cache.py","weekly_variety.py",
        ):
            ast.parse((PKG/name).read_text(encoding="utf-8"),filename=name)

    def test_week_mutations_are_serialized_but_state_browsing_is_not(self):
        source=(PKG/"websocket_v20.py").read_text(encoding="utf-8")
        self.assertIn("async with lifecycle.weekly_mutation():",source)
        self.assertIn("async with store.weekly_mutation():",source)
        state=source.split("async def ws_week_state",1)[1].split("async def ws_week_settings_set",1)[0]
        self.assertNotIn("weekly_mutation()",state)
        lifecycle=(PKG/"meal_lifecycle.py").read_text(encoding="utf-8")
        self.assertIn("self._weekly_mutation_lock = asyncio.Lock()",lifecycle)
        self.assertIn("async def weekly_mutation(self):",lifecycle)

    def test_heavy_weekly_scoring_and_costing_leave_event_loop(self):
        source=(PKG/"websocket_v20.py").read_text(encoding="utf-8")
        self.assertIn("_MAX_WEEK_CANDIDATES = 180",source)
        self.assertIn("_WEEK_NUTRITION_BATCH = 30",source)
        self.assertIn("await hass.async_add_executor_job(",source)
        self.assertIn("partial(\n            v13._rank_filtered",source)
        self.assertIn("_week_candidate_nutrition",source)
        self.assertIn("partial(\n                _score_week_pool",source)
        cache=(PKG/"recipe_cost_cache.py").read_text(encoding="utf-8")
        self.assertIn("self._lock = asyncio.Lock()",cache)
        self.assertIn("await self._hass.async_add_executor_job(",cache)
        plan=(PKG/"weekly_plan.py").read_text(encoding="utf-8")
        self.assertIn("calculate_recipe_nutrition_fast",plan)
        self.assertIn("async_add_executor_job",plan)

    def test_week_job_reports_real_progress_and_reuses_fresh_costs(self):
        source=(PKG/"websocket_v20.py").read_text(encoding="utf-8")
        for phase in ("catalog_index","nutrition","ranking","persist","cost"):
            self.assertIn(f'"{phase}"',source)
        self.assertIn("progress=score_progress",source)
        self.assertIn("Scoring candidate {candidate_index}/{pool_total}",source)
        self.assertIn("reuse_costs=True",source)
        plan=(PKG/"weekly_plan.py").read_text(encoding="utf-8")
        self.assertIn("reuse_costs=False",plan)
        self.assertIn('if reuse_costs and isinstance(slot.get("cost"), dict)',plan)
        jobs=(PKG/"websocket_v36.py").read_text(encoding="utf-8")
        self.assertIn('request["_cook4me_job_id"] = msg["job_id"]',jobs)

    def test_full_regeneration_prefers_dishes_not_in_previous_plan(self):
        module=_load_variety()
        old={"id":"old","title":"Tomato pasta","ingredients":[{"canonicalName":"tomato"},{"canonicalName":"pasta"},{"canonicalName":"basil"}]}
        same_family={"id":"new-similar","title":"Tomato pasta with basil","ingredients":[{"canonicalName":"tomato"},{"canonicalName":"pasta"},{"canonicalName":"basil"}]}
        different={"id":"different","title":"Mushroom risotto","ingredients":[{"canonicalName":"mushroom"},{"canonicalName":"rice"},{"canonicalName":"parmesan"}]}
        candidates=[same_family,different]
        signatures={id(row):module.signature(row) for row in candidates}
        fresh=module.available_candidates(candidates,signatures,[],[module.signature(old)])
        self.assertEqual([row["id"] for row in fresh],["different"])
        fallback=module.available_candidates(candidates,signatures,[])
        self.assertEqual({row["id"] for row in fallback},{"new-similar","different"})

    def test_generation_result_exposes_variety_diagnostics(self):
        source=(PKG/"websocket_v20.py").read_text(encoding="utf-8")
        for key in (
            '"candidateCount"','"candidateLimit"','"regeneratedFromExisting"',
            '"regenerationFallbackSlotIds"','"changedSlotCount"',
        ):
            self.assertIn(key,source)


if __name__=="__main__":
    unittest.main()
