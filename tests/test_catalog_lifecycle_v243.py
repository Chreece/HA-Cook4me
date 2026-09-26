"""Batch 27: sweet pantry forms, exact red-fruit package and regional produce."""
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

SEASONS = {
    'M_FOOD_328': ('season_turnip', [6, 7, 8, 9, 10, 11], 'DE', 'DE-RP'),
    'M_FOOD_572': ('season_watermelon', [5, 6, 7, 8, 9], 'GR', 'Ilia and Trifylia, Peloponnese'),
}
PANTRY = {
    'M_FOOD_462': 'maple_syrup_label_required',
    'M_FOOD_704': 'agave_syrup_label_required',
    'M_FOOD_362': 'chocolate_spread_label_required',
    'M_FOOD_339': 'chocolate_spread_label_required',
    'M_FOOD_313': 'honey_label_required',
    'local:it:488c9bff53a03f68a0d7': 'red_fruit_jam_product_guidance',
}
JAM = 'local:it:488c9bff53a03f68a0d7'
CODE = '4260248063939'
RULE = 'xucker_red_fruit_spread'
NAMES = (
    ('M_FOOD_328', 'Speiserübe', ('Mairübe', 'Herbstrübe', 'Navet')),
    ('M_FOOD_433', 'Steckrübe', ('Kohlrübe', 'Wruke', 'Rutabaga')),
    ('M_FOOD_572', 'Wassermelone', ('Wassermelone',)),
    ('M_FOOD_462', 'Ahornsirup', ('Ahornsirup',)),
    ('M_FOOD_704', 'Agavendicksaft', ('Agavendicksaft',)),
    ('M_FOOD_362', 'Schokoaufstrich', ('Schokocreme', 'Schokoladenaufstrich')),
    ('M_FOOD_313', 'Honig', ('Honig',)),
    (JAM, 'Marmelade aus roten Früchten', ('Rote-Früchte-Konfitüre', 'Rote-Früchte-Fruchtaufstrich')),
)


class CatalogLifecycle243(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {lang: catalog.ingredient_choices(lang) for lang in ('el', 'de', 'en')}

    def test_exact_profiles_reach_actual_choices_and_keep_identity_gate(self):
        expected = PANTRY | {ident: values[0] for ident, values in SEASONS.items()}
        for ident, key in expected.items():
            self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': ident})['profileId'], key)
            for lang, rows in self.rows.items():
                self.assertEqual(actual_choice(rows, ident).get('lifecycle', {}).get('profileId'), key, (lang, ident))
            for extra in ({'classification': 'equipment'}, {'needsSemanticConfirmation': True}):
                row = {'id': ident} | extra
                lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
                self.assertNotIn('lifecycle', row)
        data = lifecycle.load_lifecycle_data()
        for row in catalog.load_release_catalog()['ingredients']:
            key = data['canonicalNames'].get(row.get('canonicalName', '').casefold())
            if key in set(PANTRY.values()):
                self.assertEqual(row.get('lifecycle', {}).get('profileId'), key, row['id'])

    def test_regional_calendars_do_not_leak_to_other_countries_or_forms(self):
        for ident, (_, months, country, region) in SEASONS.items():
            for month in range(1, 13):
                found = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country=country, month=month)
                self.assertEqual((found['months'], found['sourceRegion'], found['status']),
                    (months, region, 'in_season' if month in months else 'unknown'))
                other = 'GR' if country == 'DE' else 'DE'
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country=other, month=month)['status'], 'unknown')
        self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': 'M_FOOD_433'})['profileId'], 'season_swede')
        for name in ('Watermelon juice', 'Watermelon jam', 'Frozen watermelon', 'Pickled turnip', 'Turnip greens', 'Dried turnips'):
            self.assertNotEqual(profile(name)['seasonality']['status'], 'reviewed', name)
        self.assertNotEqual(catalog.ingredient_lifecycle_profile({'ingredientId': 'M_FOOD_620'}).get('profileId'), 'season_turnip')

    def test_syrups_honey_and_chocolate_have_no_invented_opening_clock(self):
        cases = (
            ('Maple syrup', '4067796084849'), ('Maple syrup (for the sauce)', '4067796084849'),
            ('Agave syrup', '4066447413052'), ('Honey', '4067796063790'),
            ('Runny honey (optional)', '4067796063790'), ('Crystallized honey', '4067796063790'),
            ('Chocolate spread', '4066447948417'), ('Cocoa and hazelnut spread', '4066447948394'),
            ('Chocolate and hazelnut spread', '4066447948394'), ('Nutella', '4066447948394'),
        )
        for name, code in cases:
            data = profile(name)
            self.assertEqual((data['seasonality']['status'], data['afterOpening']['status']), ('not_applicable', 'label_required'))
            lot = {'brand': 'dmBio', 'barcode': code, 'storage': 'fridge', 'openedAt': '2026-09-26'}
            self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
            self.assertEqual(opening.opening_rules({'canonicalName': name, 'classification': 'food'}, lot), [])
            self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 3})['consumeBy'], '2026-09-29')
        for name in ('Honey mustard', 'Honey salad dressing', 'Maple sauce', 'Chocolate spread/cream', 'Chocolate or hazelnut spread', 'Hazelnut spread', 'Homemade chocolate spread'):
            self.assertNotIn(profile(name).get('profileId'), set(PANTRY.values()), name)

    def test_red_fruit_clock_requires_its_exact_package_and_conditions(self):
        data = profile('Red fruit jam')
        lot = {'brand': 'Xucker', 'barcode': CODE, 'storage': 'fridge', 'openedAt': '2026-09-26'}
        result = lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=('clean_spoon',))
        self.assertEqual((result['ruleId'], result['daysMin'], result['daysMax'], result['consumeBy']), (RULE, 10, 10, '2026-10-06'))
        for changes, temperature in (({'brand': 'Other'}, 4), ({'barcode': None}, 4), ({'barcode': CODE[:-1] + 'X'}, 4),
                ({'barcode': '4260248063892'}, 4), ({'barcode': '4260248063908'}, 4),
                ({'storage': 'pantry'}, 4), ({'storage': 'freezer'}, 4), ({'openedAt': None}, 4), ({}, None), ({}, -1), ({}, 4.1)):
            self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes, temperature_c=temperature, confirmed_conditions=('clean_spoon',)))
        self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))
        self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-28'}, temperature_c=4, confirmed_conditions=('clean_spoon',))['consumeBy'], '2026-09-28')
        self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 2})['consumeBy'], '2026-09-28')
        self.assertEqual(lifecycle.opening_window(profile('Jam'), lot, temperature_c=4, confirmed_conditions=('clean_spoon',))['ruleId'], RULE)
        for name in ('Strawberry jam', 'Raspberry jam', 'Berry jam', 'Orange marmalade', 'Fresh red fruit', 'Milk jam', 'Honey', 'Homemade jam'):
            self.assertNotIn('consumeBy', lifecycle.opening_window(profile(name), lot, temperature_c=4, confirmed_conditions=('clean_spoon',)), name)

    def test_selecting_red_fruit_guidance_requires_consent_without_opening(self):
        lot = {'brand': 'Xucker', 'barcode': CODE, 'openingRuleId': RULE}
        for lang, rows in self.rows.items():
            ingredient = actual_choice(rows, JAM)
            self.assertEqual([(r['id'], r['conditions']) for r in opening.opening_rules(ingredient, lot)], [(RULE, ['clean_spoon'])], lang)
            with self.assertRaises(ValueError):
                opening.configure_opening(ingredient, lot)
            configured = opening.configure_opening(ingredient, lot | {'openingConditionsConfirmed': True})
            self.assertEqual(configured['useWithinDays'], 10)
            self.assertNotIn('openedAt', configured)

    def test_supermarket_search_preserves_distinct_foods(self):
        for ident, name, aliases in NAMES:
            self.assertEqual(actual_choice(self.rows['de'], ident)['name'], name)
            for alias in aliases:
                self.assertEqual(actual_choice(catalog.ingredient_choices('de', query=alias), ident)['name'], name)
        for lang, rows in self.rows.items():
            for pair in (('M_FOOD_328', 'M_FOOD_433'), ('M_FOOD_462', 'M_FOOD_704'), ('M_FOOD_313', 'M_FOOD_462'), (JAM, 'M_FOOD_133')):
                self.assertNotEqual(actual_choice(rows, pair[0])['id'], actual_choice(rows, pair[1])['id'], (lang, pair))
        for ident, name in (('M_FOOD_328', 'Γογγύλι'), ('M_FOOD_572', 'Καρπούζι'), ('M_FOOD_462', 'Σιρόπι σφενδάμου'), ('M_FOOD_704', 'Σιρόπι αγαύης')):
            self.assertEqual(actual_choice(self.rows['el'], ident)['name'], name)


if __name__ == '__main__':
    unittest.main()
