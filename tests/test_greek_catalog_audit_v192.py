"""Greek terminology and display-only units; CI uses repository catalogs.

Only pure functions are selected from the actual source. Catalog-name lookups
are controlled in shopping-row tests; no network or Home Assistant is used.
"""
import ast
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
from types import SimpleNamespace
import unicodedata
import unittest

import test_greek_catalog_audit_v191 as previous

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components' / 'cook4me'
OVERLAY = COMPONENT / 'catalog_ui_locales' / 'zz_el_curated_v192.json'
EXPECTED = {
 'mixed-color bell pepper':'Πιπεριές διαφόρων χρωμάτων',
 'three-colour bell pepper':'Πιπεριές τριών χρωμάτων',
 'biscuit made with low-calorie chocolate powder + fondant icing decorations':'Μπισκότο με σκόνη σοκολάτας χαμηλών θερμίδων και διακόσμηση ζαχαρόπαστας',
 'cakes made with low-calorie chocolate powder + fondant icing decorations':'Κέικ με σκόνη σοκολάτας χαμηλών θερμίδων και διακόσμηση ζαχαρόπαστας',
 'cookies made with low-calorie chocolate powder plus fondant icing decorations':'Μπισκότα με σκόνη σοκολάτας χαμηλών θερμίδων και διακόσμηση ζαχαρόπαστας',
 'grapefruit segments':'Φετούλες γκρέιπφρουτ',
 'scraped seed from a vanilla pod':'Σπόροι από το εσωτερικό λοβού βανίλιας',
 'bread crumb':'Τρίμματα ψωμιού',
 'white bread crumb':'Τρίμματα λευκού ψωμιού',
 'dried breadcrumbs':'Τρίμματα αποξηραμένου ψωμιού',
 'praline added to the crumb-butter mixture':'Πραλίνα για προσθήκη στο μείγμα τριμμάτων και βουτύρου',
}


def shopping_functions():
    path = COMPONENT / 'shopping_presentation.py'
    names = {'normalize_supermarket_language', '_unit_presentation', '_fold_unit',
             'shopping_display_unit', 'shopping_rows'}
    nodes = [node for node in ast.parse(path.read_text(encoding='utf-8')).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    catalog = SimpleNamespace(
        ingredient_display_name=lambda item, language: {'el':'Ρύζι','de':'Reis','fr':'Riz','en':'Rice'}[language],
        ingredient_stock_identities=lambda item: (),
    )
    namespace = {'__file__':str(path), 'Path':Path, 'json':json, 're':re,
        'unicodedata':unicodedata, 'deepcopy':deepcopy, 'lru_cache':lru_cache,
        'release_catalog':catalog, 'inventory_identity':lambda row: 'k:' + row.get('key', 'rice'),
        'SUPPORTED_SUPERMARKET_LANGUAGES':{'en','de','el','fr'},
        'COUNTRY_LANGUAGE':{'DE':'de','GR':'el','FR':'fr'}}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace)
    return SimpleNamespace(**{name:namespace[name] for name in names})


class GreekCatalogAuditV192Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.presentation = previous.presentation_functions()
        cls.shopping = shopping_functions()

    def test_all_new_labels_reach_production_display(self):
        for key, value in EXPECTED.items():
            with self.subTest(key=key):
                self.assertEqual(self.presentation.name_key(self.presentation.clean_name(key)),key)
                self.assertEqual(self.presentation.display_name({'canonicalName':key},'el'),value)

    def test_overlay_schema_aliases_and_unicode(self):
        def unique_keys(pairs):
            out = {}
            for key,value in pairs:
                self.assertNotIn(key,out)
                out[key] = value
            return out
        data = json.loads(OVERLAY.read_text(encoding='utf-8'),object_pairs_hook=unique_keys)
        self.assertEqual(data['labels'],EXPECTED)
        self.assertEqual(data['schemaVersion'],1)
        self.assertEqual(data['language'],'el')
        self.assertEqual(data['audit']['reviewedLabelCount'],11)
        self.assertEqual(set(data['searchAliases']),set(EXPECTED))
        for key,value in EXPECTED.items():
            with self.subTest(key=key):
                self.assertEqual(value,unicodedata.normalize('NFC',value))
                self.assertNotRegex(value,r'[A-Za-z\ufffd]')
                aliases = data['searchAliases'][key]
                self.assertIn(key,aliases)
                self.assertIn(value,aliases)
                self.assertEqual(len(aliases),len({v.casefold() for v in aliases}))

    def test_low_calorie_qualifier_stays_with_the_powder(self):
        for key in EXPECTED:
            if 'low-calorie' in key:
                self.assertIn('σκόνη σοκολάτας χαμηλών θερμίδων',self.presentation.display_name({'canonicalName':key},'el'))
        self.assertNotIn('Μπισκότο σοκολάτας χαμηλών θερμίδων',EXPECTED.values())

    def test_bread_forms_and_market_languages_stay_separate(self):
        outputs = {self.presentation.display_name({'canonicalName':key},'el') for key in ('bread crumb','white bread crumb','dried breadcrumbs')}
        self.assertEqual(len(outputs),3)
        raw = {'key':'unchanged','canonicalName':'bread crumb','translations':{'de':'Brotkrumen'},'quantity':120,'unit':'g'}
        original = deepcopy(raw)
        expected_de = self.presentation.labels().get('de',{}).get('bread crumb','Brotkrumen')
        self.assertEqual(self.presentation.display_name(raw,'de'),expected_de)
        self.presentation.display_name(raw,'el')
        self.assertEqual(raw,original)

    def test_v191_labels_and_aliases_remain_intact(self):
        for key,value in previous.EXPECTED.items():
            with self.subTest(key=key):
                self.assertEqual(self.presentation.display_name({'canonicalName':key},'el'),value)
        aliases = self.presentation.locale_search_aliases()['el']
        self.assertIn('Αλεσμένα φιστίκια',aliases['ground pistachio'])

    def test_fold_removes_real_whitespace_not_letter_s(self):
        cases = {'s':'s',' T S P ':'tsp','tsp':'tsp',' TBSP ':'tbsp','κ.\u00a0σ.':'κσ','Κ. Γ.':'κγ'}
        for raw,expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.shopping._fold_unit(raw),expected)

    def test_uppercase_and_spaced_units_localize(self):
        cases = {'S':'δευτ.',' T S P ':'κ.γ.','TBSP':'κ.σ.','G':'γρ.','P C S':'τεμ.'}
        for raw,expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.shopping.shopping_display_unit(raw,2,'el'),expected)

    def test_greek_labels_translate_back_to_supermarket_language(self):
        for raw,expected in [('κ. σ.','EL'),('Κ. Γ.','TL'),('γρ.','g'),('κιλά','kg'),('τεμ.','Stück')]:
            with self.subTest(raw=raw):
                self.assertEqual(self.shopping.shopping_display_unit(raw,2,'de'),expected)

    def test_locale_and_unicode_variants(self):
        for language in ('el','el-GR','el_GR','EL-gr'):
            self.assertEqual(self.shopping.shopping_display_unit('TL',1,language),'κ.γ.')
        self.assertEqual(self.shopping.shopping_display_unit(unicodedata.normalize('NFD','λίτρα'),2,'en'),'l')

    def test_decimal_comma_singular_does_not_change_amount(self):
        for unit,expected in [('kg','κιλό'),('l','λίτρο')]:
            self.assertEqual(self.shopping.shopping_display_unit(unit,'1,0','el'),expected)
        self.assertEqual(self.shopping.shopping_display_unit('kg','1,5','el'),'κιλά')

    def test_ambiguous_translated_units_require_a_key(self):
        self.assertEqual(self.shopping.shopping_display_unit('Glas',2,'el'),'Glas')
        self.assertEqual(self.shopping.shopping_display_unit('Stück',2,'el'),'Stück')
        self.assertEqual(self.shopping.shopping_display_unit('Glas',2,'el',unit_key='UNIT_4'),'βάζα')

    def test_stable_unit_key_works_without_a_label(self):
        self.assertEqual(self.shopping.shopping_display_unit('',1,'el',unit_key='UNIT_11'),'κ.γ.')
        self.assertEqual(self.shopping.shopping_display_unit('spoon',1,'el',unit_key='UNIT_12'),'κ.σ.')
        self.assertEqual(self.shopping.shopping_display_unit('',1,'el',unit_key='unknown'),'')

    def test_reviewed_label_overrides_are_respected(self):
        self.assertEqual(self.shopping.shopping_display_unit('čajová lžička',1,'el'),'κ.γ.')

    def test_unknown_units_and_generic_spoons_are_not_converted(self):
        self.assertEqual(self.shopping.shopping_display_unit('mystery package',2,'el'),'mystery package')
        self.assertEqual(self.shopping.shopping_display_unit('spoon',2,'el'),'κουταλιές')
        self.assertEqual(self.shopping.shopping_display_unit('pinch',2,'el'),'πρέζες')

    def test_weight_fallback_is_resolved_before_greek_display(self):
        raw = {'key':'rice','name':'Riz','quantity':None,'weight':{'quantity':120,'unit':'g'}}
        original = deepcopy(raw)
        row = self.shopping.shopping_rows([raw],'el','DE',supermarket_language='de')[0]
        self.assertEqual((row['quantity'],row['unit'],row['displayUnit']),(120,'g','γρ.'))
        self.assertEqual(row['name'],'Ρύζι (Reis; Riz)')
        self.assertEqual(raw,original)

    def test_weight_unit_key_is_available_for_display(self):
        raw = {'key':'rice','name':'Riz','weight':{'quantity':'1,0','unit':'','unitKey':'UNIT_56'}}
        row = self.shopping.shopping_rows([raw],'el','DE',supermarket_language='de')[0]
        self.assertEqual(row['displayUnit'],'κιλό')
        self.assertEqual(row['quantity'],'1,0')
        self.assertEqual(row['unit'],'')

    def test_explicit_amount_and_unit_keep_precedence_over_weight(self):
        raw = {'key':'rice','name':'Riz','quantity':50,'unit':'g','weight':{'quantity':2,'unit':'kg','unitKey':'UNIT_56'}}
        row = self.shopping.shopping_rows([raw],'el','DE',supermarket_language='de')[0]
        self.assertEqual((row['quantity'],row['unit'],row['displayUnit']),(50,'g','γρ.'))

    def test_no_duplicate_language_label_and_text_rows_unchanged(self):
        raw = {'key':'rice','name':'Reis','quantity':1,'unit':'kg'}
        rows = self.shopping.shopping_rows(['free text',raw],'el','DE',supermarket_language='de')
        self.assertEqual(rows[0],'free text')
        self.assertEqual(rows[1]['name'],'Ρύζι (Reis)')
        self.assertEqual(rows[1]['supermarketLanguage'],'de')


if __name__ == '__main__':
    unittest.main()
