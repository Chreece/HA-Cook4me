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
    def test_only_v2_proven_official_source_catalogs_are_exposed(self):
        codes = [row["code"] for row in langs.language_options()]
        self.assertEqual(
            codes,
            ["ar", "bg", "cs", "de", "en", "es", "fr", "hr", "hu", "it", "ja", "ko", "pl", "pt", "ro", "ru", "sk", "sl", "tr", "uk", "zh"],
        )
        for code in ("da", "el", "fa", "fi", "nl", "no", "sv"):
            self.assertNotIn(code, codes)

    def test_language_market_mapping(self):
        self.assertEqual(langs.country_for_language("de", "GR"), "DE")
        self.assertEqual(langs.country_for_language("ja", "DE"), "JP")
        self.assertEqual(langs.country_for_language("pt", "DE"), "PT")

    def test_unsupported_language_keeps_device_country(self):
        self.assertEqual(langs.country_for_language("el", "DE"), "DE")
        self.assertFalse(langs.is_official_catalog_language("el"))

    def test_catalog_default_normalizes_to_proven_device_language(self):
        self.assertEqual(langs.normalize_catalog_language("de", "en"), "de")
        self.assertEqual(langs.normalize_catalog_language("el", "de"), "de")

    def test_codes_are_unique(self):
        codes = [row["code"] for row in langs.language_options()]
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()
