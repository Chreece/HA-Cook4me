from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import fdc_reference_data_v60 as reference  # noqa: E402
import snapshot_release_catalog_fdc_target_candidates_offline_v60 as snapshotter  # noqa: E402


def _food(fdc_id: int, description: str) -> dict:
    return {
        "fdcId": fdc_id,
        "description": description,
        "foodNutrients": [],
    }


def _index(root: Path) -> reference.ReferenceIndex:
    foundation = root / "foundation.json"
    sr = root / "sr.json"
    fndds = root / "fndds.json"
    foundation.write_text(
        json.dumps(
            {
                "FoundationFoods": [
                    _food(101, "Eggplant, raw"),
                    _food(102, "Peppers, jalapeno, raw"),
                ]
            }
        ),
        encoding="utf-8",
    )
    sr.write_text(
        json.dumps(
            {
                "SRLegacyFoods": [
                    _food(201, "Bread, crumbs, dry, grated, plain"),
                    _food(202, "Chilli sauce"),
                ]
            }
        ),
        encoding="utf-8",
    )
    fndds.write_text(
        json.dumps(
            {
                "SurveyFoods": [
                    _food(301, "Sugar, brown"),
                    _food(302, "Yogurt, NFS"),
                ]
            }
        ),
        encoding="utf-8",
    )
    manifest = {
        "schemaVersion": 1,
        "kind": reference.REFERENCE_KIND,
        "policy": {
            "candidateDiscoveryOnlyUntilReviewed": True,
            "exactFdcBindingRequired": True,
            "searchResultAutoAccepted": False,
            "apiKeyRequired": False,
            "secretsPersisted": False,
        },
        "datasets": [
            {
                "dataType": "Foundation",
                "releaseDate": "2026-04-30",
                "jsonPath": foundation.name,
                "jsonSha256": reference.sha256(foundation),
            },
            {
                "dataType": "SR Legacy",
                "releaseDate": "2018-04",
                "jsonPath": sr.name,
                "jsonSha256": reference.sha256(sr),
            },
            {
                "dataType": "Survey (FNDDS)",
                "releaseDate": "2024-10-31",
                "jsonPath": fndds.name,
                "jsonSha256": reference.sha256(fndds),
            },
        ],
    }
    path = root / "reference-manifest.v60.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return reference.ReferenceIndex(path)


def _queue(name: str) -> dict:
    return {
        "schemaVersion": 1,
        "kind": "cook4me-release-catalog-nutrition-review-targets-v60",
        "catalogVersion": "v60-test",
        "identityCount": 1,
        "reviewTargetCount": 1,
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
                "reviewTargetId": "concept:food:test",
                "reviewTargetKind": "semantic-concept",
                "semanticConceptId": "concept:food:test",
                "canonicalEnglishName": name,
                "memberIngredientIds": ["local:test"],
                "memberCount": 1,
                "usageCountSum": 1,
                "usedByRecipe": True,
            }
        ],
    }


class FdcCandidateDiscoveryAliasesV60Tests(unittest.TestCase):
    def test_accent_folding_discovers_ascii_usda_wording_without_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = _index(Path(tmp))
            rows = index.search("Jalapeño")
            self.assertEqual(rows[0]["fdcId"], 102)
            self.assertNotIn("localEvidenceQueryAlias", rows[0])
            self.assertEqual(reference.norm("Crème fraîche"), "creme fraiche")

    def test_exact_token_set_beats_word_order_and_punctuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = _index(Path(tmp))
            rows = index.search("Brown sugar")
            self.assertEqual(rows[0]["fdcId"], 301)
            self.assertEqual(rows[0]["description"], "Sugar, brown")
            self.assertNotIn("localEvidenceQueryAlias", rows[0])

    def test_zero_result_alias_fallback_is_explicitly_tagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = _index(Path(tmp))
            rows = index.search("Aubergine")
            self.assertEqual(rows[0]["fdcId"], 101)
            self.assertIs(rows[0]["localEvidenceQueryAlias"], True)
            self.assertEqual(rows[0]["localEvidenceMatchedQuery"], "eggplant")

            crumbs = index.search("Breadcrumbs")
            self.assertEqual(crumbs[0]["fdcId"], 201)
            self.assertEqual(crumbs[0]["localEvidenceMatchedQuery"], "bread crumbs")

            yoghurt = index.search("Yoghurt")
            self.assertEqual(yoghurt[0]["fdcId"], 302)
            self.assertEqual(yoghurt[0]["localEvidenceMatchedQuery"], "yogurt")

    def test_aliases_never_displace_literal_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = _index(Path(tmp))
            rows = index.search("Chilli")
            self.assertEqual(rows[0]["fdcId"], 202)
            self.assertNotIn("localEvidenceQueryAlias", rows[0])

    def test_alias_candidate_snapshot_remains_evidence_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = _index(Path(tmp))
            payload, summary = snapshotter.snapshot(_queue("Aubergine"), index)
            row = payload["items"][0]
            self.assertFalse(row["selectionPerformed"])
            self.assertTrue(row["needsManualExactIdReview"])
            self.assertEqual(row["candidates"][0]["fdcId"], 101)
            self.assertTrue(row["candidates"][0]["localEvidenceQueryAlias"])
            self.assertFalse(payload["policy"]["searchResultAutoAccepted"])
            self.assertEqual(summary["selectionCount"], 0)
            self.assertFalse(summary["networkRequestsPerformed"])


if __name__ == "__main__":
    unittest.main()
