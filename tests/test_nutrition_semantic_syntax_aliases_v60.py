from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location(
    "cook4me_nutrition_syntax_alias_test",
    TOOLS / "resolve_reviewed_release_catalog_nutrition_targets_v60.py",
)
resolver = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(resolver)

import compile_release_catalog_semantics_v60 as semantic  # noqa: E402


class NutritionSemanticSyntaxAliasTests(unittest.TestCase):
    def _semantic_review(self):
        return {
            "schemaVersion":1,
            "kind":"cook4me-reviewed-keyless-ingredient-semantics",
            "items":[
                {"language":"en","source":"Soy sauce","english":"Soy sauce","classification":"food","confidence":"high"},
                {"language":"ja","source":"A soy","english":"A- soy sauce","classification":"food","confidence":"high"},
            ],
        }

    def _alias(self):
        old = semantic._semantic_concept_id("food", "A- soy sauce")
        target = semantic._semantic_concept_id("food", "Soy sauce")
        source = semantic.source_local_ingredient_id("ja", "A soy")
        return {
            "schemaVersion":1,
            "kind":"cook4me-semantic-high-confidence-syntax-aliases",
            "policy": semantic._HIGH_CONFIDENCE_SYNTAX_ALIAS_POLICY,
            "summary":{"aliasConceptCount":1,"groupCount":1,"sourceIdentityCount":1,"excludedConflictGroupCount":0},
            "excludedConflictTargetConceptIds":[],
            "items":[{
                "oldConceptId":old,"canonicalConceptId":target,
                "oldCanonicalEnglish":"A- soy sauce","canonicalEnglish":"Soy sauce",
                "classification":"food","sourceIngredientIds":[source],
                "method":"existing-safe-syntactic-normalizer",
                "rationale":"High-confidence reviewed meaning differs only by tested safe recipe syntax and maps to the clean canonical target.",
            }],
        }

    def _nutrition_doc(self, target_id, name, fdc_id):
        return {
            "schemaVersion":1,
            "kind":"cook4me-reviewed-nutrition-target-source",
            "policy":{
                "searchResultAutoAccepted":False,
                "exactFdcBindingRequired":True,
                "semanticConceptGroupingReviewed":True,
                "providerIdentityInference":False,
            },
            "items":[{"reviewTargetId":target_id,"reviewTargetKind":"semantic-concept","canonicalEnglishName":name,"fdcId":fdc_id}],
        }

    def test_loader_canonicalizes_historical_alias_without_mutating_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "release_catalog_reviewed_keyless_ingredients.v1.json").write_text(json.dumps(self._semantic_review()), encoding="utf-8")
            (root / semantic.HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name).write_text(json.dumps(self._alias()), encoding="utf-8")
            old = semantic._semantic_concept_id("food", "A- soy sauce")
            target = semantic._semantic_concept_id("food", "Soy sauce")
            (root / "release_catalog_reviewed_nutrition_targets_001.v1.json").write_text(json.dumps(self._nutrition_doc(old, "A- soy sauce", 123)), encoding="utf-8")
            (root / "release_catalog_reviewed_nutrition_targets_002.v1.json").write_text(json.dumps(self._nutrition_doc(target, "Soy sauce", 123)), encoding="utf-8")
            reviews = resolver.load_reviews(root)
            self.assertEqual(set(reviews), {target})
            self.assertEqual(reviews[target]["fdcId"], 123)
            self.assertEqual(reviews[target]["canonicalEnglishName"], "Soy sauce")
            self.assertEqual(reviews[target]["semanticSyntaxAliasOriginalReviewTargetId"], old)
            self.assertEqual(reviews[target]["semanticSyntaxAliasOriginalCanonicalEnglishName"], "A- soy sauce")

    def test_loader_still_fails_closed_when_aliased_fdc_ids_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "release_catalog_reviewed_keyless_ingredients.v1.json").write_text(json.dumps(self._semantic_review()), encoding="utf-8")
            (root / semantic.HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name).write_text(json.dumps(self._alias()), encoding="utf-8")
            old = semantic._semantic_concept_id("food", "A- soy sauce")
            target = semantic._semantic_concept_id("food", "Soy sauce")
            (root / "release_catalog_reviewed_nutrition_targets_001.v1.json").write_text(json.dumps(self._nutrition_doc(old, "A- soy sauce", 123)), encoding="utf-8")
            (root / "release_catalog_reviewed_nutrition_targets_002.v1.json").write_text(json.dumps(self._nutrition_doc(target, "Soy sauce", 456)), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "conflicting nutrition-target review"):
                resolver.load_reviews(root)


if __name__ == "__main__":
    unittest.main()
