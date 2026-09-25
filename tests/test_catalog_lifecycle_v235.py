"""Exact condiment packages, selectable identities, and national seasons."""
from datetime import date, timedelta
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

PACKAGES = (
    ('Ketchup', 'M_FOOD_259', '4066447887723', 'dmbio_ketchup', 30, 30, ('stored_upright',)),
    ('Curry sauce', 'local:it:812ff4089c35015e672d', '4066447675887', 'dmbio_thai_curry', 3, 3, ()),
    ('Curry sauce', 'local:it:812ff4089c35015e672d', '4067796097245', 'dmbio_indian_curry', 3, 3, ()),
    ('Tomato sauce', 'M_FOOD_445', '4066447887785', 'dmbio_tomato_grilled_pepper', 3, 4, ()),
    ('Tomato sauce', 'M_FOOD_445', '4070765100709', 'dmbio_tomato_goat_cheese_320', 5, 5, ()),
    ('Tomato sauce', 'M_FOOD_445', '4066447257748', 'dmbio_tomato_goat_cheese_340', 5, 5, ()),
    ('Ajvar', 'local:pl:25df74232d2bfc8d3a3c', '4067796185997', 'dmbio_ajvar', 3, 3, ()),
)
SEASONS = (
    ('M_FOOD_32', list(range(1, 13)), 'seasonal_calendar_including_stored_produce'),
    ('M_FOOD_112', list(range(1, 13)), 'seasonal_calendar_including_stored_produce'),
    ('M_FOOD_106', list(range(1, 13)), 'regional_seasonal_availability'),
    ('M_FOOD_177', list(range(3, 12)), 'regional_seasonal_availability'),
)


class CatalogLifecycle235(unittest.TestCase):
    def test_package_identity_storage_and_printed_date_boundaries(self):
        for name, ident, code, rule, minimum, maximum, conditions in PACKAGES:
            with self.subTest(code=code):
                ingredient = {'ingredientId': ident}
                lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
                data = catalog.ingredient_lifecycle_profile(ingredient)
                for barcode in (code, code.zfill(14)):
                    result = lifecycle.opening_window(data, lot | {'barcode': barcode}, temperature_c=4, confirmed_conditions=conditions)
                    self.assertEqual((result.get('ruleId'), result.get('daysMin'), result.get('daysMax')), (rule, minimum, maximum))
                    self.assertEqual(result['remindOn'], str(date(2026, 9, 25) + timedelta(days=minimum)))
                    self.assertEqual(result['consumeBy'], str(date(2026, 9, 25) + timedelta(days=maximum)))
                    self.assertFalse(result['safetyGuarantee'])
                for changes, temp in (({'barcode': None}, 4), ({'barcode': code[:-1]+'X'}, 4),
                        ({'brand': None}, 4), ({'brand': 'Other'}, 4), ({'storage': 'pantry'}, 4),
                        ({'storage': 'freezer'}, 4), ({'openedAt': None}, 4), ({}, None), ({}, -1), ({}, 4.1)):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes, temperature_c=temp, confirmed_conditions=conditions))
                if conditions:
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
                self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-26'},
                    temperature_c=4, confirmed_conditions=conditions)['consumeBy'], '2026-09-26')
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 2})['consumeBy'], '2026-09-27')

    def test_foreign_foods_and_unknown_packages_do_not_borrow_days(self):
        names = {row[0] for row in PACKAGES} | {'Curry paste', 'Curry powder', 'Passata', 'Tomato paste',
            'Bell pepper', 'Goat cheese', 'Coconut milk', 'Ketchup (or passata)', 'Homemade ajvar'}
        for name, _, code, _, _, _, conditions in PACKAGES:
            lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
            for other in names - {name}:
                self.assertNotIn('consumeBy', lifecycle.opening_window(profile(other), lot, temperature_c=4,
                    confirmed_conditions=conditions), (name, other))
        for name, brand, code in (('Ketchup', 'Alnatura', '4104420031500'), ('Ketchup', 'dmBio', '4066447887730'),
                ('Red pesto', 'dmBio', '4066447887808'), ('Basil pesto', 'dmBio', '4066447887815')):
            self.assertNotIn('consumeBy', lifecycle.opening_window(profile(name), {'brand': brand, 'barcode': code,
                'openedAt': '2026-09-25', 'storage': 'fridge'}, temperature_c=4, confirmed_conditions=('stored_upright',)))

    def test_real_multilingual_choices_retain_confirmation_and_ingredient_identity(self):
        for language in ('el', 'de', 'en'):
            rows = catalog.ingredient_choices(language)
            for name, ident, code, rule, _, maximum, _ in PACKAGES:
                ingredient = actual_choice(rows, ident)
                lot = {'brand': 'dmBio', 'barcode': code}
                offered = opening.opening_rules(ingredient, lot)
                self.assertEqual([r['id'] for r in offered], [rule], (language, name, ident))
                with self.assertRaises(ValueError):
                    opening.configure_opening(ingredient, lot | {'openingRuleId': rule})
                configured = opening.configure_opening(ingredient, lot | {'openingRuleId': rule, 'openingConditionsConfirmed': True})
                self.assertEqual(configured['useWithinDays'], maximum)
                self.assertNotIn('openedAt', configured)
                self.assertEqual(opening.opening_rules({'name': ingredient['name']}, lot), [])

    def test_national_calendar_months_and_country_boundaries(self):
        for ident, months, basis in SEASONS:
            for month in range(1, 13):
                row = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=month)
                self.assertEqual(row['status'], 'year_round' if len(months)==12 else 'in_season' if month in months else 'unknown')
                self.assertEqual((row['months'], row['basis'], row['sourceRegion']), (months, basis, 'DE'))
                self.assertTrue(row['approximate'])
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='GR', month=month)['status'], 'unknown')
        for name in ('Frozen spinach', 'Cooked beetroot', 'Pickled beetroot', 'Sauerkraut', 'Red cabbage in a jar'):
            self.assertNotIn(lifecycle.seasonal_availability(profile(name), country='DE', month=4)['status'], ('year_round', 'in_season'))

    def test_supermarket_names_and_provider_identity(self):
        ident = 'local:it:812ff4089c35015e672d'
        self.assertEqual(catalog.ingredient_display_name({'ingredientId': ident}, 'de'), 'Currysauce')
        for term in ('Currysauce', 'Currysoße', 'Currysosse'):
            self.assertEqual(actual_choice(catalog.ingredient_choices('de', query=term), ident)['name'], 'Currysauce')
        self.assertEqual(catalog.ingredient_display_name({'ingredientId': ident}, 'el'), 'Σάλτσα κάρι')
        for row in ({'id': 'M_FOOD_259', 'classification': 'equipment'}, {'id': 'M_FOOD_259', 'needsSemanticConfirmation': True}):
            lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
            self.assertNotIn('lifecycle', row)


if __name__ == '__main__':
    unittest.main()
