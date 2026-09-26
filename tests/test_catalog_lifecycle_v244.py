"""Batch 28: stock package clocks, dry-form exclusions and edible pumpkin names."""
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

PACKAGES = (
    ('Beef stock', 'M_FOOD_54', '4009062800395', 'lacroix_beef_stock_400', 'beef_stock_product_guidance'),
    ('Fish stock', 'M_FOOD_214', '4009062800203', 'lacroix_fish_stock_400', 'fish_stock_product_guidance'),
    ('Chicken stock', 'M_FOOD_209', '4009062801200', 'lacroix_bio_chicken_stock_300', 'chicken_stock_product_guidance'),
    ('Vegetable stock', 'M_FOOD_55', '4009062801309', 'lacroix_bio_vegetable_stock_300', 'vegetable_stock_product_guidance'),
)
DRY_IDS = ('M_FOOD_50', 'M_FOOD_51', 'M_FOOD_52', 'M_FOOD_53')
NAMES = (
    ('M_FOOD_399', 'Kürbis', ('Speisekürbis',)),
    ('M_FOOD_54', 'Rinderbrühe', ('Rinderfond', 'Rinderbouillon')),
    ('M_FOOD_214', 'Fischbrühe', ('Fischfond',)),
    ('M_FOOD_209', 'Hühnerbrühe', ('Hühnerfond', 'Geflügelfond')),
    ('M_FOOD_55', 'Gemüsebrühe', ('Gemüsefond', 'Gemüsebouillon')),
    ('M_FOOD_49', 'Brühe', ('Bouillon',)),
    ('M_FOOD_50', 'Brühwürfel', ('Bouillonwürfel',)),
    ('M_FOOD_52', 'Gemüsebrühwürfel', ('Gemüsebouillonwürfel',)),
)


class CatalogLifecycle244(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {lang: catalog.ingredient_choices(lang) for lang in ('el', 'de', 'en')}

    def test_exact_package_clocks_need_brand_barcode_opening_and_refrigeration(self):
        for name, ident, code, rule, _ in PACKAGES:
            data = profile(name)
            lot = {'brand': 'Lacroix', 'barcode': code, 'storage': 'fridge', 'openedAt': '2026-09-26'}
            for temperature in (0, 4):
                found = lifecycle.opening_window(data, lot, temperature_c=temperature)
                self.assertEqual((found['ruleId'], found['daysMin'], found['daysMax'], found['consumeBy']),
                                 (rule, 2, 2, '2026-09-28'))
                self.assertFalse(found['safetyGuarantee'])
            for changes, temperature in (({'brand': 'Other'}, 4), ({'brand': None}, 4),
                    ({'barcode': None}, 4), ({'barcode': code[:-1] + 'X'}, 4),
                    ({'openedAt': None}, 4), ({'storage': 'pantry'}, 4), ({'storage': 'freezer'}, 4),
                    ({}, None), ({}, -1), ({}, 4.1)):
                self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes, temperature_c=temperature))
            self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-27'}, temperature_c=4)['consumeBy'], '2026-09-27')
            self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 1})['consumeBy'], '2026-09-27')
            self.assertEqual(lifecycle.opening_window(profile('Stock'), lot, temperature_c=4)['ruleId'], rule)
            self.assertEqual(opening.opening_rules({'ingredientId': ident}, lot)[0]['id'], rule)

    def test_flavours_prepared_broths_cubes_and_pastes_cannot_borrow_a_package_rule(self):
        excluded = ('Chicken stock cube', 'Chicken stock powder', 'Chicken stock granules',
                    'Vegetable stock cube', 'Stock cube', 'Fish stock pot', 'Beef stock paste (or beef stock powder)',
                    'Hot chicken stock', 'Boiling chicken stock', 'Homemade chicken stock',
                    'Salt-free vegetable stock', 'Unsalted vegetable stock', 'Veal stock',
                    'Meat stock', 'Chicken or vegetable stock', 'Water or stock', 'Chicken Stock & White Wine - Each')
        for name, _, code, _, _ in PACKAGES:
            lot = {'brand': 'Lacroix', 'barcode': code, 'storage': 'fridge', 'openedAt': '2026-09-26'}
            others = set(excluded) | {p[0] for p in PACKAGES if p[0] != name}
            for other in others:
                self.assertNotIn('consumeBy', lifecycle.opening_window(profile(other), lot, temperature_c=4), (name, other))
        # These unreviewed sizes and case codes must not select a nearby package.
        for code in ('4009062801248', '4009062961805', '4009062802702', '4009062802900'):
            self.assertEqual(opening.opening_rules({'ingredientId': 'M_FOOD_49'}, {'brand': 'Lacroix', 'barcode': code}), [])
        # The other provider chicken row has conflicting cube/powder translations.
        self.assertNotIn('profileId', catalog.ingredient_lifecycle_profile({'ingredientId': 'M_FOOD_56'}))

    def test_dry_stock_has_label_guidance_without_a_liquid_stock_countdown(self):
        for ident in DRY_IDS:
            data = catalog.ingredient_lifecycle_profile({'ingredientId': ident})
            self.assertEqual(data['afterOpening']['status'], 'label_required')
            self.assertNotIn('rules', data['afterOpening'])
            for _, _, code, _, _ in PACKAGES:
                self.assertEqual(opening.opening_rules({'ingredientId': ident}, {'brand': 'Lacroix', 'barcode': code}), [])
        for name, code in (('Vegetable stock cube', '4066447992373'), ('Chicken stock powder', '4066447523027')):
            data = profile(name)
            lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-26', 'storage': 'fridge'}
            self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
            self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 7})['consumeBy'], '2026-10-03')

    def test_real_catalog_choices_keep_profiles_and_require_opening_confirmation(self):
        expected = {p[1]: p[4] for p in PACKAGES} | {ident: 'dry_stock_label_required' for ident in DRY_IDS}
        expected |= {'M_FOOD_49': 'stock_product_guidance', 'M_FOOD_399': 'season_pumpkin'}
        for ident, key in expected.items():
            for lang, rows in self.rows.items():
                self.assertEqual(actual_choice(rows, ident).get('lifecycle', {}).get('profileId'), key, (lang, ident))
            for extra in ({'classification': 'equipment'}, {'needsSemanticConfirmation': True}):
                row = {'id': ident} | extra
                lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
                self.assertNotIn('lifecycle', row)
        for _, ident, code, rule, _ in PACKAGES:
            for lang, rows in self.rows.items():
                ingredient = actual_choice(rows, ident)
                lot = {'brand': 'Lacroix', 'barcode': code, 'openingRuleId': rule}
                self.assertEqual([r['id'] for r in opening.opening_rules(ingredient, lot)], [rule], lang)
                with self.assertRaises(ValueError):
                    opening.configure_opening(ingredient, lot)
                configured = opening.configure_opening(ingredient, lot | {'openingConditionsConfirmed': True})
                self.assertEqual((configured['useWithinDays'], configured['storage']), (2, 'fridge'))
                self.assertNotIn('openedAt', configured)
                opened = opening.mark_package_opened(ingredient, configured | {'openedAt': '2026-09-24'}, {}, opened_on='2026-09-26')
                self.assertEqual(opened['openedAt'], '2026-09-24')

    def test_pumpkin_keeps_its_regional_calendar_and_processed_forms_stay_separate(self):
        for month in range(1, 13):
            data = catalog.ingredient_seasonal_availability({'ingredientId': 'M_FOOD_399'}, country='DE', month=month)
            self.assertEqual((data['months'], data['sourceRegion'], data['status']),
                             ([8, 9, 10, 11, 12], 'DE-HE', 'in_season' if month >= 8 else 'unknown'))
            self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': 'M_FOOD_399'}, country='GR', month=month)['status'], 'unknown')
        for name in ('Pumpkin seed oil', 'Pumpkin seeds', 'Frozen pumpkin', 'Canned pumpkin', 'Pumpkin jam', 'Ornamental pumpkin'):
            self.assertNotEqual(profile(name)['seasonality']['status'], 'reviewed', name)

    def test_german_supermarket_names_search_and_greek_food_identities(self):
        for ident, name, aliases in NAMES:
            self.assertEqual(actual_choice(self.rows['de'], ident)['name'], name)
            for alias in aliases:
                self.assertEqual(actual_choice(catalog.ingredient_choices('de', query=alias), ident)['name'], name)
        self.assertEqual(actual_choice(self.rows['el'], 'M_FOOD_399')['name'], 'Κολοκύθα')
        self.assertEqual(actual_choice(self.rows['el'], 'M_FOOD_145')['name'], 'Κολοκύθι ή κολοκύθα')
        for lang, rows in self.rows.items():
            self.assertNotEqual(actual_choice(rows, 'M_FOOD_399')['id'], actual_choice(rows, 'M_FOOD_145')['id'], lang)
            self.assertNotIn('lifecycle', actual_choice(rows, 'M_FOOD_145'), lang)
            for liquid, cube in (('M_FOOD_49', 'M_FOOD_50'), ('M_FOOD_54', 'M_FOOD_51'),
                                 ('M_FOOD_55', 'M_FOOD_52'), ('M_FOOD_209', 'M_FOOD_53')):
                self.assertNotEqual(actual_choice(rows, liquid)['id'], actual_choice(rows, cube)['id'], lang)


if __name__ == '__main__':
    unittest.main()
