from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_semantic_full_corpus_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class SemanticCatalogFullCorpusV60Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = mod._review_paths(ROOT / "tools")
        cls.payload = mod.compile_from_paths(cls.paths)

    def test_all_base_plus_phase3_review_files_are_consumed(self):
        # One base review file plus Phase 3 batches 001..097.
        self.assertEqual(len(self.paths), 98)
        self.assertTrue(self.paths[0].name.endswith("keyless_ingredients.v1.json"))
        self.assertTrue(self.paths[-1].name.endswith("phase3_097.v1.json"))

    def test_full_reviewed_keyless_queue_has_one_source_identity_per_reviewed_label(self):
        # The v59 review overlay resolved 123 keyless labels before Phase 3; the
        # remaining impact-ranked Phase 3 queue contained 9,658 unique labels.
        expected = 123 + 9658
        self.assertEqual(self.payload["summary"]["reviewedSourceLabels"], expected)
        self.assertEqual(len(self.payload["sourceIdentityToConcept"]), expected)

    def test_semantic_compilation_never_assigns_provider_identity(self):
        self.assertFalse(self.payload["identityPolicy"]["providerIdentityAssigned"])
        self.assertFalse(self.payload["identityPolicy"]["providerKeyInference"])
        for concept in self.payload["concepts"]:
            self.assertFalse(concept["providerIdentityAssigned"])
            for source in concept["sourceIdentities"]:
                self.assertTrue(source["ingredientId"].startswith("local:"))
                self.assertFalse(source["providerIdentityAssigned"])

    def test_real_corpus_produces_cross_language_semantic_concepts(self):
        self.assertGreater(self.payload["summary"]["crossLanguageConcepts"], 0)
        self.assertLess(
            self.payload["summary"]["semanticConcepts"],
            self.payload["summary"]["reviewedSourceLabels"],
        )

    def test_ambiguous_reviewed_fragments_remain_non_food_intelligence(self):
        ambiguous = [
            concept
            for concept in self.payload["concepts"]
            if concept["classification"] == "ambiguous"
        ]
        self.assertGreater(len(ambiguous), 0)
        for concept in ambiguous:
            self.assertFalse(concept["nutritionEligible"])
            self.assertFalse(concept["dietEligible"])
            self.assertFalse(concept["allergenEligible"])
            self.assertTrue(concept["needsSemanticConfirmation"])
            self.assertEqual(concept["mergePolicy"], "source-local-conservative")

    def test_no_medium_confidence_source_is_cross_language_merged(self):
        for concept in self.payload["concepts"]:
            if any(
                source.get("confidence") == "medium"
                for source in concept["sourceIdentities"]
            ):
                self.assertEqual(concept["mergePolicy"], "source-local-conservative")
                self.assertEqual(len(concept["sourceIdentities"]), 1)


if __name__ == "__main__":
    unittest.main()
