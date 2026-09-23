"""Exercise stock coverage with the shipped Greek and German catalog choices."""
import time
import unittest
from test_stock_coverage_v198 import sc, feasibility, stock, ingredient
from coverage_v198 import release_catalog as catalog

class ShippedCatalogStockV198Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  start=time.monotonic();cls.payload=catalog.load_release_catalog();sc.warm_stock_catalog(cls.payload)
  cls.choices={language:catalog.ingredient_choices(language) for language in ('el','de')}
  print(f'Catalog warm: {time.monotonic()-start:.2f}s; {len(cls.payload["ingredients"])} source ingredients')
 def test_every_catalog_selection_matches_its_id_in_another_language(self):
  total=0
  for language,rows in self.choices.items():
   self.assertGreater(len(rows),3000)
   for row in rows:
    key=row.get('key') or row['ingredientId']
    raw=ingredient(key, row.get('canonicalName') or 'source label', 10, 'g')
    # The scanner saves the chosen key/name, not the display grouping metadata.
    inventory=stock(key,row['name'],100,'g')
    result=feasibility({'ingredients':[raw]},inventory)['items'][0]
    self.assertEqual(result['coverage'],1,(language,key,row['name'],result))
    total+=1
  print(f'Cross-language exact-ID coverage checks: {total}')
 def test_reviewed_local_skyr_siblings_match_provider_storage(self):
  key='local:de:3d101959f8ad86675b18'
  self.assertIn(key,self.payload['_runtimeIngredientById'])
  for source in ['local:pl:198a30119ce717b6c08d','local:pl:a730ae15fff9b2ec388f']:
   result=feasibility({'ingredients':[ingredient(source,'Skyr',100,'g')]},stock(key,'Σκιρ',400))['items'][0]
   self.assertEqual(result['coverage'],1)
 def test_greek_garlic_clove_uses_reviewed_gram_conversion(self):
  raw=ingredient('M_FOOD_6','Σκόρδο',1,'σκελίδα',unitKey='UNIT_28')
  result=feasibility({'ingredients':[raw]},stock('M_FOOD_6','Σκόρδο',3,'g'))['items'][0]
  self.assertEqual(result['coverage'],1);self.assertEqual(result['confidence'],'reviewed_portion')

if __name__=='__main__':unittest.main()
