"""Fermented-food package identity and fresh root/stalk seasonal boundaries."""
from datetime import date, timedelta
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

PACKAGES = (
    ('Kimchi', 'M_FOOD_595', '4066447087130', 'dmbio_kimchi', 3),
    ('Sauerkraut', 'M_FOOD_548', '4066447677652', 'dmbio_sauerkraut', 3),
)
SEASONS = (
    ('M_FOOD_83', [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12], 'seasonal_calendar_including_stored_produce'),
    ('M_FOOD_82', list(range(5, 11)), 'regional_seasonal_availability'),
    ('M_FOOD_108', [1, 2, 9, 10, 11, 12], 'regional_seasonal_availability'),
)


class CatalogLifecycle236(unittest.TestCase):
    def test_exact_packages_require_known_identity_and_cold_storage(self):
        for name, ident, code, rule, days in PACKAGES:
            with self.subTest(name=name):
                data = catalog.ingredient_lifecycle_profile({'ingredientId': ident})
                lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
                for barcode in (code, code.zfill(14)):
                    result = lifecycle.opening_window(data, lot | {'barcode': barcode}, temperature_c=4)
                    self.assertEqual((result.get('ruleId'), result.get('daysMin'), result.get('daysMax')), (rule, days, days))
                    expected = str(date(2026, 9, 25) + timedelta(days=days))
                    self.assertEqual((result['remindOn'], result['consumeBy']), (expected, expected))
                    self.assertFalse(result['safetyGuarantee'])
                for changes, temp in (({'barcode': None}, 4), ({'barcode': code[:-1]+'X'}, 4),
                        ({'brand': None}, 4), ({'brand': 'Other'}, 4), ({'storage': 'pantry'}, 4),
                        ({'storage': 'freezer'}, 4), ({'openedAt': None}, 4), ({}, None), ({}, -1), ({}, 4.1)):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes, temperature_c=temp))
                self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-26'}, temperature_c=4)['consumeBy'], '2026-09-26')
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 1})['consumeBy'], '2026-09-26')

    def test_processed_foods_do_not_borrow_other_foods_opening_rules(self):
        names = {r[0] for r in PACKAGES} | {'White cabbage', 'Napa cabbage', 'Kimchi brine', 'Aged kimchi',
            'Sour kimchi', 'Homemade kimchi', 'Napa cabbage kimchi, cut into bite-size pieces',
            'Cooked sauerkraut', 'Sauerkraut juice', 'Carrot', 'Celery', 'Celeriac'}
        for name, _, code, _, _ in PACKAGES:
            lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
            for other in names - {name}:
                self.assertNotIn('consumeBy', lifecycle.opening_window(profile(other), lot, temperature_c=4), (name, other))
            for month in range(1, 13):
                self.assertEqual(lifecycle.seasonal_availability(profile(name), country='DE', month=month)['status'], 'not_applicable')
        for name, code in (('Capers', '4066447876468'), ('Sun-dried tomatoes in oil', '4066447898729'),
                ('Dried tomatoes', '4066447885019')):
            self.assertNotIn('consumeBy', lifecycle.opening_window(profile(name), {'brand': 'dmBio', 'barcode': code,
                'openedAt': '2026-09-25', 'storage': 'fridge'}, temperature_c=4))

    def test_selectable_provider_rows_require_confirmation_and_preserve_old_guidance(self):
        for language in ('el', 'de', 'en'):
            rows = catalog.ingredient_choices(language)
            for name, ident, code, rule, days in PACKAGES:
                ingredient = actual_choice(rows, ident)
                lot = {'brand': 'dmBio', 'barcode': code}
                self.assertEqual([r['id'] for r in opening.opening_rules(ingredient, lot)], [rule], (language, ident))
                with self.assertRaises(ValueError):
                    opening.configure_opening(ingredient, lot | {'openingRuleId': rule})
                configured = opening.configure_opening(ingredient, lot | {'openingRuleId': rule, 'openingConditionsConfirmed': True})
                self.assertEqual(configured['useWithinDays'], days)
                self.assertNotIn('openedAt', configured)
                self.assertEqual(opening.opening_rules({'name': ingredient['name']}, lot), [])
            sauerkraut = actual_choice(rows, 'M_FOOD_548')
            offered = opening.opening_rules(sauerkraut, {'brand': 'Alnatura', 'barcode': '4104420033849'})
            self.assertEqual([r['id'] for r in offered], ['alnatura_sauerkraut'])

    def test_national_seasons_keep_roots_stalks_and_mixtures_separate(self):
        for ident, months, basis in SEASONS:
            for month in range(1, 13):
                row = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=month)
                self.assertEqual(row['status'], 'in_season' if month in months else 'unknown')
                self.assertEqual((row['months'], row['basis'], row['sourceRegion']), (months, basis, 'DE'))
                self.assertTrue(row['approximate'])
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='GR', month=month)['status'], 'unknown')
        for name in ('Frozen Brussels sprouts', 'Cooked celeriac', 'Celery salt', 'Celery stalk, carrot'):
            self.assertNotEqual(profile(name)['seasonality']['status'], 'reviewed', name)
        self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': 'local:uk:c5f867e413f3b9c4a152'}, country='DE', month=9)['status'], 'unknown')
        for ident, _months, _basis in SEASONS:
            self.assertFalse(catalog.ingredient_lifecycle_profile({'ingredientId': ident})['afterOpening'].get('rules'))

    def test_supermarket_names_search_and_nonfood_identity_guards(self):
        for ident, name, aliases in (
            ('M_FOOD_82', 'Stangensellerie', ('Stangensellerie', 'Staudensellerie', 'Bleichsellerie')),
            ('local:hr:9644688c28222d3e4cad', 'Petersilienwurzel', ('Petersilienwurzel', 'Wurzelpetersilie')),
        ):
            self.assertEqual(catalog.ingredient_display_name({'ingredientId': ident}, 'de'), name)
            for alias in aliases:
                self.assertEqual(actual_choice(catalog.ingredient_choices('de', query=alias), ident)['name'], name)
        self.assertEqual(catalog.ingredient_display_name({'ingredientId': 'M_FOOD_83'}, 'de'), 'Knollensellerie')
        self.assertEqual(catalog.ingredient_display_name({'ingredientId': 'M_FOOD_595'}, 'el'), 'Κίμτσι')
        for ident in ('M_FOOD_595', 'M_FOOD_548'):
            for extras in ({'classification': 'equipment'}, {'needsSemanticConfirmation': True}):
                row = {'id': ident} | extras
                lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
                self.assertNotIn('lifecycle', row)


if __name__ == '__main__':
    unittest.main()
