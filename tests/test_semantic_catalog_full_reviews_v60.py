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
        cls.review_payloads = [mod._load_payload(path) for path in cls.paths]
        cls.raw_review_items = sum(
            len(payload.get("items") or []) for payload in cls.review_payloads
        )
        cls.payload = mod.compile_semantic_concepts(
            (path.name, payload)
            for path, payload in zip(cls.paths, cls.review_payloads)
        )

    def test_all_base_plus_phase3_review_files_are_consumed(self):
        # One base review file plus Phase 3 batches 001..097.
        self.assertEqual(len(self.paths), 98)
        self.assertTrue(self.paths[0].name.endswith("keyless_ingredients.v1.json"))
        self.assertTrue(self.paths[-1].name.endswith("phase3_097.v1.json"))

    def test_full_review_corpus_exposes_raw_items_and_consistent_duplicate(self):
        # The review files contain 123 earlier review rows + 9,658 Phase-3 rows.
        # After preserving the exact provider spellings in the Phase-3 rows, one
        # (language, exact-source) label remains shared by both review generations.
        # The compiler accepts it only because the reviewed semantics agree, then
        # emits one deterministic source identity for every unique label.
        self.assertEqual(self.raw_review_items, 123 + 9658)
        self.assertEqual(self.payload["summary"]["reviewedSourceLabels"], 9780)
        self.assertEqual(len(self.payload["sourceIdentityToConcept"]), 9780)
        self.assertEqual(self.raw_review_items - 9780, 1)

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
