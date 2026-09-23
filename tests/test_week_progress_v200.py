"""Exercise production generation and executor work with controlled HA/storage."""
import ast
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from functools import partial
import importlib.util
from pathlib import Path
import sys
import threading
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/cook4me'
NAME = 'week_progress_v200_test'
pkg = types.ModuleType(NAME)
pkg.__path__ = [str(COMPONENT)]
sys.modules[NAME] = pkg
from week_progress_v200_test.executor_progress import ExecutorProgress


def module(name, **members):
    result = types.ModuleType(NAME + '.' + name)
    vars(result).update(members)
    sys.modules[result.__name__] = result
    setattr(pkg, name, result)
    return result


def functions(path, names, namespace):
    tree = ast.parse(path.read_text())
    body = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
    assert len(body) == len(names)
    for node in body:
        node.decorator_list = []
    exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), str(path), 'exec'), namespace)


class Hass:
    async def async_add_executor_job(self, function, *args):
        return await asyncio.get_running_loop().run_in_executor(None, partial(function, *args))


async def resolved(value):
    return value


class Store:
    def __init__(self):
        self.reads = [0, 0]
        self.data = {str(i): {'values': {'protein': i}} for i in range(200)}
    @property
    def generic(self):
        self.reads[0] += 1
        return deepcopy(self.data)
    @property
    def stock_lots(self):
        self.reads[1] += 1
        return {}


class Lifecycle:
    settings = {'avoidRecentDays': 0, 'leftoversFirst': False}
    leftovers = []
    def __init__(self):
        self.slots = []
        self.writes = []
    async def async_replace_week(self, start, slots):
        self.writes.append(deepcopy(slots))
        self.slots = deepcopy(slots)


def setup_generation():
    hass, lifecycle, store = Hass(), Lifecycle(), Store()
    bridge = types.SimpleNamespace(hass=hass, recipe_hub=types.SimpleNamespace(profile={'houseIngredients': []}, ui_preferences={}))
    # Actual generator; only the catalog/provider and scoring data are fixtures.
    module('release_catalog', release_catalog_ready=lambda: True)
    module('weekly_plan', MEAL_SLOT_ORDER=['breakfast', 'lunch', 'dinner'],
           meal_slots_for_date=lambda filters, settings, stamp: ['breakfast', 'lunch', 'dinner'])
    module('diet_profiles', resolve_filters=lambda profile, filters: filters)
    module('shared_recipe_filters', normalize_filters=lambda filters: filters, daily_targets=lambda filters: {},
           recipe_target_scope=lambda *args: ({}, None))
    module('nutrient_targets', daily_progress_bonus=lambda *a, **kw: {'bonus': 0}, target_bonus=lambda *a, **kw: {'bonus': 0})
    module('today_logic', recipe_identity=lambda recipe: recipe.get('id'))
    # Real variety checks are used, including the no-duplicate selection logic.
    from week_progress_v200_test import weekly_variety
    namespace = dict(__name__=NAME+'.generate', __package__=NAME, HomeAssistant=object, Any=object,
        asyncio=asyncio, deepcopy=deepcopy, date=date, datetime=datetime, timedelta=timedelta, timezone=timezone, partial=partial,
        _text=lambda value: str(value or '').strip(), _MAX_WEEK_CANDIDATES=180, _WEEK_NUTRITION_BATCH=30,
        nutrition_store_for_bridge=lambda b: resolved(store), cost_store_for_bridge=lambda b: resolved(None),
        meal_history_store_for_bridge=lambda b: resolved(types.SimpleNamespace(recent=lambda n: [])),
        normalize_nutrition_goal=lambda value: value, recipe_identity=lambda recipe: recipe.get('id'),
        recipe_matches_meal_types=lambda recipe, meals: bool(set(recipe['mealTypes']) & set(meals)),
        calculate_recipe_nutrition_fefo=lambda *a, **kw: {'totals': {'protein': 2}},
        nutrition_goal_bonus=lambda *a: {'bonus': 0}, calculate_recipe_cost=lambda *a, **kw: {'totalsByCurrency': {'EUR': 1}},
        reservation_status=lambda *a: {'shortages': [], 'unknown': []})
    functions(COMPONENT/'websocket_v20.py', {'_generate_week', '_week_candidate_nutrition', '_score_week_pool'}, namespace)
    candidates = [{'id': str(i), 'title': 'Dish '+str(i), 'ingredients': [{'key': 'food-'+str(i)}],
                   'mealTypes': ['breakfast', 'main'], 'match': {'safe': True, 'score': i}} for i in range(30)]
    async def search(bridge, *, progress=None, **kwargs):
        # This assertion fails on v199: the caller dropped the callback.
        assert callable(progress), 'weekly generation dropped catalog progress'
        report = ExecutorProgress(progress)
        def compute():
            report('catalog_index', completed=0, total=300)
            for i in range(25, 301, 25):
                report('catalog_index', completed=i, total=300)
            report('ranking', completed=0, total=len(candidates))
            report('ranking', completed=len(candidates), total=len(candidates))
            return {'items': deepcopy(candidates)}
        return await report.run(hass, compute)
    runtime = module('shared_recipe_runtime', search_filtered=search)
    return hass, bridge, lifecycle, store, namespace, runtime, candidates


class ExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_events_run_on_loop_not_worker(self):
        thread = threading.get_ident()
        delivered = []
        report = ExecutorProgress(lambda phase, **values: delivered.append((threading.get_ident(), phase, values)))
        def work():
            self.assertNotEqual(thread, threading.get_ident())
            report('catalog_index', completed=25, total=25)
            return 'ok'
        self.assertEqual(await report.run(Hass(), work), 'ok')
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0][0], thread)

    async def test_throttles_large_bursts_but_preserves_final_count(self):
        delivered = []
        report = ExecutorProgress(lambda phase, **values: delivered.append(values), interval=60)
        def work():
            for i in range(10001):
                report('ranking', completed=i, total=10000)
        await report.run(Hass(), work)
        self.assertEqual([r['completed'] for r in delivered], [0, 10000])

    async def test_phase_and_denominator_changes_emit_immediately(self):
        events = []
        report = ExecutorProgress(lambda phase, **values: events.append((phase, values['total'])), interval=60)
        def work():
            report('catalog_index', completed=0, total=100)
            report('ranking', completed=0, total=100)
            report('ranking', completed=0, total=21)
        await report.run(Hass(), work)
        self.assertEqual(events, [('catalog_index', 100), ('ranking', 100), ('ranking', 21)])

    async def test_cancel_stops_worker_before_releasing_weekly_lane_even_after_repeated_cancel(self):
        ready, release, finished = threading.Event(), threading.Event(), threading.Event()
        events, entered = [], []
        lock = asyncio.Lock()
        report = ExecutorProgress(lambda *a, **kw: events.append(kw))
        def work():
            ready.set()
            release.wait(2)
            try:
                report('catalog_index', completed=1, total=10)
            finally:
                finished.set()
        async def generation():
            async with lock:
                await report.run(Hass(), work)
        task = asyncio.create_task(generation())
        while not ready.is_set():
            await asyncio.sleep(.005)
        task.cancel()
        await asyncio.sleep(.01)
        task.cancel()
        async def next_generation():
            async with lock:
                entered.append(finished.is_set())
        second = asyncio.create_task(next_generation())
        await asyncio.sleep(.01)
        self.assertTrue(lock.locked())
        self.assertEqual(entered, [])
        release.set()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await second
        self.assertEqual(entered, [True])
        self.assertEqual(events, [])

    async def test_worker_cancel_checkpoints_exist_without_ui_subscriber(self):
        report = ExecutorProgress()
        entered = threading.Event()
        def work():
            entered.set()
            while True:
                report('ranking', completed=0, total=10)
                time.sleep(.005)
        task = asyncio.create_task(report.run(Hass(), work))
        while not entered.is_set():
            await asyncio.sleep(.005)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 1)

    async def test_worker_exceptions_propagate_and_loop_remains_responsive(self):
        report = ExecutorProgress()
        ticks = []
        async def tick():
            await asyncio.sleep(.005)
            ticks.append(1)
        timer = asyncio.create_task(tick())
        def work():
            time.sleep(.03)
            raise ValueError('test failure')
        with self.assertRaisesRegex(ValueError, 'test failure'):
            await report.run(Hass(), work)
        await timer
        self.assertEqual(ticks, [1])

    async def test_closed_reporter_does_not_send_late_callbacks(self):
        events = []
        report = ExecutorProgress(lambda *a, **kw: events.append(kw))
        report('ranking', completed=2, total=3)
        report.close()
        await asyncio.sleep(0)
        self.assertEqual(events, [])


class GenerationTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_week_forwards_catalog_progress_and_creates_21_slots(self):
        hass, bridge, lifecycle, store, ns, runtime, candidates = setup_generation()
        thread = threading.get_ident()
        events = []
        def progress(phase, **values):
            self.assertEqual(threading.get_ident(), thread)
            events.append((phase, values, bool(lifecycle.writes)))
        result = await ns['_generate_week'](hass, bridge, lifecycle, week_start='2026-09-23', languages=['de'],
            diet='vegetarian', query='', refresh=False, shared_filters={}, ui_language='el', progress=progress)
        self.assertEqual(result['slotCount'], 21)
        self.assertEqual(len(lifecycle.writes), 1)
        self.assertTrue(any(p=='catalog_index' and v.get('total')==300 and v.get('completed', 0)>0 and not persisted
                            for p,v,persisted in events))
        self.assertEqual(len({slot['recipe']['id'] for slot in lifecycle.slots}), 21)
        self.assertEqual(store.reads, [1, 1])  # 30 candidates in one snapshot batch.
        self.assertIsNone(events[0][1].get('total'))  # No fictitious 0/1 phase.
        self.assertEqual(candidates[0]['match'], {'safe': True, 'score': 0})

    async def test_cold_catalog_check_runs_off_ha_loop(self):
        hass, bridge, lifecycle, store, ns, runtime, candidates = setup_generation()
        owner = threading.get_ident()
        pkg.release_catalog.release_catalog_ready = lambda: threading.get_ident()!=owner
        await ns['_generate_week'](hass, bridge, lifecycle, week_start='2026-09-23', languages=['de'],
            diet='vegetarian', query='', refresh=False, shared_filters={}, progress=lambda *a, **kw: None)
        self.assertEqual(len(lifecycle.slots), 21)

    async def test_cancelled_search_never_persists_partial_week(self):
        hass, bridge, lifecycle, store, ns, runtime, candidates = setup_generation()
        ready = asyncio.Event()
        async def search(*a, **kw):
            ready.set()
            await asyncio.sleep(10)
        runtime.search_filtered = search
        task = asyncio.create_task(ns['_generate_week'](hass, bridge, lifecycle, week_start='2026-09-23', languages=['de'],
            diet='vegetarian', query='', refresh=False, shared_filters={}, progress=lambda *a, **kw: None))
        await ready.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(lifecycle.writes, [])

    async def test_no_matches_finishes_with_empty_plan_not_an_endless_progress_job(self):
        hass, bridge, lifecycle, store, ns, runtime, candidates = setup_generation()
        candidates.clear()
        result = await ns['_generate_week'](hass, bridge, lifecycle, week_start='2026-09-23', languages=['de'],
            diet='vegetarian', query='', refresh=False, shared_filters={}, progress=lambda *a, **kw: None)
        self.assertEqual(result['slotCount'], 0)
        self.assertEqual(len(lifecycle.writes), 1)

    async def test_failed_catalog_does_not_save_a_plan(self):
        hass, bridge, lifecycle, store, ns, runtime, candidates = setup_generation()
        async def search(*a, **kw):
            raise ValueError('catalog failed')
        runtime.search_filtered = search
        with self.assertRaisesRegex(ValueError, 'catalog failed'):
            await ns['_generate_week'](hass, bridge, lifecycle, week_start='2026-09-23', languages=['de'],
                diet='vegetarian', query='', refresh=False, shared_filters={}, progress=lambda *a, **kw: None)
        self.assertEqual(lifecycle.writes, [])

    async def test_snapshot_optimization_matches_previous_per_recipe_results(self):
        hass, bridge, lifecycle, store, ns, runtime, candidates = setup_generation()
        result = ns['_week_candidate_nutrition'](candidates, [], store)
        self.assertEqual(store.reads, [1, 1])
        expected = {id(row): ns['calculate_recipe_nutrition_fefo'](row, [], generic=store.generic, stock_lots=store.stock_lots) for row in candidates}
        self.assertEqual(result, expected)


class SharedRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_processor_snapshots_stores_once_and_keeps_all_rows(self):
        store = Store()
        module('websocket_v13', _rank_filtered=lambda bridge, rows, **kw: rows)
        module('websocket_v18', _recent_identities=lambda *a, **kw: set())
        module('costs', cost_store_for_bridge=lambda b: resolved(None))
        module('costing', calculate_recipe_cost=lambda *a, **kw: {})
        module('meal_history', meal_history_store_for_bridge=lambda b: resolved(types.SimpleNamespace(recent=lambda n: [])))
        module('nutrition', nutrition_store_for_bridge=lambda b: resolved(store))
        seen = []
        def calculate(row, house, *, generic, stock_lots):
            seen.append((id(generic), id(stock_lots)))
            return {'protein': generic['1']['values']['protein']}
        module('nutrition_fefo', calculate_recipe_nutrition_fefo=calculate)
        module('today_logic', recipe_identity=lambda r: r['id'])
        module('diet_profiles', resolve_filters=lambda profile, filters: filters)
        ns = dict(__name__=NAME+'.runtime', __package__=NAME,
                  normalize_filters=lambda f: {'maxCost': None, 'diet':'vegetarian', 'ingredients':[], 'avoidRecentDays':0},
                  apply_filters=lambda rows, settings, **kw: [{**r, 'nutrition':kw['nutrition'](r)} for r in rows])
        functions(COMPONENT/'shared_recipe_runtime.py', {'processor'}, ns)
        bridge = types.SimpleNamespace(recipe_hub=types.SimpleNamespace(profile={'houseIngredients':[]}))
        process = await ns['processor'](bridge, {})
        rows = [{'id': str(i)} for i in range(200)]
        output = await Hass().async_add_executor_job(process, rows)
        self.assertEqual(len(output), len(rows))
        self.assertEqual(store.reads, [1,1])
        self.assertEqual(len(set(seen)), 1)
        self.assertTrue(all(row['nutrition']=={'protein':1} for row in output))
        self.assertNotIn('nutrition', rows[0])

    async def test_actual_search_passes_checkpoint_to_catalog_and_processor(self):
        seen=[]
        async def processor(bridge, filters, **kw):
            self.assertIsInstance(kw['progress'], ExecutorProgress)
            def process(rows):
                kw['progress']('nutrition', completed=1, total=1)
                return rows
            return process
        def search(query, **kw):
            self.assertIsInstance(kw['progress'], ExecutorProgress)
            kw['progress']('catalog_index', completed=1, total=1)
            return {'items':kw['filter_rows']([{'id':'rice'}])}
        module('release_catalog', search_release_recipes=search)
        module('websocket_v30', _device_language=lambda b: 'de', _device_country=lambda b: 'DE')
        ns=dict(__name__=NAME+'.runtime', __package__=NAME,processor=processor)
        functions(COMPONENT/'shared_recipe_runtime.py', {'search_filtered'}, ns)
        result=await ns['search_filtered'](types.SimpleNamespace(hass=Hass()), query='', languages=['de'], language='el', filters={}, progress=lambda phase, **kw:seen.append(phase))
        self.assertEqual(result, {'items':[{'id':'rice'}]})
        self.assertEqual(seen,['catalog_index','nutrition'])

if __name__ == '__main__':
    unittest.main()
