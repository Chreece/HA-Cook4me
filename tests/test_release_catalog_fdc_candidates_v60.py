from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location(
    "cook4me_fdc_candidate_evidence_v60_test",
    TOOLS / "snapshot_release_catalog_fdc_candidates_v60.py",
)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def queue() -> dict:
    return {
        "schemaVersion": 1,
        "kind": "cook4me-release-catalog-nutrition-queue-v60",
        "catalogVersion": "v60-test",
        "identityPolicy": {
            "providerIngredientIdsPreserved": True,
            "providerIdentityInference": False,
            "sourceLocalFoodRequiresReviewedNutritionEligibility": True,
            "reviewedExactFdcProvenanceRequired": True,
            "legacyStructuralNutritionAccepted": False,
            "ambiguousExcluded": True,
            "equipmentAndOtherExcluded": True,
            "searchResultAutoAccepted": False,
        },
        "taskCount": 3,
        "tasks": [
            {
                "ingredientId": "M_FOOD_TOMATO",
                "canonicalEnglishName": "Tomato",
                "identityKind": "provider",
                "usageCount": 20,
                "usedByRecipe": True,
            },
            {
                "ingredientId": "local:de:sea-salt",
                "canonicalEnglishName": "Sea salt",
                "identityKind": "source-local",
                "usageCount": 5,
                "usedByRecipe": True,
            },
            {
                "ingredientId": "M_FOOD_UNUSED",
                "canonicalEnglishName": "Unused food",
                "identityKind": "provider",
                "usageCount": 0,
                "usedByRecipe": False,
            },
        ],
    }


def response(name: str) -> dict:
    return {
        "foods": [
            {
                "fdcId": 101,
                "description": f"{name}, raw",
                "dataType": "Foundation",
                "foodCategory": "Vegetables",
                "score": 99.1,
            },
            {
                "fdcId": 101,
                "description": f"{name}, duplicate",
                "dataType": "Foundation",
                "score": 98.0,
            },
            {
                "fdcId": 202,
                "description": f"{name}, legacy",
                "dataType": "SR Legacy",
                "scientificName": "Example species",
            },
            {
                "fdcId": 303,
                "description": f"{name}, branded",
                "dataType": "Branded",
            },
        ]
    }


class ReleaseCatalogFdcCandidatesV60Tests(unittest.TestCase):
    def test_candidate_snapshot_never_selects_or_auto_accepts(self):
        searched: list[str] = []

        def fetcher(query: str) -> dict:
            searched.append(query)
            return response(query)

        payload, summary = mod.snapshot(queue(), fetcher=fetcher, max_candidates=8)
        self.assertEqual(searched, ["Tomato", "Sea salt", "Unused food"])
        self.assertEqual(payload["kind"], "cook4me-fdc-candidate-evidence-v60")
        self.assertFalse(payload["policy"]["selectionPerformed"])
        self.assertFalse(payload["policy"]["searchResultAutoAccepted"])
        self.assertFalse(payload["policy"]["candidateSearchIsIdentityProof"])
        self.assertTrue(payload["policy"]["manualExactIdReviewRequired"])
        self.assertEqual(summary["selectionCount"], 0)
        for item in payload["items"]:
            self.assertFalse(item["selectionPerformed"])
            self.assertTrue(item["needsManualExactIdReview"])
            self.assertNotIn("selectedFdcId", item)
            self.assertNotIn("fdcId", {key: value for key, value in item.items() if key != "candidates"})

    def test_candidates_are_deduped_filtered_and_keep_response_rank(self):
        payload, summary = mod.snapshot(
            queue(),
            fetcher=lambda query: response(query),
            offset=0,
            limit=1,
            max_candidates=8,
        )
        candidates = payload["items"][0]["candidates"]
        self.assertEqual([row["fdcId"] for row in candidates], [101, 202])
        self.assertEqual([row["responseRank"] for row in candidates], [1, 3])
        self.assertEqual(candidates[0]["dataType"], "Foundation")
        self.assertEqual(candidates[1]["dataType"], "SR Legacy")
        self.assertEqual(summary["candidateCount"], 2)

    def test_reviewed_ids_are_skipped_without_search(self):
        searched: list[str] = []
        payload, summary = mod.snapshot(
            queue(),
            fetcher=lambda query: searched.append(query) or response(query),
            reviewed_ids={"M_FOOD_TOMATO"},
            offset=0,
            limit=2,
        )
        self.assertEqual(searched, ["Sea salt"])
        self.assertEqual([row["ingredientId"] for row in payload["items"]], ["local:de:sea-salt"])
        self.assertEqual(summary["alreadyReviewedSkipped"], 1)
        self.assertEqual(summary["searchedTaskCount"], 1)

    def test_slice_is_deterministic_and_preserves_impact_queue_order(self):
        searched: list[str] = []
        payload, summary = mod.snapshot(
            queue(),
            fetcher=lambda query: searched.append(query) or {"foods": []},
            offset=1,
            limit=1,
        )
        self.assertEqual(searched, ["Sea salt"])
        self.assertEqual(payload["queueSlice"]["offset"], 1)
        self.assertEqual(payload["queueSlice"]["endExclusive"], 2)
        self.assertEqual(payload["items"][0]["queueIndex"], 1)
        self.assertEqual(payload["items"][0]["usageCount"], 5)
        self.assertEqual(summary["zeroCandidateTaskCount"], 1)

    def test_bad_queue_policy_is_rejected_before_search(self):
        value = queue()
        value["identityPolicy"]["searchResultAutoAccepted"] = True
        called = False

        def fetcher(_query: str) -> dict:
            nonlocal called
            called = True
            return {"foods": []}

        with self.assertRaisesRegex(RuntimeError, "fail-closed identity policy"):
            mod.snapshot(value, fetcher=fetcher)
        self.assertFalse(called)

    def test_output_contains_no_api_key_or_review_binding(self):
        secret = "fdc-secret-that-must-not-persist"
        # snapshot never accepts an API key argument at all; the caller-owned
        # fetcher may use one but only returned public candidate evidence enters output.
        payload, summary = mod.snapshot(
            queue(),
            fetcher=lambda query: response(query),
            limit=1,
        )
        serialized = json.dumps({"payload": payload, "summary": summary})
        self.assertNotIn(secret, serialized)
        self.assertFalse(summary["secretsPersisted"])
        self.assertNotIn("reviewFile", serialized)
        self.assertNotIn("reviewedCanonicalEnglishName", serialized)


if __name__ == "__main__":
    unittest.main()
