"""New retail evidence through offline costing, including food-form boundaries."""
from datetime import date
import json
import unittest

import test_price_gaps_v87 as previous


class PriceExpansionTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(previous.PriceGapTests.setUpClass.__func__)
    setUp = previous.PriceGapTests.setUp
    asyncTearDown = previous.PriceGapTests.asyncTearDown
    store = previous.PriceGapTests.store

    async def cost(self, name, quantity, unit='', **extra):
        return await self.prices.offline_recipe_price(self.bridge, {'ingredients': [
            {'name': name, 'quantity': quantity, 'unit': unit, **extra}]}, [])

    async def test_common_gaps_are_costed_without_network_and_keep_sources(self):
        cases = [('Green onion', 130, 'g', 1.90), ('Quinoa', 500, 'g', 2.85),
                 ('Chopped tomatoes', 400, 'g', .65), ('Breadcrumbs', 400, 'g', 1.39),
                 ('Ricotta', 250, 'g', 2.99), ('Rice vinegar', 145, 'ml', 2.25),
                 ('Sesame oil', 250, 'ml', 3.75), ('Caper', 90, 'g', 1.95),
                 ('Dried Pasta', 500, 'g', .69), ('Mascarpone', 250, 'g', 4.39)]
        for name, quantity, unit, expected in cases:
            with self.subTest(name=name):
                result = await self.cost(name, quantity, unit)
                self.assertTrue(result['complete'])
                self.assertAlmostEqual(result['totalsByCurrency']['EUR'], expected)
                ref = result['ingredients'][0]['references'][0]
                self.assertEqual(ref['source'], 'retail_snapshot')
                self.assertEqual(ref['country'], 'DE')
                self.assertTrue(ref['sourceUrl'].startswith('https://'))
                self.assertTrue(ref['productName'])
                self.assertTrue(ref['note'])

    async def test_spring_onion_bunch_is_mass_not_one_piece(self):
        result = await self.cost('Welsh onion', 1, 'pcs')
        row = result['ingredients'][0]
        self.assertTrue(result['complete'])
        self.assertEqual(row['quantityEstimate']['quantity'], 15)
        self.assertEqual(row['references'][0]['basisQuantity'], 130)
        self.assertAlmostEqual(result['totalsByCurrency']['EUR'], .22)
        self.assertIn('Munich', row['references'][0]['note'])
        self.assertFalse((await self.cost('Spring onions', 1, 'bunch'))['complete'])

    async def test_fresh_and_dried_herbs_keep_their_own_price_and_portion(self):
        for name, grams, price in [('Thyme', .8, 1.29), ('Dried thyme', 1., 2.25),
                                   # Existing Open Prices cocoa evidence retains priority.
                                   ('Chives', 1., .99), ('Cocoa', 1.8, 2.79)]:
            with self.subTest(name=name):
                result = await self.cost(name, 1, 'tsp', unitKey='UNIT_11')
                self.assertTrue(result['complete'])
                row = result['ingredients'][0]
                self.assertAlmostEqual(row['quantityEstimate']['quantity'], grams)
                self.assertAlmostEqual(row['references'][0]['amount'], price)
                self.assertIn('fdc.nal.usda.gov', row['quantityEstimate']['sourceUrl'])
        self.assertFalse((await self.cost('Basil', None))['complete'])

    async def test_prepared_stocks_do_not_price_powder_cubes_or_ambiguous_spoons(self):
        for name, expected in [('Chicken stock', 3.39), ('Beef stock', 3.39), ('Veal stock', 3.29)]:
            with self.subTest(name=name):
                result = await self.cost(name, 400, 'ml')
                self.assertTrue(result['complete'])
                self.assertAlmostEqual(result['totalsByCurrency']['EUR'], expected)
                for unit, key in [('g', 'UNIT_27'), ('cube', 'UNIT_17'), ('tsp', 'UNIT_11'), ('tbsp', 'UNIT_12')]:
                    self.assertFalse((await self.cost(name, 1, unit, unitKey=key))['complete'])
        for name in ['Stock', 'Chicken stock powder', 'Beef or chicken stock', 'Cooked polenta', 'Cocoa drink']:
            self.assertFalse((await self.cost(name, 100, 'ml'))['complete'])

    async def test_private_references_stay_offline_and_country_scoped(self):
        for category in ['cook4me:chopped-tomatoes', 'cook4me:dried-pasta', 'cook4me:chicken-stock']:
            for country in ['DE', 'FR']:
                result = await self.prices._observations(self.bridge, category=category,
                    settings={'country': country, 'currency': 'EUR'}, refresh_since=1)
                self.assertEqual(bool(result['items']), country == 'DE')
        missing = await self.cost('Quinoa', None)
        self.assertFalse(missing['complete'])
        self.assertEqual(missing['ingredients'][0]['priceStatus'], 'recipe_amount_unknown')

    def test_snapshot_and_portions_are_complete_and_unambiguous(self):
        retail = json.loads((previous.COMPONENT / 'catalog/retail_prices.v1.json').read_text())['observations']
        portions = json.loads((previous.COMPONENT / 'catalog/price_portions.v1.json').read_text())['portions']
        self.assertGreaterEqual(len(retail), 82)
        self.assertEqual(len({row['id'] for row in retail}), len(retail))
        self.assertGreaterEqual(len(portions), 69)
        pairs = [(name, row['measure']) for row in portions for name in row['names']]
        self.assertEqual(len(pairs), len(set(pairs)))
        for row in retail[34:]:
            self.assertGreater(row['amount'], 0)
            self.assertGreater(row['basisQuantity'], 0)
            self.assertEqual((row['country'], row['currency']), ('DE', 'EUR'))
            self.assertGreaterEqual(row['date'], '2026-09-16')
            self.assertLessEqual(row['date'], date.today().isoformat())


if __name__ == '__main__': unittest.main()
