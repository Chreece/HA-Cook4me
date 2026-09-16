"""Screenshot food forms, persistent preview caching, and truthful coverage."""
from copy import deepcopy
import importlib
import unittest
from unittest.mock import patch
import test_price_gaps_v89 as previous

class PriceGapTests(previous.ScreenshotPriceTests):
    async def test_latest_screenshot(self):
        expected={'331197':(4,7),'317075':(6,7),'487446':(6,7),'357993':(4,10),
                  '734674':(7,8),'341615':(7,9),'834652':(6,8),'287823':(6,7)}
        seen=set()
        for family in self.catalog['recipes']:
            selected=next((str(v['variantId']) for v in family['variants'] if str(v['variantId']) in expected),None)
            if selected is None: continue
            for variant in family['variants']:
                original=deepcopy(variant)
                result=await self.prices.offline_recipe_price(self.bridge,variant,self.catalog['ingredients'])
                self.assertEqual((sum(r['coverage']==1 for r in result['ingredients']),len(result['ingredients'])),expected[selected],variant['variantId'])
                self.assertEqual(variant,original)
                self.assertFalse(result['waterOnlyEstimate'])
            seen.add(selected)
        self.assertEqual(seen,set(expected))

    async def test_new_price_facts_and_food_forms(self):
        for name,amount,unit,total in [('Raisin',500,'g',2.95),('Whole-grain pasta',500,'g',.85),
                ('Cooked flageolet beans',530,'g',4.12),('Raw beetroot',1000,'g',3.79),
                ('Jerusalem artichoke',100,'g',.69),('Parsnip',500,'g',1.99),('Poultry fillet',600,'g',6.79)]:
            result=await self.cost(name,amount,unit)
            self.assertTrue(result['complete'],name);self.assertAlmostEqual(result['totalsByCurrency']['EUR'],total)
        for name in ['Bean','Flageolet beans','Poultry','Onion soup','Pickled onion','Carrot juice']:
            self.assertFalse((await self.cost(name,100,'g'))['complete'],name)
        raw=(await self.cost('Raw red beetroot, peeled and cut into long strips',2))['ingredients'][0]
        self.assertEqual(raw['quantityEstimate']['quantity'],164)
        self.assertEqual(raw['references'][0]['basisQuantity'],1000)
        parsnip=(await self.cost('Parsnip, peeled and sliced into rounds',3))['ingredients'][0]
        self.assertEqual(parsnip['quantityEstimate']['quantity'],240)
        self.assertIn('alnatura.de',parsnip['quantityEstimate']['sourceUrl'])

    async def test_embedded_spoon_units_do_not_invent_amounts(self):
        self.assertTrue((await self.cost('Tablespoon of olive oil',1))['complete'])
        self.assertFalse((await self.cost('Tablespoon of olive oil'))['complete'])
        result=await self.cost('Tablespoon of olive oil',30,'ml')
        control=await self.cost('Olive oil',30,'ml')
        self.assertEqual(result['totalsByCurrency'],control['totalsByCurrency'])

    async def test_water_only_is_not_food_coverage(self):
        recipe={'ingredients':[{'name':'Water','quantity':100,'unit':'ml'},{'name':'Unknown food','quantity':1}]}
        for method in [self.prices.offline_recipe_price,self.prices.recipe_price]:
            result=await method(self.bridge,recipe,[])
            self.assertTrue(result['waterOnlyEstimate']);self.assertEqual(result['pricedFoodIngredientCount'],0)
            self.assertEqual(result['foodIngredientCount'],1)

    async def test_seasoning_is_excluded_from_generic_chicken_not_barcode(self):
        row=next(r for r in self.evidence['observations'] if str(r['id'])=='307878')
        self.assertFalse(self.snapshot.category_observation_allowed(row,'en:chickens'))
        self.assertFalse(any(str(r['id'])=='307878' for r in self.snapshot.snapshot_observations(category='en:chickens',country='DE',currency='EUR',unit='g')))
        self.assertTrue(self.snapshot.snapshot_observations(barcode=row['barcode'],country='DE',currency='EUR',unit='g'))
        with patch.object(self.prices,'lookup_open_prices',return_value={'ok':True,'items':[row],'usableCount':1}):
            result=await self.prices._observations(self.bridge,category='en:chickens',unit='g',settings={'country':'DE','currency':'EUR'},refresh_since=1)
        self.assertEqual(result['items'],[])

    async def test_offline_cache_survives_new_instance_and_invalidates_relevant_changes(self):
        cachemod=importlib.import_module(self.prices.__package__+'.recipe_cost_cache')
        recipe={'ingredients':[{'name':'Whole-grain pasta','quantity':250,'unit':'g'}]}
        first=await self.prices.offline_recipe_price(self.bridge,recipe,[])
        cache=await cachemod.recipe_cost_cache_for_bridge(self.bridge)
        saved=deepcopy(cache._store.saved)
        fresh=cachemod.Cook4MeRecipeCostCache(self.bridge);fresh._store.saved=saved
        await fresh.async_load()
        self.bridge._recipe_cost_cache_v1=fresh
        with patch.object(cachemod,'calculate_recipe_cost',side_effect=AssertionError('cached preview recalculated')):
            second=await self.prices.offline_recipe_price(self.bridge,recipe,[])
        self.assertFalse(first['costCacheHit']);self.assertTrue(second['costCacheHit'])
        self.assertEqual(first['totalsByCurrency'],second['totalsByCurrency'])
        changed=deepcopy(recipe);changed['ingredients'][0]['quantity']=500
        self.assertFalse((await self.prices.offline_recipe_price(self.bridge,changed,[]))['costCacheHit'])
        token=await cachemod.preview_cache_token(self.bridge)
        store=await self.store()
        await store.async_set_reference(self.prices.inventory_identity(recipe['ingredients'][0]),amount=2,currency='EUR',basis_quantity=500,basis_unit='g',country='DE',source='manual')
        self.assertNotEqual(token,await cachemod.preview_cache_token(self.bridge))
        repriced=await self.prices.offline_recipe_price(self.bridge,recipe,[])
        self.assertFalse(repriced['costCacheHit']);self.assertEqual(repriced['totalsByCurrency'],{'EUR':1.0})
        token=await cachemod.preview_cache_token(self.bridge)
        await self.bridge.recipe_hub.async_inventory_add({'name':'Whole-grain pasta'},quantity=100,unit='g')
        self.assertNotEqual(token,await cachemod.preview_cache_token(self.bridge))
        token=await cachemod.preview_cache_token(self.bridge)
        await store.async_set_settings(country='FR',currency='EUR')
        self.assertNotEqual(token,await cachemod.preview_cache_token(self.bridge))
        self.assertFalse((await self.prices.offline_recipe_price(self.bridge,recipe,[]))['complete'])

if __name__=='__main__':unittest.main()
