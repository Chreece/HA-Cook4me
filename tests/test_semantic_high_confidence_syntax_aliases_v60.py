from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_high_syntax_alias_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

POLICY = {
    "providerIdentityAssigned": False,
    "sourceLocalIdentityPreserved": True,
    "highConfidenceOnly": True,
    "safeSyntacticNormalizerRequired": True,
    "cleanCanonicalTargetRequired": True,
    "nutritionConflictTargetsExcluded": True,
    "historicalReviewFilesMutated": False,
}


class HighConfidenceSyntaxAliasTests(unittest.TestCase):
    def _reviews(self):
        return [(
            "review.json",
            {
                "schemaVersion": 1,
                "kind": "cook4me-reviewed-keyless-ingredient-semantics",
                "items": [
                    {"language":"en","source":"Soy sauce","english":"Soy sauce","classification":"food","confidence":"high"},
                    {"language":"ja","source":"A soy","english":"A- soy sauce","classification":"food","confidence":"high"},
                ],
            },
        )]

    def _alias(self):
        old = mod._semantic_concept_id("food", "A- soy sauce")
        target = mod._semantic_concept_id("food", "Soy sauce")
        source = mod.source_local_ingredient_id("ja", "A soy")
        return {
            "schemaVersion":1,
            "kind":"cook4me-semantic-high-confidence-syntax-aliases",
            "policy": POLICY,
            "summary":{"aliasConceptCount":1,"groupCount":1,"sourceIdentityCount":1,"excludedConflictGroupCount":1},
            "excludedConflictTargetConceptIds":["concept:food:conflict"],
            "items":[{
                "oldConceptId":old,"canonicalConceptId":target,
                "oldCanonicalEnglish":"A- soy sauce","canonicalEnglish":"Soy sauce",
                "classification":"food","sourceIngredientIds":[source],
                "method":"existing-safe-syntactic-normalizer",
                "rationale":"High-confidence reviewed meaning differs only by tested safe recipe syntax and maps to the clean canonical target.",
            }],
        }

    def test_high_confidence_syntax_alias_preserves_safety_eligibility(self):
        result = mod.compile_semantic_concepts(
            self._reviews(),
            high_confidence_syntax_alias_payload=self._alias(),
            high_confidence_syntax_alias_file="aliases.json",
        )
        self.assertEqual(result["summary"]["semanticConcepts"], 1)
        self.assertEqual(result["summary"]["highConfidenceSyntaxAliasConcepts"], 1)
        self.assertEqual(result["summary"]["highConfidenceSyntaxAliasSourceLabels"], 1)
        source = mod.source_local_ingredient_id("ja", "A soy")
        target = mod._semantic_concept_id("food", "Soy sauce")
        self.assertEqual(result["sourceIdentityToConcept"][source], target)
        concept = result["concepts"][0]
        self.assertTrue(concept["nutritionEligible"])
        self.assertTrue(concept["dietEligible"])
        self.assertTrue(concept["allergenEligible"])
        identity = next(row for row in concept["sourceIdentities"] if row["ingredientId"] == source)
        self.assertEqual(identity["semanticHighConfidenceSyntaxAliasOriginalConceptId"], mod._semantic_concept_id("food", "A- soy sauce"))
        self.assertEqual(identity["semanticHighConfidenceSyntaxAliasCanonicalConceptId"], target)

    def test_alias_rejects_non_clean_target(self):
        payload = self._alias()
        payload["items"][0]["canonicalConceptId"] = payload["items"][0]["oldConceptId"]
        with self.assertRaises(RuntimeError):
            mod.compile_semantic_concepts(self._reviews(), high_confidence_syntax_alias_payload=payload)

    def test_repository_alias_overlay_is_exact_and_conflict_free(self):
        tools = ROOT / "tools"
        alias_path = tools / "release_catalog_semantic_high_confidence_syntax_aliases.v1.json"
        payload = mod._load_high_confidence_syntax_alias_payload(alias_path)
        self.assertEqual(payload["summary"]["aliasConceptCount"], 128)
        self.assertEqual(payload["summary"]["groupCount"], 112)
        self.assertEqual(payload["summary"]["sourceIdentityCount"], 130)
        self.assertEqual(payload["summary"]["excludedConflictGroupCount"], 11)
        rows = list(mod.iter_review_rows([(p.name, mod._load_payload(p)) for p in mod._review_paths(tools)]))
        aliases = mod._high_confidence_syntax_alias_map(rows, payload, alias_file=alias_path.name)
        self.assertEqual(len(aliases), 128)
        excluded = set(payload["excludedConflictTargetConceptIds"])
        self.assertFalse({row["canonicalConceptId"] for row in aliases.values()} & excluded)
        compiled = mod.compile_from_paths(mod._review_paths(tools))
        self.assertEqual(compiled["summary"]["highConfidenceSyntaxAliasConcepts"], 128)
        self.assertEqual(compiled["summary"]["highConfidenceSyntaxAliasSourceLabels"], 130)
        self.assertEqual(compiled["summary"]["needsSemanticConfirmationSourceLabels"], 0)
        concept_ids = {row["conceptId"] for row in compiled["concepts"]}
        self.assertFalse(set(aliases) & concept_ids)
        self.assertTrue({row["canonicalConceptId"] for row in aliases.values()} <= concept_ids)


if __name__ == "__main__":
    unittest.main()
