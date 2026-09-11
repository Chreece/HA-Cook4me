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

    def test_all_committed_review_files_are_consumed(self):
        # One base review file, twenty Capture 3 language batches, and Phase 3 batches 001..097.
        self.assertEqual(len(self.paths), 118)
        self.assertTrue(self.paths[0].name.endswith("keyless_ingredients.v1.json"))
        names = {path.name for path in self.paths}
        for name in (
            "release_catalog_reviewed_keyless_ingredients_capture3_en_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_de_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_fr_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_es_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_pl_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_sl_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_cs_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_sk_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_ro_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_hu_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_zh_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_ru_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_ko_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_ja_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_ar_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_it_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_pt_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_tr_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_bg_001.v1.json",
            "release_catalog_reviewed_keyless_ingredients_capture3_uk_001.v1.json",
        ):
            self.assertIn(name, names)
        self.assertTrue(self.paths[-1].name.endswith("phase3_097.v1.json"))

    def test_full_review_corpus_has_one_identity_per_exact_source_label(self):
        self.assertEqual(
            self.raw_review_items,
            123 + 9658 + 26 + 19 + 5 + 35 + 13 + 1 + 32 + 29 + 34 + 36 + 34 + 48 + 49 + 57 + 74 + 79 + 87 + 93 + 144 + 149,
        )
        self.assertEqual(self.payload["summary"]["reviewedSourceLabels"], 10825)
        self.assertEqual(len(self.payload["sourceIdentityToConcept"]), 10825)
        self.assertEqual(self.raw_review_items - 10825, 0)

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
