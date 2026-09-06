from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "custom_components/cook4me/recipe_locale.py"
spec = importlib.util.spec_from_file_location("cook4me_recipe_locale", path)
locale = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(locale)


class RecipeLocaleTests(unittest.TestCase):
    def test_greek_ui_uses_greek_display_market(self):
        self.assertEqual(locale.display_country_for_language("el", "DE"), "GR")

    def test_greek_display_keeps_german_device_send_variant(self):
        display = {
            "market": "GS_GR",
            "items": [{
                "groupingFunctionalId": "500",
                "searchVariantId": "900-el",
                "recipeFunctionalId": "900-el",
                "language": "el",
                "title": "Ριζότο μανιταριών",
                "ingredients": ["200 g ρύζι"],
                "sendable": True,
            }],
        }
        device = {
            "market": "GS_DE",
            "items": [{
                "groupingFunctionalId": "500",
                "searchVariantId": "900-de",
                "variantFunctionalId": "900-de",
                "language": "de",
                "title": "Pilzrisotto",
            }],
        }
        result = locale.merge_display_and_device_catalogs(display, device, target_language="el")
        item = result["items"][0]
        self.assertEqual(item["title"], "Ριζότο μανιταριών")
        self.assertEqual(item["language"], "el")
        self.assertEqual(item["sendVariantId"], "900-de")
        self.assertEqual(item["sendGroupingFunctionalId"], "500")
        self.assertEqual(item["sendRecipeFunctionalId"], "900-de")
        self.assertTrue(item["sendable"])
        self.assertTrue(item["localizedBySeb"])
        self.assertFalse(item["translationRequired"])

    def test_foreign_device_result_requests_translation(self):
        device = {
            "market": "GS_DE",
            "items": [{
                "groupingFunctionalId": "500",
                "searchVariantId": "900-sk",
                "variantFunctionalId": "900-sk",
                "language": "sk",
                "title": "Chrumkavé rizoto",
            }],
        }
        result = locale.merge_display_and_device_catalogs({}, device, target_language="el")
        item = result["items"][0]
        self.assertTrue(item["translationRequired"])
        self.assertEqual(item["sourceLanguage"], "sk")
        self.assertTrue(item["sendable"])

    def test_greek_display_only_recipe_is_viewable_but_not_sendable(self):
        display = {
            "market": "GS_GR",
            "items": [{
                "groupingFunctionalId": "701",
                "searchVariantId": "702",
                "recipeFunctionalId": "702",
                "language": "el",
                "title": "Ελληνικό ριζότο",
                "sendable": True,
            }],
        }
        result = locale.merge_display_and_device_catalogs(display, {}, target_language="el")
        item = result["items"][0]
        self.assertEqual(item["title"], "Ελληνικό ριζότο")
        self.assertTrue(item["localizedBySeb"])
        self.assertFalse(item["sendable"])
        self.assertTrue(item["deviceVariantMissing"])

    def test_nonmatching_foreign_display_extra_is_not_duplicated(self):
        display = {
            "market": "GS_GR",
            "items": [{
                "groupingFunctionalId": "999",
                "searchVariantId": "991",
                "language": "pt",
                "title": "Risotto",
            }],
        }
        device = {
            "market": "GS_DE",
            "items": [{
                "groupingFunctionalId": "500",
                "searchVariantId": "501",
                "language": "de",
                "title": "Risotto",
            }],
        }
        result = locale.merge_display_and_device_catalogs(display, device, target_language="el")
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["groupingFunctionalId"], "500")


if __name__ == "__main__":
    unittest.main()
