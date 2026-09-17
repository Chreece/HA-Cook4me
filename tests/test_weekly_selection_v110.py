"""Selection persistence, stock arithmetic, filtered totals and batch regeneration."""
import asyncio
from copy import deepcopy
from datetime import date
import importlib
import unittest
from unittest.mock import AsyncMock

import test_meal_lifecycle_v20 as lifecycle_tests
import test_weekly_summary_v109 as summary_tests
import test_weekly_variety_v69 as variety_tests
import test_rolling_week_v67 as rolling_tests


class SelectionStoreTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        *_, cls.module = lifecycle_tests.load_modules()

    def slot(self, name, quantity=100, **fields):
        return {'id': name, 'date': '2026-09-17', 'mealType': 'breakfast',
                'recipe': {'id': name, 'title': name, 'ingredients': [
                    {'key': 'rice', 'name': 'Rice', 'quantity': quantity, 'unit': 'g'}]}, **fields}

    async def test_default_selected_and_saved_unselection_survive_reload(self):
        store = self.module.Cook4MeMealLifecycleStore(object(), 'entry')
        await store.async_replace_week('2026-09-17', [self.slot('a'), self.slot('b')])
        self.assertTrue(all(row['selected'] for row in store.slots))
        await store.async_select_slots(['a'], False)
        reloaded = self.module.Cook4MeMealLifecycleStore(object(), 'entry')
        reloaded._store.async_load = AsyncMock(return_value=deepcopy(store._data))
        await reloaded.async_load()
        self.assertEqual([row['selected'] for row in reloaded.slots], [False, True])
        snapshot = reloaded.snapshot([], start_date=date(2026, 9, 17))
        self.assertEqual(snapshot['shoppingDelta'][0]['quantity'], 100)
        self.assertEqual(snapshot['shoppingDelta'][0]['slots'], ['b'])
        before = reloaded.slots
        with self.assertRaises(ValueError):
            await reloaded.async_select_slots(['b', 'missing'], False)
        self.assertEqual(reloaded.slots, before, 'Invalid batch must not partially change selection')

    async def test_selection_changes_aggregate_coverage_and_purchase_shortage(self):
        stock = [{'key': 'rice', 'name': 'Rice', 'quantity': 150, 'unit': 'g'}]
        slots = [self.slot('a'), self.slot('b')]
        self.assertEqual(self.module.shopping_delta(slots, stock)[0]['quantity'], 50)
        slots[1]['selected'] = False
        status = self.module.reservation_status(slots, stock)
        self.assertTrue(status['fullyCovered'])
        self.assertEqual(status['items'][0]['reserved'], 100)
        self.assertEqual(self.module.shopping_delta(slots, stock), [])
        slots[0]['selected'] = False
        self.assertEqual(self.module.reservation_status(slots, stock)['items'], [])

    async def test_absent_stock_is_zero_existing_unknown_is_never_guessed(self):
        slots = [self.slot('a')]
        empty = self.module.reservation_status(slots, [])
        self.assertEqual(empty['items'][0]['available'], 0)
        self.assertEqual(empty['shortages'][0]['shortage'], 100)
        for row in [{'key': 'rice', 'name': 'Rice'},
                    {'key': 'rice', 'name': 'Rice', 'quantity': 5, 'unit': 'ml'}]:
            status = self.module.reservation_status(slots, [row])
            self.assertEqual(len(status['unknown']), 1)
            self.assertEqual(status['shortages'], [])
        unlimited = self.module.reservation_status(slots, [{'key': 'rice', 'name': 'Rice', 'unlimited': True}])
        self.assertTrue(unlimited['fullyCovered'])

    async def test_selection_handler_validates_dates_and_returns_the_shared_filtered_view(self):
        store = self.module.Cook4MeMealLifecycleStore(object(), 'entry')
        await store.async_replace_week('2026-09-17', [self.slot('a'), self.slot('b'), self.slot('old', date='2026-09-01')])
        boundary = rolling_tests.RollingWeekTests()
        boundary.lifecycle = self.module
        ns, connection, answers = boundary.boundary(store)
        call = rolling_tests.handler('ws_week_select', ns)
        message = {'id': 1, 'slot_ids': ['a', 'b'], 'selected': False,
                   'shared_filters': {'languages': ['de']}, 'ui_language': 'el'}
        await call(None, connection, message)
        self.assertEqual([row['selected'] for row in store.slots], [False, False, True])
        self.assertEqual(ns['_state'].await_args.kwargs, {'shared_filters': {'languages': ['de']}, 'ui_language': 'el'})
        with self.assertRaisesRegex(ValueError, 'next seven days'):
            await call(None, connection, {**message, 'slot_ids': ['old']})

    async def test_unselected_adaptations_do_not_block_purchasing_selected_recipes(self):
        store = self.module.Cook4MeMealLifecycleStore(object(), 'entry')
        adapted = self.slot('adapted', selected=False)
        adapted['recipe']['match'] = {'requiresSubstitutions': True}
        await store.async_replace_week('2026-09-17', [self.slot('a'), adapted])
        boundary = rolling_tests.RollingWeekTests()
        boundary.lifecycle = self.module
        ns, connection, answers = boundary.boundary(store)
        call = rolling_tests.handler('ws_week_add_shopping', ns)
        await call(None, connection, {'id': 1})
        rows = ns['_shopping_add'].await_args.args[1]
        self.assertEqual([(row['name'], row['quantity'], row['slots']) for row in rows], [('Rice', 100, ['a'])])


class SelectedSummaryTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(summary_tests.WeeklySummaryTests.setUpClass.__func__)
    setUp = summary_tests.WeeklySummaryTests.setUp
    asyncTearDown = summary_tests.WeeklySummaryTests.asyncTearDown
    store = summary_tests.WeeklySummaryTests.store
    slot = summary_tests.WeeklySummaryTests.slot

    async def test_unselected_recipes_stay_visible_but_do_not_contribute_cost_or_shopping(self):
        store = await self.store()
        await store.async_set_reference('k:rice', amount=2, currency='EUR', basis_quantity=100,
                                       basis_unit='g', country='DE', source='manual')
        slots = [self.slot('Rice'), {**self.slot('Potato'), 'selected': False}]
        view = await self.week.refresh_plan(self.bridge, {'slots': deepcopy(slots)})
        self.assertEqual(len(view['slots']), 2)
        self.assertEqual(view['selectedSlotCount'], 1)
        self.assertEqual(view['weeklyCostByCurrency'], {'EUR': 4})
        self.assertEqual([row['slots'] for row in view['shoppingDelta']], [['Rice']])
        view['slots'][0]['selected'] = False
        empty = await self.week.refresh_plan(self.bridge, view)
        self.assertEqual(empty['weeklyCostByCurrency'], {})
        self.assertEqual(empty['shoppingDelta'], [])
        self.assertEqual(empty['reservations']['items'], [])

    async def test_filtered_slots_remain_outside_selection_totals(self):
        slots = [self.slot('Rice'), self.slot('Potato', language='fr')]
        view = await self.week.refresh_plan(self.bridge, {'slots': slots}, filters={'languages': ['de']})
        self.assertEqual(view['selectedSlotCount'], 1)
        self.assertEqual(view['filteredSlotCount'], 1)
        self.assertTrue(all(row['slots'] == ['Rice'] for row in view['shoppingDelta']))


class BatchRegenerationTests(unittest.TestCase):
    setUpClass = classmethod(variety_tests.WeeklyVarietyTests.setUpClass.__func__)
    candidates = variety_tests.WeeklyVarietyTests.candidates
    generate = variety_tests.WeeklyVarietyTests.generate

    def slots(self):
        candidates = self.candidates()
        return [{'id': name, 'date': f'2026-09-{15+i}', 'mealType': 'breakfast',
                 'recipe': candidates[index], 'selected': selected}
                for i, (name, index, selected) in enumerate([('a', 0, True), ('b', 3, False), ('c', 5, True)])]

    def test_bulk_replaces_only_targets_preserving_ids_and_selection_without_duplicates(self):
        slots = self.slots()
        result = self.generate(self.candidates(), slots, replace_ids=['a', 'b'])
        self.assertEqual(result[2], slots[2])
        self.assertEqual([row['id'] for row in result], ['a', 'b', 'c'])
        self.assertEqual([row['selected'] for row in result], [True, False, True])
        originals = [self.variety.signature(row['recipe']) for row in slots]
        self.assertTrue(all(not self.variety.already_planned(self.variety.signature(row['recipe']), originals) for row in result[:2]))
        self.assertFalse(self.variety.similar(*(self.variety.signature(row['recipe']) for row in result[:2])))

    def test_no_match_keeps_originals_and_reports_unchanged_ids(self):
        slots = self.slots()
        result, meta = self.generate([], slots, replace_ids=['a', 'b'], return_result=True)
        self.assertEqual(result, slots)
        self.assertEqual(meta['unchangedSlotIds'], ['a', 'b'])

    def test_invalid_or_empty_target_list_never_rebuilds_the_whole_week(self):
        for ids in [[], ['gone'], ['a', 'gone']]:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                self.generate(self.candidates(), self.slots(), replace_ids=ids)

    def test_concurrent_selection_edit_is_not_overwritten(self):
        observed = []
        def update(lifecycle):
            lifecycle.slots[0]['selected'] = False
            observed.append(lifecycle)
        with self.assertRaisesRegex(ValueError, 'changed during generation'):
            self.generate(self.candidates(), self.slots(), replace_ids=['a'], during_search=update)
        self.assertFalse(observed[0].slots[0]['selected'])
        self.assertEqual(observed[0].slots[0]['recipe'], self.slots()[0]['recipe'])


if __name__ == '__main__':
    unittest.main()
