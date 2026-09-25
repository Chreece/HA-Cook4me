"""Nut/paste forms, exact satay package guidance and reviewed herb identities."""
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

SEASONS = {
    'M_FOOD_329': ('season_hazelnut', [9, 10, 11], 'DE-BY', 'bund_bavarian_seasons'),
    'M_FOOD_697': ('season_lemon_balm', [6, 7, 8, 9], 'DE-BY', 'lwg_garden_herbs'),
    'M_FOOD_571': ('season_sorrel', [4, 5, 6, 7, 8, 9, 10], 'DE-HE', 'bzfe_green_sauce_herbs'),
}
PANTRY = {
    'M_FOOD_330': 'ground_nuts_label_required', 'M_FOOD_400': 'ground_nuts_label_required',
    'M_FOOD_34': 'nut_butter_label_required', 'M_FOOD_706': 'tahini_label_required',
    'local:en:1934bf397d2769206ed7': 'nut_butter_label_required',
    'local:ja:20bb1c85856f86abe5f2': 'nut_butter_label_required',
    'local:pt:1f584e1700f53dafde13': 'ground_nuts_label_required',
    'local:ru:06d4624ded95ec67ba47': 'tahini_label_required',
}
NAMES = (
    ('M_FOOD_697', 'Zitronenmelisse', ('Zitronenmelisse', 'Melisse')),
    ('M_FOOD_571', 'Sauerampfer', ('Sauerampfer',)),
    ('M_FOOD_330', 'Gemahlene Haselnüsse', ('Gemahlene Haselnüsse',)),
    ('M_FOOD_400', 'Gemahlene Mandeln', ('Gemahlene Mandeln',)),
    ('local:en:1934bf397d2769206ed7', 'Mandelmus', ('Mandelmus', 'Mandelbutter')),
    ('local:ja:20bb1c85856f86abe5f2', 'Erdnussbutter mit Stückchen', ('Erdnussbutter mit Stückchen',)),
    ('M_FOOD_706', 'Sesammus (Tahin)', ('Sesammus', 'Tahin', 'Tahini', 'Sesampaste')),
    ('local:ru:06d4624ded95ec67ba47', 'Sesammus (Tahin)', ('Sesampaste',)),
)
CODE = '4066447377903'


class CatalogLifecycle239(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {lang: catalog.ingredient_choices(lang) for lang in ('el', 'de', 'en')}

    def test_exact_profiles_reach_actual_multilingual_choices(self):
        expected = PANTRY | {ident: value[0] for ident, value in SEASONS.items()}
        for language, rows in self.rows.items():
            for ident, key in expected.items():
                with self.subTest(language=language, ident=ident):
                    self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': ident}).get('profileId'), key)
                    self.assertEqual(actual_choice(rows, ident).get('lifecycle', {}).get('profileId'), key)
        names = lifecycle.load_lifecycle_data()['canonicalNames']
        for row in catalog.load_release_catalog()['ingredients']:
            expected = names.get(row.get('canonicalName', '').lower())
            if expected in set(PANTRY.values()):
                self.assertEqual(row.get('lifecycle', {}).get('profileId'), expected, row['id'])

    def test_seasonal_evidence_is_local_and_never_follows_nutrient_proxies(self):
        for ident, (key, months, region, source) in SEASONS.items():
            for month in range(1, 13):
                result = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=month)
                self.assertEqual((result['months'], result['sourceRegion'], result['sourceIds']), (months, region, [source]))
                self.assertEqual(result['status'], 'in_season' if month in months else 'unknown')
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='GR', month=month)['status'], 'unknown')
            self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': ident})['profileId'], key)
        for name in ('Lemongrass', 'Mustard greens', 'Dried lemon balm', 'Lemon balm tea', 'Sorrel sauce', 'Frozen sorrel'):
            self.assertNotIn(profile(name).get('profileId'), {'season_lemon_balm', 'season_sorrel'})
        for ident in (*SEASONS, *PANTRY):
            for extra in ({'classification': 'equipment'}, {'needsSemanticConfirmation': True}):
                row = {'id': ident} | extra
                lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
                self.assertNotIn('lifecycle', row)

    def test_processed_forms_never_inherit_harvest_or_other_product_clocks(self):
        packages = ('4066447856439', '4066447948271', '4070765069976', '4066447948318', CODE, '4066447910865')
        for ident in PANTRY:
            data = catalog.ingredient_lifecycle_profile({'ingredientId': ident})
            self.assertEqual(data['seasonality']['status'], 'not_applicable')
            self.assertEqual(data['afterOpening']['status'], 'label_required')
            for code in packages:
                lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
                self.assertEqual(opening.opening_rules({'ingredientId': ident}, lot), [])
                self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4,
                    confirmed_conditions=('closed_container',)))
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 2})['consumeBy'], '2026-09-27')
        self.assertEqual(profile('Hazelnuts')['profileId'], 'season_hazelnut')
        self.assertEqual(profile('Ground hazelnuts')['profileId'], 'ground_nuts_label_required')
        self.assertNotEqual(actual_choice(self.rows['de'], 'M_FOOD_330')['id'], actual_choice(self.rows['de'], 'M_FOOD_329')['id'])
        self.assertNotEqual(actual_choice(self.rows['de'], 'M_FOOD_400')['id'], actual_choice(self.rows['de'], 'M_FOOD_10')['id'])

    def test_satay_requires_exact_brand_barcode_refrigeration_and_opening(self):
        data = catalog.ingredient_lifecycle_profile({'ingredientId': 'M_FOOD_534'})
        lot = {'brand': 'dmBio', 'barcode': CODE, 'storage': 'fridge', 'openedAt': '2026-09-25'}
        result = lifecycle.opening_window(data, lot, temperature_c=4)
        self.assertEqual((result['ruleId'], result['daysMin'], result['daysMax'], result['consumeBy']),
            ('dmbio_peanut_sauce', 3, 3, '2026-09-28'))
        for changes, temp in (({'brand': 'Other'}, 4), ({'brand': 'Alnatura'}, 4), ({'barcode': None}, 4),
                ({'barcode': CODE[:-1] + 'X'}, 4), ({'barcode': '4066447948271'}, 4),
                ({'storage': 'pantry'}, 4), ({'storage': 'freezer'}, 4), ({'openedAt': None}, 4),
                ({}, None), ({}, -1), ({}, 4.1)):
            self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes, temperature_c=temp))
        self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-26'}, temperature_c=4)['consumeBy'], '2026-09-26')
        self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 1})['consumeBy'], '2026-09-26')
        for name in ('Peanut butter', 'Crunchy peanut butter', 'Almond butter', 'Tahini', 'Peanuts', 'Homemade satay sauce', 'Satay sauce seasoning'):
            self.assertNotIn('consumeBy', lifecycle.opening_window(profile(name), lot, temperature_c=4), name)
        previous = lifecycle.opening_window(data, lot | {'brand': 'Alnatura', 'barcode': '4104420257863'}, temperature_c=4)
        self.assertEqual((previous['ruleId'], previous['consumeBy']), ('alnatura_peanut_sauce', '2026-09-28'))

    def test_selecting_satay_guidance_requires_confirmation_and_does_not_open(self):
        lot = {'brand': 'dmBio', 'barcode': CODE, 'openingRuleId': 'dmbio_peanut_sauce'}
        for language, rows in self.rows.items():
            ingredient = actual_choice(rows, 'M_FOOD_534')
            self.assertEqual([r['id'] for r in opening.opening_rules(ingredient, lot)], ['dmbio_peanut_sauce'], language)
            with self.assertRaises(ValueError):
                opening.configure_opening(ingredient, lot)
            configured = opening.configure_opening(ingredient, lot | {'openingConditionsConfirmed': True})
            self.assertEqual(configured['useWithinDays'], 3)
            self.assertNotIn('openedAt', configured)

    def test_german_labels_and_search_keep_whole_ground_and_paste_forms_separate(self):
        for ident, name, aliases in NAMES:
            self.assertEqual(actual_choice(self.rows['de'], ident)['name'], name)
            for alias in aliases:
                self.assertEqual(actual_choice(catalog.ingredient_choices('de', query=alias), ident)['name'], name)
        for language, rows in self.rows.items():
            self.assertNotEqual(actual_choice(rows, 'M_FOOD_34')['id'], actual_choice(rows, 'M_FOOD_534')['id'])
            self.assertNotEqual(actual_choice(rows, 'M_FOOD_706')['id'], actual_choice(rows, 'M_FOOD_226')['id'])


if __name__ == '__main__':
    unittest.main()
