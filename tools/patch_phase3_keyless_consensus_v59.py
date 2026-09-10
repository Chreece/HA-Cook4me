#!/usr/bin/env python3
"""Temporary maintenance patch for conservative keyless provider-label consensus."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def patch_loader() -> None:
    path = ROOT / "tools" / "apply_release_catalog_reviews_v2.py"
    text = path.read_text(encoding="utf-8")

    marker = '''def _set_group_english(
'''
    helper = '''def _provider_label_candidates(
    provider_foods: list[dict[str, Any]],
) -> dict[str, set[str]]:
    """Index exact provider-food labels across all captured dictionaries."""
    out: dict[str, set[str]] = {}
    for row in provider_foods:
        if not isinstance(row, dict):
            continue
        key = _text(row.get("key"))
        if not key:
            continue
        for translation in row.get("translations") or []:
            if not isinstance(translation, dict):
                continue
            name = _text(translation.get("name"))
            if not name:
                continue
            out.setdefault(_norm(name), set()).add(key)
    return out


def _strict_provider_semantic_consensus(
    candidate_keys: set[str],
    provider_by_key: dict[str, dict[str, Any]],
) -> tuple[str, list[str]]:
    """Return English only when every candidate is resolved and meanings agree."""
    keys = sorted(key for key in candidate_keys if key)
    if not keys:
        return "", []
    names: list[str] = []
    for key in keys:
        row = provider_by_key.get(key)
        if not row:
            return "", keys
        english = _text(row.get("canonicalEnglishName"))
        if not english:
            return "", keys
        names.append(english)
    normalized = {_norm(name) for name in names}
    if len(normalized) != 1:
        return "", keys
    return names[0], keys


'''
    if helper not in text:
        if marker not in text:
            raise SystemExit("group helper marker not found")
        text = text.replace(marker, helper + marker, 1)

    old = '''    provider_by_key = {
        _text(row.get("key")): row
        for row in provider_foods
        if isinstance(row, dict) and _text(row.get("key"))
    }
'''
    new = '''    provider_by_key = {
        _text(row.get("key")): row
        for row in provider_foods
        if isinstance(row, dict) and _text(row.get("key"))
    }
    provider_label_candidates = _provider_label_candidates(
        [row for row in provider_foods if isinstance(row, dict)]
    )
'''
    if old not in text:
        raise SystemExit("provider map block not found")
    text = text.replace(old, new, 1)

    old = '''    keyless_review_applied = 0
    recipe_title_review_applied = 0
'''
    new = '''    keyless_review_applied = 0
    keyless_provider_consensus_applied = 0
    recipe_title_review_applied = 0
'''
    if old not in text:
        raise SystemExit("counter block not found")
    text = text.replace(old, new, 1)

    old = '''        candidate = _text(row.get("exactProviderFoodKeyCandidate"))
        provider_food = provider_by_key.get(candidate)
        if candidate and provider_food and not _text(row.get("canonicalEnglishName")):
            english = _text(provider_food.get("canonicalEnglishName"))
            if english:
                row["canonicalEnglishName"] = english
                row["canonicalEnglishSource"] = "reviewed:provider-food-exact-label-candidate"
'''
    new = '''        candidate = _text(row.get("exactProviderFoodKeyCandidate"))
        provider_food = provider_by_key.get(candidate)
        if candidate and provider_food and not _text(row.get("canonicalEnglishName")):
            english = _text(provider_food.get("canonicalEnglishName"))
            if english:
                row["canonicalEnglishName"] = english
                row["canonicalEnglishSource"] = "reviewed:provider-food-exact-label-candidate"

        # Resolve semantics without inventing identity when exact provider-food
        # labels are ambiguous only by provider key but unanimous in meaning.
        # Same-language ambiguity is safe to consider directly. Global exact
        # labels are used only for English keyless source text, where translation
        # is not inferred across languages and provider evidence is classification
        # evidence only. Every candidate must already have canonical English and
        # every canonical meaning must agree, otherwise the task stays unresolved.
        if candidate or _text(row.get("canonicalEnglishName")):
            continue
        candidates = {
            _text(value)
            for value in row.get("ambiguousProviderFoodKeyCandidates") or []
            if _text(value)
        }
        evidence = "exact same-language SEB marketing-food label consensus"
        if not candidates and language == "en":
            candidates = set(provider_label_candidates.get(_norm(source), set()))
            evidence = "exact global SEB marketing-food label consensus for English source"
        english, consensus_keys = _strict_provider_semantic_consensus(
            candidates, provider_by_key
        )
        if not english:
            continue
        row["semanticProviderFoodKeyCandidates"] = consensus_keys
        row["semanticCandidateEvidence"] = evidence
        row["canonicalEnglishName"] = english
        row["canonicalEnglishSource"] = "reviewed:provider-food-exact-label-consensus"
        row["classification"] = "food"
        row["semanticIdentityPreserved"] = True
        task_id = _text(row.pop("translationTaskId", ""))
        if task_id:
            remove_tasks.add(task_id)
        keyless_provider_consensus_applied += 1
'''
    if old not in text:
        raise SystemExit("candidate block not found")
    text = text.replace(old, new, 1)

    old = '''    summary["reviewedKeylessIngredientSemanticsApplied"] = keyless_review_applied
    summary["reviewedKeylessIngredientSemanticFiles"] = keyless_review_files
'''
    new = '''    summary["reviewedKeylessIngredientSemanticsApplied"] = keyless_review_applied
    summary["reviewedKeylessIngredientSemanticFiles"] = keyless_review_files
    summary["providerFoodConsensusKeylessSemanticsApplied"] = keyless_provider_consensus_applied
'''
    if old not in text:
        raise SystemExit("keyless summary block not found")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    test_path = ROOT / "tests" / "test_release_catalog_review_overlay.py"
    text = test_path.read_text(encoding="utf-8")
    marker = '\n\nif __name__ == "__main__":\n    unittest.main()\n'
    addition = r'''

    def test_same_language_ambiguous_provider_keys_resolve_only_on_full_consensus(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {"key": "M_FOOD_A", "canonicalEnglishName": "Cream", "translations": []},
                {"key": "M_FOOD_B", "canonicalEnglishName": "Cream", "translations": []},
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "pl",
                    "sourceName": "Śmietana",
                    "ambiguousProviderFoodKeyCandidates": ["M_FOOD_A", "M_FOOD_B"],
                    "translationTaskId": "keyless-task",
                    "localSyntheticIngredientId": "local:pl:cream",
                }
            ],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertEqual("Cream", row["canonicalEnglishName"])
        self.assertEqual("food", row["classification"])
        self.assertEqual(["M_FOOD_A", "M_FOOD_B"], row["semanticProviderFoodKeyCandidates"])
        self.assertNotIn("providerFoodKey", row)
        self.assertEqual([], remaining["tasks"])
        self.assertEqual(1, reviewed["summary"]["providerFoodConsensusKeylessSemanticsApplied"])

    def test_same_language_consensus_fails_closed_when_any_candidate_is_unresolved(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {"key": "M_FOOD_A", "canonicalEnglishName": "Cream", "translations": []},
                {"key": "M_FOOD_B", "translations": []},
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "pl",
                    "sourceName": "Śmietana",
                    "ambiguousProviderFoodKeyCandidates": ["M_FOOD_A", "M_FOOD_B"],
                    "translationTaskId": "keyless-task",
                }
            ],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertNotIn("canonicalEnglishName", row)
        self.assertEqual(["keyless-task"], [item["taskId"] for item in remaining["tasks"]])
        self.assertEqual(0, reviewed["summary"]["providerFoodConsensusKeylessSemanticsApplied"])

    def test_same_language_consensus_fails_closed_on_conflicting_meanings(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {"key": "M_FOOD_A", "canonicalEnglishName": "Cream", "translations": []},
                {"key": "M_FOOD_B", "canonicalEnglishName": "Sour cream", "translations": []},
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "pl",
                    "sourceName": "Śmietana",
                    "ambiguousProviderFoodKeyCandidates": ["M_FOOD_A", "M_FOOD_B"],
                    "translationTaskId": "keyless-task",
                }
            ],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertNotIn("canonicalEnglishName", row)
        self.assertEqual(["keyless-task"], [item["taskId"] for item in remaining["tasks"]])
        self.assertEqual(0, reviewed["summary"]["providerFoodConsensusKeylessSemanticsApplied"])

    def test_english_global_exact_provider_label_can_resolve_semantics_without_identity(self):
        prep = {
            "kind": "cook4me-release-assembly-prep",
            "summary": {},
            "providerFoods": [
                {
                    "key": "M_FOOD_A",
                    "canonicalEnglishName": "Cream",
                    "translations": [{"language": "fr", "name": "cream"}],
                },
                {
                    "key": "M_FOOD_B",
                    "canonicalEnglishName": "Cream",
                    "translations": [{"language": "de", "name": "cream"}],
                },
            ],
            "unkeyedIngredients": [
                {
                    "sourceLanguage": "en",
                    "sourceName": "cream",
                    "translationTaskId": "keyless-task",
                    "localSyntheticIngredientId": "local:en:cream",
                }
            ],
        }
        queue = {
            "kind": "cook4me-local-translation-queue",
            "tasks": [{"taskId": "keyless-task", "type": "unkeyed_ingredient"}],
        }
        reviewed, remaining = overlay.apply_reviews(prep, queue)
        row = reviewed["unkeyedIngredients"][0]
        self.assertEqual("Cream", row["canonicalEnglishName"])
        self.assertEqual("food", row["classification"])
        self.assertEqual("local:en:cream", row["localSyntheticIngredientId"])
        self.assertNotIn("providerFoodKey", row)
        self.assertEqual([], remaining["tasks"])
'''
    if marker not in text:
        raise SystemExit("unittest footer not found")
    text = text.replace(marker, addition + marker, 1)
    test_path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_loader()
    patch_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
