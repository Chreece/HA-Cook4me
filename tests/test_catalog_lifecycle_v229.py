"""Product-specific tofu bounds, pesto forms and extended German seasons."""
from copy import deepcopy
from datetime import date, timedelta
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile

PACKAGES = (
    ('Tofu', '4067796251999', 'dmbio_natural_tofu', 2, 2, 6, ()),
    ('Smoked tofu', '4067796252019', 'dmbio_smoked_tofu', 2, 2, 6, ()),
    ('Green olives', '4070765075939', 'dmbio_green_olives', 14, 0, 4, ()),
    ('Green olives', '4066447870411', 'dmbio_green_olives_at', 14, 0, 4, ()),
    ('Black olives', '4070765075953', 'dmbio_kalamon_olives', 14, 0, 4, ()),
    ('Black olives', '4066447898743', 'dmbio_kalamon_olives_at', 14, 0, 4, ()),
    ('Green and black olives', '4070765075892', 'dmbio_olive_mix', 7, 0, 4, ()),
    ('Seitan', '4066447884883', 'dmbio_seitan', 2, 0, 4, ('closed_container',)),
    ('Black olive spread', '4066447087161', 'dmbio_black_olive_spread', 14, 0, 4, ()),
    ('Basil pesto', '4066447887822', 'dmbio_pesto_verde', 5, 0, 4, ()),
)


class CatalogLifecycle229(unittest.TestCase):
    def test_verified_packages_require_identity_temperature_and_handling(self):
        for name, code, rule, days, minimum, maximum, conditions in PACKAGES:
            with self.subTest(code=code):
                data = profile(name)
                lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
                for temperature in (minimum, 4, maximum):
                    result = lifecycle.opening_window(data, lot, temperature_c=temperature, confirmed_conditions=conditions)
                    self.assertEqual((result['ruleId'], result['daysMax']), (rule, days))
                    self.assertEqual(result['consumeBy'], str(date(2026, 9, 25) + timedelta(days=days)))
                for changes, temperature in (({'barcode': None}, 4), ({'barcode': '00000000'}, 4),
                        ({'brand': None}, 4), ({'brand': 'Other'}, 4), ({'storage': 'pantry'}, 4),
                        ({'openedAt': None}, 4), ({}, minimum - 0.1), ({}, maximum + 0.1), ({}, None)):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes,
                        temperature_c=temperature, confirmed_conditions=conditions))
                if conditions:
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
                self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-26'},
                    temperature_c=4, confirmed_conditions=conditions)['consumeBy'], '2026-09-26')
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 1})['consumeBy'], '2026-09-26')

    def test_optional_minimum_temperature_validation_and_legacy_behavior(self):
        data = deepcopy(lifecycle.load_lifecycle_data())
        rule = data['profiles']['taifun_plain_tofu']['afterOpening']['rules'][-1]
        self.assertEqual(rule['id'], 'dmbio_natural_tofu')
        for invalid in (None, True, '2', -1, 6.1, float('inf'), float('nan')):
            rule['minTemperatureC'] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                lifecycle.validate_lifecycle_data(data)
        for valid in (0, 2, 6):
            rule['minTemperatureC'] = valid
            lifecycle.validate_lifecycle_data(data)
        del rule['minTemperatureC']
        lifecycle.validate_lifecycle_data(data)
        lot = {'brand': 'dmBio', 'barcode': '4070765075939', 'openedAt': '2026-09-25', 'storage': 'fridge'}
        self.assertEqual(lifecycle.opening_window(profile('Green olives'), lot, temperature_c=0)['daysMax'], 14)

    def test_tofu_and_olive_forms_do_not_share_package_rules(self):
        for name, code, _, _, _, _, _ in PACKAGES:
            lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
            incompatible = {
                'Tofu': ('Smoked tofu', 'Silken tofu', 'Seitan'),
                'Smoked tofu': ('Tofu', 'Silken tofu', 'Seitan'),
                'Green olives': ('Black olives', 'Green and black olives', 'Black olive spread'),
                'Black olives': ('Green olives', 'Green and black olives', 'Black olive spread'),
                'Green and black olives': ('Green olives', 'Black olives', 'Black olive spread'),
                'Seitan': ('Tofu', 'Seitan or tofu', 'Seitan cutlets'),
                'Black olive spread': ('Black olives', 'Green and black olives', 'Olives', 'Feta'),
                'Basil pesto': ('Red pesto', 'Tomato pesto', 'Basil', 'Pesto alla Genovese'),
            }[name]
            for other in incompatible:
                self.assertNotIn('consumeBy', lifecycle.opening_window(profile(other), lot,
                    temperature_c=4, confirmed_conditions=('closed_container',)), (name, other, code))

    def test_generic_pesto_keeps_choices_and_specific_forms_reject_cross_matches(self):
        for code, brand, conditions, allowed in (
            ('4066447887822', 'dmBio', (), ('Pesto', 'Pesto sauce', 'Basil pesto')),
            ('4104420031326', 'Alnatura', ('covered_with_oil',), ('Pesto', 'Pesto sauce', 'Basil pesto')),
            ('4104420257344', 'Alnatura', ('covered_with_oil',), ('Pesto', 'Pesto sauce', 'Red pesto', 'Tomato pesto', 'Sun-dried tomato pesto')),
        ):
            for name in ('Pesto', 'Pesto sauce', 'Basil pesto', 'Red pesto', 'Tomato pesto', 'Sun-dried tomato pesto'):
                result = lifecycle.opening_window(profile(name), {'brand': brand, 'barcode': code,
                    'openedAt': '2026-09-25', 'storage': 'fridge'}, temperature_c=4, confirmed_conditions=conditions)
                self.assertEqual('consumeBy' in result, name in allowed, (name, code))

    def test_season_boundaries_reach_provider_ingredients(self):
        for ident, months, basis in (
            ('M_FOOD_44', list(range(3, 10)), 'regional_seasonal_availability'),
            ('M_FOOD_238', list(range(6, 12)), 'outdoor_harvest'),
            ('M_FOOD_109', list(range(5, 12)), 'outdoor_harvest'),
            ('M_FOOD_383', list(range(1, 13)), 'outdoor_harvest'),
        ):
            for month in range(1, 13):
                row = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=month)
                expected = 'year_round' if len(months) == 12 else 'in_season' if month in months else 'unknown'
                self.assertEqual(row['status'], expected)
                self.assertEqual((row['months'], row['basis'], row['sourceRegion']), (months, basis, 'DE'))
                self.assertTrue(row['approximate'])
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='ZZ', month=month)['status'], 'unknown')
        for name in ('Frozen green beans', 'Canned green beans', 'Pickled cauliflower', 'Leek soup'):
            self.assertNotEqual(lifecycle.seasonal_availability(profile(name), country='DE', month=8)['status'], 'in_season')

    def test_actual_catalog_opening_editor_receives_both_temperature_bounds(self):
        for lang in ('el', 'de'):
            rows = catalog.ingredient_choices(lang)
            for ident, code, rule, days in (
                ('M_FOOD_477', '4067796251999', 'dmbio_natural_tofu', 2),
                ('M_FOOD_539', '4066447884883', 'dmbio_seitan', 2),
                ('M_FOOD_370', '4066447887822', 'dmbio_pesto_verde', 5),
            ):
                ingredient = next(r for r in rows if r.get('key') == ident)
                lot = {'brand': 'dmBio', 'barcode': code}
                offered = opening.opening_rules(ingredient, lot)
                self.assertEqual([r['id'] for r in offered], [rule])
                if ident == 'M_FOOD_477':
                    self.assertEqual((offered[0]['minTemperatureC'], offered[0]['maxTemperatureC']), (2, 6))
                selected = lot | {'openingRuleId': rule}
                with self.assertRaises(ValueError):
                    opening.configure_opening(ingredient, selected)
                configured = opening.configure_opening(ingredient, selected | {'openingConditionsConfirmed': True})
                self.assertEqual(configured['useWithinDays'], days)
                self.assertNotIn('openedAt', configured)


if __name__ == '__main__':
    unittest.main()
