"""Exact juice packages, handling conditions and missing seasonal months."""
from datetime import date, timedelta
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile

PACKAGES = (
    ('Orange juice', '4066447855494', 'dmbio_orange_juice', 3, 3, True),
    ('Beetroot juice', '4070765031096', 'dmbio_beetroot_juice_litre', 3, 3, False),
    ('Beetroot juice', '4070765031126', 'dmbio_beetroot_juice_500', 3, 3, False),
    ('Grape juice', '4066447855449', 'dmbio_grape_juice_330', 3, 3, True),
    ('Sauerkraut juice', '4070765031140', 'dmbio_sauerkraut_juice', 3, 4, True),
    ('Lemon juice', '4066447855579', 'dmbio_lemon_juice', 14, 14, True),
    ('Vegetable juice', '4066447855630', 'dmbio_vegetable_juice', 3, 4, True),
    ('Tomato juice', '4066447855685', 'dmbio_tomato_juice', 3, 3, False),
)


class CatalogLifecycle230(unittest.TestCase):
    def test_verified_juice_identity_storage_and_dates(self):
        for name, code, rule, minimum, maximum, upright in PACKAGES:
            with self.subTest(code=code):
                data = profile(name)
                lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
                conditions = ('stored_upright',) if upright else ()
                for temperature in (0, 4):
                    result = lifecycle.opening_window(data, lot, temperature_c=temperature, confirmed_conditions=conditions)
                    self.assertEqual((result['ruleId'], result['daysMin'], result['daysMax']), (rule, minimum, maximum))
                    self.assertEqual(result['remindOn'], str(date(2026, 9, 25) + timedelta(days=minimum)))
                    self.assertEqual(result['consumeBy'], str(date(2026, 9, 25) + timedelta(days=maximum)))
                    self.assertFalse(result['safetyGuarantee'])
                for changes, temperature in (({'barcode': None}, 4), ({'barcode': '00000000'}, 4),
                        ({'brand': None}, 4), ({'brand': 'Alnatura'}, 4), ({'storage': 'pantry'}, 4),
                        ({'openedAt': None}, 4), ({}, -0.1), ({}, 4.1), ({}, None)):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes,
                        temperature_c=temperature, confirmed_conditions=conditions))
                if upright:
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
                self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-26'},
                    temperature_c=4, confirmed_conditions=conditions)['consumeBy'], '2026-09-26')
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 1})['consumeBy'], '2026-09-26')

    def test_juice_rules_do_not_cross_forms_or_flavours(self):
        names = {p[0] for p in PACKAGES} | {'Apple juice', 'Fresh orange juice', 'Freshly squeezed lemon juice',
            'Lemon', 'Carrot', 'Beetroot', 'Sauerkraut', 'Tomato sauce', 'Passata', 'Fruit juice', 'Smoothie'}
        for name, code, _, _, _, _ in PACKAGES:
            for other in names - {name}:
                result = lifecycle.opening_window(profile(other), {'brand': 'dmBio', 'barcode': code,
                    'openedAt': '2026-09-25', 'storage': 'fridge'}, temperature_c=4, confirmed_conditions=('stored_upright',))
                self.assertNotIn('consumeBy', result, (name, other, code))

    def test_catalog_editor_preserves_range_and_explicit_confirmation(self):
        for language in ('el', 'de'):
            rows = catalog.ingredient_choices(language)
            for name, code, rule, minimum, maximum, upright in PACKAGES:
                ident = next(r['id'] for r in catalog.load_release_catalog()['ingredients'] if r.get('canonicalName') == name)
                ingredient = next(r for r in rows if ident in r.get('sourceIngredientIds', []) or r.get('id') == ident)
                lot = {'brand': 'dmBio', 'barcode': code}
                rules = opening.opening_rules(ingredient, lot)
                self.assertEqual([r['id'] for r in rules], [rule], (language, name))
                self.assertEqual((rules[0]['daysMin'], rules[0]['daysMax']), (minimum, maximum))
                self.assertEqual(rules[0]['conditions'], ['stored_upright'] if upright else [])
                with self.assertRaises(ValueError):
                    opening.configure_opening(ingredient, lot | {'openingRuleId': rule})
                configured = opening.configure_opening(ingredient, lot | {'openingRuleId': rule, 'openingConditionsConfirmed': True})
                self.assertEqual(configured['useWithinDays'], maximum)
                self.assertNotIn('openedAt', configured)

    def test_all_months_and_countries_for_extended_seasons(self):
        for ident, months, basis in (
            ('M_FOOD_107', [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12], 'seasonal_calendar_including_stored_produce'),
            ('M_FOOD_412', list(range(4, 12)), 'regional_seasonal_availability'),
        ):
            for month in range(1, 13):
                result = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=month)
                self.assertEqual(result['status'], 'in_season' if month in months else 'unknown')
                self.assertEqual((result['months'], result['basis'], result['sourceRegion']), (months, basis, 'DE'))
                self.assertTrue(result['approximate'])
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='GR', month=month)['status'], 'unknown')
        for name in ('Pickled radish', 'Daikon radish', 'Kimchi', 'Frozen Chinese cabbage'):
            self.assertNotEqual(lifecycle.seasonal_availability(profile(name), country='DE', month=8)['status'], 'in_season')


if __name__ == '__main__':
    unittest.main()
