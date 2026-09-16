"""Catalog coverage and bounded, unit-aware observed price retrieval."""
import asyncio
from copy import deepcopy
import importlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import test_automatic_prices_v79 as previous
import test_runtime_audit_v74 as runtime


class PriceCoverageTests(unittest.IsolatedAsyncioTestCase):
    setUp = previous.AutomaticPriceTests.setUp
    asyncTearDown = previous.AutomaticPriceTests.asyncTearDown
    store = previous.AutomaticPriceTests.store
    observed = previous.AutomaticPriceTests.observed
    raw = previous.AutomaticPriceTests.raw

    def response(self, items, pages=1):
        return io.BytesIO(json.dumps({'items': items, 'pages': pages}).encode())

    def test_country_match_beyond_first_worldwide_page(self):
        with patch.object(self.costs.urllib.request, 'urlopen', side_effect=[
            self.response([self.raw(location={'osm_address_country_code': 'FR'})], 2),
            self.response([self.raw()])]) as get, patch.object(self.costs, 'country_locations', return_value=[]):
            result = self.costs.lookup_open_prices('12345678', country='DE', currency='EUR', unit='g')
        self.assertEqual(result['usableCount'], 1)
        self.assertEqual(result['pagesChecked'], 2)
        self.assertEqual(parse_qs(urlparse(get.call_args.args[0].full_url).query)['page'], ['2'])

    def test_incompatible_page_does_not_hide_compatible_measurement(self):
        with patch.object(self.costs.urllib.request, 'urlopen', side_effect=[
            self.response([self.raw(product={'product_quantity': 1, 'product_quantity_unit': 'pcs'})], 2),
            self.response([self.raw()])]):
            result = self.costs.lookup_open_prices('12345678', country='DE', currency='EUR', unit='g')
        self.assertEqual(result['pagesChecked'], 2)
        self.assertEqual(result['items'][-1]['basisUnit'], 'g')

    def test_pagination_is_bounded_and_distinguishes_incomplete_search(self):
        with patch.object(self.costs.urllib.request, 'urlopen', side_effect=lambda *a,**k:
                         self.response([self.raw(location={'osm_address_country_code':'FR'})], 99)) as get:
            result = self.costs.lookup_open_prices('12345678', country='DE', currency='EUR')
        self.assertEqual(get.call_count, 5)
        self.assertTrue(result['searchLimited'])
        self.assertEqual(result['items'], [])

    def test_later_failure_preserves_evidence_and_reports_failure(self):
        with patch.object(self.costs.urllib.request, 'urlopen', side_effect=[
            self.response([self.raw(product={'product_quantity':1,'product_quantity_unit':'pcs'})], 2), OSError('offline')]):
            result = self.costs.lookup_open_prices('12345678', country='DE', currency='EUR', unit='g')
        self.assertFalse(result['ok']); self.assertTrue(result['searchLimited']); self.assertEqual(len(result['items']),1)

    async def test_packaged_produce_fallback_prices_real_catalog_carrot(self):
        ingredient={'key':'M_FOOD_79','name':'Carrot','canonicalName':'Carrot'}
        with patch.object(self.prices, 'lookup_open_prices', side_effect=lambda *a,**k:
                         {'ok':True,'items':[self.observed()] if k['category_type']=='PRODUCT' else []}) as lookup:
            result=await self.prices.recipe_price(self.bridge,{'ingredients':[{**ingredient,'quantity':200,'unit':'g'}]},[ingredient])
        self.assertTrue(result['complete']); self.assertEqual(result['totalsByCurrency'],{'EUR':1.2})
        self.assertEqual([c.kwargs['category_type'] for c in lookup.call_args_list],['CATEGORY','PRODUCT'])

    async def test_localized_recipe_units_resolve_without_mutating_recipe(self):
        recipe={'ingredients':[{'key':'rice','name':'Rice','quantity':200,'unit':'г','unitKey':'UNIT_27'}]}
        before=deepcopy(recipe)
        with patch.object(self.prices,'lookup_open_prices',return_value={'ok':True,'items':[self.observed()]}):
            result=await self.prices.recipe_price(self.bridge,recipe,[self.ingredient])
        self.assertTrue(result['complete']);self.assertEqual(result['totalsByCurrency'],{'EUR':1.2});self.assertEqual(recipe,before)

    async def test_incompatible_fresh_reference_does_not_block_mass_price(self):
        store=await self.store()
        await self.prices._store_observation(store,'k:rice',self.observed(basisQuantity=1,basisUnit='pcs'),generic=True)
        with patch.object(self.prices,'lookup_open_prices',return_value={'ok':True,'items':[self.observed()]}):
            result=await self.prices.recipe_price(self.bridge,self.recipe,[self.ingredient])
        self.assertTrue(result['complete'])
        self.assertEqual(store.best_reference('k:rice',unit='pcs')['basisUnit'],'pcs')
        self.assertEqual(store.best_reference('k:rice',unit='g')['basisUnit'],'g')

    async def test_unknown_recipe_amounts_do_not_use_lookup_budget(self):
        recipe={'ingredients':[{'key':'x'+str(i),'name':'Salt'} for i in range(30)]+self.recipe['ingredients']}
        with patch.object(self.prices,'lookup_open_prices',return_value={'ok':True,'items':[self.observed()]}) as lookup:
            result=await self.prices.recipe_price(self.bridge,recipe,[self.ingredient])
        self.assertEqual(lookup.call_count,1);self.assertFalse(result['ingredientLimitReached'])
        self.assertEqual(result['totalsByCurrency'],{'EUR':1.2});self.assertFalse(result['complete'])

    async def test_misses_coalesce_for_equivalent_units(self):
        with patch.object(self.prices,'lookup_open_prices',return_value={'ok':True,'items':[]}) as lookup:
            await asyncio.gather(*(self.prices.product_price(self.bridge,ingredient=self.ingredient,quantity=1,unit=unit) for unit in ['g','kg']))
        self.assertEqual(lookup.call_count,2) # One packaged and one loose lookup.

    def test_reviewed_mapping_covers_frequent_foods_without_guessing_mixtures(self):
        for name in ['Salted Butter & Unsalted butter','White Potatoes','Ginger','Chicken breast','Salmon','Crème fraîche','Spring onion','Icing sugar']:
            self.assertIsNotNone(self.prices.category_for({'canonicalName':name}),name)
        for name in ['Butter and olive oil','Salt and pepper','Pepper','Cooked rice','Rice pudding']:
            self.assertIsNone(self.prices.category_for({'canonicalName':name}),name)
        units=importlib.import_module(runtime.PREFIX+'.price_units')
        for unit in ['pinch','cup','tbsp','clove']:
            self.assertEqual(units.price_ingredient({'quantity':1,'unit':unit})['unit'],unit)

    async def test_unknown_measurements_do_not_spend_external_lookup_budget(self):
        with patch.object(self.prices,'lookup_open_prices') as lookup:
            result=await self.prices.product_price(self.bridge,ingredient=self.ingredient,quantity=1,unit='pinch')
        lookup.assert_not_called();self.assertEqual(result['status'],'basis_missing')

    async def test_partial_response_keeps_hydration_alive_and_next_call_reuses_it(self):
        gate=asyncio.Event()
        async def observations(*args,**kwargs):
            await gate.wait()
            return {'ok':True,'items':[self.observed()]}
        with patch.object(self.prices,'_observations',side_effect=observations) as lookup, patch.object(self.prices,'_RECIPE_WAIT_SECONDS',.01):
            first=await self.prices.recipe_price(self.bridge,self.recipe,[self.ingredient])
            self.assertTrue(first['priceLookupPending']);self.assertFalse(first['priceLookupIncomplete'])
            self.assertEqual(first['ingredients'][0]['priceStatus'],'lookup_pending')
            second=await self.prices.recipe_price(self.bridge,self.recipe,[self.ingredient])
            self.assertTrue(second['priceLookupPending']);self.assertEqual(lookup.call_count,1)
            jobs=list(self.bridge._price_hydrations.values());self.assertEqual(len(jobs),1)
            gate.set();await asyncio.gather(*jobs)
            final=await self.prices.recipe_price(self.bridge,self.recipe,[self.ingredient])
            self.assertFalse(final['priceLookupPending']);self.assertTrue(final['complete'])
            self.assertEqual(final['totalsByCurrency'],{'EUR':1.2});self.assertEqual(lookup.call_count,1)

    def test_real_release_catalog_mapping_coverage(self):
        payload=json.loads((Path(__file__).resolve().parents[1]/'custom_components/cook4me/catalog/merged_catalog.v1.json').read_text())
        rows={r['id']:r for r in payload['ingredients']}
        ingredients=[i for r in payload['recipes'] for v in r['variants'] for i in v.get('ingredients',[])]
        mapped=sum(bool(self.prices.category_for(rows.get(i.get('ingredientId'),{}))) for i in ingredients)
        self.assertGreater(mapped/len(ingredients),.52)


if __name__=='__main__':unittest.main()
