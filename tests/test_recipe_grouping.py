from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "custom_components/cook4me/recipe_grouping.py"
spec = importlib.util.spec_from_file_location("cook4me_recipe_grouping", path)
grouping = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(grouping)


def variant(variant_id: str, servings: int, language: str, market: str):
    return {
        "variantId": variant_id,
        "recipeFunctionalId": variant_id,
        "language": language,
        "market": market,
        "yield": {"quantity": servings, "quantityDisplay": str(servings)},
    }


class RecipeGroupingTests(unittest.TestCase):
    def test_same_recipe_serving_variants_are_one_card(self):
        device = {
            "items": [{
                "groupingFunctionalId": "257575",
                "recipeFunctionalId": "270860",
                "displayVariantId": "270860",
                "sendVariantId": "270860",
                "language": "de",
                "market": "GS_DE",
                "title": "Pfifferling-Risotto",
                "yield": {"quantity": 4},
                "variants": [
                    variant("270859", 2, "de", "GS_DE"),
                    variant("270860", 4, "de", "GS_DE"),
                    variant("270858", 6, "de", "GS_DE"),
                ],
            }]
        }
        result = grouping.merge_hydrated_catalogs(
            device,
            device,
            target_language="de",
            configured_language="de",
            device_country="DE",
            strict_language=True,
        )
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(item["availableServings"], [2.0, 4.0, 6.0])
        self.assertEqual(len(item["servingVariants"]), 3)

    def test_exact_same_title_photo_different_top_ids_merge_as_servings(self):
        items = {
            "items": [
                {
                    "groupingFunctionalId": "g2",
                    "recipeFunctionalId": "v2",
                    "displayVariantId": "v2",
                    "language": "it",
                    "market": "GS_IT",
                    "title": "Omelette di mele",
                    "cover": "https://example.test/apple-omelette.jpg",
                    "yield": {"quantity": 2},
                    "variants": [variant("v2", 2, "it", "GS_IT")],
                },
                {
                    "groupingFunctionalId": "g4",
                    "recipeFunctionalId": "v4",
                    "displayVariantId": "v4",
                    "language": "it",
                    "market": "GS_IT",
                    "title": "Omelette di mele",
                    "cover": "https://example.test/apple-omelette.jpg",
                    "yield": {"quantity": 4},
                    "variants": [variant("v4", 4, "it", "GS_IT")],
                },
                {
                    "groupingFunctionalId": "g6",
                    "recipeFunctionalId": "v6",
                    "displayVariantId": "v6",
                    "language": "it",
                    "market": "GS_IT",
                    "title": "Omelette di mele",
                    "cover": "https://example.test/apple-omelette.jpg",
                    "yield": {"quantity": 6},
                    "variants": [variant("v6", 6, "it", "GS_IT")],
                },
            ]
        }
        result = grouping.merge_hydrated_catalogs(
            items,
            items,
            target_language="it",
            configured_language="it",
            device_country="IT",
            strict_language=True,
        )
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["availableServings"], [2.0, 4.0, 6.0])

    def test_strict_german_keeps_hydrated_german_recipe(self):
        de = {
            "items": [{
                "groupingFunctionalId": "257575",
                "recipeFunctionalId": "270859",
                "displayVariantId": "270859",
                "sendVariantId": "270859",
                "language": "de",
                "market": "GS_DE",
                "title": "Pfifferling-Risotto",
                "cover": "https://example.test/risotto.jpg",
                "steps": [{"instruction": "Zutaten vorbereiten."}],
                "variants": [variant("270859", 2, "de", "GS_DE")],
            }]
        }
        result = grouping.merge_hydrated_catalogs(
            de,
            de,
            target_language="de",
            configured_language="de",
            device_country="DE",
            strict_language=True,
        )
        self.assertEqual([item["title"] for item in result["items"]], ["Pfifferling-Risotto"])
        self.assertEqual(result["items"][0]["language"], "de")

    def test_auto_greek_falls_back_to_device_language_not_random_sibling(self):
        display = {
            "items": [{
                "groupingFunctionalId": "999999",
                "recipeFunctionalId": "888888",
                "language": "cs",
                "title": "Cizí rizoto",
            }]
        }
        device = {
            "items": [{
                "groupingFunctionalId": "257575",
                "recipeFunctionalId": "270859",
                "displayVariantId": "270859",
                "sendVariantId": "270859",
                "language": "de",
                "market": "GS_DE",
                "title": "Pfifferling-Risotto",
                "variants": [variant("270859", 2, "de", "GS_DE")],
            }]
        }
        result = grouping.merge_hydrated_catalogs(
            display,
            device,
            target_language="el",
            configured_language="de",
            device_country="DE",
            strict_language=False,
        )
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(item["title"], "Pfifferling-Risotto")
        self.assertEqual(item["language"], "de")
        self.assertTrue(item["translationRequired"])

    def test_same_serving_display_sibling_is_used_for_text(self):
        display = {
            "items": [{
                "groupingFunctionalId": "500",
                "recipeFunctionalId": "el4",
                "displayVariantId": "el4",
                "language": "el",
                "market": "GS_GR",
                "title": "Ριζότο",
                "variants": [variant("el2", 2, "el", "GS_GR"), variant("el4", 4, "el", "GS_GR")],
            }]
        }
        device = {
            "items": [{
                "groupingFunctionalId": "500",
                "recipeFunctionalId": "de4",
                "displayVariantId": "de4",
                "sendVariantId": "de4",
                "language": "de",
                "market": "GS_DE",
                "title": "Risotto",
                "variants": [variant("de2", 2, "de", "GS_DE"), variant("de4", 4, "de", "GS_DE")],
            }]
        }
        result = grouping.merge_hydrated_catalogs(
            display,
            device,
            target_language="el",
            configured_language="de",
            device_country="DE",
            strict_language=False,
        )
        options = result["items"][0]["servingVariants"]
        self.assertEqual(options[0]["displayVariantId"], "el2")
        self.assertEqual(options[0]["sendVariantId"], "de2")
        self.assertEqual(options[1]["displayVariantId"], "el4")
        self.assertEqual(options[1]["sendVariantId"], "de4")

    def test_same_group_exposes_language_menu_with_servings_per_language(self):
        display = {
            "items": [{
                "groupingFunctionalId": "500",
                "recipeFunctionalId": "el4",
                "displayVariantId": "el4",
                "language": "el",
                "market": "GS_GR",
                "title": "Ριζότο",
                "variants": [variant("el2", 2, "el", "GS_GR"), variant("el4", 4, "el", "GS_GR")],
            }]
        }
        device = {
            "items": [{
                "groupingFunctionalId": "500",
                "recipeFunctionalId": "de4",
                "displayVariantId": "de4",
                "language": "de",
                "market": "GS_DE",
                "title": "Risotto",
                "variants": [variant("de2", 2, "de", "GS_DE"), variant("de4", 4, "de", "GS_DE")],
            }]
        }
        result = grouping.merge_hydrated_catalogs(
            display,
            device,
            target_language="el",
            configured_language="de",
            device_country="DE",
            strict_language=False,
        )
        item = result["items"][0]
        self.assertEqual(item["availableLanguages"], ["el", "de"])
        self.assertEqual([row["language"] for row in item["languageVariants"]], ["el", "de"])
        greek = item["languageVariants"][0]
        german = item["languageVariants"][1]
        self.assertEqual([row["servings"] for row in greek["servingVariants"]], [2.0, 4.0])
        self.assertEqual([row["servings"] for row in german["servingVariants"]], [2.0, 4.0])
        # Both display languages map the selected serving to the independently
        # validated device-locale send variant.
        self.assertEqual(greek["servingVariants"][0]["sendVariantId"], "de2")
        self.assertEqual(german["servingVariants"][0]["sendVariantId"], "de2")


if __name__ == "__main__":
    unittest.main()
