"""Verify seasonal metadata and persistence with actual catalog contracts."""
import importlib
from pathlib import Path
import sys
from types import ModuleType
import unittest

ROOT=Path(__file__).resolve().parents[1]
PKG='cook4me_season_v223'
pkg=ModuleType(PKG);pkg.__path__=[str(ROOT/'custom_components/cook4me')];sys.modules[PKG]=pkg
filters=importlib.import_module(PKG+'.shared_recipe_filters')
catalog=importlib.import_module(PKG+'.release_catalog')

class SeasonFilterTests(unittest.TestCase):
    def test_opt_in_is_strict_and_survives_user_preference_normalization(self):
        for value in (None, False, 'false', 'true', 1, [], {}):
            self.assertFalse(filters.normalize_filters({'seasonalIngredients':value})['seasonalIngredients'])
        saved=filters.merge_preferences({}, {'filtersByView':{'profile':{'seasonalIngredients':True}}})
        self.assertTrue(saved['filtersByView']['profile']['seasonalIngredients'])
        saved=filters.merge_preferences(saved, {'filtersByView':{'today':{'seasonalIngredients':False}}})
        self.assertTrue(saved['filtersByView']['profile']['seasonalIngredients'])
        self.assertFalse(saved['filtersByView']['today']['seasonalIngredients'])

    def test_actual_choices_include_country_calendars_in_ui_and_market_languages(self):
        for language in ('el','de','en'):
            rows=catalog.ingredient_choices(language)
            reviewed=[row for row in rows if row.get('lifecycle',{}).get('seasonality',{}).get('status')=='reviewed']
            self.assertGreater(len(reviewed),100)
            countries={r['country'] for row in reviewed for r in row['lifecycle']['seasonality']['regions']}
            self.assertTrue({'DE','GR'}.issubset(countries))
            self.assertTrue(all(row['displayLanguage']==language for row in rows))

    def test_recipe_results_apply_the_same_reviewed_country_calendar(self):
        def ingredient(name, months, country='DE'):
            return {
                'name': name,
                'lifecycle': {'seasonality': {'status': 'reviewed', 'regions': [
                    {'country': country, 'months': months}
                ]}},
            }

        def recipe(title, *ingredients):
            return {
                'title': title,
                'mealTypes': ['dinner'],
                'ingredients': list(ingredients),
                'match': {'score': 0},
            }

        rows = [
            recipe('September vegetables', ingredient('Pumpkin', [9, 10])),
            recipe('Spring asparagus', ingredient('Asparagus', [4, 5, 6])),
            recipe('Mixed plate', ingredient('Pumpkin', [9, 10]), ingredient('Asparagus', [4, 5, 6])),
            recipe('Unknown calendar', {'name': 'Unreviewed ingredient'}),
            recipe('Preserved food', {'name': 'Canned beans', 'lifecycle': {
                'seasonality': {'status': 'not_applicable'},
            }}),
        ]
        filtered = filters.apply_filters(
            rows, {'seasonalIngredients': True},
            season_country='DE', season_month=9, score_targets=False,
        )
        self.assertEqual(
            [row['title'] for row in filtered],
            ['September vegetables', 'Unknown calendar', 'Preserved food'],
        )
        unfiltered = filters.apply_filters(
            rows, {'seasonalIngredients': False},
            season_country='DE', season_month=9, score_targets=False,
        )
        self.assertEqual(len(unfiltered), len(rows))

    def test_recipe_season_uses_shopping_country_and_keeps_unknown_country_evidence(self):
        ingredient = {
            'lifecycle': {'seasonality': {'status': 'reviewed', 'regions': [
                {'country': 'DE', 'months': [4, 5, 6]},
                {'country': 'GR', 'months': [9, 10]},
            ]}},
        }
        self.assertFalse(filters.seasonal_ingredient_visible(ingredient, 'DE', 9))
        self.assertTrue(filters.seasonal_ingredient_visible(ingredient, 'GR', 9))
        self.assertTrue(filters.seasonal_ingredient_visible(ingredient, 'FR', 9))
        self.assertTrue(filters.seasonal_ingredient_visible(ingredient, 'DE', None))

    def test_runtime_passes_market_country_and_ha_timezone_month_to_shared_filter(self):
        runtime=(ROOT/'custom_components/cook4me/shared_recipe_runtime.py').read_text()
        self.assertIn('settings["seasonalIngredients"] or (costs is not None and cost_calculator is None)', runtime)
        self.assertIn('ZoneInfo(str(getattr(bridge.hass.config, "time_zone", "") or "UTC"))', runtime)
        self.assertIn('season_country=season_country, season_month=season_month', runtime)


if __name__=='__main__':unittest.main()
