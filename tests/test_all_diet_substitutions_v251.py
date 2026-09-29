from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
LOGIC_PATH = COMPONENT / "recipe_logic.py"
SUBS_PATH = COMPONENT / "ingredient_substitutions.py"
RELEASE_PATH = COMPONENT / "release_catalog.py"

spec = importlib.util.spec_from_file_location("cook4me_recipe_logic_v251_test", LOGIC_PATH)
assert spec is not None and spec.loader is not None
logic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logic)

sub_spec = importlib.util.spec_from_file_location("cook4me_substitutions_v251_test", SUBS_PATH)
assert sub_spec is not None and sub_spec.loader is not None
subs = importlib.util.module_from_spec(sub_spec)
sub_spec.loader.exec_module(subs)

release_spec = importlib.util.spec_from_file_location("cook4me_release_catalog_v257_test", RELEASE_PATH)
assert release_spec is not None and release_spec.loader is not None
release = importlib.util.module_from_spec(release_spec)
release_spec.loader.exec_module(release)


def catalog_row(identifier: str, name: str) -> dict:
    return {
        "id": identifier,
        "conceptId": f"concept:food:{identifier}",
        "canonicalName": name,
        "name": name,
        "classification": "food",
    }


_TARGET_NAMES = (
    "Tofu",
    "Mushrooms",
    "Chickpeas",
    "Vegetable stock",
    "Vegetable stock cube",
    "Water",
    "Coconut cream",
    "Soy cream",
    "Soy milk",
    "Unsweetened soy milk",
    "Rice milk",
    "Olive oil",
    "Coconut oil",
    "Maple syrup",
    "Agave syrup",
    "Sugar",
    "Soy sauce",
    "Agar-agar",
    "Pectin",
    "Cornstarch",
    "Lemon juice",
    "Citric acid",
    "Ground flaxseed",
)
TARGETS = [
    catalog_row(f"target-{index}", name)
    for index, name in enumerate(_TARGET_NAMES)
]


def profile(diet: str, *, allergies=(), avoid=()):
    return {
        "diet": diet,
        "allergies": list(allergies),
        "avoid": list(avoid),
        "pantry": [],
        "preferences": [],
        "habitTerms": [],
    }


def recipe(*ingredients: str):
    sources = [
        catalog_row(f"source-{index}-{logic.normalize_text(name)}", name)
        for index, name in enumerate(ingredients)
    ]
    payload = {
        "ingredients": [
            *(dict(row) for row in TARGETS),
            *sources,
        ]
    }
    summary = subs.enrich_catalog_substitutions(payload)
    if summary["missingProfiles"] or summary["unresolvedTargets"]:
        raise AssertionError(summary)
    return {
        "title": "Diet substitution matrix test",
        "ingredients": sources,
    }


class AllDietSubstitutionTests(unittest.TestCase):
    def assert_adapted(self, diet, rows, expected_keys):
        match = logic.score_recipe(recipe(*rows), profile(diet))
        self.assertFalse(match["safe"])
        self.assertTrue(match["eligibleWithSubstitutions"], (diet, rows, match))
        self.assertTrue(match["requiresSubstitutions"])
        self.assertTrue(match["substitutionCoverageComplete"])
        self.assertEqual(
            [row["ingredientIndex"] for row in match["substitutions"]],
            list(range(len(rows))),
        )
        self.assertEqual(
            [row["replacement"]["key"] for row in match["substitutions"]],
            expected_keys,
        )
        self.assertEqual(match["substitutionSources"], ["ingredient_catalog"])
        return match

    def test_pescatarian_meat_gelatin_rennet_and_lard(self):
        self.assert_adapted(
            "pescatarian",
            ["Chicken", "Gelatin", "Animal rennet", "Lard"],
            ["tofu", "agar", "microbial_rennet", "olive_oil"],
        )

    def test_vegetarian_fish_meat_gelatin_and_isinglass(self):
        self.assert_adapted(
            "vegetarian",
            ["Salmon", "Beef", "Gelatin", "Isinglass"],
            ["tofu", "tofu", "agar", "bentonite"],
        )

    def test_chicken_fillet_and_skate_are_never_bare_vegetarian_suggestions(self):
        for ingredient in ("Chicken fillet", "Skate", "Skate wing"):
            with self.subTest(ingredient=ingredient):
                match = logic.score_recipe(recipe(ingredient), profile("vegetarian"))
                self.assertFalse(match["safe"], match)
                self.assertTrue(match["eligibleWithSubstitutions"], match)
                self.assertTrue(match["requiresSubstitutions"], match)
                self.assertTrue(match["substitutionCoverageComplete"], match)
                self.assertEqual(match["substitutions"][0]["replacement"]["key"], "tofu")
                self.assertGreaterEqual(len(match["substitutions"][0]["alternatives"]), 1)

    def test_resolved_catalog_diet_intelligence_drives_substitution_without_food_words(self):
        source = catalog_row("opaque-animal", "Opaque ingredient")
        source["conceptId"] = "concept:food:opaque-animal"
        source["intelligence"] = {
            "diets": {
                "omnivore": "compatible",
                "pescatarian": "compatible",
                "vegetarian": "incompatible",
                "vegan": "incompatible",
            },
            "substitutionClass": "",
        }
        payload = {"ingredients": [*(dict(row) for row in TARGETS), source]}
        summary = subs.enrich_catalog_substitutions(payload)
        self.assertEqual(summary["missingProfiles"], [])
        self.assertEqual(source["substitutionDiets"], ["vegetarian", "vegan"])
        self.assertEqual(
            [row["key"] for row in source["substitutions"]],
            ["tofu", "mushrooms", "chickpeas"],
        )
        match = logic.score_recipe(
            {"title": "Opaque", "ingredients": [source]},
            profile("vegetarian"),
        )
        self.assertFalse(match["safe"], match)
        self.assertTrue(match["eligibleWithSubstitutions"], match)
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "tofu")

    def test_resolved_catalog_compatibility_beats_animal_looking_display_text(self):
        source = catalog_row("plant-chicken", "Chicken style plant protein")
        source["conceptId"] = "concept:food:plant-chicken"
        source["intelligence"] = {
            "diets": {
                "omnivore": "compatible",
                "pescatarian": "compatible",
                "vegetarian": "compatible",
                "vegan": "compatible",
            },
            "substitutionClass": "",
        }
        match = logic.score_recipe(
            {"title": "Plant protein", "ingredients": [source]},
            profile("vegetarian"),
        )
        self.assertTrue(match["safe"], match)
        self.assertFalse(match["requiresSubstitutions"], match)
        self.assertEqual(match["substitutions"], [])

    def test_catalog_bound_red_mullet_and_dogfish_ignore_display_language(self):
        cases = (
            ("concept:food:6d9fa4590ae08aeadd5d", "red_mullet_family"),
            ("concept:food:80a6f48cbd8439928d4c", "dogfish_family"),
        )
        for concept_id, binding_id in cases:
            with self.subTest(concept_id=concept_id):
                source = catalog_row("opaque-source", "Opaque catalog ingredient")
                source["conceptId"] = concept_id
                payload = {
                    "ingredients": [
                        *(dict(row) for row in TARGETS),
                        source,
                    ]
                }
                summary = subs.enrich_catalog_substitutions(payload)
                self.assertEqual(summary["missingProfiles"], [])
                self.assertEqual(summary["unresolvedTargets"], [])
                self.assertEqual(source["substitutionBindingId"], binding_id)
                self.assertEqual(source["substitutionDiets"], ["vegetarian", "vegan"])
                self.assertEqual(
                    [row["key"] for row in source["substitutions"]],
                    ["tofu", "mushrooms", "chickpeas"],
                )

                vegetarian = logic.score_recipe(
                    {"title": "Opaque", "ingredients": [source]},
                    profile("vegetarian"),
                )
                self.assertFalse(vegetarian["safe"], vegetarian)
                self.assertTrue(vegetarian["eligibleWithSubstitutions"], vegetarian)
                self.assertTrue(vegetarian["substitutionCoverageComplete"], vegetarian)
                self.assertEqual(
                    vegetarian["substitutions"][0]["replacement"]["key"], "tofu"
                )

                pescatarian = logic.score_recipe(
                    {"title": "Opaque", "ingredients": [source]},
                    profile("pescatarian"),
                )
                self.assertTrue(pescatarian["safe"], pescatarian)
                self.assertFalse(pescatarian["requiresSubstitutions"], pescatarian)

    def test_release_catalog_has_exact_identity_bindings_for_reported_fish(self):
        payload = release.load_release_catalog()
        expected = {
            "concept:food:6d9fa4590ae08aeadd5d": "red_mullet_family",
            "concept:food:80a6f48cbd8439928d4c": "dogfish_family",
        }
        by_concept = payload.get("_runtimeIngredientsByConcept") or {}
        for concept_id, binding_id in expected.items():
            with self.subTest(concept_id=concept_id):
                rows = [
                    row for row in by_concept.get(concept_id, ())
                    if isinstance(row, dict)
                ]
                self.assertTrue(rows, concept_id)
                self.assertTrue(
                    all(row.get("substitutionBindingId") == binding_id for row in rows),
                    rows,
                )
                self.assertTrue(
                    all(row.get("substitutionDiets") == ["vegetarian", "vegan"] for row in rows),
                    rows,
                )
                self.assertTrue(
                    all(
                        [candidate.get("key") for candidate in row.get("substitutions") or []]
                        == ["tofu", "mushrooms", "chickpeas"]
                        for row in rows
                    ),
                    rows,
                )

    def test_localized_labels_use_english_catalog_identity_for_diet_and_substitutions(self):
        source_rows = {
            "chicken-fillets": {
                "id": "chicken-fillets",
                "canonicalName": "Chicken fillet pieces",
                "classification": "food",
                "substitutionDiets": ["pescatarian", "vegetarian", "vegan"],
                "substitutions": [
                    {
                        "key": "tofu",
                        "name": "Firm tofu",
                        "compatibleDiets": ["pescatarian", "vegetarian", "vegan"],
                        "allergens": ["soy"],
                    },
                    {
                        "key": "mushrooms",
                        "name": "Mushrooms",
                        "compatibleDiets": ["pescatarian", "vegetarian", "vegan"],
                        "allergens": [],
                    },
                ],
            },
            "skate-wing": {
                "id": "skate-wing",
                "canonicalName": "Skate wing",
                "classification": "food",
                "substitutionDiets": ["vegetarian", "vegan"],
                "substitutions": [
                    {
                        "key": "tofu",
                        "name": "Firm tofu",
                        "compatibleDiets": ["vegetarian", "vegan"],
                        "allergens": ["soy"],
                    },
                    {
                        "key": "mushrooms",
                        "name": "Mushrooms",
                        "compatibleDiets": ["vegetarian", "vegan"],
                        "allergens": [],
                    },
                ],
            },
        }
        payload = {"_runtimeIngredientById": source_rows}
        old_loader = release.load_release_catalog
        release.load_release_catalog = lambda: payload
        try:
            cases = [
                ("chicken-fillets", "Κομμάτια φιλέτου κοτόπουλου", "Chicken fillet pieces"),
                ("skate-wing", "Φτερούγα σαλαχιού", "Skate wing"),
            ]
            for ingredient_id, localized, canonical in cases:
                with self.subTest(localized=localized):
                    displayed = {"ingredientId": ingredient_id, "name": localized, "foodName": localized}
                    scoring = release.recipe_safety_evidence(
                        {"title": localized, "ingredients": [displayed]}
                    )
                    row = scoring["ingredients"][0]
                    self.assertEqual(row["name"], localized)
                    self.assertEqual(row["canonicalName"], canonical)
                    match = logic.score_recipe(scoring, profile("vegetarian"))
                    self.assertFalse(match["safe"], match)
                    self.assertTrue(match["eligibleWithSubstitutions"], match)
                    self.assertTrue(match["requiresSubstitutions"], match)
                    self.assertTrue(match["substitutionCoverageComplete"], match)
                    self.assertEqual(match["substitutions"][0]["replacement"]["key"], "tofu")
        finally:
            release.load_release_catalog = old_loader

    def test_vegan_mixed_recipe_gets_replacement_for_every_conflict(self):
        self.assert_adapted(
            "vegan",
            [
                "Chicken",
                "Salmon",
                "Milk",
                "Cream",
                "Butter",
                "Yogurt",
                "Honey",
                "Cheese",
                "Egg",
                "Egg whites",
                "Whey",
                "Gelatin",
                "Animal rennet",
            ],
            [
                "tofu",
                "tofu",
                "soy_milk",
                "coconut_cream",
                "olive_oil",
                "plant_yogurt",
                "maple_syrup",
                "plant_cheese",
                "ground_flaxseed_water",
                "aquafaba",
                "pea_protein",
                "agar",
                "microbial_rennet",
            ],
        )

    def test_milk_falls_back_across_gluten_and_soy_restrictions(self):
        match = logic.score_recipe(
            recipe("Milk"),
            profile("vegan", allergies=("gluten", "soy")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "rice_milk")

    def test_cream_falls_back_across_gluten_and_soy_restrictions(self):
        match = logic.score_recipe(
            recipe("Cream"),
            profile("vegan", allergies=("gluten", "soy")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "coconut_cream")

    def test_yogurt_falls_back_when_soy_is_blocked(self):
        match = logic.score_recipe(
            recipe("Yogurt"),
            profile("vegan", allergies=("soy",)),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(
            match["substitutions"][0]["replacement"]["key"],
            "coconut_cream_lemon",
        )

    def test_fish_sauce_falls_back_when_soy_and_gluten_are_blocked(self):
        match = logic.score_recipe(
            recipe("Fish sauce"),
            profile("vegetarian", allergies=("soy", "gluten")),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "coconut_aminos")

    def test_stock_falls_back_when_celery_is_blocked(self):
        match = logic.score_recipe(
            recipe("Chicken stock"),
            profile("vegetarian", allergies=("celery",)),
        )
        self.assertTrue(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"][0]["replacement"]["key"], "water")

    def test_cheese_fails_closed_when_all_reviewed_candidates_are_uncertain_or_blocked(self):
        match = logic.score_recipe(
            recipe("Cheese"),
            profile("vegan", allergies=("soy", "nuts")),
        )
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertFalse(match["substitutionCoverageComplete"])

    def test_multilingual_derivatives_are_replaced(self):
        cases = [
            ("pescatarian", "Tierisches Lab", "microbial_rennet"),
            ("vegetarian", "Présure", "microbial_rennet"),
            ("vegetarian", "Ιχθυόκολλα", "bentonite"),
            ("vegan", "Molke", "pea_protein"),
            ("vegan", "Ορός γάλακτος", "pea_protein"),
            ("vegan", "Eiweiß", "aquafaba"),
            ("vegan", "Yema de huevo", "ground_flaxseed_water"),
        ]
        for diet, ingredient, expected in cases:
            with self.subTest(diet=diet, ingredient=ingredient):
                match = logic.score_recipe(recipe(ingredient), profile(diet))
                self.assertTrue(match["eligibleWithSubstitutions"], match)
                self.assertTrue(match["substitutionCoverageComplete"])
                self.assertEqual(match["substitutions"][0]["replacement"]["key"], expected)

    def test_omnivore_does_not_mount_diet_substitutions(self):
        match = logic.score_recipe(recipe("Chicken", "Milk", "Egg"), profile("omnivore"))
        self.assertTrue(match["safe"])
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertEqual(match["substitutions"], [])

    def test_non_diet_restrictions_still_block_adaptation(self):
        match = logic.score_recipe(
            recipe("Chicken"),
            profile("vegetarian", avoid=("tofu", "mushrooms", "chickpeas")),
        )
        self.assertFalse(match["eligibleWithSubstitutions"])
        self.assertFalse(match["substitutionCoverageComplete"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
