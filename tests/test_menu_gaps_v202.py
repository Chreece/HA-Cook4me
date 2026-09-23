"""Production weekly presentation with controlled catalog and storage boundaries."""
import asyncio
from copy import deepcopy
import importlib
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
NAME='menu_gaps_test'
pkg=types.ModuleType(NAME);pkg.__path__=[str(ROOT/'custom_components/cook4me')];sys.modules[NAME]=pkg

def module(name,**attrs):
    obj=types.ModuleType(NAME+'.'+name);vars(obj).update(attrs);sys.modules[obj.__name__]=obj;return obj

async def warm(_):return {'ingredients':[], '_runtimeNutritionIndex':{}}
async def cost(_,recipe,__):
    if recipe.get('badPrice'):raise ValueError('private provider payload must not leak')
    if recipe.get('cancel'):raise asyncio.CancelledError()
    return {'totalsByCurrency':{'EUR':2},'complete':True}

def nutrients(recipe,_):
    if recipe.get('badNutrition'):raise TypeError('invalid nutrient data')
    return {'totals':{'energyKcal':100}}

async def processor(*args,**kwargs):
    def process(rows):
        if any(row.get('badFilter') for row in rows):raise ValueError('cannot parse this record')
        return [row for row in rows if not row.get('filtered')]
    return process

module('automatic_prices',offline_recipe_price=cost)
module('release_catalog',async_warm_release_catalog=warm)
module('shared_recipe_runtime',processor=processor)
module('recipe_metrics_v60',calculate_recipe_nutrition_fast=nutrients)
seen=[]
def reservations(slots,_):seen[:] = deepcopy(slots);return []
module('meal_lifecycle',reservation_status=reservations,shopping_delta=lambda slots,inventory:[])
plan=importlib.import_module(NAME+'.weekly_plan')
class Hass:
    async def async_add_executor_job(self,fn,*args):return fn(*args)
bridge=types.SimpleNamespace(hass=Hass(),recipe_hub=types.SimpleNamespace(profile={'houseIngredients':[]}))
def slot(id='1',meal='lunch',**recipe):
    return {'id':id,'date':'2026-09-23','mealType':meal,'selected':True,'recipe':{'title':'Rice','language':'de','match':{'safe':True},**recipe}}
def state(*slots):return {'weekStart':'2026-09-23','slots':list(slots),'settings':{'mealTypes':['breakfast','lunch','dinner']}}

class GapTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_recipes_unchanged(self):
        result=await plan.refresh_plan(bridge,state(slot()))
        self.assertEqual(len(result['slots']),1);self.assertEqual(result['unavailableSlots'],[])
        self.assertEqual(result['weeklyCostByCurrency'],{'EUR':2});self.assertTrue(result['weeklyCostComplete'])
    async def test_missing_recipe_slot_is_not_lost(self):
        raw=slot();raw['recipe']=None
        result=await plan.refresh_plan(bridge,state(slot('2'),raw))
        self.assertEqual(len(result['slots']),1);self.assertEqual(result['unavailableSlots'][0]['id'],'1')
        self.assertEqual(result['unavailableSlots'][0]['reason'],'recipe_unavailable');self.assertEqual(result['filteredSlotCount'],0)
    async def test_non_object_recipe_keeps_its_position_metadata(self):
        raw=slot();raw['recipe']='unparseable'
        result=await plan.refresh_plan(bridge,state(raw))
        self.assertEqual(result['unavailableSlots'][0]['date'],'2026-09-23')
        self.assertEqual(result['unavailableSlots'][0]['reason'],'processing_error')
    async def test_bad_nutrition_does_not_abort_siblings(self):
        result=await plan.refresh_plan(bridge,state(slot('1',badNutrition=True),slot('2')))
        self.assertEqual([row['id'] for row in result['slots']],['2'])
        self.assertEqual(result['unavailableSlotCount'],1)
    async def test_bad_price_does_not_expose_private_error(self):
        result=await plan.refresh_plan(bridge,state(slot(badPrice=True)))
        self.assertNotIn('private',str(result));self.assertNotIn('badPrice',str(result['unavailableSlots']))
    async def test_filter_parse_failure_isolates_only_bad_row(self):
        result=await plan.refresh_plan(bridge,state(slot('1',badFilter=True),slot('2')),filters={'languages':['de']})
        self.assertEqual([row['id'] for row in result['slots']],['2'])
        self.assertEqual(result['unavailableSlots'][0]['reason'],'processing_error')
    async def test_filtered_is_distinct_from_parse_failure(self):
        result=await plan.refresh_plan(bridge,state(slot('1',filtered=True),slot('2')),filters={'languages':['de']})
        self.assertEqual(result['filteredSlotCount'],1);self.assertEqual(result['unavailableSlotCount'],0)
        self.assertEqual(result['unavailableSlots'][0]['reason'],'filtered')
        self.assertNotIn('title',result['unavailableSlots'][0])
    async def test_language_filter_is_still_enforced(self):
        result=await plan.refresh_plan(bridge,state(slot()),filters={'languages':['el']})
        self.assertEqual(result['slots'],[]);self.assertEqual(result['unavailableSlots'][0]['reason'],'filtered')
    async def test_unsafe_leftover_never_becomes_eligible(self):
        raw=slot(match={'safe':False});raw['leftoverId']='leftover'
        result=await plan.refresh_plan(bridge,state(raw),filters={'languages':['de']})
        self.assertEqual(result['slots'],[]);self.assertEqual(result['unavailableSlots'][0]['reason'],'filtered')
    async def test_gap_does_not_reserve_stock_or_count_as_free(self):
        result=await plan.refresh_plan(bridge,state(slot('1',badPrice=True),slot('2')))
        self.assertEqual([row['id'] for row in seen],['2']);self.assertEqual(result['selectedSlotCount'],1)
        self.assertFalse(result['weeklyCostComplete']);self.assertEqual(result['weeklyCostByCurrency'],{'EUR':2})
    async def test_expected_slots_respect_disabled_weekdays_and_filters(self):
        data=state(slot());data['settings']['weekdayMealTypes']={'wednesday':[]}
        result=await plan.refresh_plan(bridge,data,filters={'languages':['de'],'mealTypes':['main']})
        self.assertFalse(any(row['date']=='2026-09-23' for row in result['expectedMealSlots']))
        self.assertEqual({row['mealType'] for row in result['expectedMealSlots']},{'lunch','dinner'})
    async def test_empty_menu_has_known_empty_positions_not_fake_recipes(self):
        result=await plan.refresh_plan(bridge,state())
        self.assertEqual(result['slots'],[]);self.assertEqual(len(result['expectedMealSlots']),21)
        self.assertEqual(result['weeklyCostByCurrency'],{});self.assertFalse(result['weeklyCostComplete'])
    async def test_no_calendar_is_invented_without_valid_week_start(self):
        data=state();data['weekStart']='bad'
        result=await plan.refresh_plan(bridge,data);self.assertEqual(result['expectedMealSlots'],[])
    async def test_read_only_snapshot_does_not_change_stored_plan(self):
        saved=state(slot('1',badPrice=True),slot('2'));original=deepcopy(saved)
        await plan.refresh_plan(bridge,deepcopy(saved));self.assertEqual(saved,original)
    async def test_progress_reaches_last_slot_even_when_one_is_unavailable(self):
        events=[]
        await plan.refresh_plan(bridge,state(slot('1',badPrice=True),slot('2')),progress=lambda phase,**data:events.append(data))
        self.assertEqual(events[-1]['completed'],2)
    async def test_cancellation_propagates(self):
        with self.assertRaises(asyncio.CancelledError):await plan.refresh_plan(bridge,state(slot(cancel=True)))
    async def test_connection_errors_are_not_swallowed_as_parsing(self):
        old=sys.modules[NAME+'.automatic_prices'].offline_recipe_price
        async def broken(*args):raise ConnectionError('offline')
        sys.modules[NAME+'.automatic_prices'].offline_recipe_price=broken
        try:
            with self.assertRaises(ConnectionError):await plan.refresh_plan(bridge,state(slot()))
        finally:sys.modules[NAME+'.automatic_prices'].offline_recipe_price=old

if __name__=='__main__':unittest.main()
