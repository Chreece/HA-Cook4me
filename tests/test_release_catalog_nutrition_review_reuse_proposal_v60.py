from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import propose_release_catalog_nutrition_review_reuse_v60 as proposal  # noqa: E402


def _candidate_payload(items: list[dict]) -> dict:
    return {
        "schemaVersion": 1,
        "kind": proposal.CANDIDATE_KIND,
        "catalogVersion": "2026-09-11-v60-capture3",
        "referenceManifestSha256": "e135" * 16,
        "policy": {
            "candidateSearchIsIdentityProof": False,
            "selectionPerformed": False,
            "searchResultAutoAccepted": False,
            "manualExactIdReviewRequired": True,
            "providerIngredientIdentityInference": False,
            "networkRequestsPerformed": False,
            "secretsPersisted": False,
        },
        "items": items,
    }


def _target(
    target_id: str,
    canonical: str,
    *,
    fdc_id: int | None = None,
    rank: int = 1,
    usage: int = 1,
) -> dict:
    candidates = []
    if fdc_id is not None:
        candidates.append(
            {
                "fdcId": fdc_id,
                "description": f"Food {fdc_id}",
                "dataType": "Survey (FNDDS)",
                "localEvidenceRank": rank,
                "localEvidenceScore": 1000.0,
            }
        )
    return {
        "reviewTargetId": target_id,
        "reviewTargetKind": (
            "semantic-concept"
            if target_id.startswith("concept:food:")
            else "provider-identity"
        ),
        "canonicalEnglishName": canonical,
        "usageCountSum": usage,
        "candidates": candidates,
        "selectionPerformed": False,
        "needsManualExactIdReview": True,
    }


def _review(target_id: str, canonical: str, fdc_id: int) -> dict:
    return {
        "reviewTargetId": target_id,
        "reviewTargetKind": "provider-identity",
        "canonicalEnglishName": canonical,
        "fdcId": fdc_id,
        "confidence": "high",
    }


class NutritionReviewReuseProposalV60Tests(unittest.TestCase):
    def test_exact_canonical_unambiguous_history_proposes_only_when_own_candidate_exists(self):
        reviews = {
            "M_OLD": _review("M_OLD", "Tomato", 123),
            "M_OLD_2": _review("M_OLD_2", "  TOMATO  ", 123),
        }
        candidates = _candidate_payload(
            [_target("concept:food:new", " tomato ", fdc_id=123, rank=2, usage=42)]
        )

        payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["kind"], proposal.PROPOSAL_KIND)
        self.assertEqual(payload["proposalCount"], 1)
        self.assertEqual(payload["conflictCount"], 0)
        row = payload["proposals"][0]
        self.assertEqual(row["reviewTargetId"], "concept:food:new")
        self.assertEqual(row["proposedFdcId"], 123)
        self.assertEqual(row["candidateEvidenceRank"], 2)
        self.assertEqual(row["historicalReviewCount"], 2)
        self.assertEqual(row["historicalReviewTargetIds"], ["M_OLD", "M_OLD_2"])
        self.assertEqual(row["confidence"], "proposal-only")
        self.assertFalse(row["selectionPerformed"])
        self.assertTrue(row["needsManualExactIdReview"])
        self.assertEqual(summary["proposalUsageCount"], 42)
        self.assertEqual(summary["selectionCount"], 0)
        self.assertFalse(summary["networkRequestsPerformed"])
        self.assertFalse(summary["secretsPersisted"])

    def test_conflicting_historical_ids_fail_closed(self):
        reviews = {
            "M_OLD": _review("M_OLD", "Tomato", 123),
            "M_OLD_2": _review("M_OLD_2", "tomato", 456),
        }
        candidates = _candidate_payload(
            [_target("concept:food:new", "Tomato", fdc_id=123, usage=9)]
        )

        payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalCount"], 0)
        self.assertEqual(payload["conflictCount"], 1)
        self.assertEqual(payload["conflicts"][0]["historicalFdcIds"], [123, 456])
        self.assertEqual(summary["proposalCount"], 0)
        self.assertEqual(summary["conflictCount"], 1)

    def test_prior_id_missing_from_target_own_candidates_is_not_proposed(self):
        reviews = {"M_OLD": _review("M_OLD", "Tomato", 123)}
        candidates = _candidate_payload(
            [_target("concept:food:new", "Tomato", fdc_id=456, usage=7)]
        )

        payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalCount"], 0)
        self.assertEqual(summary["exactCanonicalHistoryTargetCount"], 1)
        self.assertEqual(summary["missingTargetOwnCandidateCount"], 1)

    def test_already_reviewed_target_is_skipped_even_if_present_in_stale_candidate_snapshot(self):
        reviews = {
            "M_CURRENT": _review("M_CURRENT", "Tomato", 123),
            "M_OLD": _review("M_OLD", "Tomato", 123),
        }
        candidates = _candidate_payload(
            [_target("M_CURRENT", "Tomato", fdc_id=123, usage=99)]
        )

        payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalCount"], 0)
        self.assertEqual(summary["alreadyReviewedTargetSkipped"], 1)
        self.assertEqual(summary["exactCanonicalHistoryTargetCount"], 0)

    def test_no_exact_canonical_history_means_no_proposal(self):
        reviews = {"M_OLD": _review("M_OLD", "Tomato", 123)}
        candidates = _candidate_payload(
            [_target("concept:food:new", "Tomato paste", fdc_id=123, usage=3)]
        )

        payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalCount"], 0)
        self.assertEqual(summary["exactCanonicalHistoryTargetCount"], 0)

    def test_nfkc_case_whitespace_normalization_does_not_strip_accents(self):
        reviews = {
            "M_CREME": _review("M_CREME", "Crème fraîche", 111),
            "M_CREME_PLAIN": _review("M_CREME_PLAIN", "Creme fraiche", 222),
        }
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:accented",
                    "  CRÈME   FRAÎCHE ",
                    fdc_id=111,
                    usage=2,
                )
            ]
        )

        payload, _summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalCount"], 1)
        self.assertEqual(payload["proposals"][0]["proposedFdcId"], 111)

    def test_unsafe_candidate_policy_is_rejected(self):
        candidates = _candidate_payload([])
        candidates["policy"]["searchResultAutoAccepted"] = True
        with self.assertRaisesRegex(RuntimeError, "unsafe policy"):
            proposal.propose(candidates, {})

    def test_proposal_policy_is_review_only(self):
        candidates = _candidate_payload(
            [_target("concept:food:new", "Tomato", fdc_id=123)]
        )
        payload, summary = proposal.propose(
            candidates,
            {"M_OLD": _review("M_OLD", "Tomato", 123)},
        )

        self.assertEqual(
            payload["policy"],
            {
                "selectionPerformed": False,
                "searchResultAutoAccepted": False,
                "candidateSearchIsIdentityProof": False,
                "providerIdentityInference": False,
                "manualExactIdReviewRequired": True,
                "exactCanonicalHistoryRequired": True,
                "unambiguousHistoricalFdcIdRequired": True,
                "targetOwnCandidateEvidenceRequired": True,
                "networkRequestsPerformed": False,
                "secretsPersisted": False,
            },
        )
        self.assertEqual(summary["selectionCount"], 0)


if __name__ == "__main__":
    unittest.main()
