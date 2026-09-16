"""Exercise the real offline catalog through Home Assistant's response scheduler."""
import unittest
import test_ingredient_endpoint_v80 as previous


class OfflineCatalogTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = previous.IngredientEndpointTests.asyncSetUp
    drain = previous.IngredientEndpointTests.drain

    async def test_catalog_available_in_english_greek_and_german_without_cloud(self):
        for index, language in enumerate(('en','el','de'),1):
            self.assertIsNone(self.v31.ws_ingredient_catalog(self.hass,self.connection,
                {'id':index,'language':language,'refresh':True}))
            await self.drain()
        self.assertEqual(self.errors,[])
        for _,result in self.results:
            self.assertTrue(result['offline']);self.assertEqual(result['presentationVersion'],63)
            self.assertGreater(len(result['items']),2900)
            self.assertTrue(all(row['displayLanguage']==result['language'] for row in result['items']))
            self.assertTrue(any('M_FOOD_421' in row['sourceIngredientIds'] for row in result['items']))
        self.cloud.assert_not_awaited()
