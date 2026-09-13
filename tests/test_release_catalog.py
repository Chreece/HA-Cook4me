from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components/cook4me/release_catalog.py"
spec = importlib.util.spec_from_file_location("cook4me_release_catalog_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class ReleaseCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "merged.json"
        mod._CATALOG_PATH = self.path
        mod.load_release_catalog.cache_clear()

    def tearDown(self):
        mod.load_release_catalog.cache_clear()
        self.tmp.cleanup()

    @staticmethod
    def _recipe_ingredient() -> dict:
        return {
            "ingredientId": "M_FOOD_TOMATO",
            "key": "M_FOOD_TOMATO",
            "quantity": 400,
            "unit": "g",
        }

    def _write(self, complete=True, *, include_de=True):
        variants = [
            {
                "variantId": "VAR_EN",
                "recipeFunctionalId": "REC_EN",
                "groupingFunctionalId": "GROUP_1",
                "title": "Tomato soup",
                "language": "en",
                "market": "GS_GB",
                "servings": 4,
                "ingredients": [self._recipe_ingredient()],
                "nutrition": {
                    "totals": {"energyKcal": 72},
                    "perServing": {"energyKcal": 18},
                    "coverage": 1,
                    "estimated": True,
                },
            }
        ]
        if include_de:
            variants.append(
                {
                    "variantId": "VAR_DE",
                    "recipeFunctionalId": "REC_DE",
                    "groupingFunctionalId": "GROUP_1",
                    "title": "Tomatensuppe",
                    "language": "de",
                    "market": "GS_DE",
                    "servings": 4,
                    "ingredients": [self._recipe_ingredient()],
                    "nutrition": {
                        "totals": {"energyKcal": 72},
                        "perServing": {"energyKcal": 18},
                        "coverage": 1,
                        "estimated": True,
                    },
                }
            )
        self.path.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "catalogVersion": "test-release",
                    "complete": complete,
                    "ingredients": [
                        {
                            "id": "M_FOOD_TOMATO",
                            "key": "M_FOOD_TOMATO",
                            "canonicalName": "Tomato",
                            "translations": {"en": "Tomato", "de": "Tomate"},
                            "nutrition": {
                                "basis": "per100g",
                                "values": {"energyKcal": 18, "protein": 0.9},
                                "source": "usda_fdc",
                            },
                        }
                    ],
                    "recipes": [
                        {
                            "groupingFunctionalId": "GROUP_1",
                            "canonicalName": "Tomato soup",
                            "variants": variants,
                        }
                    ],
                    "source": {
                        "auditedCatalogCount": 28,
                        "sourceCatalogCount": 21,
                    },
                }
            ),
            encoding="utf-8",
        )
        mod.load_release_catalog.cache_clear()

    def test_incomplete_catalog_never_activates(self):
        self._write(complete=False)
        self.assertFalse(mod.release_catalog_ready())
        self.assertFalse(mod.release_catalog_summary()["offlineSearchReady"])

    def test_ingredient_picker_is_compact_localized_and_keeps_canonical_identity(self):
        self._write()
        rows = mod.ingredient_rows("de")
        self.assertEqual(rows[0]["id"], "M_FOOD_TOMATO")
        self.assertEqual(rows[0]["key"], "M_FOOD_TOMATO")
        self.assertEqual(rows[0]["name"], "Tomate")
        self.assertEqual(rows[0]["canonicalName"], "Tomato")
        self.assertNotIn("nutrition", rows[0])

        enriched = mod.ingredient_rows("de", include_nutrition=True)
        self.assertEqual(enriched[0]["nutrition"]["values"]["energyKcal"], 18)

    def test_offline_search_resolves_normalized_ingredient_reference(self):
        self._write()
        result = mod.search_release_recipes(
            "tomate",
            language="de",
            configured_language="de",
            country="DE",
            strict_language=True,
        )
        self.assertEqual(len(result["items"]), 1)
        ingredient = result["items"][0]["ingredients"][0]
        self.assertEqual(ingredient["ingredientId"], "M_FOOD_TOMATO")
        self.assertEqual(ingredient["name"], "Tomate")
        self.assertEqual(ingredient["canonicalName"], "Tomato")
        self.assertNotIn("translations", ingredient)
        self.assertNotIn("nutrition", ingredient)

    def test_offline_search_selects_display_language_and_device_send_variant(self):
        self._write()
        result = mod.search_release_recipes(
            "tomato",
            language="en",
            configured_language="de",
            country="DE",
            strict_language=True,
        )
        self.assertTrue(result["offline"])
        self.assertFalse(result["checkedOnline"])
        self.assertEqual(result["items"][0]["title"], "Tomato soup")
        self.assertEqual(result["items"][0]["displayVariantId"], "VAR_EN")
        self.assertEqual(result["items"][0]["sendVariantId"], "VAR_DE")
        self.assertTrue(result["items"][0]["sendable"])
        self.assertEqual(result["items"][0]["nutrition"]["perServing"]["energyKcal"], 18)

    def test_foreign_only_recipe_remains_visible_but_not_sendable(self):
        self._write(include_de=False)
        result = mod.search_release_recipes(
            "tomato",
            language="en",
            configured_language="de",
            country="DE",
            strict_language=True,
        )
        self.assertEqual(len(result["items"]), 1)
        item = result["items"][0]
        self.assertEqual(item["displayVariantId"], "VAR_EN")
        self.assertFalse(item["sendable"])
        self.assertNotIn("sendVariantId", item)
        self.assertNotIn("sendRecipeFunctionalId", item)

    def test_strict_language_uses_prebuilt_language_index(self):
        self._write()
        payload = mod.load_release_catalog()
        self.assertEqual(payload["_runtimeRecipeByLanguage"]["de"], (0,))
        self.assertEqual(payload["_runtimeRecipeByLanguage"]["en"], (0,))
        self.assertEqual(payload["_runtimeRawVariantCount"], 2)

    def test_strict_language_does_not_mislabel_fallback_variant_as_source_catalog(self):
        self._write()
        result = mod.search_release_recipes(
            "",
            language="fr",
            configured_language="de",
            country="DE",
            strict_language=True,
        )
        self.assertEqual(result["items"], [])
        self.assertEqual(result["page"]["totalElements"], 0)


if __name__ == "__main__":
    unittest.main()
