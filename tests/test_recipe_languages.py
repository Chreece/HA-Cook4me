from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "custom_components/cook4me/recipe_languages.py"
spec = importlib.util.spec_from_file_location("cook4me_recipe_languages", path)
langs = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(langs)


class RecipeLanguageTests(unittest.TestCase):
    def test_observed_catalog_languages_include_current_samples(self):
        codes = {row["code"] for row in langs.language_options()}
        for code in ("el", "de", "en", "sk", "hu", "cs", "pt", "bg"):
            self.assertIn(code, codes)

    def test_language_market_mapping(self):
        self.assertEqual(langs.country_for_language("el", "DE"), "GR")
        self.assertEqual(langs.country_for_language("de", "GR"), "DE")
        self.assertEqual(langs.country_for_language("ja", "DE"), "JP")

    def test_unknown_language_keeps_device_country(self):
        self.assertEqual(langs.country_for_language("xx", "DE"), "DE")

    def test_codes_are_unique(self):
        codes = [row["code"] for row in langs.language_options()]
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
