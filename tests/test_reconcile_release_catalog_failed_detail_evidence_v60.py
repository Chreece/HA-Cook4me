from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import reconcile_release_catalog_failed_detail_evidence_v60 as reconcile  # noqa: E402
import release_catalog_detail_not_found_v60 as detail_not_found  # noqa: E402


def catalog() -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "test-v60",
        "complete": False,
        "source": {
            "auditedCatalogCount": 1,
            "catalogs": [
                {
                    "language": "en",
                    "country": "GB",
                    "market": "GS_GB",
                    "uniqueVariants": 2,
                    "hydratedVariants": 1,
                    "failedDetails": 1,
                }
            ],
            "failedDetailCount": 1,
            "unresolvedCanonicalIngredientNames": 0,
            "unresolvedCanonicalRecipeNames": 0,
            "nutritionRequiredForComplete": False,
        },
        "ingredients": [],
        "recipes": [],
    }


def evidence() -> dict:
    return {
        "schemaVersion": 1,
        "kind": reconcile.EVIDENCE_KIND,
        "catalogVersion": "test-v60",
        "generatedAt": "2026-09-14T11:07:10+00:00",
        "summary": {
            "failedCatalogCount": 1,
            "declaredFailedDetailCount": 1,
            "currentCandidateCount": 1,
            "probedCount": 1,
            "searchFailureCount": 0,
            "outcomes": {"http-404": 1},
        },
        "catalogs": [
            {
                "language": "en",
                "country": "GB",
                "market": "GS_GB",
                "declaredUniqueVariants": 2,
                "declaredHydratedVariants": 1,
                "declaredFailedDetails": 1,
                "state": "probed",
                "searchManifestCountStable": True,
                "candidateCountMatchesDeclaredFailures": True,
                "unattributedDeclaredFailureCount": 0,
                "evidence": [
                    {"variantId": "B", "outcome": "http-404", "httpStatuses": [404]}
                ],
            }
        ],
    }


class FailedDetailReconciliationTests(unittest.TestCase):
    def test_exact_public_404_evidence_reconciles_failures(self):
        payload = catalog()
        # The capture completeness helper also checks recipe/ingredient semantic
        # counters and detail arithmetic, not table non-emptiness.
        result = reconcile.reconcile(payload, evidence())
        row = result["source"]["catalogs"][0]
        self.assertEqual(row["failedDetails"], 0)
        self.assertEqual(row["detailNotFoundCount"], 1)
        self.assertEqual(row["detailNotFoundVariantIds"], ["B"])
        self.assertEqual(result["source"]["failedDetailCount"], 0)
        self.assertEqual(result["source"]["detailNotFoundCount"], 1)
        self.assertEqual(
            result["source"]["detailNotFoundPolicy"],
            detail_not_found._CURRENT_PROBE_POLICY,
        )
        self.assertEqual(detail_not_found.validation_errors(result), [])
        self.assertTrue(result["complete"])

    def test_non_404_probe_remains_fail_closed(self):
        value = evidence()
        value["summary"]["outcomes"] = {"http-other": 1}
        value["catalogs"][0]["evidence"][0].update(
            {"outcome": "http-other", "httpStatuses": [500]}
        )
        with self.assertRaises(RuntimeError):
            reconcile.reconcile(catalog(), value)

    def test_manifest_or_count_drift_remains_fail_closed(self):
        for mutate in ("manifest", "candidate", "count"):
            with self.subTest(mutate=mutate):
                value = evidence()
                if mutate == "manifest":
                    value["catalogs"][0]["searchManifestCountStable"] = False
                elif mutate == "candidate":
                    value["catalogs"][0]["candidateCountMatchesDeclaredFailures"] = False
                else:
                    value["catalogs"][0]["declaredFailedDetails"] = 2
                with self.assertRaises(RuntimeError):
                    reconcile.reconcile(catalog(), value)

    def test_current_probe_policy_requires_evidence_metadata(self):
        result = reconcile.reconcile(catalog(), evidence())
        for field in (
            "detailNotFoundEvidenceKind",
            "detailNotFoundEvidenceGeneratedAt",
            "detailNotFoundSearchManifestStable",
            "detailNotFoundCandidateCountMatched",
            "detailNotFoundPublicApp404Only",
        ):
            with self.subTest(field=field):
                broken = deepcopy(result)
                broken["source"].pop(field, None)
                self.assertTrue(detail_not_found.validation_errors(broken))


if __name__ == "__main__":
    unittest.main()
