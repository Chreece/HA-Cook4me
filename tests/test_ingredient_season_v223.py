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

if __name__=='__main__':unittest.main()
