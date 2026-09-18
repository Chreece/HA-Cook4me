"""Offline price evidence, exact package quantities and country search regressions."""
from datetime import datetime, timedelta, timezone
import importlib
import io
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import test_automatic_prices_v79 as previous
import test_runtime_audit_v74 as runtime


class OfflinePriceTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = previous.AutomaticPriceTests.asyncTearDown
    store = previous.AutomaticPriceTests.store
    observed = previous.AutomaticPriceTests.observed
    raw = previous.AutomaticPriceTests.raw

    def setUp(self):
        previous.AutomaticPriceTests.setUp(self)
        self.snapshot = importlib.import_module(runtime.PREFIX + '.price_snapshot')
        self.quantities = importlib.import_module(runtime.PREFIX + '.price_quantities')

    def seed(self, **changes):
        return {'schemaVersion': 1, 'observations': [self.observed(categories=['en:rices'], **changes)],
                'locationsByCountry': {'DE': [11, 12], 'FR': [21]}}

    def lookup(self, **changes):
        return self.costs.lookup_open_prices(category='en:rices', category_type='PRODUCT',
            country='DE', currency='EUR', unit='g', **changes)

    async def test_real_automatic_recipe_cost_works_offline_and_remains_estimate(self):
        with patch.object(self.snapshot, '_load', return_value=self.seed()), \
                patch.object(self.costs.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            result = await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient])
            again = await self.prices.recipe_price(self.bridge, self.recipe, [self.ingredient])
        self.assertTrue(result['complete'])
        self.assertTrue(result['estimated'])
        self.assertEqual(result['totalsByCurrency'], {'EUR': 1.2})
        self.assertEqual(again['totalsByCurrency'], {'EUR': 1.2})
        self.assertEqual(result['ingredients'][0]['references'][0]['source'], 'open_prices_category')
        self.assertEqual(result['ingredients'][0]['references'][0]['observationId'], 7)
        self.assertTrue(all(not key[0] for key in getattr(self.bridge, '_price_queries', {})), 'Category evidence is not a confirmed barcode assignment')

    def test_snapshot_boundaries_and_actual_observation_expiry(self):
        cases = [dict(country='FR'), dict(currency='USD'), dict(categories=['en:rice-pudding']),
                 dict(date=(datetime.now(timezone.utc).date()-timedelta(days=181)).isoformat()),
                 dict(date='2099-01-01'), dict(basisUnit='pcs'), dict(usable=False)]
        for changes in cases:
            seed = self.seed()
            seed['observations'][0].update(changes)
            with self.subTest(changes=changes), patch.object(self.snapshot, '_load', return_value=seed):
                self.assertEqual(self.snapshot.snapshot_observations(category='en:rices', country='DE',currency='EUR',unit='g'), [])

    def test_first_lookup_uses_seed_without_network_even_with_other_preferred_form(self):
        with patch.object(self.snapshot, '_load', return_value=self.seed()), patch.object(self.costs.urllib.request, 'urlopen') as get:
            result = self.costs.lookup_open_prices(category='en:rices', category_type='CATEGORY',
                country='DE', currency='EUR', unit='kg', prefer_snapshot=True)
        get.assert_not_called()
        self.assertTrue(result['offlineSnapshot'])
        self.assertEqual(result['pagesChecked'], 0)

    async def test_explicit_refresh_uses_live_result_and_keeps_provenance(self):
        with patch.object(self.snapshot, '_load', return_value=self.seed()):
            await self.prices.product_price(self.bridge, ingredient=self.ingredient, quantity=200, unit='g')
            with patch.object(self.costs.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps({'items':[self.raw(id=9,price=4)]}).encode())) as get:
                result = await self.prices.product_price(self.bridge, ingredient=self.ingredient, quantity=200,unit='g',refresh_since=time.monotonic())
        self.assertEqual(get.call_count, 1)
        self.assertEqual(result['estimate'], 1.6)
        self.assertEqual(result['reference']['observationId'], 9)

    async def test_after_24_hours_refresh_does_not_reseed_old_snapshot(self):
        with patch.object(self.snapshot, '_load', return_value=self.seed()):
            await self.prices.product_price(self.bridge, ingredient=self.ingredient, quantity=200,unit='g')
            store = await self.store()
            for ref in store._data['references'].values():
                ref['updatedAt']=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
            getattr(self.bridge, '_price_queries', {}).clear()
            with patch.object(self.costs.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps({'items':[self.raw(id=10,price=5)]}).encode())) as get:
                result=await self.prices.product_price(self.bridge,ingredient=self.ingredient,quantity=200,unit='g')
        self.assertEqual(get.call_count,1)
        self.assertEqual(result['estimate'],2)

    async def test_offline_refresh_failure_retains_saved_price(self):
        with patch.object(self.snapshot,'_load',return_value=self.seed()):
            await self.prices.product_price(self.bridge,ingredient=self.ingredient,quantity=200,unit='g')
            with patch.object(self.costs.urllib.request,'urlopen',side_effect=OSError('offline')):
                result=await self.prices.product_price(self.bridge,ingredient=self.ingredient,quantity=200,unit='g',refresh_since=time.monotonic())
        self.assertTrue(result['lookupFailed'])
        self.assertEqual(result['estimate'],1.2)

    async def test_manual_prices_and_disabled_automatic_preference_take_priority(self):
        store=await self.store()
        await store.async_set_settings(auto_global_prices=False)
        with patch.object(self.snapshot,'_load',return_value=self.seed()),patch.object(self.costs.urllib.request,'urlopen') as get:
            result=await self.prices.product_price(self.bridge,ingredient=self.ingredient,quantity=200,unit='g')
        get.assert_not_called();self.assertIsNone(result['estimate'])
        await store.async_set_reference('k:rice',amount=1,currency='EUR',basis_quantity=1000,basis_unit='g',country='DE',source='manual')
        await store.async_set_settings(auto_global_prices=True)
        with patch.object(self.costs.urllib.request,'urlopen') as get:
            result=await self.prices.product_price(self.bridge,ingredient=self.ingredient,quantity=200,unit='g')
        get.assert_not_called();self.assertEqual(result['estimate'],.2)

    def test_country_search_reaches_local_stores_before_global_fallback(self):
        seen=[]
        def response(req, **kwargs):
            params=parse_qs(urlparse(req.full_url).query);seen.append(params)
            items=[self.raw(location={'osm_address_country_code':'FR'})] if len(seen)==1 else [self.raw()]
            return io.BytesIO(json.dumps({'items':items,'pages':1}).encode())
        with patch.object(self.costs,'country_locations',return_value=list(range(1,601))),patch.object(self.costs.urllib.request,'urlopen',side_effect=response):
            result=self.lookup()
        self.assertEqual(result['usableCount'],1)
        self.assertEqual(seen[0]['location_id__in'][0].split(',')[0],'1')
        self.assertEqual(seen[1]['location_id__in'][0].split(',')[0],'301')
        self.assertNotIn('location_osm_address_country_code',seen[0])

    def test_new_store_can_be_found_by_worldwide_fallback(self):
        seen=[]
        def response(req,**kwargs):
            params=parse_qs(urlparse(req.full_url).query);seen.append(params)
            return io.BytesIO(json.dumps({'items':[] if 'location_id__in' in params else [self.raw()],'pages':1}).encode())
        with patch.object(self.costs,'country_locations',return_value=[11]),patch.object(self.costs.urllib.request,'urlopen',side_effect=response):
            result=self.lookup()
        self.assertEqual(result['usableCount'],1);self.assertEqual(len(seen),2)
        self.assertFalse(result['searchLimited'])

    def test_country_queries_remain_bounded(self):
        with patch.object(self.costs,'country_locations',return_value=list(range(1,901))),patch.object(self.costs.urllib.request,'urlopen',side_effect=lambda *a,**k:io.BytesIO(json.dumps({'items':[self.raw(location={'osm_address_country_code':'FR'})],'pages':99}).encode())) as get:
            result=self.lookup()
        self.assertEqual(get.call_count,5);self.assertTrue(result['searchLimited'])
        self.assertEqual(result['usableCount'],0)

    def test_explicit_package_labels_and_multipacks(self):
        for label, expected in {'10 Stück':(10,'pcs'),'6 eggs':(6,'pcs'),'6 œufs':(6,'pcs'),
                '0,5 kg':(.5,'kg'),'6 x 125 g':(750,'g'),'2×0.5 l':(1,'l'),'250 ml':(250,'ml')}.items():
            with self.subTest(label=label):
                self.assertEqual(self.quantities.explicit_product_basis({'quantity':label}),expected)
        result=self.costs._normalize_open_prices([self.raw(product={'quantity':'10 Eier'})],code='12345678',curr='EUR',market='DE',category='',category_type='PRODUCT',cutoff=datetime.now(timezone.utc).date()-timedelta(days=180),today=datetime.now(timezone.utc).date())
        self.assertEqual((result[0]['basisQuantity'],result[0]['basisUnit']),(10,'pcs'))

    def test_never_guess_servings_density_count_or_ambiguous_package_labels(self):
        for label in ['10','2 portions','1 bunch','400 g (240 g drained)','500 g + 100 g free','1.5 eggs','0 g','1 kg / 2 l','1,000 g','6 x']:
            with self.subTest(label=label):
                # A three-digit decimal can mean a thousands separator: reject it.
                self.assertEqual(self.quantities.explicit_product_basis({'quantity':label}),(None,''))
        self.assertEqual(self.quantities.explicit_product_basis({'product_name':'Rice 500 g','serving_size':'100g'}),(None,''))
        self.assertEqual(self.quantities.explicit_product_basis({'product_quantity':500,'product_quantity_unit':'g','quantity':'1kg'}),(500,'g'))

    def test_shipped_snapshot_has_only_public_price_evidence_and_supported_categories(self):
        data=json.loads((Path(__file__).resolve().parents[1]/'custom_components/cook4me/catalog/observed_prices.v1.json').read_text())
        tags={v[0] for v in self.prices._CATEGORIES.values()}
        self.assertGreaterEqual(len(data['observations']),350)
        self.assertGreaterEqual(len([r for r in data['observations'] if r['country']=='DE']),170)
        for row in data['observations']:
            missing_categories = set(row['categories']) - tags
            self.assertFalse(missing_categories, (row.get('id'), sorted(missing_categories)))
            self.assertGreater(row['amount'],0);self.assertGreater(row['basisQuantity'],0)
            self.assertNotIn('owner',row);self.assertNotIn('proof',row)
        self.assertEqual(data['license'],'ODbL-1.0')
        for name in ['Pepper','Salt and pepper','Rice pudding','Cooked rice']:
            self.assertIsNone(self.prices.category_for({'canonicalName':name}))
        self.assertEqual(
            self.prices.category_for({'canonicalName':'Green pepper'}),
            ('cook4me:green-bell-pepper', 'REFERENCE'),
        )
        for name in ['Coconut cream','Seitan','Ghee','Cream cheese','Rapeseed oil','Frozen green peas','Dried penne pasta']:
            self.assertIsNotNone(self.prices.category_for({'canonicalName':name}))


if __name__=='__main__':unittest.main()
