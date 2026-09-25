"""Verified dmBio cans/creams and reviewed official catalog propagation."""
from datetime import date, timedelta
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile

NONMETAL = ('transferred_to_nonmetal_container',)
PACKAGES = (
    ('Canned red kidney beans', '4067796187038', 'dmbio_kidney_beans', 3, 4, NONMETAL),
    ('White beans (canned)', '4067796187052', 'dmbio_cannellini_beans', 3, 4, NONMETAL),
    ('Canned lentils', '4066447373189', 'dmbio_brown_lentils', 3, 4, NONMETAL),
    ('Canned sweetcorn', '4067796153903', 'dmbio_sweetcorn', 2, 2, ()),
    ('Canned chopped tomatoes', '4066447887679', 'dmbio_tomato_pieces', 3, 3, NONMETAL),
    ('Plant-based cream', '4066447965988', 'dmbio_oat_cuisine', 4, 4, ()),
    ('Soy cream', '4070765067460', 'dmbio_soy_cuisine', 4, 4, ()),
    ('Plant-based cream', '4066447876642', 'dmbio_almond_cuisine', 4, 4, ()),
    ('Applesauce', '4067796068498', 'dmbio_apple_puree', 3, 3, ()),
    ('Applesauce', '4067796068559', 'dmbio_apple_puree_cold_grated', 3, 3, ()),
)


class CatalogLifecycle228(unittest.TestCase):
    def test_exact_package_ranges_conditions_and_date_precedence(self):
        for name, code, rule, minimum, maximum, conditions in PACKAGES:
            with self.subTest(code=code):
                data = profile(name)
                lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
                result = lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=conditions)
                self.assertEqual((result['ruleId'], result['daysMin'], result['daysMax']), (rule, minimum, maximum))
                self.assertEqual(result['remindOn'], str(date(2026, 9, 25) + timedelta(days=minimum)))
                self.assertEqual(result['consumeBy'], str(date(2026, 9, 25) + timedelta(days=maximum)))
                for changes, temperature in (({'barcode': None}, 4), ({'barcode': '00000000'}, 4),
                        ({'openedAt': None}, 4), ({'storage': 'pantry'}, 4), ({}, 5), ({}, None)):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes,
                        temperature_c=temperature, confirmed_conditions=conditions))
                for changes in ({'brand': None}, {'brand': 'Other'}):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes,
                        temperature_c=4, confirmed_conditions=conditions))
                if conditions:
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
                self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-26'},
                    temperature_c=4, confirmed_conditions=conditions)['consumeBy'], '2026-09-26')
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 1})['consumeBy'], '2026-09-26')

    def test_package_rules_do_not_transfer_to_wrong_food_forms(self):
        for _, code, rule, _, _, conditions in PACKAGES:
            for name in ('Dried beans', 'Dried lentils', 'Tomato', 'Tomato paste', 'Soy milk',
                         'Oat milk', 'Coconut milk', 'Cream', 'Apple', 'Apple juice'):
                result = lifecycle.opening_window(profile(name),
                    {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'},
                    temperature_c=4, confirmed_conditions=conditions)
                self.assertNotEqual(result.get('ruleId'), rule, (name, code))
        for code in ('4066447965988', '4066447876642'):
            self.assertNotIn('consumeBy', lifecycle.opening_window(profile('Soy cream'),
                {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}, temperature_c=4))

    def test_updated_season_windows_and_processed_forms(self):
        for ident, months, basis in (
            ('M_FOOD_147', list(range(5, 11)), 'outdoor_harvest'),
            ('M_FOOD_132', list(range(3, 11)), 'regional_seasonal_availability'),
            ('M_FOOD_327', list(range(6, 11)), 'regional_seasonal_availability'),
        ):
            for month in range(1, 13):
                row = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=month)
                self.assertEqual(row['status'], 'in_season' if month in months else 'unknown')
                self.assertEqual((row['months'], row['basis'], row['sourceRegion']), (months, basis, 'DE'))
                self.assertTrue(row['approximate'])
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='GR', month=month)['status'], 'unknown')
        for name in ('Dried blueberries', 'Fermented cucumbers', 'Zucchini flowers', 'Cucumber juice'):
            self.assertEqual(lifecycle.seasonal_availability(profile(name), country='DE', month=10)['status'], 'unknown')

        self.assertEqual(lifecycle.seasonal_availability(profile('Blueberry jam'), country='DE', month=10)['status'], 'not_applicable')

    def test_reviewed_provider_ids_reach_real_choices_without_broadening_identity(self):
        data = lifecycle.load_lifecycle_data()
        for ident, expected in data['ingredientIds'].items():
            self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': ident})['profileId'], expected, ident)
        for lang in ('el', 'de'):
            rows = catalog.ingredient_choices(lang)
            for ident in ('M_FOOD_147', 'M_FOOD_132', 'M_FOOD_79', 'M_FOOD_325', 'M_FOOD_256'):
                row = next(r for r in rows if r.get('key') == ident)
                self.assertEqual(row['lifecycle']['profileId'], data['ingredientIds'][ident])
        # Conflicting food identities and spice homonyms stay unmapped.
        for ident in ('M_FOOD_399', 'M_FOOD_328', 'M_FOOD_388', 'M_FOOD_358'):
            self.assertNotIn('profileId', catalog.ingredient_lifecycle_profile({'ingredientId': ident}))
        # Batch 23 gives the unqualified kidney-bean row product-only evidence.
        # Its dry/canned ambiguity must never select a generic canned interval.
        generic_beans = catalog.ingredient_lifecycle_profile({'ingredientId': 'M_FOOD_653'})
        self.assertTrue(all(rule.get('productBarcodes') for rule in generic_beans['afterOpening']['rules']))
        self.assertEqual(generic_beans['seasonality']['status'], 'unknown')
        for brand in ('Alnatura', 'dmBio', 'Bonduelle', 'Other'):
            self.assertNotIn('consumeBy', lifecycle.opening_window(generic_beans,
                {'brand': brand, 'openedAt': '2026-09-25', 'storage': 'fridge'},
                temperature_c=4, confirmed_conditions=NONMETAL))

    def test_actual_catalog_opening_editor_keeps_range_and_confirmation(self):
        rows = catalog.ingredient_choices('el')
        ingredient = next(r for r in rows if r.get('lifecycle', {}).get('profileId') == 'canned_lentils')
        lot = {'brand': 'dmBio', 'barcode': '4066447373189'}
        rules = opening.opening_rules(ingredient, lot)
        self.assertEqual([(r['id'], r['daysMin'], r['daysMax'], r['conditions']) for r in rules],
                         [('dmbio_brown_lentils', 3, 4, list(NONMETAL))])
        selected = lot | {'openingRuleId': rules[0]['id']}
        with self.assertRaises(ValueError):
            opening.configure_opening(ingredient, selected)
        configured = opening.configure_opening(ingredient, selected | {'openingConditionsConfirmed': True})
        self.assertEqual(configured['useWithinDays'], 4)
        self.assertNotIn('openedAt', configured)


if __name__ == '__main__':
    unittest.main()
