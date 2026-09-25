"""Plant-drink package identity, clean-spoon guidance and winter calendars."""
from datetime import date, timedelta
import unittest

from test_catalog_lifecycle_v227 import catalog, lifecycle, opening, profile

PACKAGES = (
    ('Almond milk', '4070765022797', 'dmbio_almond_drink', 4, 4, 'stored_upright'),
    ('Almond milk', '4067796002065', 'dmbio_almond_drink_at', 4, 4, 'stored_upright'),
    ('Oat milk', '4070765022780', 'dmbio_oat_gluten_free', 4, 4, 'stored_upright'),
    ('Oat milk', '4067796194807', 'dmbio_oat_natur_at', 3, 4, 'stored_upright'),
    ('Cashew milk', '4070765022810', 'dmbio_cashew_drink', 3, 4, 'stored_upright'),
    ('Ginger juice', '4066447982046', 'dmbio_ginger_juice', 14, 14, 'clean_spoon'),
)

SEASONS = (
    ('M_FOOD_79', [1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12], 'seasonal_calendar_including_stored_produce'),
    ('M_FOOD_341', list(range(1, 13)), 'seasonal_calendar_including_stored_produce'),
    ('M_FOOD_171', list(range(1, 13)), 'regional_seasonal_availability'),
    ('local:pl:97ac0ee4858007c36310', [1, 2, 3, 4, 9, 10, 11, 12], 'regional_seasonal_availability'),
)


def actual_choice(rows, ident):
    return next(r for r in rows if r.get('id') == ident or r.get('key') == ident or ident in r.get('sourceIngredientIds', []))


class CatalogLifecycle231(unittest.TestCase):
    def test_exact_packages_require_handling_and_refrigeration(self):
        for name, code, rule, minimum, maximum, condition in PACKAGES:
            with self.subTest(code=code):
                data = profile(name)
                lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
                for temperature in (0, 4):
                    result = lifecycle.opening_window(data, lot, temperature_c=temperature, confirmed_conditions=(condition,))
                    self.assertEqual((result['ruleId'], result['daysMin'], result['daysMax']), (rule, minimum, maximum))
                    self.assertEqual(result['remindOn'], str(date(2026, 9, 25) + timedelta(days=minimum)))
                    self.assertEqual(result['consumeBy'], str(date(2026, 9, 25) + timedelta(days=maximum)))
                    self.assertFalse(result['safetyGuarantee'])
                for changes, temperature in (({'barcode': None}, 4), ({'barcode': '00000000'}, 4),
                        ({'brand': None}, 4), ({'brand': 'Other'}, 4), ({'storage': 'pantry'}, 4),
                        ({'openedAt': None}, 4), ({}, -0.1), ({}, 4.1), ({}, None)):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot | changes,
                        temperature_c=temperature, confirmed_conditions=(condition,)))
                for unconfirmed in ((), ('closed_container',)):
                    self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4, confirmed_conditions=unconfirmed))
                self.assertEqual(lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-26'},
                    temperature_c=4, confirmed_conditions=(condition,))['consumeBy'], '2026-09-26')
                self.assertEqual(lifecycle.opening_window(data, lot | {'useWithinDays': 1})['consumeBy'], '2026-09-26')

    def test_specific_drinks_reject_other_bases_and_processed_forms(self):
        names = {p[0] for p in PACKAGES} | {'Soy milk', 'Rice milk', 'Coconut milk', 'Coconut drink',
            'Almond cream', 'Almonds', 'Cashews', 'Ginger', 'Ginger shot', 'Lemon juice', 'Milk'}
        for name, code, rule, _, _, condition in PACKAGES:
            lot = {'brand': 'dmBio', 'barcode': code, 'openedAt': '2026-09-25', 'storage': 'fridge'}
            for other in names - {name}:
                self.assertNotIn('consumeBy', lifecycle.opening_window(profile(other), lot,
                    temperature_c=4, confirmed_conditions=(condition,)), (name, other))
            generic = lifecycle.opening_window(profile('Plant milk'), lot, temperature_c=4, confirmed_conditions=(condition,))
            self.assertEqual('consumeBy' in generic, name != 'Ginger juice')
            if name != 'Ginger juice':
                self.assertEqual(generic['ruleId'], rule)

    def test_real_catalog_choices_and_opening_editor(self):
        for language in ('el', 'de'):
            rows = catalog.ingredient_choices(language)
            for name, code, rule, minimum, maximum, condition in PACKAGES:
                ident = 'local:ko:ebae66f49637679858fb' if name == 'Ginger juice' else 'local:en:2d9f581b4fc8823f558a'
                ids = (ident, 'M_FOOD_265') if name == 'Almond milk' else (ident,)
                for ident in ids:
                    ingredient = actual_choice(rows, ident)
                    lot = {'brand': 'dmBio', 'barcode': code}
                    offered = opening.opening_rules(ingredient, lot)
                    self.assertEqual([r['id'] for r in offered], [rule], (language, name, ident))
                    self.assertEqual((offered[0]['daysMin'], offered[0]['daysMax'], offered[0]['conditions']),
                                     (minimum, maximum, [condition]))
                    with self.assertRaises(ValueError):
                        opening.configure_opening(ingredient, lot | {'openingRuleId': rule})
                    configured = opening.configure_opening(ingredient, lot | {'openingRuleId': rule, 'openingConditionsConfirmed': True})
                    self.assertEqual(configured['useWithinDays'], maximum)
                    self.assertNotIn('openedAt', configured)

    def test_exact_provider_almond_mapping_retains_brand_guidance(self):
        ingredient = {'ingredientId': 'M_FOOD_265'}
        self.assertEqual(catalog.ingredient_lifecycle_profile(ingredient)['profileId'], 'alpro_drinks')
        for code in ('4070765022797', '4067796002065'):
            self.assertEqual(len(opening.opening_rules(ingredient, {'brand': 'dmBio', 'barcode': code})), 1)
        self.assertEqual(opening.opening_rules(ingredient, {'brand': 'dmBio', 'barcode': '4070765022780'}), [])
        alpro = opening.opening_rules(ingredient, {'brand': 'Alpro'})
        self.assertEqual([(r['id'], r['daysMax']) for r in alpro], [('alpro_drinks', 5)])
        for row in ({'id': 'M_FOOD_265', 'classification': 'equipment'}, {'id': 'M_FOOD_265', 'needsSemanticConfirmation': True}):
            lifecycle.enrich_catalog_ingredients({'ingredients': [row]})
            self.assertNotIn('lifecycle', row)

    def test_german_supermarket_names_and_search_keep_exact_identity(self):
        names = (
            ('local:pl:97ac0ee4858007c36310', 'Feldsalat', "Lamb's lettuce"),
            ('local:en:2d9f581b4fc8823f558a', 'Pflanzendrink', 'Plant milk'),
            ('local:ko:ebae66f49637679858fb', 'Ingwersaft', 'Ginger juice'),
        )
        rows = catalog.ingredient_choices('de')
        sources = {r['id']: r for r in catalog.load_release_catalog()['ingredients']}
        for ident, german, canonical in names:
            self.assertEqual(actual_choice(rows, ident)['name'], german)
            self.assertEqual(catalog.ingredient_display_name({'ingredientId': ident}, 'de'), german)
            self.assertEqual(actual_choice(catalog.ingredient_choices('de', query=german), ident)['name'], german)
            self.assertEqual(sources[ident]['canonicalName'], canonical)
        self.assertEqual(actual_choice(catalog.ingredient_choices('de', query='Pflanzenmilch'), names[1][0])['name'], 'Pflanzendrink')

    def test_winter_summer_and_country_boundaries(self):
        for ident, months, basis in SEASONS:
            for month in range(1, 13):
                result = catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='DE', month=month)
                expected = 'year_round' if len(months) == 12 else 'in_season' if month in months else 'unknown'
                self.assertEqual(result['status'], expected, (ident, month))
                self.assertEqual((result['months'], result['basis'], result['sourceRegion']), (months, basis, 'DE'))
                self.assertTrue(result['approximate'])
                self.assertEqual(catalog.ingredient_seasonal_availability({'ingredientId': ident}, country='GR', month=month)['status'], 'unknown')
        for name in ('Frozen carrots', 'Pickled onions', 'Carrot juice', 'Dried onion', 'Mixed salad'):
            self.assertNotIn(lifecycle.seasonal_availability(profile(name), country='DE', month=2)['status'], ('in_season', 'year_round'))


if __name__ == '__main__':
    unittest.main()
