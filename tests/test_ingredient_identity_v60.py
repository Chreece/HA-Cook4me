from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "custom_components/cook4me/ingredient_identity.py"
spec = importlib.util.spec_from_file_location("cook4me_ingredient_identity_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class IngredientIdentityV60Tests(unittest.TestCase):
    def test_concept_identity_wins_without_becoming_provider_key(self):
        item = {
            "conceptId": "concept:food:tomato",
            "ingredientId": "local:de:abc123",
            "canonicalName": "Tomato",
        }
        self.assertEqual(mod.canonical_identity(item), "c:concept:food:tomato")
        self.assertEqual(
            mod.identity_candidates(item),
            (
                "c:concept:food:tomato",
                "l:local:de:abc123",
                "n:tomato",
            ),
        )
        self.assertNotIn("k:concept:food:tomato", mod.identity_candidates(item))

    def test_provider_key_remains_provider_identity(self):
        item = {
            "ingredientId": "M_FOOD_TOMATO",
            "foodKey": "M_FOOD_TOMATO",
            "name": "Tomato",
        }
        self.assertEqual(mod.canonical_identity(item), "k:M_FOOD_TOMATO")
        self.assertEqual(mod.legacy_identity(item), "k:M_FOOD_TOMATO")

    def test_legacy_name_candidate_survives_concept_migration(self):
        item = {
            "conceptId": "concept:food:tomato",
            "canonicalName": "Tomato",
        }
        self.assertEqual(mod.identity_candidates(item)[-1], "n:tomato")
        self.assertEqual(mod.legacy_identity(item), "n:tomato")

    def test_same_concept_matches_across_languages_even_when_names_differ(self):
        de = {
            "conceptId": "concept:food:tomato",
            "ingredientId": "local:de:one",
            "name": "Tomate",
        }
        el = {
            "conceptId": "concept:food:tomato",
            "ingredientId": "local:el:two",
            "name": "Ντομάτα",
        }
        self.assertTrue(mod.same_ingredient(de, el))

    def test_different_unreviewed_local_ids_do_not_merge_from_names(self):
        de = {
            "ingredientId": "local:de:one",
            "name": "Kabak",
        }
        en = {
            "ingredientId": "local:en:two",
            "name": "Zucchini",
        }
        self.assertFalse(mod.same_ingredient(de, en))

    def test_existing_name_only_records_still_match_reviewed_concept_alias_when_name_matches(self):
        old = {"name": "Tomato"}
        new = {
            "conceptId": "concept:food:tomato",
            "canonicalName": "Tomato",
        }
        self.assertTrue(mod.same_ingredient(old, new))

    def test_string_legacy_identity_is_preserved(self):
        self.assertEqual(mod.canonical_identity("Crème fraîche"), "n:creme fraiche")


if __name__ == "__main__":
    unittest.main()
