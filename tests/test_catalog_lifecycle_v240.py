"""Exact provider forms, regional seasons and flavour-specific jam package rules."""
from datetime import date, timedelta
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile
from test_catalog_lifecycle_v231 import actual_choice

SEASONS = {
    'M_FOOD_89': ('season_button_mushroom', list(range(1, 13)), 'DE', 'DE'),
    'M_FOOD_460': ('season_shiitake', list(range(1, 13)), 'DE', 'DE'),
    'M_FOOD_591': ('season_king_oyster_mushroom', list(range(1, 13)), 'DE', 'DE'),
    'M_FOOD_315': ('season_mirabelle', [7, 8, 9], 'DE', 'DE-HE'),
    'M_FOOD_331': ('season_walnut', [9, 10], 'DE', 'DE'),
    'M_FOOD_227': ('season_pomegranate', [10, 11], 'GR', 'Limni, northern Evia'),
    'M_FOOD_398': ('season_pumpkin', [8, 9, 10, 11, 12], 'DE', 'DE-HE'),
    'M_FOOD_307': ('season_melon', [8, 9], 'DE', 'DE-BY'),
    'M_FOOD_114': ('season_spring_onion', list(range(3, 12)), 'DE', 'DE'),
}
PANTRY = {
    'M_FOOD_76': 'alnatura_capers', 'M_FOOD_344': 'alnatura_olives',
    'M_FOOD_345': 'alnatura_black_olives', 'M_FOOD_346': 'alnatura_green_olives',
    'M_FOOD_138': 'alnatura_pickled_cucumber', 'M_FOOD_385': 'alnatura_chickpeas',
    'M_FOOD_237': 'alnatura_kidney_beans', 'M_FOOD_679': 'alnatura_dried_tomatoes',
    'M_FOOD_133': 'jam_product_guidance', 'M_FOOD_644': 'fruit_spread_label_required',
    'local:de:6765d19c4588510aef2f': 'strawberry_jam_product_guidance',
    'local:ru:9e49d4451eedbb24c39e': 'raspberry_jam_product_guidance',
}
JAMS = (
    ('local:de:6765d19c4588510aef2f', 'Strawberry jam', '4260248063892', 'xucker_strawberry_spread'),
    ('local:ru:9e49d4451eedbb24c39e', 'Raspberry jam', '4260248063908', 'xucker_raspberry_spread'),
)
NAMES = (
    ('M_FOOD_591', 'Kräuterseitlinge', ('Kräuterseitlinge',)),
    ('M_FOOD_227', 'Granatapfel', ('Granatapfel',)),
    ('M_FOOD_398', 'Hokkaidokürbis', ('Hokkaidokürbis',)),
    ('M_FOOD_644', 'Orangenmarmelade', ('Orangenkonfitüre', 'Orangen-Fruchtaufstrich')),
    (JAMS[0][0], 'Erdbeermarmelade', ('Erdbeerkonfitüre', 'Erdbeer-Fruchtaufstrich')),
    (JAMS[1][0], 'Himbeermarmelade', ('Himbeerkonfitüre', 'Himbeer-Fruchtaufstrich')),
)


class CatalogLifecycle240(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {lang: catalog.ingredient_choices(lang) for lang in ('el', 'de', 'en')}

    def test_exact_profiles_reach_real_choices_without_relaxing_identity_gate(self):
        expected = PANTRY | {ident: value[0] for ident, value in SEASONS.items()}
        for ident, key in expected.items():
            self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': ident})['profileId'], key)
            for language, rows in self.rows.items():
                self.assertEqual(actual_choice(rows, ident).get('lifecycle', {}).get('profileId'), key, (language, ident))
            for extra in ({'classification': 'equipment'}, {'needsSemanticConfirmation': True}):
                row = {'id': ident} | extra
                lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
                self.assertNotIn('lifecycle', row)
        names = lifecycle.load_lifecycle_data()['canonicalNames']
        for row in catalog.load_release_catalog()['ingredients']:
            key = names.get(row.get('canonicalName', '').lower())
            if key in {'jam_product_guidance', 'strawberry_jam_product_guidance',
                       'raspberry_jam_product_guidance', 'fruit_spread_label_required'}:
                self.assertEqual(row.get('lifecycle', {}).get('profileId'), key, row['id'])

    def test_seasons_cover_twelve_months_and_keep_geographic_boundaries(self):
        for ident, (key, months, country, region) in SEASONS.items():
            for month in range(1, 13):
                data = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country=country, month=month)
                expected = 'year_round' if len(months) == 12 else 'in_season' if month in months else 'unknown'
                self.assertEqual((data['status'], data['months'], data['sourceRegion']), (expected, months, region), (ident, month))
                other = 'GR' if country == 'DE' else 'DE'
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country=other, month=month)['status'], 'unknown')
            self.assertEqual(catalog.ingredient_lifecycle_profile({'ingredientId': ident})['profileId'], key)
        for ident in ('M_FOOD_89', 'M_FOOD_460', 'M_FOOD_591'):
            data = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=1)
            self.assertEqual((data['basis'], data['sourceIds']), ('regional_seasonal_availability', ['bzfe_cultivated_mushrooms']))
        for name in ('Dried shiitake mushrooms', 'Walnut oil', 'Pomegranate juice', 'Melon jam', 'Frozen pumpkin'):
            self.assertNotEqual(profile(name)['seasonality']['status'], 'reviewed', name)
        for ident in ('M_FOOD_399', 'M_FOOD_113', 'M_FOOD_388', 'M_FOOD_358'):
            self.assertNotIn(catalog.ingredient_lifecycle_profile({'ingredientId': ident}).get('profileId'), {v[0] for v in SEASONS.values()})

    def test_restored_pantry_ids_keep_only_exact_product_rules(self):
        for ident, code, days, conditions in (
            ('M_FOOD_76', '42298601', 5, ()),
            ('M_FOOD_344', '4104420211827', 14, ()),
            ('M_FOOD_346', '4104420211827', 14, ()),
            ('M_FOOD_345', '4104420132085', 14, ()),
            ('M_FOOD_138', '4104420257641', 5, ()),
            ('M_FOOD_385', '4104420230972', 2, ()),
            ('M_FOOD_237', '4104420187894', 3, ('transferred_to_container',)),
            ('M_FOOD_679', '40045528', 2, ()),
        ):
            data = catalog.ingredient_lifecycle_profile({'ingredientId': ident})
            self.assertTrue(all(rule.get('productBarcodes') for rule in data['afterOpening']['rules']))
            self.assertNotEqual(data['seasonality']['status'], 'reviewed')
            lot = {'brand': 'Alnatura', 'barcode': code, 'storage': 'fridge', 'openedAt': '2026-09-25'}
            result = lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=conditions)
            self.assertEqual(result.get('consumeBy'), str(date(2026, 9, 25) + timedelta(days=days)), ident)
            for changes in ({'brand': 'Other'}, {'barcode': None}):
                self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes, temperature_c=4, confirmed_conditions=conditions))
        for ident, code in (('M_FOOD_345', '4104420211827'), ('M_FOOD_346', '4104420132085')):
            self.assertEqual(opening.opening_rules({'ingredientId': ident}, {'brand': 'Alnatura', 'barcode': code}), [])

    def test_jam_windows_require_matching_flavour_brand_barcode_and_handling(self):
        for ident, name, code, rule in JAMS:
            data = profile(name)
            lot = {'brand': 'Xucker', 'barcode': code, 'storage': 'fridge', 'openedAt': '2026-09-25'}
            result = lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=('clean_spoon',))
            self.assertEqual((result['ruleId'], result['daysMin'], result['daysMax'], result['consumeBy']), (rule, 10, 10, '2026-10-05'))
            for changes, temp in (({'brand': 'Other'}, 4), ({'brand': 'dmBio'}, 4), ({'barcode': None}, 4),
                    ({'barcode': code[:-1] + 'X'}, 4), ({'storage': 'pantry'}, 4), ({'storage': 'freezer'}, 4),
                    ({'openedAt': None}, 4), ({}, None), ({}, -1), ({}, 4.1)):
                self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes, temperature_c=temp, confirmed_conditions=('clean_spoon',)))
            for conditions in ((), ('closed_container',)):
                self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=conditions))
            self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-28'}, temperature_c=4, confirmed_conditions=('clean_spoon',))['consumeBy'], '2026-09-28')
            self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 2})['consumeBy'], '2026-09-27')
            generic = catalog.ingredient_lifecycle_profile({'ingredientId': 'M_FOOD_133'})
            self.assertEqual(lifecycle.opening_window(generic, lot, temperature_c=4, confirmed_conditions=('clean_spoon',))['ruleId'], rule)
            for other in {'Strawberry jam', 'Raspberry jam', 'Orange marmalade', 'Strawberries', 'Raspberries', 'Milk jam', 'Chestnut jam', 'Homemade jam'} - {name}:
                self.assertNotIn('consumeBy', lifecycle.opening_window(profile(other), lot, temperature_c=4, confirmed_conditions=('clean_spoon',)), other)

    def test_vague_fruit_spread_labels_never_become_numeric_limits(self):
        for name in ('Apple jam', 'Berry jam', 'Blueberry jam', 'Cherry jam', 'Cranberry jam', 'Orange jam', 'Orange marmalade'):
            data = profile(name)
            self.assertEqual((data['seasonality']['status'], data['afterOpening']['status']), ('not_applicable', 'label_required'))
            for code in ('4260248063892', '4260248063908', '4067796111118'):
                self.assertEqual(opening.opening_rules({'canonicalName': name, 'classification': 'food'}, {'brand': 'Xucker', 'barcode': code}), [])
        for name in ('Jam', 'Strawberry jam'):
            data = profile(name)
            lot = {'brand': 'dmBio', 'barcode': '4067796111118', 'storage': 'fridge', 'openedAt': '2026-09-25'}
            self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=('clean_spoon',)))
            self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 3})['consumeBy'], '2026-09-28')

    def test_selecting_jam_guidance_does_not_open_the_package(self):
        for ident, _, code, rule in JAMS:
            lot = {'brand': 'Xucker', 'barcode': code, 'openingRuleId': rule}
            for language, rows in self.rows.items():
                ingredient = actual_choice(rows, ident)
                offered = opening.opening_rules(ingredient, lot)
                self.assertEqual([(r['id'], r['conditions']) for r in offered], [(rule, ['clean_spoon'])], language)
                with self.assertRaises(ValueError):
                    opening.configure_opening(ingredient, lot)
                configured = opening.configure_opening(ingredient, lot | {'openingConditionsConfirmed': True})
                self.assertEqual(configured['useWithinDays'], 10)
                self.assertNotIn('openedAt', configured)

    def test_supermarket_names_search_and_fruit_flavours_remain_distinct(self):
        for ident, name, aliases in NAMES:
            self.assertEqual(actual_choice(self.rows['de'], ident)['name'], name)
            for alias in aliases:
                self.assertEqual(actual_choice(catalog.ingredient_choices('de', query=alias), ident)['name'], name)
        self.assertEqual(actual_choice(self.rows['el'], 'M_FOOD_398')['name'], 'Κολοκύθα Χοκάιντο')
        for alias in ('Χοκάιντο', 'Hokkaido', 'onion squash'):
            self.assertEqual(actual_choice(catalog.ingredient_choices('el', query=alias), 'M_FOOD_398')['name'], 'Κολοκύθα Χοκάιντο')
        for language, rows in self.rows.items():
            ids = [actual_choice(rows, ident)['id'] for ident in ('M_FOOD_133', 'M_FOOD_644', JAMS[0][0], JAMS[1][0])]
            self.assertEqual(len(set(ids)), 4, language)


if __name__ == '__main__':
    unittest.main()
