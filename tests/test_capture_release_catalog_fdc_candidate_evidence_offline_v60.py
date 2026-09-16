from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


capture_mod = _load(
    "capture_release_catalog_fdc_candidate_evidence_offline_v60_test",
    TOOLS / "capture_release_catalog_fdc_candidate_evidence_offline_v60.py",
)
triage_mod = _load(
    "classify_release_catalog_fdc_candidate_evidence_v60_test",
    TOOLS / "classify_release_catalog_fdc_candidate_evidence_v60.py",
)


class FakeIndex:
    manifest_sha256 = "abc123"

    def __init__(self, rows):
        self.rows = rows

    def search(self, query, *, max_candidates=12):
        return [dict(row) for row in self.rows.get(query, [])[:max_candidates]]


class BulkCandidateEvidenceTests(unittest.TestCase):
    def _targets(self):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-release-catalog-nutrition-review-targets-v60",
            "catalogVersion": "v-test",
            "reviewTargetCount": 4,
            "policy": {
                "exactIngredientIdentityCompletenessPreserved": True,
                "providerIdentityInference": False,
                "providerIdentityReviewGrouped": False,
                "sourceLocalGroupingRequiresSemanticConcept": True,
                "sourceLocalGroupingRequiresHighConfidence": True,
                "sourceLocalGroupingRequiresExactCanonicalEnglish": True,
                "reviewedExactFdcProvenanceRequired": True,
                "searchResultAutoAccepted": False,
                "candidateSearchIsIdentityProof": False,
            },
            "targets": [
                {
                    "reviewTargetId": "M_FOOD_1",
                    "reviewTargetKind": "provider-identity",
                    "canonicalEnglishName": "Tomato",
                    "memberIngredientIds": ["M_FOOD_1"],
                    "memberCount": 1,
                    "usageCountSum": 20,
                    "usedByRecipe": True,
                },
                {
                    "reviewTargetId": "M_FOOD_2",
                    "reviewTargetKind": "provider-identity",
                    "canonicalEnglishName": "Mystery blend",
                    "memberIngredientIds": ["M_FOOD_2"],
                    "memberCount": 1,
                    "usageCountSum": 5,
                    "usedByRecipe": True,
                },
                {
                    "reviewTargetId": "concept:food:rice",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Rice",
                    "memberIngredientIds": ["local:el:rice", "local:de:rice"],
                    "memberCount": 2,
                    "usageCountSum": 12,
                    "usedByRecipe": True,
                },
                {
                    "reviewTargetId": "concept:food:rare",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Rare thing",
                    "memberIngredientIds": ["local:en:rare"],
                    "memberCount": 1,
                    "usageCountSum": 0,
                    "usedByRecipe": False,
                },
            ],
        }

    def test_capture_preserves_target_identity_and_never_selects(self):
        index = FakeIndex(
            {
                "Tomato": [
                    {"fdcId": 1, "description": "Tomato", "dataType": "Foundation"},
                    {"fdcId": 2, "description": "Tomatoes, red, ripe", "dataType": "SR Legacy"},
                ],
                "Mystery blend": [
                    {"fdcId": 3, "description": "Prepared food blend", "dataType": "Survey (FNDDS)"}
                ],
                "Rice": [
                    {"fdcId": 4, "description": "Rice", "dataType": "Foundation"},
                    {"fdcId": 5, "description": "Rice", "dataType": "SR Legacy"},
                ],
                "Rare thing": [],
            }
        )
        evidence, summary = capture_mod.capture(self._targets(), index)
        self.assertEqual(evidence["reviewTargetCount"], 4)
        self.assertEqual(summary["selectionCount"], 0)
        self.assertFalse(evidence["policy"]["candidateSearchIsIdentityProof"])
        self.assertEqual(
            [row["reviewTargetId"] for row in evidence["items"]],
            [row["reviewTargetId"] for row in self._targets()["targets"]],
        )
        tomato = evidence["items"][0]
        self.assertEqual(tomato["literalExactDescriptionMatchCount"], 1)
        self.assertEqual(tomato["literalExactDescriptionFdcIds"], [1])
        rice = evidence["items"][2]
        self.assertEqual(rice["literalExactDescriptionMatchCount"], 2)
        self.assertEqual(summary["zeroCandidateCount"], 1)

    def test_capture_records_alias_fallback_without_accepting_it(self):
        index = FakeIndex(
            {
                "Tomato": [
                    {
                        "fdcId": 1,
                        "description": "Tomato",
                        "localEvidenceQueryAlias": True,
                        "localEvidenceMatchedQuery": "tomatoes",
                    }
                ],
                "Mystery blend": [],
                "Rice": [],
                "Rare thing": [],
            }
        )
        evidence, summary = capture_mod.capture(self._targets(), index)
        self.assertTrue(evidence["items"][0]["candidateAliasFallbackUsed"])
        self.assertEqual(summary["aliasFallbackTargetCount"], 1)
        self.assertEqual(summary["selectionCount"], 0)

    def test_triage_classifies_all_lanes_without_binding(self):
        evidence = {
            "schemaVersion": 1,
            "kind": capture_mod.EVIDENCE_KIND,
            "catalogVersion": "v-test",
            "referenceManifestSha256": "abc123",
            "reviewTargetCount": 5,
            "policy": {
                "candidateSearchIsIdentityProof": False,
                "selectionPerformed": False,
                "searchResultAutoAccepted": False,
                "providerIngredientIdentityInference": False,
                "reviewedExactFdcBindingRequired": True,
                "literalExactDescriptionIsIdentityProof": False,
                "singletonCandidateIsIdentityProof": False,
                "aliasFallbackIsIdentityProof": False,
                "networkRequestsPerformed": False,
                "apiKeyRequired": False,
                "secretsPersisted": False,
            },
            "items": [
                {"reviewTargetId": "a", "canonicalEnglishName": "A", "memberCount": 1, "usageCountSum": 10, "usedByRecipe": True, "candidateCount": 2, "literalExactDescriptionMatchCount": 1, "candidates": [{}, {}]},
                {"reviewTargetId": "b", "canonicalEnglishName": "B", "memberCount": 1, "usageCountSum": 8, "usedByRecipe": True, "candidateCount": 2, "literalExactDescriptionMatchCount": 2, "candidates": [{}, {}]},
                {"reviewTargetId": "c", "canonicalEnglishName": "C", "memberCount": 1, "usageCountSum": 6, "usedByRecipe": True, "candidateCount": 1, "literalExactDescriptionMatchCount": 0, "candidates": [{}]},
                {"reviewTargetId": "d", "canonicalEnglishName": "D", "memberCount": 1, "usageCountSum": 4, "usedByRecipe": True, "candidateCount": 3, "literalExactDescriptionMatchCount": 0, "candidates": [{}, {}, {}]},
                {"reviewTargetId": "e", "canonicalEnglishName": "E", "memberCount": 2, "usageCountSum": 0, "usedByRecipe": False, "candidateCount": 0, "literalExactDescriptionMatchCount": 0, "candidates": []},
            ],
        }
        triage, summary = triage_mod.classify(evidence)
        self.assertEqual(
            summary["reviewTargetsByLane"],
            {
                "unique-literal-exact": 1,
                "multiple-literal-exact": 1,
                "singleton-nonexact": 1,
                "multi-candidate": 1,
                "zero-candidate": 1,
            },
        )
        self.assertEqual(summary["bindingCreatedCount"], 0)
        self.assertEqual(summary["selectionCount"], 0)
        self.assertTrue(all(row["manualReviewRequired"] for row in triage["items"]))
        self.assertTrue(all(row["bindingCreated"] is False for row in triage["items"]))
        self.assertEqual(summary["memberIdentityCount"], 6)

    def test_duplicate_review_target_is_rejected(self):
        targets = self._targets()
        targets["targets"][1]["reviewTargetId"] = targets["targets"][0]["reviewTargetId"]
        with self.assertRaisesRegex(RuntimeError, "duplicate review target"):
            capture_mod.capture(targets, FakeIndex({}))


if __name__ == "__main__":
    unittest.main()
