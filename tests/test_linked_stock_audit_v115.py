"""Regression cases found while auditing linked physical stock and exact labels."""
from copy import deepcopy
import asyncio
import importlib
import itertools
import unittest
from unittest.mock import AsyncMock
import test_product_packages_v112 as packages
import test_runtime_audit_v74 as runtime


class LinkedStockAuditTests(unittest.IsolatedAsyncioTestCase):
    setUp=packages.PackageTests.setUp
    asyncTearDown=packages.PackageTests.asyncTearDown
    api=packages.PackageTests.api
    message=packages.PackageTests.message
    create=packages.PackageTests.create
    details=packages.PackageTests.details

    def module(self,name):return importlib.import_module(runtime.PREFIX+'.'+name)
    def lot(self,key,quantity,unit='g',links=None,lot_id='shared',date='2027-01-01'):
        return {'key':key,'name':key,'quantity':quantity,'unit':unit,'lots':[{'id':lot_id,'quantity':quantity,'bestBefore':date,'ingredientLinks':links or []}]}
    def requests(self):return [{'key':'rice','name':'Rice','quantity':300,'unit':'g'},{'key':'oats','name':'Oats','quantity':300,'unit':'g'}]
    def slots(self,recipe):return [{'id':'slot','date':'2026-09-18','mealType':'lunch','recipe':recipe,'selected':True}]

    def test_shared_stock_is_reassigned_instead_of_creating_false_shopping_shortages(self):
        stock=[self.lot('rice',500,links=[self.oats]),self.lot('rice',500,lot_id='rice-only',date='2028-01-01')]
        recipe={'ingredients':self.requests()}
        result=self.module('meal_lifecycle').reservation_status(self.slots(recipe),stock)
        self.assertEqual(result['shortages'],[])
        food=self.module('food_intelligence').recipe_quantity_feasibility(recipe,stock)
        self.assertEqual(food['shortages'],[])
        updated,report=self.module('inventory').apply_consumption(stock,self.requests())
        self.assertEqual(sum(row['quantity'] for row in report['deductedLots']),600)
        self.assertEqual(sum(row['quantity'] for row in updated),400)

    def test_mixed_dimensions_consume_the_compatible_linked_package(self):
        stock=[self.lot('rice',500,'g',links=[self.oats],lot_id='mass'),self.lot('milk',600,'ml',links=[self.oats],lot_id='volume')]
        updated,report=self.module('inventory').apply_consumption(stock,[{**self.oats,'quantity':250,'unit':'ml'}])
        self.assertEqual([(lot['lotId'],lot['quantity']) for lot in report['deductedLots']],[('volume',250)])
        self.assertEqual(next(row for row in updated if row['key']=='rice')['quantity'],500)

    def test_expiry_priority_does_not_count_one_product_once_per_link(self):
        from datetime import date
        stock=[self.lot('rice',500,links=[self.oats],date='2026-09-19')]
        inventory=self.module('inventory')
        once=inventory.recipe_expiry_priority({'ingredients':[self.requests()[0]]},stock,today=date(2026,9,18))
        twice=inventory.recipe_expiry_priority({'ingredients':self.requests()},stock,today=date(2026,9,18))
        self.assertEqual(twice['priority'],once['priority'])

    def test_partial_exact_label_cannot_be_reused_for_a_second_ingredient(self):
        stock=[self.lot('rice',500,links=[self.oats])]
        exact={'k:rice':[{'inventoryLotId':'shared','quantity':100,'unit':'g','nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':10}}}]}
        result=self.module('nutrition_fefo').calculate_recipe_nutrition_fefo({'ingredients':self.requests()},stock,stock_lots=exact)
        self.assertEqual(result['totals']['protein'],10)

    async def test_deleted_lot_nutrition_cannot_attach_to_a_sibling_with_the_same_expiry(self):
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        store._data['stockLots']={'k:rice':[{'inventoryLotId':'deleted','quantity':100,'unit':'g','bestBefore':'2027-01-01','nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':10}}}]}
        await self.module('nutrition_inventory').async_reconcile_nutrition_inventory(store,[self.lot('rice',500,lot_id='remaining')])
        self.assertEqual(store.stock_lots,{})

    async def test_failed_barcode_mapping_save_does_not_publish_in_memory_changes(self):
        store=self.module('barcode').Cook4MeBarcodeMappingStore(self.hass,'one')
        store._store.async_save=AsyncMock(side_effect=OSError('disk full'))
        with self.assertRaises(OSError):await store.async_set('12345678',{'ingredient':self.rice,'ingredientLinks':[self.rice,self.oats]})
        self.assertIsNone(store.get('12345678'))

    async def test_concurrent_barcode_saves_keep_both_durable_mappings(self):
        store=self.module('barcode').Cook4MeBarcodeMappingStore(self.hass,'one')
        saved={}
        async def persist(data):
            nonlocal saved
            if len(data)==1:await asyncio.sleep(.01)
            saved=deepcopy(data)
        store._store.async_save=persist
        await asyncio.gather(store.async_set('12345678',{'ingredient':self.rice}),store.async_set('87654321',{'ingredient':self.oats}))
        self.assertEqual(set(saved),{'12345678','87654321'})
        self.assertEqual(set(store._data),set(saved))

    async def test_confirmed_consumption_cannot_borrow_a_sibling_label(self):
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        original={'inventoryLotId':'sibling','quantity':500,'unit':'g','bestBefore':'2027-01-01','nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':10}}}
        store._data['stockLots']={'k:rice':[deepcopy(original)]}
        result=await self.module('nutrition_inventory').async_consume_nutrition_report(store,{'deductedLots':[{'identity':'k:rice','lotId':'other','quantity':100,'unit':'g','bestBefore':'2027-01-01'}]})
        self.assertEqual(result['totals'],{})
        self.assertEqual(store.stock_lots['k:rice'],[original])

    async def test_nutrition_reconciliation_reserves_capacity_for_exact_ids_before_legacy_labels(self):
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        record={'quantity':500,'unit':'g','bestBefore':'2027-01-01','nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':10}}}
        store._data['stockLots']={'k:rice':[deepcopy(record),{**record,'inventoryLotId':'shared'}]}
        await self.module('nutrition_inventory').async_reconcile_nutrition_inventory(store,[self.lot('rice',500)])
        self.assertEqual(sum(row['quantity'] for row in store.stock_lots['k:rice']),500)
        self.assertEqual(store.stock_lots['k:rice'][0]['inventoryLotId'],'shared')

    async def test_failed_nutrition_write_preserves_previous_label_amounts(self):
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        store._data['stockLots']={'k:rice':[{'inventoryLotId':'shared','quantity':500,'unit':'g','nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':10}}}]}
        before=deepcopy(store._data);store._store.async_save=AsyncMock(side_effect=OSError('disk full'))
        with self.assertRaises(OSError):await self.module('nutrition_inventory').async_reconcile_nutrition_inventory(store,[self.lot('rice',200)])
        self.assertEqual(store._data,before)

    async def test_concurrent_nutrition_consumption_deducts_both_reports(self):
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        store._data['stockLots']={'k:rice':[{'inventoryLotId':'shared','quantity':500,'unit':'g','nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':10}}}]}
        entered,release=asyncio.Event(),asyncio.Event()
        saved={}
        async def persist(data):
            nonlocal saved
            if not entered.is_set():
                entered.set()
                await release.wait()
            saved=deepcopy(data)
        store._store.async_save=persist
        consume=self.module('nutrition_inventory').async_consume_nutrition_report
        report={'deductedLots':[{'identity':'k:rice','lotId':'shared','quantity':100,'unit':'g'}]}
        first=asyncio.create_task(consume(store,report))
        await asyncio.wait_for(entered.wait(),1)
        second=asyncio.create_task(consume(store,report))
        await asyncio.sleep(0)
        release.set()
        results=await asyncio.wait_for(asyncio.gather(first,second),1)
        self.assertEqual([result['totals']['protein'] for result in results],[10,10])
        self.assertEqual(store.stock_lots['k:rice'][0]['quantity'],300)
        self.assertEqual(saved,store._data)

    async def test_failed_nutrition_consumption_can_retry_without_double_deduction(self):
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        store._data['stockLots']={'k:rice':[{'inventoryLotId':'shared','quantity':500,'unit':'g','nutrition':{'basisQuantity':100,'basisUnit':'g','values':{'protein':10}}}]}
        store._store.async_save=AsyncMock(side_effect=[OSError('disk full'),None])
        consume=self.module('nutrition_inventory').async_consume_nutrition_report
        report={'deductedLots':[{'identity':'k:rice','lotId':'shared','quantity':100,'unit':'g'}]}
        with self.assertRaises(OSError):await consume(store,report)
        self.assertEqual(store.stock_lots['k:rice'][0]['quantity'],500)
        result=await asyncio.wait_for(consume(store,report),1)
        self.assertEqual(result['totals']['protein'],10)
        self.assertEqual(store.stock_lots['k:rice'][0]['quantity'],400)

    async def test_nutrition_reconciliation_does_not_overwrite_concurrent_reference_save(self):
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        profile={'basisQuantity':100,'basisUnit':'g','values':{'protein':10}}
        store._data['stockLots']={'k:rice':[{'inventoryLotId':'shared','quantity':500,'unit':'g','nutrition':profile}]}
        entered,release=asyncio.Event(),asyncio.Event()
        saved={}
        async def persist(data):
            nonlocal saved
            if not entered.is_set():
                entered.set()
                await release.wait()
            saved=deepcopy(data)
        store._store.async_save=persist
        first=asyncio.create_task(self.module('nutrition_inventory').async_reconcile_nutrition_inventory(store,[self.lot('rice',200)]))
        await asyncio.wait_for(entered.wait(),1)
        second=asyncio.create_task(store.async_set_generic('k:oats',self.oats,profile))
        await asyncio.sleep(0)
        release.set()
        await asyncio.wait_for(asyncio.gather(first,second),1)
        self.assertIsNotNone(store.get_generic('k:oats'))
        self.assertEqual(store.stock_lots['k:rice'][0]['quantity'],200)
        self.assertEqual(saved,store._data)

    def test_allocation_can_reassign_through_multiple_links_and_matches_small_exhaustive_cases(self):
        allocator=self.module('stock_allocation')
        for choices in itertools.product(((0,),(1,),(0,1)),repeat=3):
            stock=[self.lot('product-'+str(i),1,links=[{'key':'food-'+str(key),'name':str(key)} for key in allowed],lot_id='lot-'+str(i)) for i,allowed in enumerate(choices)]
            demands=[{'key':'food-0','name':'A','quantity':1,'unit':'g'},{'key':'food-1','name':'B','quantity':2,'unit':'g'}]
            expected=max(sum(counts) for assignment in itertools.product(*[(-1,*allowed) for allowed in choices]) if (counts:=[assignment.count(0),assignment.count(1)])[0]<=1 and counts[1]<=2)
            result=allocator.allocate_stock(stock,demands)
            self.assertEqual(sum((row or {}).get('quantity',0) for row in result),expected,choices)
            totals={}
            for row in result:
                for lot in (row or {}).get('lots',[]):totals[lot['id']]=totals.get(lot['id'],0)+lot['quantity']
            self.assertTrue(all(value<=1 for value in totals.values()))
        stock=[self.lot('rice',100,links=[self.oats],lot_id='a'),self.lot('oats',100,links=[{'key':'milk','name':'Milk'}],lot_id='b'),self.lot('rice',100,lot_id='c',date='2028-01-01')]
        needs=[{'key':key,'name':key,'quantity':100,'unit':'g'} for key in ('rice','oats','milk')]
        self.assertEqual([row['quantity'] for row in allocator.allocate_stock(stock,needs)],[100,100,100])

    async def test_recipe_prices_and_nutrition_follow_the_same_reassigned_physical_lots(self):
        ns=await self.api();await self.create(ns,package_count=1,ingredient_links=[self.oats])
        await self.create(ns,request_id='dedicated-package-115-001',package_count=1,
                          best_before='2028-01-01',paid_price={'amount':5,'currency':'EUR'},
                          nutrition={'basisQuantity':100,'basisUnit':'g','values':{'protein':20}})
        # Give the shared product the earlier expiry, so naive FEFO would spend it on rice.
        house=self.bridge.recipe_hub.profile['houseIngredients']
        shared=next(lot for lot in house[0]['lots'] if not lot.get('bestBefore'))
        shared['bestBefore']='2027-01-01'
        recipe={'ingredients':self.requests()}
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        result=self.module('nutrition_fefo').calculate_recipe_nutrition_fefo(recipe,house,stock_lots=store.stock_lots)
        self.assertEqual(result['totals']['protein'],60)
        prices=await self.costs.cost_store_for_bridge(self.bridge)
        result=self.module('costing').calculate_recipe_cost(recipe,house,prices)
        self.assertEqual(result['totalsByCurrency']['EUR'],3.5)
        self.assertEqual(result['exactPurchaseCoverage'],1)

    def test_allocation_converts_mass_units_and_preserves_explicit_package_choice(self):
        stock=[self.lot('rice',.5,'kg',links=[self.oats]),self.lot('rice',500,'g',lot_id='rice-only',date='2028-01-01')]
        result=self.module('stock_allocation').allocate_stock(stock,[{'key':'rice','name':'Rice','quantity':300,'unit':'g','lotId':'rice-only'},{'key':'oats','name':'Oats','quantity':.3,'unit':'kg'}])
        self.assertEqual([row['quantity'] for row in result],[300,.3])
        self.assertEqual([row['lots'][0]['id'] for row in result],['rice-only','shared'])

if __name__=='__main__':unittest.main()
