"""Batch 29: exact edamame/bamboo packages and a regional avocado calendar."""
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

PACKAGES = (
    ('Edamame', 'M_FOOD_589', 'dmBio', '4066447954203', 'dmbio_edamame_210', 3, 4, ('transferred_to_nonmetal_container',)),
    ('Bamboo shoot', 'M_FOOD_404', "Shan'shi", '9120012040076', 'shanshi_bamboo_330', 2, 2, ()),
)
MONTHS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12]
FROZEN = 'local:it:193160561cb022adc657'
CANNED = 'local:bg:e6f939805db91fac44fb'
BOILED = 'local:ja:af3abe173f1e16f9f584'
NAMES = (
    ('M_FOOD_24', 'Avocado', 'Αβοκάντο'),
    ('M_FOOD_589', 'Edamame', 'Ενταμάμε (edamame)'),
    ('M_FOOD_404', 'Bambussprossen', 'Βλαστοί μπαμπού'),
    (CANNED, 'Bambussprossen (Konserve)', 'Βλαστοί μπαμπού κονσέρβας'),
    (FROZEN, 'Edamame (tiefgekühlt)', 'Κατεψυγμένο ενταμάμε (edamame)'),
    (BOILED, 'Gekochte Bambussprossen', 'Βρασμένοι βλαστοί μπαμπού'),
)


class CatalogLifecycle245(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {lang: catalog.ingredient_choices(lang) for lang in ('el', 'de', 'en')}

    def test_exact_products_keep_ranges_conditions_and_earlier_dates(self):
        for name, ident, brand, code, rule, low, high, conditions in PACKAGES:
            data = profile(name)
            lot = {'brand': brand, 'barcode': code, 'storage': 'fridge', 'openedAt': '2026-09-26'}
            for temperature in (0, 4):
                found = lifecycle.opening_window(data, lot, temperature_c=temperature, confirmed_conditions=conditions)
                self.assertEqual((found['ruleId'], found['daysMin'], found['daysMax'], found['remindOn'], found['consumeBy']),
                    (rule, low, high, f'2026-09-{26 + low}', f'2026-09-{26 + high}'))
                self.assertFalse(found['safetyGuarantee'])
            for changes, temperature in (({'brand': 'Other'}, 4), ({'brand': None}, 4),
                    ({'barcode': None}, 4), ({'barcode': code[:-1] + 'X'}, 4),
                    ({'openedAt': None}, 4), ({'storage': 'pantry'}, 4), ({'storage': 'freezer'}, 4),
                    ({}, None), ({}, -1), ({}, 4.1)):
                self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes,
                    temperature_c=temperature, confirmed_conditions=conditions))
            if conditions:
                for wrong in ((), ('transferred_to_container',)):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=wrong))
            self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-27'},
                temperature_c=4, confirmed_conditions=conditions)['consumeBy'], '2026-09-27')
            self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 1})['consumeBy'], '2026-09-27')
            self.assertEqual(opening.opening_rules({'ingredientId': ident}, lot)[0]['id'], rule)

    def test_frozen_prepared_and_unrelated_foods_do_not_borrow_package_clocks(self):
        excluded = ('Frozen edamame', 'Frozen edamame beans', 'Frozen edamame pods', 'Edamame pods (frozen)',
                    'Soybeans', 'Black beans', 'Soy milk', 'Bamboo fibre',
                    'Boiled bamboo shoots, cut into bite-size pieces', 'Avocado', 'Avocado oil')
        for name, _, brand, code, _, _, _, conditions in PACKAGES:
            lot = {'brand': brand, 'barcode': code, 'storage': 'fridge', 'openedAt': '2026-09-26'}
            for other in excluded + tuple(p[0] for p in PACKAGES if p[0] != name):
                self.assertNotIn('consumeBy', lifecycle.opening_window(profile(other), lot,
                    temperature_c=4, confirmed_conditions=conditions), (name, other))
        # A six-jar case GTIN is not the consumer package.
        self.assertEqual(opening.opening_rules({'ingredientId': 'M_FOOD_404'},
            {'brand': "Shan'shi", 'barcode': '9002600274318'}), [])
        for name in ('Bamboo shoots', 'Bamboo shoots, drained', 'Canned bamboo shoots', 'Canned bamboo shoots, drained'):
            data = profile(name)
            self.assertEqual(data['afterOpening']['rules'][0]['productBarcodes'], ['9120012040076'])
            self.assertNotIn('consumeBy', lifecycle.opening_window(data,
                {'brand': "Shan'shi", 'storage': 'fridge', 'openedAt': '2026-09-26'}, temperature_c=4))

    def test_actual_choices_and_opening_editor_preserve_identity_and_confirmation(self):
        expected = {'M_FOOD_24': 'season_avocado_gr', 'M_FOOD_589': 'edamame_product_guidance',
                    'M_FOOD_662': 'edamame_product_guidance', 'M_FOOD_404': 'bamboo_shoots_product_guidance',
                    'M_FOOD_735': 'bamboo_shoots_product_guidance', CANNED: 'canned_bamboo_shoots_product_guidance'}
        for ident, key in expected.items():
            for lang, rows in self.rows.items():
                self.assertEqual(actual_choice(rows, ident).get('lifecycle', {}).get('profileId'), key, (lang, ident))
            for extra in ({'classification': 'equipment'}, {'needsSemanticConfirmation': True}):
                row = {'id': ident} | extra
                lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
                self.assertNotIn('lifecycle', row)
        for _, ident, brand, code, rule, _, high, _ in PACKAGES:
            for lang, rows in self.rows.items():
                ingredient = actual_choice(rows, ident)
                lot = {'brand': brand, 'barcode': code, 'openingRuleId': rule}
                self.assertEqual([r['id'] for r in opening.opening_rules(ingredient, lot)], [rule], lang)
                with self.assertRaises(ValueError):
                    opening.configure_opening(ingredient, lot)
                configured = opening.configure_opening(ingredient, lot | {'openingConditionsConfirmed': True})
                self.assertEqual((configured['useWithinDays'], configured['storage']), (high, 'fridge'))
                self.assertNotIn('openedAt', configured)
                opened = opening.mark_package_opened(ingredient, configured | {'openedAt': '2026-09-24'}, {}, opened_on='2026-09-26')
                self.assertEqual(opened['openedAt'], '2026-09-24')
        for ident in (FROZEN, BOILED, 'local:pl:38bd7ec91183cbdbfdfa'):
            self.assertNotIn('profileId', catalog.ingredient_lifecycle_profile({'ingredientId': ident}))

    def test_avocado_calendar_is_regional_and_processed_forms_stay_unknown(self):
        for month in range(1, 13):
            data = catalog.ingredient_seasonal_availability({'ingredientId': 'M_FOOD_24'}, country='GR', month=month)
            self.assertEqual((data['months'], data['sourceRegion'], data['status']),
                (MONTHS, 'GR-M', 'in_season' if month in MONTHS else 'unknown'))
            for country in ('DE', 'AT', ''):
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': 'M_FOOD_24'}, country=country, month=month)['status'], 'unknown')
        for name in ('Avocado oil', 'Frozen avocado', 'Guacamole', 'Avocado, peeled and diced, mixed with lemon juice'):
            self.assertNotEqual(profile(name)['seasonality']['status'], 'reviewed', name)
        for name in ('Avocado, diced', 'Diced avocado', 'Avocados, diced', 'Avocado, sliced lengthwise 5 mm thick'):
            self.assertEqual(profile(name)['profileId'], 'season_avocado_gr')
        for name in ('Edamame', 'Bamboo shoot'):
            self.assertEqual(profile(name)['seasonality']['status'], 'unknown')
        self.assertEqual(profile('Canned bamboo shoots')['seasonality']['status'], 'not_applicable')

    def test_supermarket_names_search_and_duplicate_grouping(self):
        for ident, german, greek in NAMES:
            for lang, name in (('de', german), ('el', greek)):
                self.assertEqual(actual_choice(self.rows[lang], ident)['name'], name)
        for lang in ('de', 'el'):
            rows = self.rows[lang]
            self.assertEqual(actual_choice(rows, 'M_FOOD_404')['id'], actual_choice(rows, 'M_FOOD_735')['id'])
            self.assertEqual(actual_choice(rows, 'M_FOOD_589')['id'], actual_choice(rows, 'local:en:9d8b9ecfee09b251cd9f')['id'])
            self.assertNotEqual(actual_choice(rows, 'M_FOOD_589')['id'], actual_choice(rows, FROZEN)['id'])
            for ident in (CANNED, BOILED):
                self.assertNotEqual(actual_choice(rows, 'M_FOOD_404')['id'], actual_choice(rows, ident)['id'])
        for query, ident in (('junge Sojabohnen', 'M_FOOD_589'), ('Bambustriebe', 'M_FOOD_404'),
                             ('Bambussprossen im Glas', CANNED), ('Avocados', 'M_FOOD_24')):
            actual_choice(catalog.ingredient_choices('de', query=query), ident)
        actual_choice(catalog.ingredient_choices('el', query='φασόλια ενταμάμε'), 'M_FOOD_589')


if __name__ == '__main__':
    unittest.main()
