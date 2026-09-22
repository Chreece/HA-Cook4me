"""Exact-key Greek overlay regressions against production presentation code.

AST selection isolates unchanged pure production functions from optional imports.
CI reads the complete repository label maps, not the sampled development data.
"""
from __future__ import annotations
import ast
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import re
from types import SimpleNamespace
import unicodedata
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components' / 'cook4me'
OVERLAY_NAME = 'zz_el_curated_v191.json'
OVERLAY = COMPONENT / 'catalog_ui_locales' / OVERLAY_NAME
EXPECTED = {
    '100% pistachio cream': 'Κρέμα κελυφωτού φιστικιού 100%',
    'fresh unsalted pistachio': 'Φρέσκα ανάλατα κελυφωτά φιστίκια',
    'ground pistachio': 'Αλεσμένα κελυφωτά φιστίκια',
    'pistachio': 'Κελυφωτά φιστίκια',
    'pistachio cream': 'Κρέμα κελυφωτού φιστικιού',
    'pistachio flavoring': 'Άρωμα κελυφωτού φιστικιού',
    'pistachio flavouring': 'Άρωμα κελυφωτού φιστικιού',
    'pistachio kernels': 'Ψίχα κελυφωτού φιστικιού',
    'pistachio paste': 'Πάστα κελυφωτού φιστικιού',
    'roasted pistachio': 'Καβουρδισμένα κελυφωτά φιστίκια',
    'shelled pistachio': 'Ψίχα κελυφωτού φιστικιού',
    'almond milk': 'Ρόφημα αμυγδάλου',
    'hazelnut milk': 'Ρόφημα φουντουκιού',
    'plant milk': 'Φυτικό ρόφημα',
    'plant-based milk': 'Φυτικό ρόφημα',
    'unsweetened condensed milk': 'Μη ζαχαρούχο συμπυκνωμένο γάλα (εβαπορέ)',
    'unsweetened hazelnut puree': 'Άγλυκος πουρές φουντουκιού',
    'unsweetened hazelnut spread': 'Άγλυκο άλειμμα φουντουκιού',
    'unsweetened soy milk': 'Άγλυκο ρόφημα σόγιας',
    'corn on the cob': 'Καλαμπόκι στον σπάδικα',
    'raw corn on the cob': 'Ωμό καλαμπόκι στον σπάδικα',
    'raw corn cobs': 'Ωμά καλαμπόκια στον σπάδικα',
    'sugar for caramel': 'Ζάχαρη για καραμέλα',
    'sugar for cream': 'Ζάχαρη για την κρέμα',
    'sugar for syrup': 'Ζάχαρη για το σιρόπι',
    'sugar for the caramel': 'Ζάχαρη για την καραμέλα',
    'sugar for the cream': 'Ζάχαρη για την κρέμα',
    'sugar for the fruit': 'Ζάχαρη για τα φρούτα',
    'any seed': 'Σπόροι της επιλογής σας',
    'clementine segments': 'Φετούλες κλημεντίνης',
    'mustard seed and cumin seed': 'Σπόροι μουστάρδας και κύμινου',
    'pinches of fresh thyme leaf': 'Πρέζες φρέσκων φύλλων θυμαριού',
    'shelled walnut': 'Καρυδόψιχα',
}


def presentation_functions():
    path = COMPONENT / 'catalog_presentation.py'
    functions = {'norm', 'name_key', 'clean_name', 'labels',
                 'locale_search_aliases', 'display_name', 'excluded_names'}
    constants = {'_PLURALS', '_AMOUNT', '_UNITS', '_PREP'}
    nodes = []
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in constants for target in node.targets
        ):
            nodes.append(node)
    found = {n.name for n in nodes if isinstance(n, ast.FunctionDef)}
    if found != functions:
        raise RuntimeError('Production presentation contract changed; review this audit')
    namespace = {'__file__': str(path), 'Path': Path, 'lru_cache': lru_cache,
                 'json': json, 're': re, 'unicodedata': unicodedata}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return SimpleNamespace(**{name: namespace[name] for name in functions})


def previous_layers():
    path = COMPONENT / 'ingredient_ui_labels.json'
    result = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    aliases, excluded = {}, set()
    for path in sorted((COMPONENT / 'catalog_ui_locales').glob('*.json')):
        if path.name == OVERLAY_NAME:
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        excluded.update(data.get('excludedNames', []))
        if data.get('schemaVersion') != 1:
            continue
        language = data.get('language', '')
        result.setdefault(language, {}).update(data.get('labels', {}))
        for key, values in data.get('searchAliases', {}).items():
            if isinstance(values, str):
                values = [values]
            if isinstance(values, list):
                aliases.setdefault(language, {}).setdefault(key, []).extend(values)
    return result, aliases, excluded


class GreekCatalogAuditV191Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.presentation = presentation_functions()
        cls.before, cls.before_aliases, cls.before_excluded = previous_layers()

    def test_effective_labels_match_all_reviewed_entries(self):
        for key, expected in EXPECTED.items():
            with self.subTest(ingredient=key):
                self.assertEqual(self.presentation.display_name({'canonicalName': key}, 'el'), expected)

    def test_all_keys_are_reachable_after_production_normalization(self):
        for key in EXPECTED:
            with self.subTest(key=key):
                self.assertEqual(self.presentation.name_key(self.presentation.clean_name(key)), key)

    def test_overlay_has_no_duplicate_json_keys(self):
        def reject_duplicate_keys(pairs):
            result = {}
            for key, value in pairs:
                self.assertNotIn(key, result, f'duplicate JSON key: {key}')
                result[key] = value
            return result
        json.loads(OVERLAY.read_text(encoding='utf-8'), object_pairs_hook=reject_duplicate_keys)

    def test_schema_and_review_count(self):
        data = json.loads(OVERLAY.read_text(encoding='utf-8'))
        self.assertEqual(data['schemaVersion'], 1)
        self.assertEqual(data['language'], 'el')
        self.assertEqual(data['labels'], EXPECTED)
        self.assertEqual(data['audit']['reviewedLabelCount'], len(EXPECTED))
        self.assertEqual(set(data['searchAliases']), set(EXPECTED))

    def test_labels_are_nfc_greek_without_english_fragments(self):
        for key, label in EXPECTED.items():
            with self.subTest(key=key):
                self.assertEqual(label, unicodedata.normalize('NFC', label))
                self.assertRegex(label, r'[Α-Ωα-ω]')
                self.assertNotRegex(label, r'[A-Za-z]')
                self.assertNotIn('\ufffd', label)

    def test_pistachio_variants_stay_explicit_without_added_origin(self):
        for key in EXPECTED:
            if 'pistachio' in key:
                label = self.presentation.display_name({'canonicalName': key}, 'el')
                with self.subTest(key=key):
                    self.assertIn('κελυφ', label.casefold())
                    self.assertNotIn('αιγ', self.presentation.norm(label))
                    self.assertNotIn('αραπ', self.presentation.norm(label))

    def test_unsweetened_labels_do_not_claim_sugar_free(self):
        for key in EXPECTED:
            if key.startswith('unsweetened '):
                label = self.presentation.display_name({'canonicalName': key}, 'el')
                with self.subTest(key=key):
                    self.assertNotIn('χωρις ζαχαρη', self.presentation.norm(label))
                    self.assertTrue('αγλυκ' in self.presentation.norm(label) or 'μη ζαχαρουχο' in self.presentation.norm(label))

    def test_raw_and_roasted_qualifiers_survive(self):
        cases = {'raw corn on the cob': 'Ωμό', 'raw corn cobs': 'Ωμά',
                 'roasted pistachio': 'Καβουρδισμένα',
                 'fresh unsalted pistachio': 'Φρέσκα ανάλατα'}
        for key, qualifier in cases.items():
            with self.subTest(key=key):
                self.assertIn(qualifier, self.presentation.display_name({'canonicalName': key}, 'el'))

    def test_cream_paste_flavouring_and_kernels_are_not_collapsed(self):
        keys = ('pistachio cream', 'pistachio paste', 'pistachio flavouring', 'pistachio kernels')
        self.assertEqual(len({self.presentation.display_name({'canonicalName': key}, 'el') for key in keys}), len(keys))

    def test_sugar_recipe_roles_remain_visible(self):
        cases = {'sugar for caramel': 'καραμέλα', 'sugar for cream': 'κρέμα',
                 'sugar for syrup': 'σιρόπι', 'sugar for the fruit': 'φρούτα'}
        for key, role in cases.items():
            with self.subTest(key=key):
                self.assertIn(role, self.presentation.display_name({'canonicalName': key}, 'el'))

    def test_choice_of_seed_is_not_a_required_mixture(self):
        label = self.presentation.display_name({'canonicalName': 'any seed'}, 'el')
        self.assertIn('επιλογής', label)
        self.assertNotIn('ανάμεικτ', label.casefold())

    def test_entire_non_greek_label_maps_are_unchanged(self):
        after = self.presentation.labels()
        for language in (set(self.before) | set(after)) - {'el'}:
            with self.subTest(language=language):
                self.assertEqual(after.get(language, {}), self.before.get(language, {}))

    def test_all_untargeted_greek_labels_are_unchanged(self):
        after = self.presentation.labels().get('el', {})
        for key, value in self.before.get('el', {}).items():
            if key not in EXPECTED:
                with self.subTest(key=key):
                    self.assertEqual(after.get(key), value)

    def test_original_and_new_names_are_search_aliases(self):
        aliases = self.presentation.locale_search_aliases().get('el', {})
        for key, value in EXPECTED.items():
            with self.subTest(key=key):
                current = set(aliases.get(key, ()))
                self.assertIn(key, current)
                self.assertIn(value, current)

    def test_all_previous_search_aliases_are_retained(self):
        after = self.presentation.locale_search_aliases()
        for language, entries in self.before_aliases.items():
            for key, values in entries.items():
                normal = self.presentation.name_key(key)
                for value in values:
                    text = str(value).strip()
                    if text:
                        with self.subTest(language=language, key=key, alias=text):
                            self.assertIn(text, after.get(language, {}).get(normal, ()))

    def test_legacy_pistachio_spelling_remains_searchable(self):
        aliases = self.presentation.locale_search_aliases()['el']
        self.assertIn('Αλεσμένα φιστίκια', aliases['ground pistachio'])
        self.assertIn('Αλεσμένα κελυφωτά φυστίκια', aliases['ground pistachio'])

    def test_plural_keys_and_greek_locale_variants(self):
        for name in ('ground pistachios', 'GROUND PISTACHIOS'):
            for language in ('el', 'el-GR', 'el_GR', 'EL-gr'):
                with self.subTest(name=name, language=language):
                    self.assertEqual(self.presentation.display_name({'canonicalName': name}, language), EXPECTED['ground pistachio'])

    def test_no_ingredient_recipe_or_nutrient_mutation(self):
        for key in EXPECTED:
            raw = {'key': 'test:' + key, 'ingredientId': 'original:' + key,
                   'canonicalName': key, 'name': 'Original recipe label',
                   'quantity': 1.5, 'unit': 'g', 'unitKey': 'UNIT_27',
                   'priceCategory': 'test:category', 'nutrition': {'sample': 12.3},
                   'translations': {'de': 'Beispielzutat'}}
            original = deepcopy(raw)
            self.presentation.display_name(raw, 'el')
            self.presentation.display_name(raw, 'de')
            with self.subTest(key=key):
                self.assertEqual(raw, original)

    def test_overlay_cannot_supply_prices_or_nutrition(self):
        data = json.loads(OVERLAY.read_text(encoding='utf-8'))
        self.assertEqual(set(data), {'schemaVersion', 'language', 'translationSource', 'labels', 'searchAliases', 'audit'})
        self.assertEqual(self.presentation.excluded_names(), self.before_excluded)

    def test_german_source_translation_does_not_become_greek(self):
        raw = {'canonicalName': 'ground pistachio', 'translations': {'de': 'Gemahlene Pistazien'}}
        expected = self.before.get('de', {}).get('ground pistachio', 'Gemahlene Pistazien')
        self.assertEqual(self.presentation.display_name(raw, 'de'), expected)
        self.assertEqual(self.presentation.display_name(raw, 'el'), EXPECTED['ground pistachio'])

    def test_unknown_ingredient_does_not_borrow_nut_label(self):
        raw = {'canonicalName': 'v191 unknown pistachio composite',
               'translations': {'el': 'Άγνωστο σύνθετο υλικό δοκιμής'}}
        self.assertEqual(self.presentation.display_name(raw, 'el'), 'Άγνωστο σύνθετο υλικό δοκιμής')

    def test_every_overlay_alias_is_unique_ignoring_case(self):
        data = json.loads(OVERLAY.read_text(encoding='utf-8'))
        for key, values in data['searchAliases'].items():
            with self.subTest(key=key):
                self.assertEqual(len(values), len({v.casefold() for v in values}))


if __name__ == '__main__':
    unittest.main()
