"""Actual preference normalization and locked Hub writes; no HA/network calls."""
import ast
import asyncio
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / 'custom_components/cook4me'
PACKAGE = 'cook4me_view_preferences_tests'
package = ModuleType(PACKAGE)
package.__path__ = [str(COMPONENT)]
sys.modules[PACKAGE] = package
# Unused scoring imports are isolated; the normalizers and their dependencies
# (diet exclusions and scoped nutrient targets) below are production code.
for name, attrs in [('today_logic', {'recipe_matches_meal_types': None, 'offline_meal_types': None}),
                    ('food_intelligence', {'nutrition_goal_bonus': None})]:
    module = ModuleType(PACKAGE+'.'+name)
    vars(module).update(attrs)
    sys.modules[module.__name__] = module
spec = importlib.util.spec_from_file_location(PACKAGE+'.shared_recipe_filters', COMPONENT/'shared_recipe_filters.py')
preferences = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = preferences
spec.loader.exec_module(preferences)

source = ast.parse((COMPONENT/'recipe_hub.py').read_text())
methods = [deepcopy(method) for node in source.body if isinstance(node, ast.ClassDef)
           for method in node.body if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef))
           and method.name in {'user_ui_preferences', 'async_set_user_ui_preferences'}]
ns = {'__name__': PACKAGE+'.hub_test', '__package__': PACKAGE, 'deepcopy': deepcopy, 'Any': object}
exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])), str(COMPONENT/'recipe_hub.py'), 'exec'), ns)

class Hub:
    user_ui_preferences = ns['user_ui_preferences']
    async_set_user_ui_preferences = ns['async_set_user_ui_preferences']
    def __init__(self):
        self._data = {'userUiPreferences': {}}
        self._lock = asyncio.Lock()
        self.saved = None
    async def _save(self):
        self.saved = deepcopy(self._data)
        await asyncio.sleep(0)

class Preferences(unittest.TestCase):
    def test_normalizes_every_supported_view(self):
        raw = {'filtersByView': {view: {'maxCost': '4', 'diet': 'vegetarian'} for view in preferences.TABS}}
        result = preferences.normalize_preferences(raw)
        self.assertEqual(set(result['filtersByView']), preferences.TABS)
        self.assertTrue(all(v['maxCost'] == 4 for v in result['filtersByView'].values()))
    def test_unknown_views_and_non_objects_are_rejected(self):
        result = preferences.normalize_preferences({'filtersByView': {'unknown': {}, 'today': [], 'week': {'maxCost': 3}}})
        self.assertEqual(set(result['filtersByView']), {'week'})
    def test_legacy_preferences_remain_supported(self):
        result = preferences.normalize_preferences({'filters': {'maxCost': 2}, 'lastTab': 'week'})
        self.assertEqual(result['filters']['maxCost'], 2)
        self.assertEqual(result['lastTab'], 'week')
    def test_same_limits_apply_to_per_view_filters(self):
        result = preferences.normalize_preferences({'filtersByView': {'today': {'maxCost': float('inf'), 'ingredients': ['x']*1000}}})
        self.assertIsNone(result['filtersByView']['today']['maxCost'])
        self.assertEqual(result['filtersByView']['today']['ingredients'], ['x'])
    def test_diet_exclusions_and_targets_survive(self):
        raw = {'dietProfile': 'member:one', 'diet': 'vegetarian', 'excludedTerms': ['peanut'],
               'nutrientTargets': {'daily': {'proteinTarget': 80}, 'mealTypes': {}}}
        result = preferences.normalize_preferences({'filtersByView': {'today': raw}})['filtersByView']['today']
        self.assertEqual(result['dietProfile'], 'member:one')
        self.assertEqual(result['excludedTerms'], ['peanut'])
        self.assertEqual(result['nutrientTargets']['daily']['proteinTarget'], 80)
    def test_partial_view_write_preserves_other_views(self):
        result = preferences.merge_preferences({'filtersByView': {'today': {'maxCost': 2}}, 'lastTab': 'today'},
                                               {'filtersByView': {'week': {'maxCost': 8}}})
        self.assertEqual(result['filtersByView']['today']['maxCost'], 2)
        self.assertEqual(result['filtersByView']['week']['maxCost'], 8)
        self.assertEqual(result['lastTab'], 'today')
    def test_merge_does_not_mutate_inputs(self):
        original = {'filtersByView': {'today': {'ingredients': ['x']}}}
        result = preferences.merge_preferences(original, {'lastTab': 'week'})
        result['filtersByView']['today']['ingredients'].append('y')
        self.assertEqual(original['filtersByView']['today']['ingredients'], ['x'])

class Persistence(unittest.IsolatedAsyncioTestCase):
    async def test_real_hub_method_preserves_independent_views(self):
        hub = Hub()
        await hub.async_set_user_ui_preferences('one', {'filtersByView': {'today': {'maxCost': 2}}})
        await hub.async_set_user_ui_preferences('one', {'filtersByView': {'week': {'maxCost': 8}}})
        value = hub.user_ui_preferences('one')['filtersByView']
        self.assertEqual(value['today']['maxCost'], 2)
        self.assertEqual(value['week']['maxCost'], 8)
    async def test_two_users_and_entries_are_isolated(self):
        hub, second = Hub(), Hub()
        await hub.async_set_user_ui_preferences('one', {'filtersByView': {'today': {'maxCost': 2}}})
        await hub.async_set_user_ui_preferences('two', {'filtersByView': {'today': {'maxCost': 8}}})
        self.assertEqual(hub.user_ui_preferences('one')['filtersByView']['today']['maxCost'], 2)
        self.assertEqual(second.user_ui_preferences('one'), {})
    async def test_concurrent_different_view_updates_keep_both(self):
        hub = Hub()
        await asyncio.gather(*(hub.async_set_user_ui_preferences('one', {'filtersByView': {view: {'maxCost': value}}})
                               for view, value in [('today', 2), ('week', 8)]))
        self.assertEqual(set(hub.user_ui_preferences('one')['filtersByView']), {'today', 'week'})
    async def test_saved_map_survives_restart_normalization_and_copy(self):
        hub = Hub()
        await hub.async_set_user_ui_preferences('one', {'filtersByView': {'week': {'maxCost': 8}}})
        second = Hub()
        second._data['userUiPreferences'] = {key: preferences.normalize_preferences(value)
                                            for key, value in hub.saved['userUiPreferences'].items()}
        snapshot = second.user_ui_preferences('one')
        snapshot['filtersByView']['week']['maxCost'] = 99
        self.assertEqual(second.user_ui_preferences('one')['filtersByView']['week']['maxCost'], 8)

if __name__ == '__main__':
    unittest.main()
