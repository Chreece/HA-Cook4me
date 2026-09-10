#!/usr/bin/env python3
"""Temporary patch: exact SEB food-label candidates prove food semantics, not identity."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    path = ROOT / "tools" / "apply_release_catalog_reviews_v2.py"
    text = path.read_text(encoding="utf-8")

    old = '''        candidate = _text(row.get("exactProviderFoodKeyCandidate"))
        provider_food = provider_by_key.get(candidate)
        if candidate and provider_food and not _text(row.get("canonicalEnglishName")):
            english = _text(provider_food.get("canonicalEnglishName"))
            if english:
                row["canonicalEnglishName"] = english
                row["canonicalEnglishSource"] = "reviewed:provider-food-exact-label-candidate"

        # Resolve semantics without inventing identity when exact provider-food
'''
    new = '''        candidate = _text(row.get("exactProviderFoodKeyCandidate"))
        provider_food = provider_by_key.get(candidate)
        if candidate and provider_food:
            english = _text(
                row.get("canonicalEnglishName")
                or provider_food.get("canonicalEnglishName")
            )
            if english:
                row["canonicalEnglishName"] = english
                row.setdefault(
                    "canonicalEnglishSource",
                    "reviewed:provider-food-exact-label-candidate",
                )
                # A unique exact same-language label in SEB's own marketing-food
                # dictionary proves the source label is food. It does NOT prove
                # that a keyless recipe line carries that provider identity, so
                # providerFoodKey remains deliberately absent and the local
                # synthetic ingredient identity is preserved.
                row["classification"] = "food"
                row["semanticCandidateEvidence"] = (
                    "unique exact same-language SEB marketing-food label"
                )
                row["semanticIdentityPreserved"] = True
                task_id = _text(row.pop("translationTaskId", ""))
                if task_id:
                    remove_tasks.add(task_id)
                keyless_provider_consensus_applied += 1
                continue

        # Resolve semantics without inventing identity when exact provider-food
'''
    if old not in text:
        raise SystemExit("exact candidate block not found")
    text = text.replace(old, new, 1)

    test_path = ROOT / "tests" / "test_release_catalog_review_overlay.py"
    tests = test_path.read_text(encoding="utf-8")
    marker = '\n\nif __name__ == "__main__":\n    unittest.main()\n'
    addition = r'''

    def test_unique_exact_provider_food_candidate_proves_food_not_identity(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {
                    "key": "M_FOOD_WATER",
                    "canonicalEnglishName": "Water",
                    "translations": [{"language": "de", "name": "Wasser"}],
                }
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "de",
                    "sourceName": "Wasser",
                    "exactProviderFoodKeyCandidate": "M_FOOD_WATER",
                    "localSyntheticIngredientId": "local:de:water",
                    "translationTaskId": "keyless-task",
                }
            ],
            "recipeGroups": [],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertEqual("Water", row["canonicalEnglishName"])
        self.assertEqual("food", row["classification"])
        self.assertEqual("local:de:water", row["localSyntheticIngredientId"])
        self.assertNotIn("providerFoodKey", row)
        self.assertTrue(row["semanticIdentityPreserved"])
        self.assertEqual([], remaining["tasks"])

    def test_unique_exact_candidate_stays_open_until_provider_english_is_resolved(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {
                    "key": "M_FOOD_UNKNOWN",
                    "translations": [{"language": "de", "name": "Unbekannt"}],
                }
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "de",
                    "sourceName": "Unbekannt",
                    "exactProviderFoodKeyCandidate": "M_FOOD_UNKNOWN",
                    "localSyntheticIngredientId": "local:de:unknown",
                    "translationTaskId": "keyless-task",
                }
            ],
            "recipeGroups": [],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertNotIn("classification", row)
        self.assertNotIn("providerFoodKey", row)
        self.assertEqual(["keyless-task"], [task["taskId"] for task in remaining["tasks"]])
'''
    if marker not in tests:
        raise SystemExit("unittest footer not found")
    tests = tests.replace(marker, addition + marker, 1)
    test_path.write_text(tests, encoding="utf-8")
    path.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
