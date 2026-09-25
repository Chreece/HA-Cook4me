"""Reviewed package periods, national seasons and exact provider-ID propagation."""
from copy import deepcopy
from datetime import date, timedelta
import importlib
import unittest

from test_catalog_amounts_v225 import PKG

lifecycle = importlib.import_module(PKG+'.ingredient_lifecycle')
catalog = importlib.import_module(PKG+'.release_catalog')
opening = importlib.import_module(PKG+'.product_opening')

PACKAGES = (
    ('Passata', '4066447887730', 'dmbio_passata_500', 3, ()),
    ('Passata', '4070765018783', 'dmbio_passata_690', 3, ('closed_container',)),
    ('Chickpeas', '4070765042894', 'dmbio_chickpeas_350', 2, ()),
    ('Canned chickpeas', '4070765071559', 'dmbio_chickpeas_700', 2, ()),
    ('Coconut milk', '4067796063882', 'dmbio_coconut_milk_400', 4, ()),
    ('Coconut milk', '4067796075519', 'dmbio_coconut_milk_250', 4, ()),
    ('Soy milk', '4070765022803', 'dmbio_soy_drink', 4, ('stored_upright',)),
    ('Rice milk', '4067796002102', 'dmbio_rice_drink', 4, ('stored_upright',)),
    ('Coconut drink', '4070765022827', 'dmbio_coconut_drink', 4, ('stored_upright',)),
    ('Oat milk', '4070765022759', 'dmbio_oat_natur', 4, ('stored_upright',)),
    ('Oat milk', '4070765022841', 'dmbio_oat_barista', 4, ('stored_upright',)),
)


def profile(name):
    payload = {'ingredients': [{'id': 'example', 'canonicalName': name, 'classification': 'food'}]}
    lifecycle.enrich_catalog_ingredients(payload)
    return lifecycle.lifecycle_profile(payload['ingredients'][0])


class CatalogLifecycle(unittest.TestCase):
    def test_verified_packages_have_scoped_deadlines(self):
        for name, code, rule, days, conditions in PACKAGES:
            with self.subTest(name=name, code=code):
                data = profile(name)
                lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
                result = lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=conditions)
                expected = str(date(2026, 9, 25) + timedelta(days=days))
                self.assertEqual((result['ruleId'], result['daysMax'], result['remindOn'], result['consumeBy']), (rule, days, expected, expected))
                self.assertFalse(result['safetyGuarantee'])
                for changes, temp in (({'barcode': None}, 4), ({'barcode': code[:-1]+'X'}, 4),
                        ({'brand': None}, 4), ({'brand': 'Alpro'}, 4), ({'openedAt': None}, 4),
                        ({'storage': 'pantry'}, 4), ({'storage': 'freezer'}, 4), ({}, 5), ({}, None)):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes, temperature_c=temp, confirmed_conditions=conditions))
                if conditions:
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
                capped = lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-26'}, temperature_c=4, confirmed_conditions=conditions)
                self.assertEqual(capped['consumeBy'], '2026-09-26')
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 1})['consumeBy'], '2026-09-26')

    def test_new_codes_do_not_cross_food_forms(self):
        for name, code, _, _, conditions in PACKAGES:
            lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
            for other in ('Dried chickpeas', 'Hummus', 'Coconut cream', 'Coconut water', 'Tomato paste', 'Tomato sauce'):
                self.assertNotIn('consumeBy', lifecycle.opening_window(profile(other), lot, temperature_c=4, confirmed_conditions=conditions), (name, other))
        for name, wrong in (('Coconut milk', '4070765022827'), ('Coconut drink', '4067796063882'), ('Soy milk', '4070765022759')):
            self.assertNotIn('consumeBy', lifecycle.opening_window(profile(name), {'brand': 'dmBio', 'barcode': wrong, 'openedAt': '2026-09-25', 'storage': 'fridge'}, temperature_c=4, confirmed_conditions=('stored_upright',)))

    def test_extended_seasons_and_fresh_form_boundaries(self):
        for name, months, basis in (
            ('Bell pepper', list(range(3, 12)), 'regional_seasonal_availability'),
            ('Spring onions', list(range(3, 12)), 'outdoor_harvest'),
            ('Parsnip', [1, 2, 3, 10, 11, 12], 'regional_seasonal_availability'),
            ('Nettle leaves, washed using gloves', list(range(3, 10)), 'outdoor_harvest'),
        ):
            data = profile(name)
            for month in range(1, 13):
                row = lifecycle.seasonal_availability(data, country='DE', month=month)
                self.assertEqual(row['status'], 'in_season' if month in months else 'unknown')
                self.assertEqual((row['months'], row['basis']), (months, basis))
                self.assertEqual(lifecycle.seasonal_availability(data, country='GR', month=month)['status'], 'unknown')
            self.assertNotIn('rules', data['afterOpening'])
        for name in ('Blanched nettle leaves', 'Dried nettle leaves', 'Nettle seeds', 'Frozen peppers', 'Ground pepper', 'Paprika', 'Pepper'):
            self.assertNotEqual(profile(name)['seasonality']['status'], 'reviewed', name)

    def test_exact_ids_do_not_bypass_ambiguity_or_nonfood_classification(self):
        data = lifecycle.load_lifecycle_data()
        for invalid in (None, [], {'': 'season_bell_pepper'}, {'M_FOOD_389': 'missing'}):
            bad = deepcopy(data);bad['ingredientIds'] = invalid
            with self.assertRaises(ValueError):
                lifecycle.validate_lifecycle_data(bad)
        for classification, unconfirmed in (('equipment', False), ('ambiguous', False), ('food', True)):
            payload = {'ingredients': [{'id': 'M_FOOD_389', 'canonicalName': 'Pepper', 'classification': classification, 'needsSemanticConfirmation': unconfirmed}]}
            lifecycle.enrich_catalog_ingredients(payload)
            self.assertNotIn('lifecycle', payload['ingredients'][0])

    def test_provider_choices_and_opening_editor_receive_the_evidence(self):
        for ident in ('M_FOOD_389', 'M_FOOD_390', 'M_FOOD_391', 'M_FOOD_392', 'M_FOOD_743'):
            self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=9)['status'], 'in_season')
        for ident in ('M_FOOD_388', 'M_FOOD_358', 'M_FOOD_377'):
            self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=9)['status'], 'unknown')
        for lang in ('el', 'de'):
            rows = catalog.ingredient_choices(lang)
            pepper = next(r for r in rows if r.get('key') == 'M_FOOD_389')
            self.assertEqual(pepper['lifecycle']['profileId'], 'season_bell_pepper')
        for ident, code, rule, conditions in (
            ('M_FOOD_267', '4067796063882', 'dmbio_coconut_milk_400', ()),
            ('M_FOOD_624', '4070765022803', 'dmbio_soy_drink', ('stored_upright',)),
        ):
            lot = {'brand': 'dmBio', 'barcode': code}
            offered = opening.opening_rules({'ingredientId': ident}, lot)
            self.assertEqual([r['id'] for r in offered], [rule])
            self.assertEqual(offered[0]['conditions'], list(conditions))
            with self.assertRaises(ValueError):
                opening.configure_opening({'ingredientId': ident}, lot | {'openingRuleId': rule})
            configured = opening.configure_opening({'ingredientId': ident}, lot | {'openingRuleId': rule, 'openingConditionsConfirmed': True})
            self.assertEqual(configured['useWithinDays'], 4)
            self.assertNotIn('openedAt', configured)


if __name__ == '__main__':
    unittest.main()
