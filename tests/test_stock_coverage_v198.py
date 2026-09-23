"""Production coverage regressions: language-independent identity and quantities."""
from copy import deepcopy
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('coverage_v198');pkg.__path__=[str(ROOT/'custom_components/cook4me')];sys.modules[pkg.__name__]=pkg
from coverage_v198 import stock_coverage as sc
from coverage_v198.food_intelligence import recipe_quantity_feasibility as feasibility

CATALOG={'ingredients':[
 {'id':'rice','key':'rice','canonicalName':'Rice'},
 {'id':'rice-de','canonicalName':'Rice','conceptId':'concept:food:rice','classification':'food'},
 {'id':'rice-el','canonicalName':'Rice','conceptId':'concept:food:rice','classification':'food'},
 {'id':'dried-rice','canonicalName':'Dried rice','classification':'food'},
 {'id':'cooked-rice','canonicalName':'Cooked rice','classification':'food'},
 {'id':'milk','canonicalName':'Milk','classification':'food'},
 {'id':'soy-milk','canonicalName':'Soy milk','classification':'food'},
 {'id':'garlic','canonicalName':'Garlic','classification':'food'},
 {'id':'chopped-garlic','canonicalName':'Chopped garlic','classification':'food'},
 {'id':'garlic-powder','canonicalName':'Garlic powder','classification':'food'},
 {'id':'unconfirmed','canonicalName':'Rice','needsSemanticConfirmation':True},
 {'id':'equipment','canonicalName':'Rice','classification':'equipment'},
]}

def stock(key='rice',name='Ρύζι',amount=500,unit='g',links=None):
 return [{'key':key,'name':name,'unit':unit,'lots':[{'id':'lot1','quantity':amount,**({'ingredientLinks':links} if links else {})}]}]

def ingredient(key='rice',name='Reis',amount=100,unit='g',**extra):
 return {'ingredientId':key,'name':name,'foodName':name,'quantity':amount,'unit':unit,**extra}

def check(item,inventory):
 return feasibility({'ingredients':[item]},inventory)['items'][0]

class StockCoverageV198Tests(unittest.TestCase):
 def setUp(self):sc.warm_stock_catalog(CATALOG)
 def test_ingredient_id_survives_different_display_language(self):
  result=check(ingredient(),stock());self.assertEqual(result['coverage'],1);self.assertEqual(result['key'],'rice')
 def test_only_id_field_also_survives(self):
  item=ingredient();item['id']=item.pop('ingredientId');self.assertEqual(check(item,stock())['coverage'],1)
 def test_explicit_key_wins_over_stale_ingredient_id(self):
  self.assertEqual(check({**ingredient('milk'),'key':'rice'},stock())['coverage'],1)
 def test_stale_food_key_cannot_override_explicit_key(self):
  row=check({**ingredient('rice'),'key':'rice','foodKey':'milk'},stock());self.assertEqual(row['key'],'rice');self.assertEqual(row['coverage'],1)
 def test_indices_stay_aligned_when_legacy_string_rows_are_skipped(self):
  result=feasibility({'ingredients':['legacy text',ingredient(amount=300),ingredient(amount=300)]},stock(amount=450))
  self.assertEqual([row['ingredientIndex'] for row in result['items']],[1,2])
 def test_locale_specific_and_provider_ids_join(self):
  for key in ('rice','rice-el','rice-de'):
   for stored in ('rice','rice-el','rice-de'):
    with self.subTest(key=key,stored=stored):self.assertEqual(check(ingredient(key),stock(stored))['coverage'],1)
 def test_shared_product_mapping_works(self):
  inventory=stock('barcode-product',name='My product',links=[{'key':'rice-el','name':'Ρύζι'}]);self.assertEqual(check(ingredient('rice-de'),inventory)['coverage'],1)
 def test_two_requests_cannot_reuse_same_physical_lot(self):
  result=feasibility({'ingredients':[ingredient('rice-de',amount=300),ingredient('rice-el',amount=300)]},stock(amount=450))
  self.assertEqual(sorted(r['coverage'] for r in result['items']),[.5,1]);self.assertEqual(result['quantityCoverage'],.75)
  self.assertEqual([r['ingredientIndex'] for r in result['items']],[0,1])
 def test_partial_stock_is_partial_not_zero(self):
  self.assertEqual(check(ingredient(amount=1000),stock(amount=250))['coverage'],.25)
 def test_gram_unit_id_overrides_translated_label(self):
  self.assertEqual(check(ingredient(unit='γραμμάρια',unitKey='UNIT_27'),stock())['coverage'],1)
 def test_localized_stock_and_requirement_units(self):
  self.assertEqual(check(ingredient(unit='γρ.'),stock(unit='γραμμάρια'))['coverage'],1)
 def test_decimal_comma_kg(self):
  self.assertEqual(check(ingredient(amount='0,5',unit='κιλά'),stock(amount=500))['coverage'],1)
 def test_weight_fallback(self):
  item=ingredient(amount=None,unit='');item['weight']={'quantity':100,'unit':'γρ.','unitKey':'UNIT_27'};self.assertEqual(check(item,stock())['coverage'],1)
 def test_garlic_clove_uses_server_food_name_not_greek_display(self):
  item=ingredient('garlic','Σκόρδο',1,'σκελίδα',unitKey='UNIT_28');row=check(item,stock('garlic','Σκόρδο',3))
  self.assertEqual(row['coverage'],1);self.assertEqual(row['confidence'],'reviewed_portion')
 def test_reviewed_preparation_alias_can_use_assigned_raw_food(self):
  self.assertEqual(check(ingredient('chopped-garlic','Σκόρδο ψιλοκομμένο'),stock('garlic'))['coverage'],1)
 def test_food_forms_do_not_collapse(self):
  for requested,stored in [('garlic-powder','garlic'),('rice','cooked-rice'),('soy-milk','milk')]:
   self.assertEqual(check(ingredient(requested,'Same translated name'),stock(stored,'Same translated name'))['coverage'],0)
 def test_unconfirmed_canonical_match_is_not_proof(self):
  self.assertEqual(check(ingredient('unconfirmed','Ρύζι'),stock())['coverage'],0)
 def test_equipment_does_not_gain_food_aliases(self):
  self.assertEqual(check(ingredient('equipment','Ρύζι'),stock())['coverage'],0)
 def test_unknown_key_cannot_gain_match_by_identical_ui_name(self):
  self.assertEqual(check(ingredient('other','Ρύζι'),stock())['coverage'],0)
 def test_name_only_legacy_row_still_matches(self):
  self.assertEqual(check({'name':'Ρύζι','quantity':50,'unit':'g'},stock())['coverage'],1)
 def test_unknown_measurement_stays_unknown(self):
  row=check(ingredient(unit='bag'),stock());self.assertIsNone(row['coverage']);self.assertEqual(row['status'],'incompatible_unit')
 def test_unknown_requirement_stays_unknown(self):
  row=check(ingredient(amount=None),stock());self.assertIsNone(row['coverage'])
 def test_unlimited_stock_retained(self):
  row=check(ingredient(),[{'key':'rice','name':'Ρύζι','unit':'g','unlimited':True}]);self.assertEqual(row['coverage'],1)
 def test_recipe_and_storage_never_mutate(self):
  recipe={'ingredients':[ingredient('rice-el',unit='γρ.')]};inventory=stock(unit='γραμμάρια');before=deepcopy((recipe,inventory));feasibility(recipe,inventory);self.assertEqual((recipe,inventory),before)
 def test_empty_index_is_safe_and_direct_ids_still_match(self):
  sc.warm_stock_catalog({'ingredients':[]});self.assertEqual(check(ingredient(),stock())['coverage'],1)
 def test_no_disk_reads_when_checking_coverage(self):
  from unittest.mock import patch
  with patch.object(Path,'read_text',side_effect=AssertionError('disk I/O')):
   self.assertEqual(check(ingredient(),stock())['coverage'],1)

class RuntimeSourceV198Tests(unittest.TestCase):
 def test_runtime_url_constructor_and_editor_version_are_rotated(self):
  text=(ROOT/'custom_components/cook4me/panel.py').read_text();self.assertIn('runtime-v198',text);self.assertIn('&editor=196&runtime=198',text)
  js=(ROOT/'custom_components/cook4me/frontend/cook4me-panel-v180.js').read_text();self.assertIn('ProductEditorMixin',js);self.assertIn('cook4me-recipe-hub-panel-v180-runtime-v198',js)
 def test_setup_builds_stock_index_off_event_loop(self):
  source=(ROOT/'custom_components/cook4me/__init__.py').read_text();self.assertIn('await hass.async_add_executor_job(warm_stock_catalog)',source);self.assertIn('catalog and stock index ready in %.2f seconds',source)

if __name__=='__main__':unittest.main()
