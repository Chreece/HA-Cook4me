"""One physical product can serve multiple reviewed catalogue ingredient identities."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import AsyncMock

import test_runtime_audit_v74 as runtime
import test_product_packages_v112 as packages


class ProductLinksTests(packages.PackageTests):
    async def test_links_persist_once_and_unknown_catalogue_ids_are_rejected(self):
        ns=await self.api()
        _, ids=await self.create(ns,package_count=1,ingredient_links=[self.oats,self.rice,self.oats])
        house=self.bridge.recipe_hub.profile['houseIngredients']
        self.assertEqual(sum(row['quantity'] for row in house),500)
        self.assertEqual(len(house),1)
        links=house[0]['lots'][0]['ingredientLinks']
        self.assertEqual([row['key'] for row in links],['rice','oats'])
        self.assertEqual(self.mapping.async_set.await_args.args[1]['ingredientLinks'],links)
        restored=type(self.bridge.recipe_hub)(self.hass,'one');restored._store.saved=self.bridge.recipe_hub._store.saved
        await restored.async_load();self.bridge.recipe_hub=restored
        details=await self.details(ns,ids[0]);self.assertEqual(details['lot']['ingredientLinks'],links)
        ns['_catalog']=AsyncMock(return_value=[{'key':'rice','name':'Ρύζι'},{'key':'oats','name':'Βρώμη'}])
        localized=await self.details(ns,ids[0])
        self.assertEqual(localized['version'],details['version'])
        self.assertEqual(localized['lot']['ingredientLinks'][1]['name'],'Βρώμη')
        before=deepcopy(restored.profile['houseIngredients'])
        await ns['ws_product_add'](self.hass,self.connection,self.message(request_id='unknown-link-114-0001',ingredient_links=[{'key':'missing','name':'Not in catalogue'}]))
        self.assertEqual(self.errors[-1][0],'product_validation');self.assertEqual(restored.profile['houseIngredients'],before)

    async def test_shared_reservations_nutrition_prices_and_consumption(self):
        ns=await self.api();_,ids=await self.create(ns,package_count=1,ingredient_links=[self.oats])
        house=self.bridge.recipe_hub.profile['houseIngredients']
        recipe={'ingredients':[{'key':'rice','name':'Rice','quantity':300,'unit':'g'}, {'key':'oats','name':'Oats','quantity':300,'unit':'g'}]}
        lifecycle=importlib.import_module(runtime.PREFIX+'.meal_lifecycle')
        slots=[{'id':'slot','date':'2026-09-18','mealType':'lunch','recipe':recipe,'selected':True}]
        reservations=lifecycle.reservation_status(slots,house)
        self.assertEqual(sum(row['reserved'] for row in reservations['items']),500)
        self.assertEqual(reservations['shortages'][0]['shortage'],100)
        self.assertEqual(lifecycle.shopping_delta(slots,house)[0]['quantity'],100)
        food=importlib.import_module(runtime.PREFIX+'.food_intelligence')
        self.assertEqual(food.recipe_quantity_feasibility(recipe,house)['shortages'][0]['missingQuantity'],100)
        store=await self.nutrition.nutrition_store_for_bridge(self.bridge)
        fefo=importlib.import_module(runtime.PREFIX+'.nutrition_fefo')
        nutrition=fefo.calculate_recipe_nutrition_fefo(recipe,house,stock_lots=store.stock_lots)
        self.assertEqual(nutrition['totals']['protein'],40)
        self.assertEqual(nutrition['ingredients'][1]['sources'][0]['lotId'],ids[0])
        costs=await self.costs.cost_store_for_bridge(self.bridge)
        # Isolate exact package evidence from future purchase estimates.
        costs._data['references']={key:value for key,value in costs._data['references'].items() if value['identity'].startswith('lot:')}
        calculator=importlib.import_module(runtime.PREFIX+'.costing')
        price=calculator.calculate_recipe_cost(recipe,house,costs)
        self.assertEqual(price['totalsByCurrency']['EUR'],2.5)
        inventory=importlib.import_module(runtime.PREFIX+'.inventory')
        updated, report=inventory.apply_consumption(house,[{'key':'oats','name':'Oats','quantity':300,'unit':'g'}, {'key':'rice','name':'Rice','quantity':300,'unit':'g'}])
        self.assertEqual(updated,[])
        self.assertEqual(sum(row['quantity'] for row in report['deductedLots']),500)
        self.assertEqual({row['lotId'] for row in report['deductedLots']},{ids[0]})
        self.assertEqual(house[0]['quantity'],500,'Predictions and trial consumption do not mutate live stock')

    async def test_only_linked_packages_are_available_to_an_alias_and_edits_are_individual(self):
        ns=await self.api();_,ids=await self.create(ns,package_count=2,ingredient_links=[self.oats])
        detail=await self.details(ns,ids[0])
        await ns['ws_product_add'](self.hass,self.connection,self.message(request_id='unlink-package-114-001',edit_lot_id=ids[0],expected_version=detail['version'],package_count=1,ingredient_links=[]))
        inventory=importlib.import_module(runtime.PREFIX+'.inventory')
        house=self.bridge.recipe_hub.profile['houseIngredients']
        self.assertEqual(inventory.stock_for_ingredient(house,self.oats)['quantity'],500)
        self.assertEqual(inventory.stock_for_ingredient(house,self.rice)['quantity'],1000)
        updated,report=inventory.apply_consumption(house,[{'key':'oats','name':'Oats','quantity':800,'unit':'g'}])
        self.assertEqual(updated[0]['quantity'],500)
        self.assertEqual([lot['id'] for lot in updated[0]['lots']],[ids[0]])
        self.assertEqual([lot['lotId'] for lot in report['deductedLots']],[ids[1]])

    async def test_barcode_recalls_all_links_and_cache_detects_assignment_changes(self):
        ns=await self.api();_,ids=await self.create(ns,package_count=1,ingredient_links=[self.oats])
        saved=self.mapping.async_set.await_args.args[1];self.mapping.get=lambda code:saved
        await ns['ws_barcode_lookup'](self.hass,self.connection,{'id':3,'entry_id':'one','barcode':'12345678'})
        self.assertEqual([row['key'] for row in self.results[-1]['mapping']['ingredientLinks']],['rice','oats'])
        cache=importlib.import_module(runtime.PREFIX+'.recipe_cost_cache')
        house=self.bridge.recipe_hub.profile['houseIngredients'];costs=await self.costs.cost_store_for_bridge(self.bridge)
        recipe={'ingredients':[{'key':'oats','name':'Oats','quantity':100,'unit':'g'}]}
        before=cache.pricing_fingerprint(recipe,house,costs)
        changed=deepcopy(house);changed[0]['lots'][0]['ingredientLinks']=[self.rice]
        self.assertNotEqual(before,cache.pricing_fingerprint(recipe,changed,costs))


if __name__=='__main__':unittest.main()
