"""Provider evidence reaches real choices without weakening package/form gates."""
from datetime import date, timedelta
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

MAPPINGS = {
    'M_FOOD_263': 'milk', 'M_FOOD_269': 'milk', 'M_FOOD_271': 'milk',
    'M_FOOD_268': 'hazelnut_drinks', 'M_FOOD_280': 'alnatura_lentils',
    'M_FOOD_653': 'alnatura_kidney_beans', 'M_FOOD_533': 'alnatura_salsa',
    'M_FOOD_534': 'alnatura_peanut_sauce', 'M_FOOD_507': 'label_required',
    'M_FOOD_681': 'label_required', 'M_FOOD_150': 'label_required',
    'M_FOOD_184': 'label_required', 'M_FOOD_614': 'label_required',
    'M_FOOD_151': 'label_required', 'M_FOOD_497': 'label_required',
    'M_FOOD_152': 'label_required', 'M_FOOD_306': 'mayonnaise_label_required',
    'M_FOOD_323': 'mustard_label_required', 'M_FOOD_324': 'mustard_label_required',
    'M_FOOD_444': 'soy_sauce_label_required',
}
PACKAGES = (
    ('M_FOOD_268', 'Alnatura', '4104420237292', 'alnatura_hazelnut_drink', 4, 4, ()),
    ('M_FOOD_280', 'Alnatura', '4104420187931', 'alnatura_lentils_can', 2, 2, ()),
    ('M_FOOD_280', 'dmBio', '4066447373189', 'dmbio_brown_lentils', 3, 4, ('transferred_to_nonmetal_container',)),
    ('M_FOOD_653', 'Alnatura', '4104420187894', 'alnatura_kidney_beans_can', 3, 3, ('transferred_to_container',)),
    ('M_FOOD_653', 'dmBio', '4067796187038', 'dmbio_kidney_beans', 3, 4, ('transferred_to_nonmetal_container',)),
    ('M_FOOD_533', 'Alnatura', '42398479', 'alnatura_salsa_dip', 3, 3, ()),
    ('M_FOOD_534', 'Alnatura', '4104420257863', 'alnatura_peanut_sauce', 3, 3, ()),
)
SEASONS = (('M_FOOD_63', list(range(5, 12))), ('M_FOOD_478', list(range(6, 11))))
NAMES = (
    ('M_FOOD_268', 'Haselnussdrink', ('Haselnussdrink', 'Haselnussmilch')),
    ('M_FOOD_534', 'Satésauce', ('Satésauce', 'Sataysauce', 'Saté-Sauce')),
    ('M_FOOD_269', 'Fettarme Milch', ('Fettarme Milch', 'Teilentrahmte Milch')),
    ('M_FOOD_150', 'Crème fraîche', ('Crème fraîche', 'Creme fraiche')),
)


class CatalogLifecycle237(unittest.TestCase):
    def test_reviewed_provider_mappings_reach_real_multilingual_choices(self):
        for language in ('el', 'de', 'en'):
            rows = catalog.ingredient_choices(language)
            for ident, expected in MAPPINGS.items():
                with self.subTest(language=language, ident=ident):
                    self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': ident}).get('profileId'), expected)
                    self.assertEqual(actual_choice(rows, ident).get('lifecycle', {}).get('profileId'), expected)
            for ident, brand, code, rule, minimum, maximum, conditions in PACKAGES:
                ingredient = actual_choice(rows, ident)
                lot = {'brand': brand, 'barcode': code}
                offered = opening.opening_rules(ingredient, lot)
                self.assertEqual([(r['id'], r['daysMin'], r['daysMax'], r['conditions']) for r in offered],
                    [(rule, minimum, maximum, list(conditions))], (language, ident))
                with self.assertRaises(ValueError):
                    opening.configure_opening(ingredient, lot | {'openingRuleId': rule})
                configured = opening.configure_opening(ingredient, lot | {'openingRuleId': rule, 'openingConditionsConfirmed': True})
                self.assertEqual(configured['useWithinDays'], maximum)
                self.assertNotIn('openedAt', configured)

    def test_package_identity_storage_and_earlier_printed_dates_still_apply(self):
        for ident, brand, code, rule, minimum, maximum, conditions in PACKAGES:
            data = catalog.ingredient_lifecycle_profile({'ingredientId': ident})
            lot = {'brand': brand, 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
            result = lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=conditions)
            self.assertEqual((result.get('ruleId'), result.get('daysMin'), result.get('daysMax')), (rule, minimum, maximum))
            self.assertEqual(result['remindOn'], str(date(2026, 9, 25) + timedelta(days=minimum)))
            self.assertEqual(result['consumeBy'], str(date(2026, 9, 25) + timedelta(days=maximum)))
            for changes, temp in (({'barcode': None}, 4), ({'barcode': code[:-1]+'X'}, 4),
                    ({'brand': 'Other'}, 4), ({'storage': 'pantry'}, 4), ({'storage': 'freezer'}, 4),
                    ({'openedAt': None}, 4), ({}, None), ({}, -1), ({}, 4.1)):
                self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes, temperature_c=temp, confirmed_conditions=conditions))
            if conditions:
                self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
            self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-26'}, temperature_c=4,
                confirmed_conditions=conditions)['consumeBy'], '2026-09-26')
            for other in ('Dried lentils', 'Dried kidney beans', 'Peanuts', 'Hazelnuts', 'Tomato', 'Soy sauce'):
                self.assertNotIn('consumeBy', lifecycle.opening_window(profile(other), lot, temperature_c=4, confirmed_conditions=conditions), other)

    def test_milk_requires_heat_treatment_and_does_not_cover_other_forms(self):
        lot = {'openedAt': '2026-09-25', 'storage': 'fridge'}
        for ident in ('M_FOOD_263', 'M_FOOD_269', 'M_FOOD_271'):
            data = catalog.ingredient_lifecycle_profile({'ingredientId': ident})
            self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
            result = lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=('pasteurized_or_uht',))
            self.assertEqual((result['ruleId'], result['consumeBy']), ('milk', '2026-09-28'))
            self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | {'storage': 'pantry'},
                temperature_c=4, confirmed_conditions=('pasteurized_or_uht',)))
        for name in ('Raw milk', 'Milk powder', 'Coconut milk', 'Yoghurt', 'Cream'):
            self.assertNotIn('consumeBy', lifecycle.opening_window(profile(name), lot, temperature_c=4,
                confirmed_conditions=('pasteurized_or_uht',)), name)

    def test_label_required_entries_never_invent_a_clock(self):
        for ident, key in MAPPINGS.items():
            if key not in ('label_required', 'mayonnaise_label_required', 'mustard_label_required', 'soy_sauce_label_required'):
                continue
            data = catalog.ingredient_lifecycle_profile({'ingredientId': ident})
            self.assertEqual(data['afterOpening']['status'], 'label_required')
            self.assertEqual(opening.opening_rules({'ingredientId': ident}, {'brand': 'Alnatura'}), [])
            lot = {'brand': 'Alnatura', 'openedAt': '2026-09-25', 'storage': 'fridge'}
            self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
            self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 2})['consumeBy'], '2026-09-27')
        for ident in MAPPINGS:
            for extras in ({'classification': 'equipment'}, {'needsSemanticConfirmation': True}):
                row = {'id': ident} | extras
                lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
                self.assertNotIn('lifecycle', row)

    def test_national_calendars_do_not_extend_to_preserved_or_mixed_food(self):
        for ident, months in SEASONS:
            for month in range(1, 13):
                row = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=month)
                self.assertEqual((row['months'], row['sourceRegion'], row['basis']), (months, 'DE', 'regional_seasonal_availability'))
                self.assertEqual(row['status'], 'in_season' if month in months else 'unknown')
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='GR', month=month)['status'], 'unknown')
        for name in ('Frozen broccoli', 'Dried tomatoes', 'Canned tomatoes', 'Tomato paste', 'Tomato, tomato paste'):
            self.assertNotEqual(profile(name)['seasonality']['status'], 'reviewed', name)
        self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': 'local:uk:c534c21ad6bc2dbd4af4'}, country='DE', month=9)['status'], 'unknown')

    def test_german_names_remain_searchable_and_creme_fraiche_is_separate_from_cream(self):
        for ident, name, aliases in NAMES:
            self.assertEqual(catalog.ingredient_display_name({'ingredientId': ident}, 'de'), name)
            for alias in aliases:
                self.assertEqual(actual_choice(catalog.ingredient_choices('de', query=alias), ident)['name'], name)
        rows = catalog.ingredient_choices('de')
        creme, cream = actual_choice(rows, 'M_FOOD_150'), actual_choice(rows, 'M_FOOD_681')
        self.assertNotEqual(creme['id'], cream['id'])
        self.assertEqual(cream['name'], 'Sahne')
        self.assertNotIn('M_FOOD_150', cream.get('sourceIngredientIds', []))


if __name__ == '__main__':
    unittest.main()
