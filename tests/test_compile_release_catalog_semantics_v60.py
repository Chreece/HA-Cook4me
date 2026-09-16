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

    def test_explicit_exact_confirmation_merges_medium_into_existing_high_concept(self):
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
        self.assertEqual(result["summary"]["exactConfirmedSourceLabels"], 1)
        self.assertEqual(result["summary"]["syntacticConfirmedSourceLabels"], 0)
        self.assertEqual(
            result["summary"]["needsSemanticConfirmationSourceLabels"], 0
        )
        self.assertEqual(result["sourceIdentityToConcept"][source_id], concept_id)
        concept = result["concepts"][0]
        identity = next(
            row
            for row in concept["sourceIdentities"]
            if row["ingredientId"] == source_id
        )
        self.assertEqual(
            identity["semanticConfirmationMethod"],
            "explicit-reviewed-english-classification",
        )

    def _syntax_payload(self, medium_english, high_english, *, source="Medium source"):
        return self._payload(
            [
                {
                    "language": "uk",
                    "source": source,
                    "english": medium_english,
                    "classification": "food",
                    "confidence": "medium",
                },
                {
                    "language": "en",
                    "source": high_english,
                    "english": high_english,
                    "classification": "food",
                    "confidence": "high",
                },
            ]
        )

    def _assert_syntax_merge(self, medium_english, high_english):
        payload = self._syntax_payload(medium_english, high_english)
        source_id = mod.source_local_ingredient_id("uk", "Medium source")
        result = mod.compile_semantic_concepts(
            [("batch.json", payload)],
            syntax_confirmation_ids={source_id},
            syntax_confirmation_file="syntax.txt",
        )
        concept_id = mod._semantic_concept_id("food", high_english)
        self.assertEqual(result["sourceIdentityToConcept"][source_id], concept_id)
        self.assertEqual(result["summary"]["syntacticConfirmedSourceLabels"], 1)
        self.assertEqual(
            result["summary"]["needsSemanticConfirmationSourceLabels"], 0
        )
        concept = next(
            row for row in result["concepts"] if row["conceptId"] == concept_id
        )
        identity = next(
            row
            for row in concept["sourceIdentities"]
            if row["ingredientId"] == source_id
        )
        self.assertEqual(
            identity["semanticConfirmationMethod"],
            "explicit-reviewed-syntactic-normalization",
        )

    def test_whitelisted_section_prefix_is_syntax_only(self):
        self._assert_syntax_merge("A- melted butter", "Melted butter")

    def test_whitelisted_malformed_quantity_prefix_is_syntax_only(self):
        self._assert_syntax_merge(
            "/2 onion, peeled and chopped", "Onion, peeled and chopped"
        )

    def test_whitelisted_review_annotation_is_syntax_only(self):
        self._assert_syntax_merge("Egg noodles (source grammar)", "Egg noodles")

    def test_whitelisted_quantity_annotation_preserves_real_qualifier(self):
        self._assert_syntax_merge(
            "Candied lemon (without flesh, thinly sliced; quantity fragment: /2)",
            "Candied lemon (without flesh, thinly sliced)",
        )
        self.assertEqual(
            mod._safe_syntactic_english(
                "Lemon (finely grated zest; quantity fragment: /3)"
            ),
            "Lemon (finely grated zest)",
        )

    def test_unwhitelisted_syntax_equivalent_row_remains_pending(self):
        payload = self._syntax_payload("A- melted butter", "Melted butter")
        result = mod.compile_semantic_concepts([("batch.json", payload)])
        self.assertEqual(result["summary"]["syntacticConfirmedSourceLabels"], 0)
        self.assertEqual(
            result["summary"]["needsSemanticConfirmationSourceLabels"], 1
        )
        self.assertEqual(result["summary"]["semanticConcepts"], 2)

    def test_alternative_ingredient_wording_is_not_syntactically_erased(self):
        value = "Vegetable stock (or salted water; source grammar)"
        self.assertEqual(mod._safe_syntactic_english(value), value)
        payload = self._syntax_payload(value, "Vegetable stock")
        source_id = mod.source_local_ingredient_id("uk", "Medium source")
        with self.assertRaisesRegex(
            RuntimeError, "does not remove approved syntax noise"
        ):
            mod.compile_semantic_concepts(
                [("batch.json", payload)],
                syntax_confirmation_ids={source_id},
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

    def test_exact_confirmation_rejects_wrong_meaning(self):
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
                [("batch.json", payload)],
                confirmation_payload=wrong,
            )

    def test_ambiguous_review_is_preserved_and_cannot_be_syntax_confirmed(self):
        source = "очищених та тонко нарізаних"
        payload = self._payload(
            [
                {
                    "language": "uk",
                    "source": source,
                    "english": "Peeled and thinly sliced",
                    "classification": "ambiguous",
                    "confidence": "medium",
                }
            ]
        )
        result = mod.compile_semantic_concepts([("batch.json", payload)])
        concept = result["concepts"][0]
        self.assertFalse(concept["nutritionEligible"])
        self.assertFalse(concept["dietEligible"])
        self.assertFalse(concept["allergenEligible"])
        self.assertTrue(concept["needsSemanticConfirmation"])
        source_id = mod.source_local_ingredient_id("uk", source)
        with self.assertRaisesRegex(RuntimeError, "cannot merge classification"):
            mod.compile_semantic_concepts(
                [("batch.json", payload)],
                syntax_confirmation_ids={source_id},
            )

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

    def test_repository_confirmation_overlays_are_exact_and_lossless(self):
        tools = ROOT / "tools"
        exact_path = tools / "release_catalog_semantic_confirmations.v1.json"
        syntax_path = (
            tools
            / "release_catalog_semantic_syntactic_confirmation_ids.v1.txt"
        )
        exact_items = json.loads(
            exact_path.read_text(encoding="utf-8")
        )["items"]
        syntax_ids = mod._load_syntax_confirmation_ids(syntax_path)
        self.assertEqual(len(exact_items), 115)
        self.assertEqual(len(syntax_ids), 54)
        self.assertFalse(
            {row["sourceIngredientId"] for row in exact_items} & syntax_ids
        )

        paths = mod._review_paths(tools)
        payloads = [(path.name, mod._load_payload(path)) for path in paths]
        baseline = mod.compile_semantic_concepts(payloads)
        confirmed = mod.compile_from_paths(paths)
        total = len(exact_items) + len(syntax_ids)

        self.assertEqual(
            confirmed["summary"]["exactConfirmedSourceLabels"],
            len(exact_items),
        )
        self.assertEqual(
            confirmed["summary"]["syntacticConfirmedSourceLabels"],
            len(syntax_ids),
        )
        self.assertEqual(confirmed["summary"]["confirmedSourceLabels"], total)
        self.assertEqual(
            baseline["summary"]["needsSemanticConfirmationSourceLabels"]
            - confirmed["summary"]["needsSemanticConfirmationSourceLabels"],
            total,
        )
        self.assertEqual(
            baseline["summary"]["semanticConcepts"]
            - confirmed["summary"]["semanticConcepts"],
            total,
        )
        self.assertEqual(
            confirmed["summary"]["needsSemanticConfirmationSourceLabels"],
            330,
        )

        concepts = {
            row["conceptId"]: row for row in confirmed["concepts"]
        }
        for source_id in syntax_ids:
            target_id = confirmed["sourceIdentityToConcept"][source_id]
            concept = concepts[target_id]
            self.assertFalse(concept["needsSemanticConfirmation"])
            identity = next(
                row
                for row in concept["sourceIdentities"]
                if row["ingredientId"] == source_id
            )
            self.assertEqual(
                identity["semanticConfirmationMethod"],
                "explicit-reviewed-syntactic-normalization",
            )


if __name__ == "__main__":
    unittest.main()
