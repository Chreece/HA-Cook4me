"""Fresh herbs, dried pantry forms and edible pea pods retain their identities."""
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

SEASONS = {
    'M_FOOD_30': ('season_basil', [6, 7, 8, 9, 10], 'DE'),
    'M_FOOD_115': ('season_chives', [4, 5, 6, 7, 8, 9, 10], 'DE-HE'),
    'M_FOOD_16': ('season_dill', [5, 6, 7, 8, 9], 'DE'),
    'M_FOOD_308': ('season_mint', [5, 6, 7, 8, 9, 10], 'DE-NW'),
    'M_FOOD_369': ('season_parsley_leaf', [4, 5, 6, 7, 8, 9, 10], 'DE-HE'),
    'M_FOOD_425': ('season_rosemary', [5, 6, 7, 8, 9, 10], 'DE'),
    'M_FOOD_476': ('season_thyme', [5, 6, 7, 8, 9, 10], 'DE'),
    'M_FOOD_386': ('season_snow_pea', [6, 7, 8], 'DE'),
}
STAPLES = tuple(f'M_FOOD_{n}' for n in (361, 512, 186, 270, 764, 421, 457, 467))
DRIED = (
    ('local:cs:1f8e27d7a4cef1e89f30', 'Dried basil', 'Getrockneter Basilikum'),
    ('local:ar:60cfe5ae0e2acb107586', 'Dried mint', 'Getrocknete Minze'),
    ('local:ar:6aac151aef2122c6c395', 'Pinch of dried mint', 'Getrocknete Minze'),
    ('local:pt:1448f1bbee196aeb295a', 'Dried oregano', 'Getrockneter Oregano'),
    ('local:ar:5ba01e09f1d91e988370', 'Dried oregano leaves', 'Getrockneter Oregano'),
    ('local:cs:3380c9010d1c7969e973', 'Dried thyme', 'Getrockneter Thymian'),
    ('local:fr:6221208c901db8fa7336', 'Dried herbs', 'Getrocknete Kräuter'),
    ('local:ja:d1aad1b0ac021e0a0ff9', 'Dried herbs (such as rosemary)', 'Getrocknete Kräuter'),
    ('local:ar:cc22e4c94f86438999f6', 'Mixed dried herbs', 'Getrocknete Kräutermischung'),
)
NAMES = (
    ('M_FOOD_386', 'Zuckerschoten', ('Zuckerschoten', 'Zuckererbsen', 'Kaiserschoten')),
    ('M_FOOD_512', 'Getrocknete Bohnen', ('Getrocknete Bohnen',)),
    ('M_FOOD_764', 'Gemahlener schwarzer Pfeffer', ('Gemahlener schwarzer Pfeffer',)),
)


class CatalogLifecycle238(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {lang: catalog.ingredient_choices(lang) for lang in ('el', 'de', 'en')}

    def test_reviewed_forms_reach_actual_multilingual_choices(self):
        expected = {ident: row[0] for ident, row in SEASONS.items()}
        expected.update({ident: 'dry_staple' for ident in (*STAPLES, *(row[0] for row in DRIED))})
        for language, rows in self.rows.items():
            for ident, key in expected.items():
                with self.subTest(language=language, ident=ident):
                    self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': ident}).get('profileId'), key)
                    self.assertEqual(actual_choice(rows, ident).get('lifecycle', {}).get('profileId'), key)

    def test_seasons_keep_their_country_region_and_month_boundaries(self):
        for ident, (_, months, region) in SEASONS.items():
            for month in range(1, 13):
                result = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=month)
                self.assertEqual((result['months'], result['sourceRegion']), (months, region))
                self.assertEqual(result['status'], 'in_season' if month in months else 'unknown')
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='GR', month=month)['status'], 'unknown')

    def test_dried_forms_do_not_inherit_fresh_seasons_or_short_opening_windows(self):
        lot = {'openedAt': '2026-09-25', 'storage': 'fridge', 'brand': 'Alnatura', 'barcode': '4104420187894'}
        for ident in (*STAPLES, *(row[0] for row in DRIED)):
            data = catalog.ingredient_lifecycle_profile({'ingredientId': ident})
            self.assertEqual(data['seasonality']['status'], 'not_applicable')
            self.assertEqual(data['afterOpening']['status'], 'label_required')
            self.assertEqual(opening.opening_rules({'ingredientId': ident}, lot), [])
            self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4,
                confirmed_conditions=('pasteurized_or_uht', 'transferred_to_container')))
            self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 2})['consumeBy'], '2026-09-27')
        for _, name, _ in DRIED:
            self.assertEqual(profile(name)['profileId'], 'dry_staple')

    def test_edible_pods_remain_distinct_from_shelled_and_preserved_peas(self):
        for name in ('Mangetout', 'Mangetout, washed and cut in two', 'Snow peas', 'Mangetout peas'):
            self.assertEqual(profile(name)['profileId'], 'season_snow_pea')
        self.assertEqual(profile('Fresh peas')['profileId'], 'season_fresh_pea')
        for name in ('Frozen peas', 'Canned peas', 'Dried peas', 'Pea shoots'):
            self.assertNotEqual(profile(name)['seasonality']['status'], 'reviewed', name)

    def test_unreviewed_forms_and_nonfood_rows_do_not_gain_guidance(self):
        for n in (85, 349, 453, 183, 399, 388, 358):
            self.assertNotIn('profileId', catalog.ingredient_lifecycle_profile({'ingredientId': f'M_FOOD_{n}'}))
        self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': 'M_FOOD_328'})['profileId'], 'season_turnip')
        for ident in (*SEASONS, *STAPLES):
            for extras in ({'classification': 'equipment'}, {'needsSemanticConfirmation': True}):
                row = {'id': ident} | extras
                lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
                self.assertNotIn('lifecycle', row)

    def test_supermarket_names_search_and_deduplication_preserve_source_amounts(self):
        for ident, name, aliases in NAMES:
            self.assertEqual(actual_choice(self.rows['de'], ident)['name'], name)
            for alias in aliases:
                self.assertEqual(actual_choice(catalog.ingredient_choices('de', query=alias), ident)['name'], name)
        for ident, _, name in DRIED:
            self.assertEqual(actual_choice(self.rows['de'], ident)['name'], name)
        mint, pinch = DRIED[1][0], DRIED[2][0]
        for language, expected in (('el', 'Αποξηραμένη μέντα'), ('de', 'Getrocknete Minze'), ('en', 'Dried mint')):
            rows = self.rows[language]
            choice = actual_choice(rows, mint)
            self.assertEqual((choice['name'], choice['id']), (expected, actual_choice(rows, pinch)['id']))
            self.assertEqual(sum(row['name'] == expected for row in rows), 1)
            self.assertNotEqual(choice['id'], actual_choice(rows, 'M_FOOD_308')['id'])
            self.assertIn(pinch, choice['sourceIngredientIds'])
        raw = next(row for row in catalog.load_release_catalog()['ingredients'] if row['id'] == pinch)
        self.assertEqual(raw['canonicalName'], 'Pinch of dried mint')
        self.assertEqual(raw['translations']['en'], 'Pinch of dried mint')


if __name__ == '__main__':
    unittest.main()
