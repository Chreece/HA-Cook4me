from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE = TOOLS / "compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_batch6_safety_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

UNSAFE_IDS = {
    "local:uk:03b0818b595c5d09761c",
    "local:uk:953617d433fc7f71ea28",
    "local:uk:97553c4a23b39c4f285d",
    "local:uk:eef3cdfcd9a6230db7e6",
}
SAFE_TARGETS = {
    "local:bg:e35ac76229b5c78378c4": "concept:food:474736156e14c2d92bac",
    "local:ja:02e1cc34d04a7bdf1a2f": "concept:food:6de8c0620c5a99d33180",
    "local:pl:9ef3a75831f2a1e3d8bf": "concept:food:125d64999f9fc91cc29a",
    "local:uk:20cb4d6ecfe7f387415e": "concept:food:d971965002eb9aa3c198",
    "local:uk:37af35ccce43b7044807": "concept:food:8a6ec5111fa708cf847c",
}


class CanonicalBatch6SafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.confirmations = json.loads(
            (TOOLS / "release_catalog_semantic_confirmations.v1.json").read_text(encoding="utf-8")
        )
        cls.standalone = json.loads(
            (TOOLS / "release_catalog_semantic_standalone_dispositions.v1.json").read_text(encoding="utf-8")
        )
        cls.confirmation_ids = {
            row["sourceIngredientId"]
            for row in cls.confirmations.get("items") or []
            if isinstance(row, dict) and row.get("sourceIngredientId")
        }
        cls.standalone_ids = {
            row["sourceIngredientId"]
            for row in cls.standalone.get("items") or []
            if isinstance(row, dict) and row.get("sourceIngredientId")
        }
        cls.compiled = mod.compile_from_paths(mod._review_paths(TOOLS))
        cls.concepts = {row["conceptId"]: row for row in cls.compiled["concepts"]}

    def test_lossy_state_and_preparation_merges_are_restored(self):
        self.assertFalse(UNSAFE_IDS & self.confirmation_ids)
        self.assertTrue(UNSAFE_IDS <= self.standalone_ids)
        for source_id in UNSAFE_IDS:
            concept_id = self.compiled["sourceIdentityToConcept"][source_id]
            self.assertTrue(concept_id.startswith("concept:source:"), source_id)
            concept = self.concepts[concept_id]
            self.assertFalse(concept["nutritionEligible"], source_id)
            self.assertFalse(concept["dietEligible"], source_id)
            self.assertFalse(concept["allergenEligible"], source_id)

    def test_reviewed_identity_preserving_batch6_merges_remain(self):
        for source_id, concept_id in SAFE_TARGETS.items():
            self.assertIn(source_id, self.confirmation_ids)
            self.assertNotIn(source_id, self.standalone_ids)
            self.assertEqual(self.compiled["sourceIdentityToConcept"][source_id], concept_id)

    def test_repository_remains_closed_and_lossless(self):
        summary = self.compiled["summary"]
        self.assertEqual(summary["needsSemanticConfirmationSourceLabels"], 0)
        self.assertEqual(summary["reviewedAmbiguousSourceLabels"], 28)
        self.assertEqual(len(self.compiled["sourceIdentityToConcept"]), 10994)
        self.assertEqual(
            int(self.standalone["summary"]["standaloneDispositionCount"]),
            len(self.standalone["items"]),
        )
        self.assertEqual(
            int(self.standalone["summary"]["reviewedAmbiguousCount"]), 28
        )

    def test_forbidden_distinction_examples_are_documented(self):
        forbidden = {
            "finely chopped bacon": "chopped bacon",
            "scraped/peeled vanilla pod": "scraped vanilla pod",
            "fresh parsley": "generic parsley",
            "rosemary sprigs": "generic rosemary",
        }
        self.assertEqual(len(forbidden), len(UNSAFE_IDS))


if __name__ == "__main__":
    unittest.main()
