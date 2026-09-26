"""Batch 31: exact BBQ/horseradish opening clocks and fresh horseradish season."""
import json
from pathlib import Path
import unittest

from test_catalog_lifecycle_v227 import lifecycle, profile

ROOT = Path(__file__).resolve().parents[1]


class CatalogLifecycle247(unittest.TestCase):
    def test_exact_heinz_barbecue_package_has_fourteen_day_clock(self):
        for name in ('Barbecue sauce', 'BBQ sauce'):
            data = profile(name)
            self.assertEqual(data['profileId'], 'barbecue_sauce_product_guidance')
            self.assertEqual(data['seasonality']['status'], 'not_applicable')
            lot = {
                'brand': 'Heinz',
                'barcode': '8715700036106',
                'storage': 'fridge',
                'openedAt': '2026-09-26',
            }
            found = lifecycle.opening_window(data, lot, temperature_c=4)
            self.assertEqual(
                (found['ruleId'], found['daysMin'], found['daysMax'], found['remindOn'], found['consumeBy']),
                ('heinz_barbecue_10l', 14, 14, '2026-10-10', '2026-10-10'),
            )
            self.assertFalse(found['safetyGuarantee'])
            for changes, temperature in (
                ({'brand': 'Other'}, 4),
                ({'barcode': '8715700036113'}, 4),
                ({'storage': 'pantry'}, 4),
                ({'openedAt': None}, 4),
                ({}, 4.1),
                ({}, None),
            ):
                self.assertNotIn(
                    'consumeBy',
                    lifecycle.opening_window(data, lot | changes, temperature_c=temperature),
                    (name, changes, temperature),
                )
            self.assertEqual(
                lifecycle.opening_window(data, lot | {'bestBefore': '2026-09-30'}, temperature_c=4)['consumeBy'],
                '2026-09-30',
            )
            self.assertEqual(
                lifecycle.opening_window(data, lot | {'useWithinDays': 5})['consumeBy'],
                '2026-10-01',
            )

    def test_honey_barbecue_stays_unmapped_until_exact_package_evidence_exists(self):
        data = profile('Honey barbecue sauce')
        self.assertNotIn('profileId', data)
        lot = {
            'brand': 'Heinz',
            'barcode': '8715700036106',
            'storage': 'fridge',
            'openedAt': '2026-09-26',
        }
        self.assertNotIn('consumeBy', lifecycle.opening_window(data, lot, temperature_c=4))

    def test_fresh_horseradish_has_only_the_reviewed_bavarian_harvest_month(self):
        data = profile('Horseradish')
        self.assertEqual(data['profileId'], 'season_horseradish_by')
        self.assertEqual(data['afterOpening']['status'], 'unknown')
        for month in range(1, 13):
            de = lifecycle.seasonal_availability(data, country='DE', month=month)
            self.assertEqual(de['status'], 'in_season' if month == 10 else 'unknown')
            self.assertEqual((de['months'], de['sourceRegion'], de['basis']), ([10], 'DE-BY', 'outdoor_harvest'))
            self.assertEqual(lifecycle.seasonal_availability(data, country='GR', month=month)['status'], 'unknown')
        for other in ('Horseradish sauce', 'Daikon radish', 'Korean radish', 'Takuan pickled daikon',
                      'Dried daikon strips', 'Daikon sprouts'):
            if other == 'Horseradish sauce':
                self.assertNotEqual(profile(other)['profileId'], 'season_horseradish_by')
            else:
                self.assertNotIn('profileId', profile(other), other)

    def test_exact_byodo_prepared_horseradish_has_twenty_one_day_clock(self):
        data = profile('Horseradish sauce')
        self.assertEqual(data['profileId'], 'horseradish_sauce_product_guidance')
        self.assertEqual(data['seasonality']['status'], 'not_applicable')
        lot = {
            'brand': 'Byodo',
            'barcode': '4018462160558',
            'storage': 'fridge',
            'openedAt': '2026-09-26',
        }
        for temperature in (2, 4, 7):
            found = lifecycle.opening_window(data, lot, temperature_c=temperature)
            self.assertEqual(
                (found['ruleId'], found['daysMin'], found['daysMax'], found['remindOn'], found['consumeBy']),
                ('byodo_tafelmeerrettich_100', 21, 21, '2026-10-17', '2026-10-17'),
            )
        for changes, temperature in (
            ({'brand': 'Other'}, 4),
            ({'barcode': '4018462160565'}, 4),
            ({'storage': 'pantry'}, 4),
            ({'openedAt': None}, 4),
            ({}, 1.9),
            ({}, 7.1),
            ({}, None),
        ):
            self.assertNotIn(
                'consumeBy',
                lifecycle.opening_window(data, lot | changes, temperature_c=temperature),
                (changes, temperature),
            )
        self.assertEqual(
            lifecycle.opening_window(data, lot | {'bestBefore': '2026-10-01'}, temperature_c=4)['consumeBy'],
            '2026-10-01',
        )

    def test_existing_radish_calendar_is_untouched(self):
        data = profile('Radish')
        self.assertEqual(data['profileId'], 'season_radish')
        self.assertEqual(data['seasonality']['regions'][0]['months'], [4, 5, 6, 7, 8, 9, 10, 11])

    def test_german_supermarket_names_keep_processed_and_fresh_forms_distinct(self):
        de = json.loads(
            (ROOT / 'custom_components/cook4me/catalog_ui_locales/de.json').read_text(encoding='utf-8')
        )
        expected = {
            'barbecue sauce': 'BBQ-Sauce',
            'bbq sauce': 'BBQ-Sauce',
            'honey barbecue sauce': 'Honig-BBQ-Sauce',
            'radish': 'Radieschen',
            'radishes': 'Radieschen',
            'red radishes': 'Rote Radieschen',
            'daikon radish': 'Daikon-Rettich',
            'daikon radish sprouts': 'Daikon-Sprossen',
            'daikon sprouts': 'Daikon-Sprossen',
            'dried daikon strips': 'Getrocknete Daikonstreifen',
            'takuan pickled daikon': 'Takuan (eingelegter Daikon)',
            'julienned takuan pickled radish': 'Takuan (eingelegter Daikon), feine Streifen',
            'korean radish': 'Koreanischer Rettich',
            'horseradish': 'Meerrettich',
            'horseradish sauce': 'Meerrettichsauce',
            'blanched siraegi dried radish greens': 'Blanchierte getrocknete Rettichblätter (Siraegi)',
        }
        for key, value in expected.items():
            self.assertEqual(de['labels'][key], value)
        self.assertIn('Kren', de['searchAliases']['horseradish'])
        self.assertIn('Tafelmeerrettich', de['searchAliases']['horseradish sauce'])
        self.assertIn('Daikon', de['searchAliases']['daikon radish'])


if __name__ == '__main__':
    unittest.main()
