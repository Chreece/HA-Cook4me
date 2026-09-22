"""Greek measurement-bearing names: no fixed quantity in a display label.

CI reads the repository's complete locale files. Existing helpers select pure
production functions; only catalog identity resolution is controlled in the
shopping tests. No Home Assistant, network or pricing provider is used.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unicodedata
import unittest

import test_greek_catalog_audit_v191 as previous
import test_greek_catalog_audit_v192 as units

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components' / 'cook4me'
OVERLAY = COMPONENT / 'catalog_ui_locales' / 'zz_el_curated_v193.json'
EXAMPLES = {
    'tablespoon of olive oil': 'Ελαιόλαδο (κ.σ.)',
    'tbsp fresh coriander': 'Φρέσκος κόλιανδρος (κ.σ.)',
    'tablespoon of frozen green pea': 'Κατεψυγμένος αρακάς (κ.σ.)',
    'tbsp plain yogurt': 'Σκέτο γιαούρτι (κ.σ.)',
    'tbsp sugar for fruit': 'Ζάχαρη για τα φρούτα (κ.σ.)',
    'tsp breadcrumbs': 'Τρίμματα ψωμιού (κ.γ.)',
    'tsp turmeric': 'Κουρκουμάς (κ.γ.)',
    'tsp toasted sesame seed': 'Καβουρδισμένο σουσάμι (κ.γ.)',
    'teaspoon of vanilla extract': 'Εκχύλισμα βανίλιας (κ.γ.)',
    'cup of long-grain white rice': 'Λευκό μακρύκοκκο ρύζι (φλιτζάνι)',
}


def prior_labels():
    path = COMPONENT / 'ingredient_ui_labels.json'
    result = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    for path in sorted((COMPONENT / 'catalog_ui_locales').glob('*.json')):
        if path.name >= OVERLAY.name:
            continue  # Compare only preceding layers, not a later audit.
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('schemaVersion') == 1:
            result.setdefault(data['language'], {}).update(data.get('labels', {}))
    return result


class GreekCatalogAuditV193Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.presentation = previous.presentation_functions()
        cls.data = json.loads(OVERLAY.read_text(encoding='utf-8'))
        cls.labels = cls.data['labels']
        cls.before = prior_labels()

    def test_schema_scope_and_no_duplicate_keys(self):
        def unique(pairs):
            out = {}
            for key, value in pairs:
                self.assertNotIn(key, out)
                out[key] = value
            return out
        data = json.loads(OVERLAY.read_text(encoding='utf-8'), object_pairs_hook=unique)
        self.assertEqual(data['schemaVersion'], 1)
        self.assertEqual(data['language'], 'el')
        self.assertEqual(data['audit']['reviewedLabelCount'], 91)
        self.assertEqual(len(data['labels']), 91)
        self.assertEqual(set(data['searchAliases']), set(data['labels']))
        self.assertEqual(set(data), {'schemaVersion', 'language', 'translationSource', 'labels', 'searchAliases', 'audit'})

    def test_every_target_previously_inserted_one(self):
        for key in self.labels:
            with self.subTest(key=key):
                self.assertTrue(self.before['el'][key].startswith('1 '))

    def test_all_keys_reach_the_production_display_path(self):
        for key, value in self.labels.items():
            with self.subTest(key=key):
                self.assertEqual(self.presentation.name_key(self.presentation.clean_name(key)), key)
                self.assertEqual(self.presentation.display_name({'canonicalName': key}, 'el'), value)

    def test_reviewed_examples_use_natural_ingredient_first_greek(self):
        for key, value in EXAMPLES.items():
            with self.subTest(key=key):
                self.assertEqual(self.labels[key], value)

    def test_no_inserted_numbers_and_original_measurement_hint_survives(self):
        counts = {'κ.σ.': 0, 'κ.γ.': 0, 'φλιτζάνι': 0}
        for key, label in self.labels.items():
            with self.subTest(key=key):
                self.assertNotRegex(label, r'[0-9¼½¾⅓⅔⅛⅜⅝⅞]')
                unit = 'φλιτζάνι' if key.startswith('cup of ') else 'κ.γ.' if key.startswith(('tsp ', 'teaspoon of ')) else 'κ.σ.'
                self.assertTrue(label.endswith('(' + unit + ')'))
                counts[unit] += 1
        self.assertEqual(counts, {'κ.σ.': 53, 'κ.γ.': 34, 'φλιτζάνι': 4})

    def test_labels_are_nfc_greek_without_english_fragments(self):
        for key, label in self.labels.items():
            with self.subTest(key=key):
                self.assertEqual(label, unicodedata.normalize('NFC', label))
                self.assertRegex(label, r'^[Α-ΩΆΈΉΊΌΎΏ]')
                self.assertNotRegex(label, r'[A-Za-z\ufffd]')

    def test_old_and_new_wording_and_source_names_remain_searchable(self):
        effective = self.presentation.locale_search_aliases()['el']
        for key, label in self.labels.items():
            with self.subTest(key=key):
                aliases = self.data['searchAliases'][key]
                self.assertEqual(len(aliases), len({value.casefold() for value in aliases}))
                for value in (key, label, self.before['el'][key]):
                    self.assertIn(value, aliases)
                    self.assertIn(value, effective[key])

    def test_previous_aliases_remain_in_the_merged_index(self):
        effective = self.presentation.locale_search_aliases()['el']
        for path in sorted((COMPONENT / 'catalog_ui_locales').glob('*.json')):
            if path.name >= OVERLAY.name:
                continue
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('language') != 'el':
                continue
            for key, values in data.get('searchAliases', {}).items():
                if isinstance(values, str):
                    values = [values]
                if not isinstance(values, list):
                    continue
                normalized = self.presentation.name_key(key)
                for value in values:
                    value = str(value).strip()
                    if value:
                        self.assertIn(value, effective[normalized])

    def test_non_greek_maps_and_untargeted_greek_labels_are_unchanged(self):
        after = self.presentation.labels()
        for language, labels in self.before.items():
            for key, label in labels.items():
                if language == 'el' and key in self.labels:
                    continue
                with self.subTest(language=language, key=key):
                    self.assertEqual(after[language][key], label)

    def test_food_form_and_recipe_role_qualifiers_survive(self):
        expected = {
            'tbsp canned tomato puree': 'κονσέρβας',
            'tablespoon of frozen green pea': 'Κατεψυγμένος',
            'tbsp fresh basil leaf': 'Φρέσκα φύλλα',
            'tbsp plain yogurt': 'Σκέτο',
            'tbsp clarified butter': 'Διαυγασμένο',
            'tsp hot pepper sauce': 'Καυτερή',
            'tsp runny honey': 'Ρευστό',
            'tsp toasted sesame seed': 'Καβουρδισμένο',
            'teaspoon of cooked lobster puree': 'μαγειρεμένου',
            'tablespoon of fish sauce for the meat': 'για το κρέας',
            'tbsp sugar for fruit': 'για τα φρούτα',
            'cup of long-grain white rice': 'Λευκό μακρύκοκκο',
        }
        for key, text in expected.items():
            self.assertIn(text, self.labels[key])
        self.assertNotEqual(self.labels['tbsp tomato sauce'], self.labels['tbsp canned tomato puree'])
        self.assertNotEqual(self.labels['tsp ginger'], self.labels['tsp fresh ginger'])

    def test_explicit_fractions_percentages_and_unknown_measures_are_untouched(self):
        for key in ('one-third teaspoon turmeric', 'one-third vanilla pod', '100% pistachio cream',
                    'heaped tablespoons of wheat flour', 'pinch of salt', 'tbsp', 'tsp'):
            with self.subTest(key=key):
                self.assertNotIn(key, self.labels)
                self.assertEqual(self.presentation.labels()['el'][key], self.before['el'][key])

    def test_display_does_not_rewrite_keys_quantities_or_pricing_evidence(self):
        for amount in (None, 0, 0.5, 1, 2, '1,5'):
            raw = {'key': 'source-key', 'ingredientId': 'source-id',
                   'canonicalName': 'tablespoon of olive oil', 'name': 'Source label',
                   'quantity': amount, 'unit': '', 'unitKey': 'UNIT_12',
                   'weight': {'quantity': 15, 'unit': 'ml'},
                   'priceCategory': 'en:olive-oils', 'priceCatalogMatched': True,
                   'nutrition': {'energy': 12}, 'translations': {'de': 'Olivenöl'}}
            before = deepcopy(raw)
            self.assertEqual(self.presentation.display_name(raw, 'el'), EXAMPLES['tablespoon of olive oil'])
            self.assertEqual(raw, before)

    def test_greek_ui_does_not_replace_german_supermarket_name(self):
        shopping = units.shopping_functions()
        raw = {'key': 'source-key', 'canonicalName': 'tablespoon of olive oil',
               'name': 'tablespoon of olive oil', 'quantity': 2, 'unit': 'tbsp',
               'translations': {'de': 'Olivenöl'}}
        before = deepcopy(raw)
        shopping.shopping_rows.__globals__['release_catalog'] = SimpleNamespace(
            ingredient_display_name=lambda item, language: self.presentation.display_name(item, language),
            ingredient_stock_identities=lambda item: ())
        result = shopping.shopping_rows([raw], 'el', 'DE', supermarket_language='de')[0]
        self.assertEqual(result['uiName'], EXAMPLES['tablespoon of olive oil'])
        self.assertEqual(result['supermarketName'], self.presentation.display_name(raw, 'de'))
        self.assertNotEqual(result['supermarketName'], result['uiName'])
        self.assertEqual(result['supermarketLanguage'], 'de')
        self.assertEqual((result['quantity'], result['unit'], result['displayUnit']), (2, 'tbsp', 'κ.σ.'))
        self.assertEqual(result['key'], raw['key'])
        self.assertEqual(raw, before)

    def test_greek_supermarket_label_can_be_used_with_german_ui(self):
        shopping = units.shopping_functions()
        raw = {'key': 'source-key', 'canonicalName': 'tablespoon of olive oil',
               'name': 'tablespoon of olive oil', 'quantity': '1,5', 'unit': 'tbsp',
               'translations': {'de': 'Olivenöl'}}
        shopping.shopping_rows.__globals__['release_catalog'] = SimpleNamespace(
            ingredient_display_name=lambda item, language: self.presentation.display_name(item, language),
            ingredient_stock_identities=lambda item: ())
        result = shopping.shopping_rows([raw], 'de', 'DE', supermarket_language='el')[0]
        self.assertEqual(result['supermarketName'], EXAMPLES['tablespoon of olive oil'])
        self.assertEqual(result['uiName'], self.presentation.display_name(raw, 'de'))
        self.assertEqual(result['supermarketLanguage'], 'el')
        self.assertEqual((result['quantity'], result['unit'], result['displayUnit']), ('1,5', 'tbsp', 'EL'))

    def test_greek_locale_variants_use_the_same_labels(self):
        for language in ('el', 'el_GR', 'el-GR', 'EL-gr'):
            self.assertEqual(self.presentation.display_name({'canonicalName': 'tsp turmeric'}, language), 'Κουρκουμάς (κ.γ.)')


if __name__ == '__main__':
    unittest.main()
