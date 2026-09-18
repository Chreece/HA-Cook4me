"""User screenshot regressions with real offline evidence and quantity sources."""
from copy import deepcopy
import json
import unittest

import test_price_gaps_v87 as previous


class ScreenshotPriceTests(unittest.IsolatedAsyncioTestCase):
    setUpClass = classmethod(previous.PriceGapTests.setUpClass.__func__)
    setUp = previous.PriceGapTests.setUp
    asyncTearDown = previous.PriceGapTests.asyncTearDown
    store = previous.PriceGapTests.store

    async def cost(self, name, quantity=None, unit='', **extra):
        return await self.prices.offline_recipe_price(self.bridge, {'ingredients': [
            {'name': name, 'quantity': quantity, 'unit': unit, **extra}]}, [])

    async def test_all_serving_variants_of_screenshot_recipes(self):
        expected = {'922611': (5,5), '331285': (7,7), '511709': (6,7), '301641': (5,5),
                    '491186': (6,7), '374645': (8,10), '282073': (7,8), '287823': (5,7),
                    '307808': (4,5), '826311': (5,6), '816820': (3,8), '862912': (5,7),
                    '252627': (5,6), '834656': (7,8)}
        checked = set(); count = 0
        for family in self.catalog['recipes']:
            selected = next((str(v['variantId']) for v in family['variants'] if str(v['variantId']) in expected), None)
            if selected is None: continue
            for variant in family['variants']:
                with self.subTest(variant=variant['variantId'], title=variant['title']):
                    original = deepcopy(variant)
                    result = await self.prices.offline_recipe_price(self.bridge, variant, self.catalog['ingredients'])
                    priced = sum(row['coverage'] == 1 for row in result['ingredients'])
                    self.assertGreaterEqual(priced, expected[selected][0])
                    self.assertEqual(len(result['ingredients']), expected[selected][1])
                    self.assertEqual(result['complete'], priced == len(result['ingredients']))
                    self.assertGreater(result['totalsByCurrency']['EUR'], 0)
                    self.assertEqual(variant, original, 'Original recipe and device payload are unchanged')
                    count += 1
                    if str(variant['variantId']) == selected: checked.add(selected)
        self.assertEqual(checked, set(expected))
        self.assertEqual(count, 34)

    async def test_new_price_facts_through_offline_costing(self):
        for name, quantity, unit, expected in [('Almond milk',1000,'ml',1.35),('Skyr',450,'g',1.99),
                ('Carnaroli rice',500,'g',2.65),('Grated kaşar cheese',400,'g',5.99),
                ('Semolina',500,'g',1.79),('Soy cream',200,'ml',.70),('Maple syrup',250,'ml',3.75)]:
            with self.subTest(name=name):
                result = await self.cost(name,quantity,unit)
                self.assertTrue(result['complete'])
                self.assertAlmostEqual(result['totalsByCurrency']['EUR'], expected)
                ref = result['ingredients'][0]['references'][0]
                self.assertEqual(ref['source'], 'retail_snapshot')
                self.assertEqual((ref['country'],ref['currency']), ('DE','EUR'))
                self.assertTrue(ref['sourceUrl'].startswith('https://'))
                self.assertTrue(ref['productName']); self.assertTrue(ref['note'])

    async def test_count_and_spoon_estimates_keep_their_sources(self):
        for name, grams in [('Banana',118),('Pear',178),('Orange',131),('Plum',66),('Strawberry',12),('Date',7.1)]:
            with self.subTest(name=name):
                result = await self.cost(name,1)
                self.assertTrue(result['complete'])
                estimate = result['ingredients'][0]['quantityEstimate']
                self.assertAlmostEqual(estimate['quantity'], grams)
                self.assertIn('fdc.nal.usda.gov',estimate['sourceUrl'])
                self.assertTrue(estimate['assumedCount'])
        for name, grams in [('Slivered almonds',6.75),('Hazelnut',8.4375),('Curry paste',15)]:
            result = await self.cost(name,1,'tbsp')
            self.assertTrue(result['complete'])
            estimate = result['ingredients'][0]['quantityEstimate']
            self.assertAlmostEqual(estimate['quantity'], grams)
        self.assertNotIn('USDA', estimate['label'])
        self.assertIn('clubhouseforchefs.ca',estimate['sourceUrl'])
        self.assertNotIn('fdcId', estimate)
        shallot = (await self.cost('Shallot',1))['ingredients'][0]['quantityEstimate']
        self.assertEqual(shallot['quantity'],30)
        self.assertIn('alnatura.de',shallot['sourceUrl'])
        self.assertNotIn('USDA',shallot['label'])

    async def test_coconut_uses_edible_yield_and_discloses_both_portions(self):
        gram_result = await self.cost('Coconut',397,'g')
        self.assertEqual(gram_result['totalsByCurrency'],{'EUR':3.99})
        result = await self.cost('Coconut',3,'tbsp')
        self.assertTrue(result['complete'])
        estimate = result['ingredients'][0]['quantityEstimate']
        self.assertEqual(estimate['portionIds'],[86163,86164])
        self.assertAlmostEqual(estimate['quantity'],15/397)
        self.assertEqual(result['ingredients'][0]['references'][0]['basisUnit'],'pcs')
        self.assertIn('not dried coconut',result['ingredients'][0]['references'][0]['note'])

    async def test_cream_identity_is_scoped_and_never_uses_tofu_purchase_price(self):
        row = {'ingredientId':'M_FOOD_477','quantity':200,'unit':'ml','unitKey':'UNIT_35'}
        store = await self.store()
        await store.async_set_reference('k:M_FOOD_477',amount=100,currency='EUR',basis_quantity=200,
            basis_unit='ml',country='DE',source='manual')
        for identity_field in ['variantId','variantFunctionalId','recipeFunctionalId','id']:
            result = await self.prices.offline_recipe_price(self.bridge,{identity_field:'287823','ingredients':[row]},self.catalog['ingredients'])
            self.assertTrue(result['complete']); self.assertEqual(result['totalsByCurrency'],{'EUR':.70})
            self.assertEqual(result['ingredients'][0]['identity'],'k:cook4me:recipe-tofu-cream')
        canonical = self.prices.canonical_recipe({'variantId':'other','ingredients':[row]},self.catalog['ingredients'])
        self.assertEqual(canonical['ingredients'][0]['key'],'M_FOOD_477')
        canonical = self.prices.canonical_recipe({'variantId':'287823','ingredients':[{**row,'unit':'g','unitKey':'UNIT_27'}]},self.catalog['ingredients'])
        self.assertEqual(canonical['ingredients'][0]['key'],'M_FOOD_477')

    async def test_unknown_amounts_and_different_food_forms_remain_unpriced(self):
        for name, quantity, unit in [('Salt',None,''),('Chocolate',4,''),('Saffron',1,''),
                ('Coconut',None,''),('Coconut',1,'pack'),('Almond cream',100,'ml'),
                ('Tofu',200,'ml'),('Bean',100,'g'),('Stock',850,'ml')]:
            with self.subTest(name=name): self.assertFalse((await self.cost(name,quantity,unit))['complete'])
        for name in ['Dried coconut','Desiccated coconut','Coconut flour']:
            category = self.prices.category_for({'name':name})
            self.assertNotEqual(category[0] if category else '', 'en:coconuts')
        await (await self.store()).async_set_settings(country='FR',currency='EUR')
        self.assertFalse((await self.cost('Almond milk',1000,'ml'))['complete'])

    def test_all_portion_keys_are_unique_and_positive(self):
        pairs=[]
        for filename in ['price_portions.v1.json','price_reference_portions.v1.json']:
            data=json.loads((previous.COMPONENT/'catalog'/filename).read_text())
            for row in data['portions']:
                self.assertGreater(row['grams'],0)
                pairs.extend((name,row['measure']) for name in row['names'])
        self.assertEqual(len(pairs),len(set(pairs)))


if __name__ == '__main__': unittest.main()
