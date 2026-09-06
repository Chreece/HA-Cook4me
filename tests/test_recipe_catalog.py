from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "custom_components" / "cook4me" / "vendor"
sys.path.insert(0, str(VENDOR))
path = VENDOR / "cook4me_recipe_catalog.py"
spec = importlib.util.spec_from_file_location("cook4me_recipe_catalog_test", path)
rc = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(rc)


class RecipeCatalogTests(unittest.TestCase):
    def test_real_step_fields_are_not_dropped(self):
        root = {
            "steps": [
                {
                    "fid": {"functionalId": "410287"},
                    "applicationDescription": "Schalotten zerkleinern.",
                    "type": {"key": "PREPARATION", "name": "Preparation"},
                },
                {
                    "fid": {"functionalId": "410289"},
                    "applicationDescription": "Die Hälfte des Öls in die Pfanne geben.",
                    "applianceDescription": "Die Hälfte des Öls in die Pfanne geben.",
                    "type": {"key": "ADD_INGREDIENT"},
                },
            ]
        }
        steps = rc.extract_recipe_steps(root)
        self.assertEqual(steps[0]["instruction"], "Schalotten zerkleinern.")
        self.assertEqual(steps[1]["instruction"], "Die Hälfte des Öls in die Pfanne geben.")
        self.assertEqual(len(steps), 2)

    def test_cover_is_recipe_root_not_nested_brand_logo(self):
        root = {
            "brand": {
                "resourceMedias": [
                    {
                        "isCover": True,
                        "media": {
                            "type": "PHOTO",
                            "thumbnail": "https://example.invalid/red-T-logo.png",
                        },
                    }
                ]
            },
            "resourceMedias": [
                {
                    "isCover": True,
                    "media": {
                        "type": "PHOTO",
                        "thumbnail": "https://example.invalid/actual-recipe.jpg",
                    },
                }
            ],
        }
        self.assertEqual(
            rc.extract_recipe_cover(root),
            "https://example.invalid/actual-recipe.jpg",
        )

    def test_grouping_collapses_variants_and_keeps_device_send_variant(self):
        items = [
            {
                "groupingFunctionalId": "750197",
                "searchVariantId": "de-2",
                "recipeFunctionalId": "de-2",
                "language": "de",
                "market": "GS_DE",
                "yield": {"quantity": 2},
                "title": "Knuspriges Risotto",
                "sendable": True,
            },
            {
                "groupingFunctionalId": "750197",
                "searchVariantId": "el-4",
                "recipeFunctionalId": "el-4",
                "language": "el",
                "market": "GS_GR",
                "yield": {"quantity": 4},
                "title": "Τραγανό ριζότο",
                "sendable": True,
            },
            {
                "groupingFunctionalId": "750197",
                "searchVariantId": "de-4",
                "recipeFunctionalId": "de-4",
                "language": "de",
                "market": "GS_DE",
                "yield": {"quantity": 4},
                "title": "Knuspriges Risotto",
                "sendable": True,
            },
        ]
        result = rc.collapse_variants(
            items,
            preferred_language="el",
            configured_language="de",
            country="DE",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Τραγανό ριζότο")
        self.assertEqual(result[0]["displayVariantId"], "el-4")
        self.assertEqual(result[0]["sendVariantId"], "de-4")
        self.assertEqual(result[0]["availableServings"], [2.0, 4.0])

    def test_distinct_groupings_are_not_deduped_by_title(self):
        items = [
            {"groupingFunctionalId": "1", "searchVariantId": "a", "title": "Same", "language": "de"},
            {"groupingFunctionalId": "2", "searchVariantId": "b", "title": "Same", "language": "de"},
        ]
        result = rc.collapse_variants(
            items,
            preferred_language="de",
            configured_language="de",
            country="DE",
        )
        self.assertEqual(len(result), 2)

    def test_search_dto_cover_is_strict(self):
        row = rc._light_search_row(
            {
                "identifier": {"functionalId": "123"},
                "groupingId": "456",
                "lang": "el",
                "cover": {
                    "media": {
                        "type": "PHOTO",
                        "thumbnail": "https://example.invalid/recipe.jpg",
                    }
                },
                "partnerDetailsMobile": {
                    "media": {"type": "PHOTO", "thumbnail": "https://example.invalid/partner.png"}
                },
            }
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["cover"], "https://example.invalid/recipe.jpg")
        self.assertEqual(row["groupingFunctionalId"], "456")
        self.assertEqual(row["language"], "el")


if __name__ == "__main__":
    unittest.main()
