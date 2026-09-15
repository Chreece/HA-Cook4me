from __future__ import annotations

import importlib
from pathlib import Path
import socket
import sys
import types
import unittest
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/cook4me"


class CatalogPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = types.ModuleType("cook4me_presentation_test")
        package.__path__ = [str(COMPONENT)]
        sys.modules[package.__name__] = package
        cls.release = importlib.import_module(f"{package.__name__}.release_catalog")
        cls.presentation = importlib.import_module(f"{package.__name__}.catalog_presentation")
        cls.payload = cls.release.load_release_catalog()

    def search(self, query, **kwargs):
        with patch.object(socket, "socket", side_effect=AssertionError("catalog opened network")):
            return self.release.search_release_recipes(query, language="el", configured_language="de", country="DE", group_families=True, **kwargs)

    def test_rice_collapses_sixty_quantity_and_language_publications(self):
        result = self.search("arroz", size=50)
        rice = result["items"][0]
        self.assertEqual(rice["canonicalName"], "Rice")
        self.assertEqual(rice["publicationCount"], 60)
        self.assertIn("es", rice["availableLanguages"])
        self.assertIn("de", rice["availableLanguages"])
        self.assertEqual(rice["availableServings"], [200, 300, 400, 500, 600])
        self.assertTrue(all(row["label"].endswith("g") for row in rice["servingVariants"]))
        self.assertEqual(len({row["displayFamilyId"] for row in result["items"]}), len(result["items"]))
        self.assertLess(result["page"]["totalElements"], result["rawMatchedPublications"])

    def test_grouping_happens_before_pagination_and_selected_catalogs_remain_respected(self):
        first = self.search("arroz", size=7, catalog_languages=["es", "pt"])
        second = self.search("arroz", size=7, page=1, catalog_languages=["es", "pt"])
        self.assertEqual(len(first["items"]), 7)
        self.assertEqual(first["page"]["totalElements"], second["page"]["totalElements"])
        self.assertFalse({r["displayFamilyId"] for r in first["items"]} & {r["displayFamilyId"] for r in second["items"]})
        for row in first["items"]+second["items"]:
            self.assertIn(row["language"], {"es", "pt"})
            self.assertLessEqual(set(row["availableLanguages"]), {"es", "pt"})

    def test_requested_quantity_keeps_its_actual_ingredient_amounts_and_delivery_identity(self):
        for variant, quantity in [("258313", 200), ("258312", 500)]:
            row = self.release.recipe_by_variant(variant, language="el", configured_language="de", country="DE", group_families=True)
            self.assertEqual(row["displayVariantId"], variant)
            self.assertEqual(row["ingredients"][0]["quantity"], quantity)
            self.assertEqual(row["yield"]["quantity"], quantity)
            self.assertFalse(row.get("sendVariantId"), "A shared display family cannot invent a cross-language device proof")
        german = self.release.recipe_by_variant("278301", language="de", configured_language="de", country="DE", group_families=True)
        self.assertEqual(german["sendVariantId"], "278301")
        self.assertEqual(german["sendGroupingFunctionalId"], "3141015")

    def test_rice_has_no_assigned_profile_and_specific_reference_types_are_separate(self):
        ingredient = {"ingredientId": "M_FOOD_421", "foodName": "Arroz"}
        self.assertIsNone(self.release.ingredient_nutrition_profile(ingredient))
        self.assertEqual(self.release.ingredient_display_name(ingredient, "el"), "Ρύζι")
        references = self.release.ingredient_nutrition_references(ingredient, "el")
        self.assertEqual(len(references), 4)
        self.assertTrue(all(row["referenceOnly"] for row in references))
        cooked = next(row for row in references if row["name"] == "Μαγειρεμένο ρύζι")
        self.assertEqual(cooked["nutrition"]["values"]["energyKcal"], 129)
        self.assertIsNone(self.release.ingredient_nutrition_profile(ingredient))
        self.assertEqual(self.release.ingredient_nutrition_references({"ingredientId": "unknown", "name": "Rice"}, "el"), [])

    def test_clean_names_preserve_food_specifications_but_remove_recipe_prose(self):
        pairs = {"/2 onion, peeled and chopped": "onion", "/5 teaspoon red chili paste (to taste)": "red chili paste", "100 g vegetarian steaks": "vegetarian steaks", "175 g red mullet, scaled and cleaned": "red mullet", "2 tbsp mirin": "mirin", "2 tbsp red wine vinegar": "red wine vinegar", "00 Pasta flour": "00 Pasta flour", "100% pistachio cream": "100% pistachio cream", "15% fat cream": "15% fat cream"}
        for raw, expected in pairs.items():
            self.assertEqual(self.presentation.clean_name(raw), expected)

    def test_real_picker_has_one_localized_choice_for_rice_onion_and_mirin(self):
        rows = self.release.ingredient_choices("el")
        for name in ("Ρύζι", "Κρεμμύδι", "Μίριν"):
            selected = [row for row in rows if row["name"] == name]
            self.assertEqual(len(selected), 1, name)
            self.assertIn(selected[0]["ingredientId"], selected[0]["sourceIngredientIds"])
        self.assertLess(len(rows), len(self.payload["ingredients"])/2)
        self.assertFalse(any(row["name"].startswith(("/2 ", "/5 ", "2 tbsp ", "175 g ")) for row in rows))
        self.assertEqual(len({row["displayGroupId"] for row in rows}), len(rows))
        self.assertEqual(len(self.payload["ingredients"]), 11748)


if __name__ == "__main__":
    unittest.main()
