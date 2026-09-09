from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components" / "cook4me" / "release_catalog.py"
spec = importlib.util.spec_from_file_location("cook4me_release_catalog_test", MODULE)
release_catalog = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(release_catalog)


def _payload() -> dict:
    return {
        "schemaVersion": 1,
        "release": {
            "id": "test-catalog",
            "complete": True,
            "failedLanguages": [],
            "failedDetailCount": 0,
            "languageAudit": [
                {"language": "en", "truncated": False},
                {"language": "de", "truncated": False},
            ],
        },
        "ingredients": [
            {
                "id": "M_FOOD_TOMATO",
                "canonicalName": "Tomato",
                "names": {"en": "Tomato", "de": "Tomate"},
                "nutrition": {"energyKcal": 18.0, "protein": 0.9},
            }
        ],
        "recipes": [
            {
                "id": "GROUP_SOUP",
                "canonicalTitle": "Tomato soup",
                "titles": {"en": "Tomato soup", "de": "Tomatensuppe"},
                "ingredients": [
                    {
                        "foodKey": "M_FOOD_TOMATO",
                        "foodName": "Tomato",
                        "quantity": 500,
                        "unit": "g",
                    }
                ],
                "nutrition": {
                    "totals": {"energyKcal": 90.0, "protein": 4.5},
                    "perServing": {"energyKcal": 45.0, "protein": 2.25},
                    "coverage": 1.0,
                },
                "variants": [
                    {
                        "language": "en",
                        "country": "GB",
                        "variantId": "en-soup",
                        "recipeFunctionalId": "en-soup",
                        "groupingFunctionalId": "GROUP_SOUP",
                    },
                    {
                        "language": "de",
                        "country": "DE",
                        "variantId": "de-soup",
                        "recipeFunctionalId": "de-soup",
                        "groupingFunctionalId": "GROUP_SOUP",
                    },
                ],
            }
        ],
    }


class ReleaseCatalogArchitectureTests(unittest.TestCase):
    def _load(self, payload: dict):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return release_catalog.load_release_catalog(path)

    def test_complete_catalog_is_offline_usable_and_localized(self):
        catalog = self._load(_payload())
        self.assertTrue(catalog.complete)
        self.assertTrue(catalog.usable)
        self.assertTrue(catalog.metadata()["rowContractComplete"])

        ingredients = catalog.ingredient_rows("de")
        self.assertEqual(ingredients[0]["key"], "M_FOOD_TOMATO")
        self.assertEqual(ingredients[0]["name"], "Tomate")
        self.assertEqual(ingredients[0]["canonicalName"], "Tomato")
        self.assertEqual(ingredients[0]["nutrition"]["energyKcal"], 18.0)

        recipes = catalog.recipes_for_language("de", query="Tomatensuppe", size=10)
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0]["title"], "Tomatensuppe")
        self.assertEqual(recipes[0]["canonicalTitle"], "Tomato soup")
        self.assertEqual(recipes[0]["searchVariantId"], "de-soup")
        self.assertEqual(recipes[0]["nutrition"]["perServing"]["energyKcal"], 45.0)
        self.assertTrue(recipes[0]["releaseCatalog"])

    def test_failed_detail_disables_release_catalog(self):
        payload = _payload()
        payload["release"]["failedDetailCount"] = 1
        catalog = self._load(payload)
        self.assertFalse(catalog.complete)
        self.assertFalse(catalog.usable)
        self.assertFalse(catalog.metadata()["auditComplete"])

    def test_truncated_language_scan_disables_release_catalog(self):
        payload = _payload()
        payload["release"]["languageAudit"][1]["truncated"] = True
        catalog = self._load(payload)
        self.assertFalse(catalog.complete)
        self.assertFalse(catalog.usable)

    def test_missing_canonical_english_name_disables_release_catalog(self):
        payload = _payload()
        payload["ingredients"][0]["canonicalName"] = ""
        catalog = self._load(payload)
        self.assertFalse(catalog.row_contract_complete)
        self.assertFalse(catalog.usable)

    def test_missing_ingredient_nutrition_disables_release_catalog(self):
        payload = _payload()
        payload["ingredients"][0].pop("nutrition")
        catalog = self._load(payload)
        self.assertFalse(catalog.row_contract_complete)
        self.assertFalse(catalog.usable)

    def test_missing_recipe_nutrition_disables_release_catalog(self):
        payload = _payload()
        payload["recipes"][0].pop("nutrition")
        catalog = self._load(payload)
        self.assertFalse(catalog.row_contract_complete)
        self.assertFalse(catalog.usable)

    def test_repository_bootstrap_catalog_is_deliberately_inert(self):
        catalog = release_catalog.load_release_catalog(
            ROOT / "custom_components" / "cook4me" / "catalog" / "release_catalog.json"
        )
        self.assertFalse(catalog.usable)


if __name__ == "__main__":
    unittest.main()
