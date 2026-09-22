from pathlib import Path
import ast
import importlib.util
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
PKG=ROOT/"custom_components"/"cook4me"
WEEK=PKG/"websocket_v20.py"
LIFECYCLE=PKG/"meal_lifecycle.py"
VARIETY=PKG/"weekly_variety.py"
PLAN=PKG/"weekly_plan.py"
JOBS=PKG/"websocket_v36.py"
COST_CACHE=PKG/"recipe_cost_cache.py"


def _function_source(path, name):
    source=path.read_text(encoding="utf-8")
    tree=ast.parse(source)
    node=next(
        item for item in tree.body
        if isinstance(item,(ast.FunctionDef,ast.AsyncFunctionDef)) and item.name==name
    )
    return ast.get_source_segment(source,node) or ""


def _load_variety():
    package=types.ModuleType("cook4me_weekly_variety_test")
    package.__path__=[str(PKG)]
    sys.modules[package.__name__]=package

    presentation=types.ModuleType(package.__name__+".catalog_presentation")
    presentation.clean_name=lambda value: str(value or "").strip()
    presentation.name_key=lambda value: " ".join(str(value or "").casefold().split())
    sys.modules[presentation.__name__]=presentation

    today=types.ModuleType(package.__name__+".today_logic")
    today.recipe_identity=lambda recipe: str((recipe or {}).get("id") or "")
    sys.modules[today.__name__]=today

    spec=importlib.util.spec_from_file_location(
        package.__name__+".weekly_variety",VARIETY
    )
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class WeeklyResponsiveVarietyV181Tests(unittest.TestCase):
    def test_full_regenerate_excludes_current_week_before_fallback(self):
        module=_load_variety()
        old={
            "id":"old",
            "title":"Tomato basil pasta",
            "ingredients":[
                {"key":"pasta"},{"key":"tomato"},{"key":"basil"},{"key":"olive-oil"}
            ],
        }
        near_duplicate={
            "id":"near",
            "title":"Basil tomato pasta",
            "ingredients":[
                {"key":"pasta"},{"key":"tomato"},{"key":"basil"},{"key":"olive-oil"}
            ],
        }
        alternative={
            "id":"different",
            "title":"Mushroom barley bowl",
            "ingredients":[
                {"key":"barley"},{"key":"mushroom"},{"key":"parsley"},{"key":"lemon"}
            ],
        }
        candidates=[old,near_duplicate,alternative]
        signatures={id(row):module.signature(row) for row in candidates}
        available=module.available_candidates(
            candidates,signatures,[],[module.signature(old)]
        )
        self.assertEqual([row["id"] for row in available],["different"])

    def test_weekly_candidate_work_is_bounded_and_scored_off_event_loop(self):
        source=WEEK.read_text(encoding="utf-8")
        generate=_function_source(WEEK,"_generate_week")
        self.assertIn("_MAX_WEEK_CANDIDATES = 180",source)
        self.assertIn("candidates = list(candidates[:_MAX_WEEK_CANDIDATES])",generate)
        self.assertIn("hass.async_add_executor_job",generate)
        self.assertIn("_score_week_pool",generate)
        self.assertNotIn("for candidate in pool:",generate)
        self.assertIn("available_candidates(",generate)
        self.assertIn('"candidateCount": len(candidates)',generate)
        self.assertIn('"changedSlotCount": changed_slots',generate)
        self.assertIn('"regenerationFallbackSlotIds": regeneration_fallback_slots',generate)

    def test_week_mutations_are_fifo_but_read_only_week_state_is_not_locked(self):
        lifecycle=LIFECYCLE.read_text(encoding="utf-8")
        self.assertIn("self._weekly_mutation_lock = asyncio.Lock()",lifecycle)
        self.assertIn("async def weekly_mutation(self)",lifecycle)
        self.assertIn("async with self._weekly_mutation_lock:",lifecycle)

        for name in (
            "ws_week_generate","ws_week_settings_set","ws_week_slot_clear",
            "ws_week_select","ws_week_add_shopping","ws_leftover_consume",
        ):
            self.assertIn("weekly_mutation()",_function_source(WEEK,name),name)

        state=_function_source(WEEK,"ws_week_state")
        self.assertNotIn("weekly_mutation()",state)
        self.assertIn("await _state(",state)

    def test_week_job_has_real_progress_including_final_per_slot_refresh(self):
        week=WEEK.read_text(encoding="utf-8")
        jobs=JOBS.read_text(encoding="utf-8")
        plan=PLAN.read_text(encoding="utf-8")
        self.assertIn('request["_cook4me_job_id"] = msg["job_id"]',jobs)
        self.assertIn("def _emit_week_progress(",week)
        self.assertIn('message="Queued behind another weekly plan change"',week)
        self.assertIn('kind="week_generate_queued"',week)
        self.assertIn('"ranking"',week)
        self.assertIn('"persist"',week)
        self.assertIn("Scoring {len(pool)} candidates",week)
        self.assertIn("progress=progress",week)
        self.assertIn("total_slots = max(1, len(slots))",plan)
        self.assertIn('progress("cost", completed=0, total=total_slots',plan)
        self.assertIn("completed=index",plan)

    def test_recipe_cost_calculator_cannot_block_ha_loop(self):
        source=COST_CACHE.read_text(encoding="utf-8")
        cost=_function_source(COST_CACHE,"async_cost")
        self.assertIn("self._lock = asyncio.Lock()",source)
        self.assertIn("async with self._lock:",cost)
        self.assertIn("await self._hass.async_add_executor_job(",cost)
        self.assertIn("calculate_recipe_cost",cost)


if __name__=="__main__":
    unittest.main()
