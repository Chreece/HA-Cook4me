"""Budget benchmarks fill eligible gaps without changing verified price evidence."""
from copy import deepcopy
from datetime import date, timedelta
import importlib
import json
import unittest
from unittest.mock import patch
import test_price_gaps_v87 as previous


class BudgetFallbackTests(unittest.IsolatedAsyncioTestCase):
    setUpClass=classmethod(previous.PriceGapTests.setUpClass.__func__)
    store=previous.PriceGapTests.store
    asyncTearDown=previous.PriceGapTests.asyncTearDown

    def setUp(self):
        previous.PriceGapTests.setUp(self)
        self.bench=importlib.import_module(self.prices.__package__+'.price_benchmarks')
        self.bench._pools.cache_clear();self.addCleanup(self.bench._pools.cache_clear)

    async def cost(self,name,quantity=100,unit='g',**extra):
        return await self.prices.offline_recipe_price(self.bridge,{'ingredients':[{'name':name,'quantity':quantity,'unit':unit,**extra}]},[])

    async def test_matched_ingredient_gets_traceable_budget_not_a_claimed_price(self):
        result=await self.cost('Green asparagus',70)
        self.assertFalse(result['complete']);self.assertEqual(result['totalsByCurrency'],{})
        self.assertTrue(result['budgetComplete']);self.assertGreater(result['budgetTotalsByCurrency']['EUR'],0)
        row=result['ingredients'][0];self.assertEqual(row['coverage'],0);self.assertEqual(row['budgetCoverage'],1)
        estimate=row['fallbackEstimate'];self.assertEqual(estimate['confidence'],'low');self.assertEqual(estimate['level'],'food_group')
        self.assertEqual(estimate['group'],'vegetables');self.assertTrue(estimate['sourceIds']);self.assertLessEqual(len(estimate['sources']),4)
        self.assertLessEqual(estimate['low'],estimate['amount']);self.assertGreaterEqual(estimate['high'],estimate['amount'])
        self.assertEqual((estimate['country'],estimate['currency']),('DE','EUR'))
        self.assertTrue(all(x['sourceUrl'].startswith('https://') for x in estimate['sources']))
        self.assertFalse((await self.store()).snapshot()['references'],'Preview benchmarks never pollute saved reference prices')

    async def test_exact_price_and_manual_price_take_priority(self):
        for name in ['Onion','Whole-grain pasta','Poultry fillet']:
            result=await self.cost(name)
            self.assertTrue(result['complete']);self.assertNotIn('fallbackIngredientCount',result)
        store=await self.store();identity=self.prices.inventory_identity({'name':'Green asparagus'})
        await store.async_set_reference(identity,amount=2,currency='EUR',basis_quantity=100,basis_unit='g',country='DE',source='manual')
        result=await self.cost('Green asparagus',100)
        self.assertEqual(result['totalsByCurrency'],{'EUR':2});self.assertNotIn('fallbackIngredientCount',result)

    async def test_unknown_food_nonfood_missing_amount_and_unusable_unit_stay_unknown(self):
        for name,quantity,unit in [('Alien mystery food',100,'g'),('Salt',None,''),('Poultry',6,''),('Saffron',1,''),('Bean',3,'pack')]:
            result=await self.cost(name,quantity,unit,priceCatalogMatched=True,priceCategory='en:onions')
            self.assertNotIn('fallbackIngredientCount',result,(name,unit))
        for classification in ['other','equipment']:
            result=await self.prices.offline_recipe_price(self.bridge,{'ingredients':[{'key':'not-food','quantity':100,'unit':'g'}]},[{'key':'not-food','canonicalName':'Rice','classification':classification}])
            self.assertFalse(result['ingredients'][0].get('fallbackEstimate'))
        with patch.object(self.bench,'_load',return_value={'observations':[]}):
            self.bench._pools.cache_clear();self.assertNotIn('fallbackIngredientCount',await self.cost('Green asparagus'))

    async def test_catalog_match_without_a_price_taxonomy_uses_basket(self):
        recipe={'ingredients':[{'ingredientId':'local:test:food','quantity':100,'unit':'g'}]}
        catalog=[{'id':'local:test:food','canonicalName':'Reviewed rare food','classification':'food'}]
        result=await self.prices.offline_recipe_price(self.bridge,recipe,catalog)
        self.assertTrue(result['budgetComplete']);self.assertEqual(result['ingredients'][0]['fallbackEstimate']['level'],'food_basket')
        self.assertEqual(recipe['ingredients'][0],{'ingredientId':'local:test:food','quantity':100,'unit':'g'})

    async def test_count_conversion_prefers_sourced_grams_over_a_whole_vegetable_price(self):
        result=await self.cost('Radish',4,'')
        estimate=result['ingredients'][0]['fallbackEstimate']
        self.assertEqual(estimate['unit'],'g');self.assertTrue(estimate['quantityEstimate']);self.assertLess(estimate['quantity'],100)

    async def test_duplicate_rows_keep_their_own_amount_and_auto_off_invalidates_cache(self):
        recipe={'ingredients':[{'name':'Green asparagus','quantity':100,'unit':'g'},{'name':'Green asparagus','quantity':250,'unit':'g'}]}
        result=await self.prices.offline_recipe_price(self.bridge,recipe,[])
        amounts=[r['fallbackEstimate']['amount'] for r in result['ingredients']]
        self.assertAlmostEqual(amounts[1],2.5*amounts[0],places=3)
        repeated=await self.prices.offline_recipe_price(self.bridge,recipe,[])
        self.assertTrue(repeated['costCacheHit']);self.assertEqual(repeated['budgetTotalsByCurrency'],result['budgetTotalsByCurrency'])
        await (await self.store()).async_set_settings(auto_global_prices=False)
        disabled=await self.prices.offline_recipe_price(self.bridge,recipe,[])
        self.assertFalse(disabled['costCacheHit']);self.assertNotIn('fallbackIngredientCount',disabled)

    async def test_partial_purchase_prices_only_the_uncovered_remainder(self):
        await self.bridge.recipe_hub.async_inventory_add({'name':'Green asparagus'},quantity=100,unit='g')
        lot=self.bridge.recipe_hub.profile['houseIngredients'][0]['lots'][0]
        store=await self.store()
        await store.async_set_reference('lot:'+lot['id'],amount=2,currency='EUR',basis_quantity=100,basis_unit='g',country='DE',source='purchase',confidence='exact_purchase')
        result=await self.cost('Green asparagus',200)
        row=result['ingredients'][0];self.assertEqual(row['coverage'],.5);self.assertEqual(result['totalsByCurrency'],{'EUR':2})
        self.assertEqual(row['fallbackEstimate']['quantity'],100)
        self.assertAlmostEqual(result['budgetTotalsByCurrency']['EUR'],round(2+row['fallbackEstimate']['amount'],2))

    async def test_dried_tomato_pieces_use_the_sourced_edible_mass(self):
        result=await self.prices.offline_recipe_price(self.bridge,{'ingredients':[{'key':'dry-tomato','quantity':4,'unit':'pcs'}]},[{'key':'dry-tomato','canonicalName':'Sun-dried tomatoes (optional)','classification':'food'}])
        estimate=result['ingredients'][0]['fallbackEstimate']
        self.assertEqual((estimate['quantity'],estimate['unit']),(8,'g'))
        self.assertEqual(estimate['quantityEstimate']['portionId'],83340)
        self.assertFalse(result['complete']);self.assertTrue(result['budgetComplete'])

    async def test_live_cost_path_also_returns_the_budget(self):
        with patch.object(self.prices,'lookup_open_prices',return_value={'ok':True,'items':[],'usableCount':0}):
            result=await self.prices.recipe_price(self.bridge,{'ingredients':[{'name':'Green asparagus','quantity':70,'unit':'g'}]},[])
        self.assertTrue(result['budgetComplete']);self.assertFalse(result['complete'])

    def test_only_local_fresh_positive_prices_enter_benchmark(self):
        today=date.today().isoformat()
        base={'id':1,'source':'open_prices','categories':['en:onions'],'usable':True,'country':'DE','currency':'EUR','date':today,'amount':2,'basisQuantity':1000,'basisUnit':'g','barcode':'one'}
        rows=[base,{**base,'id':2,'barcode':'two','amount':4},
              {**base,'id':3,'barcode':'foreign','country':'FR','amount':100},
              {**base,'id':4,'barcode':'expired','date':(date.today()-timedelta(days=181)).isoformat(),'amount':100},
              {**base,'id':5,'barcode':'negative','amount':-5},
              {**base,'id':6,'barcode':'one','date':(date.today()-timedelta(days=1)).isoformat(),'amount':100},
              {**base,'id':7,'barcode':'water','source':'utility_snapshot','amount':.001}]
        with patch.object(self.bench,'_load',return_value={'observations':rows}):
            self.bench._pools.cache_clear()
            estimate=self.bench.fallback_estimate({'name':'Radish','quantity':100,'unit':'g','priceCatalogMatched':True},country='DE',currency='EUR')
            self.assertEqual(estimate['sampleCount'],2);self.assertEqual(estimate['amount'],.3)
            self.assertEqual(estimate['sourceIds'],[1,2]);self.assertEqual((estimate['low'],estimate['high']),(.2,.4))
            self.assertIsNone(self.bench.fallback_estimate({'name':'Radish','quantity':100,'unit':'g','priceCatalogMatched':True},country='DE',currency='USD'))

if __name__=='__main__':unittest.main()
