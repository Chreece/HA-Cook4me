"""Real screenshot recipes, identity collisions and traceable reference estimates."""
from copy import deepcopy
from datetime import date, timedelta
import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_automatic_prices_v79 as previous

COMPONENT = Path(__file__).resolve().parents[1] / 'custom_components/cook4me'


class PriceGapTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = previous.AutomaticPriceTests.asyncTearDown
    store = previous.AutomaticPriceTests.store

    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((COMPONENT / 'catalog/merged_catalog.v1.json').read_text())
        cls.evidence = {'schemaVersion': 1, 'observations': []}
        for filename in ['observed_prices.v1.json', 'retail_prices.v1.json']:
            cls.evidence['observations'] += json.loads((COMPONENT / 'catalog' / filename).read_text())['observations']

    def setUp(self):
        previous.AutomaticPriceTests.setUp(self)
        self.snapshot = importlib.import_module(previous.runtime.PREFIX + '.price_snapshot')
        self.measures = importlib.import_module(previous.runtime.PREFIX + '.price_measurements')
        self.identity = importlib.import_module(previous.runtime.PREFIX + '.price_identity')
        self.real = patch.object(self.snapshot, '_load', return_value=deepcopy(self.evidence))
        self.real.start(); self.addCleanup(self.real.stop)
        network = patch.object(self.prices, 'lookup_open_prices', side_effect=AssertionError('unexpected network'))
        network.start(); self.addCleanup(network.stop)

    async def test_screenshot_recipes_through_real_offline_cost_path(self):
        expected = {'805952': (8, 8), '314558': (6, 8), '963752': (11, 11), '785571': (5, 5),
                    '270881': (7, 10), '879742': (12, 12), '288189': (6, 7)}
        seen = set()
        for recipe in self.catalog['recipes']:
            for variant in recipe['variants']:
                key = str(variant.get('variantId') or variant.get('id'))
                if key not in expected: continue
                with self.subTest(variant=key):
                    original = deepcopy(variant)
                    result = await self.prices.offline_recipe_price(self.bridge, variant, self.catalog['ingredients'])
                    rows = result['ingredients']; covered = sum(row['coverage'] == 1 for row in rows)
                    self.assertEqual((covered, len(rows)), expected[key])
                    self.assertEqual(result['complete'], covered == len(rows))
                    self.assertTrue(result['totalsByCurrency']['EUR'] > 0)
                    self.assertEqual(variant, original)
                    if key == '288189':
                        self.assertEqual([r['priceStatus'] for r in rows if r['coverage'] < 1], ['recipe_amount_unknown'])
                    if key == '963752':
                        self.assertEqual(len([r for r in rows if any('en:parmigiano-reggiano' in ref.get('categories', []) for ref in r['references'])]), 2,
                                         'Distinct source rows must not be silently deduplicated')
                    seen.add(key)
        self.assertEqual(seen, set(expected))

    def test_pepper_and_tomato_paste_use_reviewed_identity(self):
        black = {'ingredientId': 'M_FOOD_388', 'name': 'Pepper', 'quantity': 1, 'unitKey': 'UNIT_11'}
        self.assertEqual(self.prices.category_for(black)[0], 'en:ground-black-peppers')
        self.assertTrue(any(o['unit'] == 'g' and o['quantity'] == 2.3 for o in self.measures.price_options(black)))
        for key in ['M_FOOD_377', 'M_FOOD_389', 'unknown']:
            other = {**black, 'ingredientId': key}
            self.assertIsNone(self.prices.category_for(other))
            self.assertFalse(any(o['unit'] == 'g' for o in self.measures.price_options(other)))
        paste = {'ingredientId': 'M_FOOD_131', 'name': 'Tomato purée', 'quantity': 1, 'unitKey': 'UNIT_12'}
        self.assertEqual(self.prices.category_for(paste)[0], 'en:tomato-pastes')
        self.assertTrue(any(o['unit'] == 'g' and o['quantity'] == 16 for o in self.measures.price_options(paste)))

    async def test_cube_and_prepared_broth_keep_powder_units_separate(self):
        for raw, amount in [({'quantity': 1, 'unit': 'Würfel', 'unitKey': 'UNIT_21'}, .125),
                            ({'quantity': 500, 'unit': 'ml'}, .125)]:
            result = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [{'name': 'Vegetable stock', **raw}]}, [])
            self.assertTrue(result['complete']); self.assertAlmostEqual(result['totalsByCurrency']['EUR'], round(amount, 2))
        result = await self.prices.offline_recipe_price(self.bridge, {'ingredients': [{'name': 'Vegetable stock', 'quantity': 10, 'unit': 'g'}]}, [])
        self.assertFalse(result['complete'])
        for country in ['DE', 'FR']:
            result = await self.prices._observations(self.bridge, category='cook4me:vegetable-stock', unit='ml',
                settings={'country': country, 'currency': 'EUR'}, refresh_since=1)
            self.assertEqual(bool(result['items']), country == 'DE')

    async def test_water_is_a_dated_regional_tariff_with_notes_and_expiry(self):
        recipe = {'ingredients': [{'name': 'Water', 'quantity': 2, 'unit': 'l'}]}
        result = await self.prices.recipe_price(self.bridge, recipe, [])
        self.assertTrue(result['complete'])
        ref = result['ingredients'][0]['references'][0]
        self.assertEqual(ref['source'], 'utility_snapshot')
        self.assertIn('not your household tariff', ref['note'])
        store = await self.store()
        for row in store._data['references'].values(): row['date'] = (date.today() - timedelta(days=181)).isoformat()
        self.assertIsNone(store.best_reference(ref['identity'], country='DE', currency='EUR'))
        stale = deepcopy(self.evidence)
        for row in stale['observations']: row['date'] = (date.today() - timedelta(days=181)).isoformat()
        with patch.object(self.snapshot, '_load', return_value=stale):
            result = await self.prices.offline_recipe_price(self.bridge, recipe, [])
        self.assertFalse(result['complete'])

    def test_density_is_food_specific_and_does_not_infer_unknown_amounts(self):
        options = self.measures.price_options({'name': 'Thick crème fraîche', 'quantity': 300, 'unit': 'ml'})
        density = next(o for o in options if o['unit'] == 'g')
        self.assertAlmostEqual(density['quantity'], 293.4)
        self.assertIn('38%', density['estimate']['label'])
        self.assertEqual(self.measures.price_options({'name': 'Mystery sauce', 'quantity': 300, 'unit': 'ml'}), [{'quantity': 300., 'unit': 'ml'}])
        for name in ['Salt', 'Pepper', 'Water', 'Thick crème fraîche']:
            self.assertEqual(self.measures.price_options({'name': name}), [])
        self.assertFalse(self.identity.is_cost_heading({'name': 'Additionally:'}))
        self.assertFalse(self.identity.is_cost_heading({'key': 'local:pl:67b936187af6ea892acb', 'quantity': 1}))

    async def test_upgrade_clears_old_external_estimates_and_keeps_user_prices(self):
        store = await self.store()
        for source in ['manual', 'purchase', 'open_prices_category', 'retail_snapshot', 'utility_snapshot']:
            await store.async_set_reference(source, amount=1, currency='EUR', basis_quantity=1, basis_unit='g', source=source, country='DE')
        saved = deepcopy(store._data); saved['priceEvidenceRevision'] = 86
        fresh = self.costs.Cook4MeCostStore(self.hass, 'test'); fresh._store.saved = saved
        await fresh.async_load()
        self.assertEqual({r['source'] for r in fresh._data['references'].values()}, {'manual', 'purchase'})


if __name__ == '__main__': unittest.main()
