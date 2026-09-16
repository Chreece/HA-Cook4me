from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_semantics_v60_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class SemanticIngredientCompilerTests(unittest.TestCase):
    def _payload(self, items):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-reviewed-keyless-ingredient-semantics",
            "items": items,
        }

    def _confirmation(self, items):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-semantic-ingredient-confirmations",
            "policy": {
                "providerIdentityAssigned": False,
                "exactReviewedEnglishAndClassificationOnly": True,
                "sourceLocalIdentityPreserved": True,
                "manualConfirmationRequired": True,
            },
            "items": items,
        }

    def test_high_confidence_food_labels_share_semantic_concept_not_provider_key(self):
        payload = self._payload(
            [
                {
                    "language": "de",
                    "source": "Tomate",
                    "english": "Tomato",
                    "classification": "food",
                    "confidence": "high",
                },
                {
                    "language": "el",
                    "source": "Ντομάτα",
                    "english": "Tomato",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        result = mod.compile_semantic_concepts([("batch.json", payload)])
        self.assertEqual(result["summary"]["reviewedSourceLabels"], 2)
        self.assertEqual(result["summary"]["semanticConcepts"], 1)
        concept = result["concepts"][0]
        self.assertEqual(concept["canonicalEnglish"], "Tomato")
        self.assertEqual(concept["classification"], "food")
        self.assertEqual(concept["aliases"]["de"], ["Tomate"])
        self.assertEqual(concept["aliases"]["el"], ["Ντομάτα"])
        self.assertFalse(concept["providerIdentityAssigned"])
        self.assertTrue(concept["nutritionEligible"])
        self.assertTrue(
            all(
                row["ingredientId"].startswith("local:")
                for row in concept["sourceIdentities"]
            )
        )
        self.assertNotIn("providerKey", concept)

    def test_medium_confidence_semantics_stay_source_local_without_confirmation(self):
        payload = self._payload(
            [
                {
                    "language": "tr",
                    "source": "Kabak",
                    "english": "Zucchini",
                    "classification": "food",
                    "confidence": "medium",
                },
                {
                    "language": "de",
                    "source": "Zucchini",
                    "english": "Zucchini",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        result = mod.compile_semantic_concepts([("batch.json", payload)])
        self.assertEqual(result["summary"]["semanticConcepts"], 2)
        medium = next(
            row
            for row in result["concepts"]
            if row["sourceIdentities"][0]["language"] == "tr"
        )
        self.assertEqual(medium["mergePolicy"], "source-local-conservative")
        self.assertTrue(medium["needsSemanticConfirmation"])

    def test_explicit_confirmation_merges_medium_into_existing_high_concept(self):
        payload = self._payload(
            [
                {
                    "language": "tr",
                    "source": "Kabak",
                    "english": "Zucchini",
                    "classification": "food",
                    "confidence": "medium",
                },
                {
                    "language": "de",
                    "source": "Zucchini",
                    "english": "Zucchini",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        source_id = mod.source_local_ingredient_id("tr", "Kabak")
        concept_id = mod._semantic_concept_id("food", "Zucchini")
        confirmation = self._confirmation(
            [
                {
                    "sourceIngredientId": source_id,
                    "confirmedConceptId": concept_id,
                }
            ]
        )
        result = mod.compile_semantic_concepts(
            [("batch.json", payload)],
            confirmation_payload=confirmation,
            confirmation_file="confirmations.json",
        )
        self.assertEqual(result["summary"]["semanticConcepts"], 1)
        self.assertEqual(result["summary"]["confirmedSourceLabels"], 1)
        self.assertEqual(
            result["summary"]["needsSemanticConfirmationSourceLabels"], 0
        )
        self.assertEqual(result["sourceIdentityToConcept"][source_id], concept_id)
        concept = result["concepts"][0]
        self.assertFalse(concept["needsSemanticConfirmation"])
        self.assertEqual(concept["mergePolicy"], "reviewed-high-exact-english")
        confirmed_identity = next(
            row
            for row in concept["sourceIdentities"]
            if row["ingredientId"] == source_id
        )
        self.assertEqual(confirmed_identity["confidence"], "medium")
        self.assertEqual(
            confirmed_identity["semanticConfirmationMethod"],
            "explicit-reviewed-english-classification",
        )
        self.assertEqual(
            confirmed_identity["semanticConfirmationFile"], "confirmations.json"
        )

    def test_confirmation_requires_existing_high_confidence_target(self):
        payload = self._payload(
            [
                {
                    "language": "tr",
                    "source": "Kabak",
                    "english": "Zucchini",
                    "classification": "food",
                    "confidence": "medium",
                }
            ]
        )
        source_id = mod.source_local_ingredient_id("tr", "Kabak")
        confirmation = self._confirmation(
            [
                {
                    "sourceIngredientId": source_id,
                    "confirmedConceptId": mod._semantic_concept_id(
                        "food", "Zucchini"
                    ),
                }
            ]
        )
        with self.assertRaisesRegex(RuntimeError, "lacks high-confidence"):
            mod.compile_semantic_concepts(
                [("batch.json", payload)],
                confirmation_payload=confirmation,
            )

    def test_confirmation_rejects_wrong_meaning_or_ambiguous_source(self):
        food_payload = self._payload(
            [
                {
                    "language": "tr",
                    "source": "Kabak",
                    "english": "Zucchini",
                    "classification": "food",
                    "confidence": "medium",
                },
                {
                    "language": "de",
                    "source": "Zucchini",
                    "english": "Zucchini",
                    "classification": "food",
                    "confidence": "high",
                },
                {
                    "language": "de",
                    "source": "Tomate",
                    "english": "Tomato",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        source_id = mod.source_local_ingredient_id("tr", "Kabak")
        wrong = self._confirmation(
            [
                {
                    "sourceIngredientId": source_id,
                    "confirmedConceptId": mod._semantic_concept_id(
                        "food", "Tomato"
                    ),
                }
            ]
        )
        with self.assertRaisesRegex(RuntimeError, "does not preserve exact"):
            mod.compile_semantic_concepts(
                [("batch.json", food_payload)],
                confirmation_payload=wrong,
            )

        ambiguous_payload = self._payload(
            [
                {
                    "language": "uk",
                    "source": "очищених та тонко нарізаних",
                    "english": "Peeled and thinly sliced",
                    "classification": "ambiguous",
                    "confidence": "medium",
                }
            ]
        )
        ambiguous_id = mod.source_local_ingredient_id(
            "uk", "очищених та тонко нарізаних"
        )
        ambiguous_confirmation = self._confirmation(
            [
                {
                    "sourceIngredientId": ambiguous_id,
                    "confirmedConceptId": mod._semantic_concept_id(
                        "ambiguous", "Peeled and thinly sliced"
                    ),
                }
            ]
        )
        with self.assertRaisesRegex(RuntimeError, "cannot merge classification"):
            mod.compile_semantic_concepts(
                [("batch.json", ambiguous_payload)],
                confirmation_payload=ambiguous_confirmation,
            )

    def test_ambiguous_review_is_preserved_but_never_nutrition_eligible(self):
        payload = self._payload(
            [
                {
                    "language": "uk",
                    "source": "очищених та тонko нарізanих",
                    "english": "Peeled and thinly sliced",
                    "classification": "ambiguous",
                    "confidence": "medium",
                }
            ]
        )
        result = mod.compile_semantic_concepts([("batch.json", payload)])
        concept = result["concepts"][0]
        self.assertEqual(concept["classification"], "ambiguous")
        self.assertFalse(concept["nutritionEligible"])
        self.assertFalse(concept["dietEligible"])
        self.assertFalse(concept["allergenEligible"])
        self.assertTrue(concept["needsSemanticConfirmation"])

    def test_source_local_identity_matches_v2_contract_and_is_stable(self):
        first = mod.source_local_ingredient_id("de", "Tomate")
        second = mod.source_local_ingredient_id("de", "Tomate")
        other = mod.source_local_ingredient_id("el", "Ντομάτα")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("local:de:"))

    def test_conflicting_duplicate_review_fails_closed(self):
        payload = self._payload(
            [
                {
                    "language": "de",
                    "source": "Sahne",
                    "english": "Cream",
                    "classification": "food",
                    "confidence": "high",
                },
                {
                    "language": "de",
                    "source": "Sahne",
                    "english": "Whipping cream",
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )
        with self.assertRaises(RuntimeError):
            mod.compile_semantic_concepts([("batch.json", payload)])

    def test_repository_confirmation_overlay_is_exact_and_lossless(self):
        tools = ROOT / "tools"
        confirmation_path = tools / "release_catalog_semantic_confirmations.v1.json"
        confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
        items = confirmation["items"]
        self.assertGreaterEqual(len(items), 100)

        paths = mod._review_paths(tools)
        payloads = [(path.name, mod._load_payload(path)) for path in paths]
        baseline = mod.compile_semantic_concepts(payloads)
        confirmed = mod.compile_from_paths(paths)

        self.assertEqual(
            confirmed["summary"]["confirmedSourceLabels"], len(items)
        )
        self.assertEqual(
            baseline["summary"]["needsSemanticConfirmationSourceLabels"]
            - confirmed["summary"]["needsSemanticConfirmationSourceLabels"],
            len(items),
        )
        self.assertEqual(
            baseline["summary"]["semanticConcepts"]
            - confirmed["summary"]["semanticConcepts"],
            len(items),
        )

        concepts = {
            row["conceptId"]: row for row in confirmed["concepts"]
        }
        seen_sources = set()
        for item in items:
            source_id = item["sourceIngredientId"]
            target_id = item["confirmedConceptId"]
            self.assertNotIn(source_id, seen_sources)
            seen_sources.add(source_id)
            self.assertEqual(
                confirmed["sourceIdentityToConcept"][source_id], target_id
            )
            concept = concepts[target_id]
            self.assertFalse(concept["needsSemanticConfirmation"])
            identity = next(
                row
                for row in concept["sourceIdentities"]
                if row["ingredientId"] == source_id
            )
            self.assertEqual(
                identity["semanticConfirmationMethod"],
                "explicit-reviewed-english-classification",
            )


if __name__ == "__main__":
    unittest.main()
