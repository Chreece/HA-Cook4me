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


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reference = _load("fdc_reference_data_v60_test", TOOLS / "fdc_reference_data_v60.py")
offline_candidates = _load(
    "fdc_offline_candidates_v60_test",
    TOOLS / "snapshot_release_catalog_fdc_target_candidates_offline_v60.py",
)
offline_resolver = _load(
    "fdc_offline_resolver_v60_test",
    TOOLS / "resolve_reviewed_release_catalog_nutrition_targets_offline_v60.py",
)


def _food(fdc_id: int, description: str, *, data_type: str) -> dict:
    return {
        "fdcId": fdc_id,
        "description": description,
        "dataType": data_type,
        "foodCategory": {"description": "Vegetables"},
        "foodNutrients": [
            {
                "nutrient": {"name": "Energy", "unitName": "kcal"},
                "amount": 18.0,
            },
            {
                "nutrient": {"name": "Protein", "unitName": "g"},
                "amount": 0.9,
            },
        ],
    }


def _targets() -> dict:
    return {
        "schemaVersion": 1,
        "kind": "cook4me-release-catalog-nutrition-review-targets-v60",
        "catalogVersion": "v60-test",
        "identityCount": 2,
        "reviewTargetCount": 2,
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
                "reviewTargetId": "M_FOOD_TOMATO",
                "reviewTargetKind": "provider-identity",
                "canonicalEnglishName": "Tomato",
                "memberIngredientIds": ["M_FOOD_TOMATO"],
                "memberCount": 1,
                "usageCountSum": 2,
                "usedByRecipe": True,
            },
            {
                "reviewTargetId": "concept:food:sea-salt",
                "reviewTargetKind": "semantic-concept",
                "semanticConceptId": "concept:food:sea-salt",
                "canonicalEnglishName": "Sea salt",
                "memberIngredientIds": ["local:de:salt"],
                "memberCount": 1,
                "usageCountSum": 1,
                "usedByRecipe": True,
            },
        ],
    }


class FdcReferenceDataV60Tests(unittest.TestCase):
    def _reference(self, root: Path):
        foundation = root / "foundation.json"
        sr = root / "sr.json"
        foundation.write_text(
            json.dumps({"FoundationFoods": [_food(123, "Tomatoes, red, ripe, raw", data_type="Foundation")]}),
            encoding="utf-8",
        )
        sr.write_text(
            json.dumps({"SRLegacyFoods": [_food(456, "Salt, table", data_type="SR Legacy")]}),
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
            ],
        }
        manifest_path = root / "reference-manifest.v60.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return reference.ReferenceIndex(manifest_path)

    def test_local_search_is_evidence_only_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = self._reference(Path(tmp))
            candidates = index.search("Tomato", max_candidates=8)
            self.assertEqual(candidates[0]["fdcId"], 123)
            self.assertEqual(candidates[0]["dataType"], "Foundation")
            self.assertIn("localEvidenceScore", candidates[0])
            self.assertEqual(index.search("Completely unrelated phrase"), [])

    def test_offline_candidate_snapshot_never_selects(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = self._reference(Path(tmp))
            payload, summary = offline_candidates.snapshot(_targets(), index)
            self.assertFalse(payload["policy"]["selectionPerformed"])
            self.assertFalse(payload["policy"]["searchResultAutoAccepted"])
            self.assertFalse(payload["policy"]["networkRequestsPerformed"])
            self.assertEqual(summary["reviewTargetCount"], 2)
            self.assertEqual(summary["selectionCount"], 0)

    def test_reviewed_exact_id_resolves_from_local_dataset_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = self._reference(Path(tmp))
            reviews = {
                "M_FOOD_TOMATO": {
                    "reviewTargetId": "M_FOOD_TOMATO",
                    "reviewTargetKind": "provider-identity",
                    "canonicalEnglishName": "Tomato",
                    "fdcId": 123,
                    "confidence": "high",
                    "reviewFile": "targets.v1.json",
                },
                "concept:food:sea-salt": {
                    "reviewTargetId": "concept:food:sea-salt",
                    "reviewTargetKind": "semantic-concept",
                    "canonicalEnglishName": "Sea salt",
                    "fdcId": 456,
                    "confidence": "high",
                    "reviewFile": "targets.v1.json",
                },
            }
            cache, pending = offline_resolver.resolve_offline(_targets(), {}, reviews, index)
            self.assertEqual(pending["summary"]["pendingReviewTargetCount"], 0)
            self.assertFalse(pending["summary"]["networkRequestsPerformed"])
            self.assertFalse(pending["summary"]["apiKeyRequired"])
            self.assertEqual(cache["M_FOOD_TOMATO"]["sourceId"], 123)
            self.assertEqual(cache["M_FOOD_TOMATO"]["sourceReferenceDataset"], "Foundation")
            self.assertEqual(cache["local:de:salt"]["sourceId"], 456)
            self.assertEqual(cache["local:de:salt"]["sourceReferenceDataset"], "SR Legacy")

    def test_unreviewed_target_stays_pending_even_when_candidate_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = self._reference(Path(tmp))
            cache, pending = offline_resolver.resolve_offline(_targets(), {}, {}, index)
            self.assertEqual(cache, {})
            self.assertEqual(pending["summary"]["pendingReviewTargetCount"], 2)
            self.assertEqual(pending["summary"]["fdcDetailFetchCount"], 0)


if __name__ == "__main__":
    unittest.main()
