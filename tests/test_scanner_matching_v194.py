"""Production matcher tests, no Home Assistant or network required."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scanner_matching_v194', ROOT/'custom_components/cook4me/scanner_matching.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def row(key, name, canonical=None, aliases=(), **extra):
    return dict(key=key, name=name, canonicalName=canonical or name, searchAliases=list(aliases), **extra)


def keys(product, catalog):
    return {v['ingredient']['key'] for v in m.suggest_catalog_matches(product, catalog)}


class ScannerMatchingTests(unittest.TestCase):
    def test_all_matches_not_twelve_or_thirty(self):
        catalog = [row(f'carrot-{i}', 'Carrot', aliases=['Karotten']) for i in range(75)]
        self.assertEqual(len(m.suggest_catalog_matches({'productName':'Bio Karotten'}, catalog)), 75)

    def test_identity_not_label_deduplication(self):
        self.assertEqual(keys({'name':'rice'}, [row('a','Rice'),row('b','Rice'),row('a','Rice')]), {'a','b'})

    def test_greek_ui_german_product(self):
        self.assertEqual(keys({'productName':'Bio Karotten'}, [row('c','Καρότα','carrot',['Karotten','carrots'])]), {'c'})

    def test_accents_final_sigma_and_uppercase(self):
        self.assertEqual(keys({'name':'ΑΡΑΚΑΣ'},[row('p','Αρακάς','pea')]),{'p'})

    def test_translations_match_without_english_product(self):
        self.assertEqual(keys({'name':'Ρύζι'},[row('r','Reis','rice',translations={'el':'Ρύζι'})]), {'r'})

    def test_normalized_product_name_maps(self):
        self.assertEqual(keys({'productNames':{'de':'Naturjoghurt','el':'Γιαούρτι'}},[row('y','Γιαούρτι','yogurt',['Naturjoghurt'])]),{'y'})

    def test_whole_product_offers_preparation_variants(self):
        cat=[row('a','Carrot'),row('b','Peeled carrot'),row('c','Carrot, finely chopped'),row('d','Diced carrot')]
        self.assertEqual(keys({'name':'Carrots'},cat),{'a','b','c','d'})

    def test_canned_legume_offers_cooked_not_dried(self):
        cat=[row('a','Chickpea'),row('b','Cooked chickpea'),row('c','Canned chickpea'),row('d','Dried chickpea'),row('e','Chickpea flour')]
        self.assertEqual(keys({'name':'Canned chickpeas'},cat),{'a','b','c'})

    def test_category_state_cannot_be_overridden_by_broad_parent(self):
        cat=[row('a','Fresh tomato'),row('b','Canned tomato'),row('c','Tomato sauce')]
        self.assertEqual(keys({'name':'Tomaten','categories':['tomatoes','canned tomatoes']},cat),{'b'})

    def test_raw_food_is_not_soup(self):
        self.assertEqual(keys({'name':'Tomato soup'},[row('t','Tomato'),row('s','Tomato soup')]),{'s'})

    def test_milk_chocolate_not_milk(self):
        self.assertEqual(keys({'name':'Milk chocolate'},[row('m','Milk'),row('c','Milk chocolate')]),{'c'})

    def test_peanut_butter_not_raw_nuts_or_dairy_butter(self):
        cat=[row('p','Peanut'),row('b','Butter'),row('pb','Peanut butter')]
        self.assertEqual(keys({'name':'Peanut butter'},cat),{'pb'})

    def test_coconut_milk_not_dairy_milk(self):
        self.assertEqual(keys({'name':'Coconut milk'},[row('m','Milk'),row('c','Coconut milk')]),{'c'})

    def test_compound_guard_without_specific_catalog_candidate(self):
        for product, canonical in [('Coconut milk','Milk'),('Oat drink','Milk'),('Peanut butter','Butter'),
                                    ('Strawberry yogurt','Plain yogurt'),('Erdbeerjoghurt','Yogurt')]:
            with self.subTest(product=product):
                self.assertEqual(keys({'genericName':canonical,'productName':product},[row('x',canonical)]),set())

    def test_plain_yogurt_does_not_get_flavoured_sibling(self):
        self.assertEqual(keys({'name':'Plain yogurt'},[row('p','Plain yogurt'),row('s','Strawberry yogurt')]),{'p'})

    def test_percentages_and_different_varieties_are_not_erased(self):
        self.assertEqual(keys({'name':'Cream 30%'},[row('x','Cream 15%'),row('y','Cream 30%')]),{'y'})
        self.assertNotIn('g', keys({'name':'Red lentils'},[row('r','Red lentil'),row('g','Green lentil')]))

    def test_unsweetened_does_not_match_sweetened(self):
        self.assertEqual(keys({'name':'Unsweetened almond drink'},[row('u','Unsweetened almond drink'),row('s','Sweetened almond drink')]),{'u'})

    def test_rice_flour_not_whole_rice(self):
        self.assertEqual(keys({'name':'Rice flour'},[row('r','Rice'),row('f','Rice flour')]),{'f'})

    def test_mix_is_not_multiple_full_packages(self):
        self.assertEqual(keys({'name':'Mixed carrots and peas'},[row('c','Carrot'),row('p','Pea')]),set())

    def test_pickles_not_raw_cucumber(self):
        self.assertEqual(keys({'name':'Pickled cucumber'},[row('c','Cucumber'),row('p','Pickled cucumber')]),{'p'})

    def test_smoked_tofu_not_plain(self):
        self.assertEqual(keys({'name':'Smoked tofu'},[row('p','Tofu'),row('s','Smoked tofu')]),{'s'})

    def test_cooked_rice_not_dried(self):
        self.assertEqual(keys({'name':'Cooked rice'},[row('c','Cooked rice'),row('d','Dried rice')]),{'c'})

    def test_dried_herb_not_fresh(self):
        self.assertNotIn('f',keys({'name':'Dried basil'},[row('f','Fresh basil'),row('d','Dried basil')]))

    def test_frozen_not_fresh(self):
        self.assertEqual(keys({'name':'Frozen peas'},[row('f','Fresh pea'),row('z','Frozen pea'),row('p','Pea')]),{'z','p'})

    def test_no_arbitrary_prefix_stemming(self):
        self.assertEqual(keys({'name':'Spiced snack'},[row('x','Spice')]),set())

    def test_package_ingredients_list_not_evidence(self):
        self.assertEqual(keys({'name':'Unrecognized product','ingredients':['milk','sugar']},[row('m','Milk'),row('s','Sugar')]),set())

    def test_non_food_and_ambiguous_are_excluded(self):
        cat=[row('a','Rice',classification='equipment'),row('b','Rice',needsSemanticConfirmation=True),row('c','Rice')]
        self.assertEqual(keys({'name':'Rice'},cat),{'c'})

    def test_category_namespace_and_hyphens(self):
        self.assertEqual(keys({'categoryTags':['en:canned-chickpeas']},[row('c','Canned chickpea'),row('d','Dried chickpea')]),{'c'})

    def test_broad_category_not_food_identity(self):
        self.assertEqual(keys({'categories':['vegetables']},[row('v','Vegetables')]),set())

    def test_read_only(self):
        product={'name':'Carrot'};cat=[row('a','Carrot',sourceIngredientIds=['a','legacy'])];before=deepcopy((product,cat))
        result=m.suggest_catalog_matches(product,cat);result[0]['ingredient']['sourceIngredientIds'].append('changed')
        self.assertEqual((product,cat),before)

    def test_confirmation_is_mandatory(self):
        results=m.suggest_catalog_matches({'name':'Rice'},[row('r','Rice')])
        self.assertTrue(results[0]['requiresConfirmation']);self.assertIsNone(m.confident_match(results))

    def test_reasons_and_identity_metadata(self):
        out=m.suggest_catalog_matches({'name':'Carrot'},[row('a','Carrot',sourceIngredientIds=['old']),row('b','Peeled carrot')])
        self.assertEqual(out[0]['reason'],'name_exact');self.assertEqual(out[1]['reason'],'preparation_variant')
        self.assertEqual(out[0]['ingredient']['sourceIngredientIds'],['old'])

    def test_explicit_limit_is_honoured(self):
        cat=[row(str(i),'Rice') for i in range(50)]
        self.assertEqual(len(m.suggest_catalog_matches({'name':'Rice'},cat,limit=40)),40)
        self.assertEqual(m.suggest_catalog_matches({'name':'Rice'},cat,limit=0),[])
        for value in (-1,True,'all'):
            with self.assertRaises(ValueError):m.suggest_catalog_matches({'name':'Rice'},cat,limit=value)

    def test_malformed_inputs_do_not_crash(self):
        for product in (None,[],{}, {'categories':None}):
            self.assertEqual(m.suggest_catalog_matches(product,[None,{},'rice']),[])

    def test_stable_order(self):
        cat=[row('b','Rice'),row('a','Rice')]
        self.assertEqual(m.suggest_catalog_matches({'name':'rice'},cat),m.suggest_catalog_matches({'name':'rice'},cat[::-1]))

    def test_large_catalog_smoke(self):
        cat=[row(str(i),f'Unknown ingredient {i}') for i in range(3000)]+[row('r','Rice')]
        start=time.monotonic();self.assertEqual(keys({'name':'Rice'},cat),{'r'})
        self.assertLess(time.monotonic()-start,10)

if __name__=='__main__':unittest.main()
