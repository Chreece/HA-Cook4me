from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, COMPONENT / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


logic = load("cook4me_recipe_logic_v253_test", "recipe_logic.py")
subs = load("cook4me_ingredient_substitutions_v253_test", "ingredient_substitutions.py")


def target(identifier, name):
    return {
        "id": identifier,
        "conceptId": f"concept:food:{identifier}",
        "canonicalName": name,
        "classification": "food",
    }


TARGETS = [
    target("tofu", "Tofu"),
    target("mushrooms", "Mushrooms"),
    target("chickpeas", "Chickpeas"),
    target("veg-stock", "Vegetable stock"),
    target("veg-stock-cube", "Vegetable stock cube"),
    target("water", "Water"),
    target("coconut-cream", "Coconut cream"),
    target("soy-cream", "Soy cream"),
    target("soy-milk", "Soy milk"),
    target("soy-milk-unsweet", "Unsweetened soy milk"),
    target("rice-milk", "Rice milk"),
    target("olive-oil", "Olive oil"),
    target("coconut-oil", "Coconut oil"),
    target("maple", "Maple syrup"),
    target("agave", "Agave syrup"),
    target("sugar", "Sugar"),
    target("soy-sauce", "Soy sauce"),
    target("agar", "Agar-agar"),
    target("pectin", "Pectin"),
    target("cornstarch", "Cornstarch"),
    target("lemon", "Lemon juice"),
    target("citric", "Citric acid"),
    target("flax", "Ground flaxseed"),
]


def profile(diet, *, allergies=(), avoid=()):
    return {
        "diet": diet,
        "allergies": list(allergies),
        "avoid": list(avoid),
        "pantry": [],
        "preferences": [],
        "habitTerms": [],
    }


class CatalogOwnedSubstitutionTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            target("cod", "Cod"),
            target("milk", "Milk"),
            target("egg-white", "Egg whites"),
            target("gelatin", "Gelatin"),
            target("rennet", "Animal rennet"),
            target("stock", "Chicken stock"),
            target("honey", "Honey"),
            target("cheese", "Cheese"),
            target("yogurt", "Yogurt"),
            target("whey", "Whey"),
        ]
        self.payload = {"ingredients": [*TARGETS, *self.sources]}
        self.summary = subs.enrich_catalog_substitutions(self.payload)
        self.by_id = {row["id"]: row for row in self.payload["ingredients"]}

    def test_catalog_rows_own_multiple_real_targets(self):
        cod = self.by_id["cod"]
        self.assertEqual(
            [row["key"] for row in cod["substitutions"]],
            ["tofu", "mushrooms", "chickpeas"],
        )
        self.assertEqual(cod["substitutionDiets"], ["vegetarian", "vegan"])
        self.assertEqual(
            [row["target"]["conceptId"] for row in cod["substitutions"]],
            [
                "concept:food:tofu",
                "concept:food:mushrooms",
                "concept:food:chickpeas",
            ],
        )

    def test_compound_and_reviewed_virtual_targets_stay_catalog_metadata(self):
        egg = self.by_id["egg-white"]
        candidates = {row["key"]: row for row in egg["substitutions"]}
        self.assertTrue(candidates["aquafaba"]["target"]["substitutionOnly"])
        self.assertEqual(
            [part["target"]["conceptId"] for part in candidates["ground_flaxseed_water"]["components"]],
            ["concept:food:flax", "concept:food:water"],
        )
        self.assertEqual(candidates["aquafaba"]["catalogSource"], "ingredient_substitutions.v1")

    def test_recipe_mounts_all_safe_catalog_candidates(self):
        cod = self.by_id["cod"]
        match = logic.score_recipe(
            {"title": "Cod", "ingredients": [cod]},
            profile("vegetarian", allergies=("soy",)),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        row = match["substitutions"][0]
        self.assertEqual(row["source"], "ingredient_catalog")
        self.assertEqual([item["key"] for item in row["alternatives"]], ["mushrooms", "chickpeas"])
        self.assertEqual(row["replacement"]["key"], "mushrooms")
        self.assertEqual(match["substitutionCandidateCount"], 2)
        self.assertEqual(match["substitutionSources"], ["ingredient_catalog"])

    def test_catalog_metadata_conflict_mounts_without_text_guessing(self):
        source = target("provider-protein", "Provider protein")
        source["substitutionDiets"] = ["vegetarian"]
        source["substitutions"] = list(self.by_id["cod"]["substitutions"])
        match = logic.score_recipe(
            {"title": "Provider recipe", "ingredients": [source]},
            profile("vegetarian"),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutionSources"], ["ingredient_catalog"])
        self.assertEqual(
            [row["key"] for row in match["substitutions"][0]["alternatives"]],
            ["tofu", "mushrooms", "chickpeas"],
        )

    def test_filtering_can_remove_some_candidates_without_hiding_recipe(self):
        milk = self.by_id["milk"]
        match = logic.score_recipe(
            {"title": "Milk recipe", "ingredients": [milk]},
            profile("vegan", allergies=("soy",)),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        alternatives = match["substitutions"][0]["alternatives"]
        self.assertEqual([row["key"] for row in alternatives], ["rice_milk"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "rice_milk")

    def test_catalog_excluded_ingredient_identity_filters_candidate(self):
        cod = self.by_id["cod"]
        selected = profile("vegetarian", allergies=("soy",))
        selected["excludedIngredients"] = [
            {"ingredientId": "mushrooms", "canonicalName": "Different display label"}
        ]
        match = logic.score_recipe(
            {"title": "Cod", "ingredients": [cod]},
            selected,
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(
            [row["key"] for row in match["substitutions"][0]["alternatives"]],
            ["chickpeas"],
        )

    def test_all_filtered_candidates_fail_closed(self):
        cod = self.by_id["cod"]
        match = logic.score_recipe(
            {"title": "Cod", "ingredients": [cod]},
            profile("vegetarian", avoid=("tofu", "mushrooms", "chickpeas")),
        )
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertFalse(match["substitutionCoverageComplete"])

    def test_unmapped_manual_recipe_retains_legacy_fallback_only(self):
        match = logic.score_recipe(
            {"title": "Manual cod", "ingredients": [{"name": "Cod"}]},
            profile("vegetarian"),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutionSources"], ["legacy_text_fallback"])
        self.assertEqual(match["substitutions"][0]["candidateCount"], 1)

    def test_substitution_catalog_resolves_all_declared_profiles(self):
        self.assertGreater(self.summary["ingredientCount"], 0)
        self.assertGreater(self.summary["sourceProfiles"], 0)
        self.assertGreater(self.summary["virtualIngredientCount"], 0)
        self.assertEqual(self.summary["missingProfiles"], [])
        self.assertEqual(self.summary["unresolvedTargets"], [])
        aquafaba = self.by_id["substitution:aquafaba"]
        self.assertTrue(aquafaba["substitutionOnly"])
        self.assertEqual(aquafaba["classification"], "substitution")
        self.assertEqual(aquafaba["conceptId"], "concept:substitution:aquafaba")

    def test_source_to_candidate_mapping_is_catalog_data_not_python_lists(self):
        catalog = subs.load_substitution_catalog()
        profiles = catalog.get("sourceProfiles") or []
        self.assertTrue(profiles)
        animal = next(row for row in profiles if row.get("id") == "animal_protein")
        self.assertEqual(animal["candidateKeys"], ["tofu", "mushrooms", "chickpeas"])
        source = (COMPONENT / "ingredient_substitutions.py").read_text(encoding="utf-8")
        self.assertIn('catalog.get("sourceProfiles")', source)
        self.assertNotIn('return ["tofu", "mushrooms", "chickpeas"]', source)

    def test_release_catalog_and_ingredient_info_expose_substitutions(self):
        core = (COMPONENT / "release_catalog_v60_core.py").read_text(encoding="utf-8")
        presentation = (COMPONENT / "catalog_presentation.py").read_text(encoding="utf-8")
        api = (COMPONENT / "websocket_v18.py").read_text(encoding="utf-8")
        self.assertIn('"substitutions"', core)
        self.assertIn('"substitutionDiets"', core)
        self.assertIn('"substitutions"', presentation)
        self.assertIn('raw.get("substitutionOnly")', presentation)
        self.assertIn('"catalogSubstitutions": catalog_substitutions', api)


if __name__ == "__main__":
    unittest.main(verbosity=2)
