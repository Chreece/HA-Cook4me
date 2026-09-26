"""Batch 30: label-guided pastes and fresh/cooked okra identity boundaries."""
from copy import deepcopy
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

MONTHS = [6, 7, 8, 9, 10]
MISO_PASTE = 'local:de:9e2ecd84a99467ced2f7'
RED_MISO = 'local:ja:29e9ba0509fc962d9582'
DARK_MISO = 'local:en:5dc729930b0125b5f3a2'
MISO_SOUP = 'local:ar:a152ac07cac717f74176'
INSTANT_SOUP = 'local:hu:72fad76b836516fc0c1c'
COOKED = 'local:ja:f2862792bd59cf2c5bb5'
BOILED = 'local:ja:25aa0547cccb6cbbcb7b'
FROZEN = 'local:ar:1460261e3dd36afdb4b1'
DRIED = 'local:tr:cd19d4118548e88c0fd9'
WEIKA = 'local:ar:a6ad5ea2ec90e44e3bf1'
NAMES = (
    ('M_FOOD_316', 'Misopaste', 'Πάστα μίσο'),
    (RED_MISO, 'Rote Misopaste', 'Κόκκινη πάστα μίσο'),
    (DARK_MISO, 'Dunkle Misopaste', 'Σκούρα πάστα μίσο'),
    (MISO_SOUP, 'Misosuppe', 'Σούπα μίσο'),
    (INSTANT_SOUP, 'Instant-Misosuppe', 'Μείγμα για στιγμιαία σούπα μίσο'),
    ('M_FOOD_239', 'Harissapaste', 'Πάστα χαρίσα (harissa)'),
    ('M_FOOD_669', 'Okraschoten', 'Μπάμιες'),
    (COOKED, 'Gekochte Okraschoten', 'Βρασμένες μπάμιες'),
    (FROZEN, 'Okraschoten (tiefgekühlt)', 'Κατεψυγμένες μπάμιες'),
    (DRIED, 'Getrocknete Okraschoten', 'Αποξηραμένες μπάμιες'),
    (WEIKA, 'Okrapulver (Weika)', 'Σκόνη αποξηραμένης μπάμιας (weika)'),
)
PASTES = ('Miso', 'Miso paste', 'Miso (for sauce)', 'Miso (for finishing)',
          'Dark miso paste', 'Red miso', 'Red miso (for sauce)', 'Harissa')


class CatalogLifecycle246(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {lang: catalog.ingredient_choices(lang) for lang in ('de', 'el', 'en')}

    def test_pastes_require_package_labels_without_invented_intervals(self):
        for name in PASTES:
            data = profile(name)
            self.assertEqual(data['afterOpening']['status'], 'label_required')
            self.assertEqual(data['seasonality']['status'], 'not_applicable')
            self.assertNotIn('rules', data['afterOpening'])
            for brand, barcode in (('Arche', '4020943134149'), ('Hikari', ''),
                                   ('BioGourmet', '4039057412876'), ('Lacroix', '4009062124224')):
                lot = {'brand': brand, 'barcode': barcode, 'storage': 'fridge', 'openedAt': '2026-09-26'}
                for temperature in (None, 4):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=temperature))
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 7})['consumeBy'], '2026-10-03')
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 7, 'bestBefore': '2026-09-28'})['consumeBy'], '2026-09-28')
        for name in ('Miso soup', 'Instant miso soup mix', 'Homemade miso soup',
                     'Harissa powder', 'Chili pepper', 'Gochujang', 'Soy sauce with miso'):
            self.assertNotIn('profileId', profile(name), name)

    def test_actual_paste_choices_and_manual_opening_stay_supported(self):
        for ident in ('M_FOOD_316', MISO_PASTE, RED_MISO, DARK_MISO, 'M_FOOD_239'):
            expected = 'harissa_paste_label_required' if ident == 'M_FOOD_239' else 'miso_paste_label_required'
            for lang, rows in self.rows.items():
                ingredient = actual_choice(rows, ident)
                self.assertEqual(ingredient['lifecycle']['profileId'], expected, (lang, ident))
                self.assertEqual(opening.opening_rules(ingredient, {'brand': 'Arche', 'barcode': '4020943134149'}), [])
                with self.assertRaises(ValueError):
                    opening.configure_opening(ingredient, {'openingRuleId': 'unverified', 'openingConditionsConfirmed': True})
                with self.assertRaises(ValueError):
                    opening.mark_package_opened(ingredient, {}, {}, opened_on='2026-09-26')
                lot = opening.mark_package_opened(ingredient, {'useWithinDays': 7}, {}, opened_on='2026-09-26')
                self.assertEqual((lot['openedAt'], lot['applyOpeningExpiry']), ('2026-09-26', True))
                self.assertEqual(opening.mark_package_opened(ingredient, lot, {}, opened_on='2026-09-28')['openedAt'], '2026-09-26')
        for ident in ('M_FOOD_316', 'M_FOOD_239', 'M_FOOD_669'):
            for extra in ({'classification': 'equipment'}, {'needsSemanticConfirmation': True}):
                row = {'id': ident} | extra
                lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
                self.assertNotIn('lifecycle', row)

    def test_okra_has_only_the_reviewed_regional_fresh_calendar(self):
        for month in range(1, 13):
            data = catalog.ingredient_seasonal_availability({'ingredientId': 'M_FOOD_669'}, country='GR', month=month)
            self.assertEqual((data['months'], data['sourceRegion'], data['basis'], data['status']),
                (MONTHS, 'Imathia', 'outdoor_harvest', 'in_season' if month in MONTHS else 'unknown'))
            for country in ('DE', 'AT', ''):
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': 'M_FOOD_669'}, country=country, month=month)['status'], 'unknown')
        for name in ('Okra', 'Okra, cut diagonally in half', 'Okra, rubbed with salt, washed and cut 1 cm wide', 'Okra, trimmed'):
            self.assertEqual(profile(name)['profileId'], 'season_okra_gr')
            self.assertEqual(profile(name)['afterOpening']['status'], 'unknown')
        for ident in (COOKED, BOILED, FROZEN, DRIED, WEIKA):
            self.assertNotIn('profileId', catalog.ingredient_lifecycle_profile({'ingredientId': ident}))
            for lang, rows in self.rows.items():
                choice = actual_choice(rows, ident)
                self.assertNotIn('lifecycle', choice, (lang, ident))
                self.assertNotEqual(choice['id'], actual_choice(rows, 'M_FOOD_669')['id'], (lang, ident))

    def test_cooked_override_preserves_raw_identity_nutrients_and_search_names(self):
        raw = {'id': COOKED, 'canonicalName': 'Okra, salt-boiled and finely chopped (for finishing)',
               'translations': {'ja': 'オクラ(仕上げ用 塩ゆでしてみじん切り)'},
               'nutrition': {'protein': 1.9}, 'amount': 40, 'unit': 'g'}
        original = deepcopy(raw)
        presented = catalog._core._presentation.presentation_ingredient(raw)
        self.assertEqual(raw, original)
        for key in ('id', 'nutrition', 'amount', 'unit'):
            self.assertEqual(presented[key], original[key])
        self.assertEqual(presented['canonicalName'], 'Boiled okra')
        self.assertIn(original['canonicalName'], presented['aliases']['en'])
        for lang, rows in self.rows.items():
            self.assertEqual(actual_choice(rows, COOKED)['id'], actual_choice(rows, BOILED)['id'])
            self.assertIn(original['canonicalName'], actual_choice(rows, COOKED)['searchAliases'])
        self.assertEqual(catalog.ingredient_display_name({'ingredientId': COOKED}, 'el'), 'Βρασμένες μπάμιες')

    def test_supermarket_names_deduplicate_only_equivalent_forms(self):
        for ident, german, greek in NAMES:
            for lang, name in (('de', german), ('el', greek)):
                self.assertEqual(actual_choice(self.rows[lang], ident)['name'], name)
        for lang in ('de', 'el'):
            rows = self.rows[lang]
            self.assertEqual(actual_choice(rows, 'M_FOOD_316')['id'], actual_choice(rows, MISO_PASTE)['id'])
            for ident in (RED_MISO, DARK_MISO, MISO_SOUP, INSTANT_SOUP):
                self.assertNotEqual(actual_choice(rows, 'M_FOOD_316')['id'], actual_choice(rows, ident)['id'])
        for lang, query, ident in (('de', 'Miso-Paste', 'M_FOOD_316'), ('de', 'Bamya', 'M_FOOD_669'),
                ('de', 'Harissa', 'M_FOOD_239'), ('el', 'μπάμια', 'M_FOOD_669'),
                ('el', 'πάστα καυτερής πιπεριάς', 'M_FOOD_239')):
            actual_choice(catalog.ingredient_choices(lang, query=query), ident)


if __name__ == '__main__':
    unittest.main()
