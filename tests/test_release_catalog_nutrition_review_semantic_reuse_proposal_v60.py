from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import propose_release_catalog_nutrition_review_semantic_reuse_v60 as proposal  # noqa: E402


def _candidate_payload(items: list[dict]) -> dict:
    return {
        "schemaVersion": 1,
        "kind": proposal.CANDIDATE_KIND,
        "catalogVersion": "2026-09-14-v60-progressive",
        "referenceManifestSha256": "6ad2" * 16,
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


def _candidate(fdc_id: int, *, rank: int = 1, description: str | None = None) -> dict:
    return {
        "fdcId": fdc_id,
        "description": description or f"Food {fdc_id}",
        "dataType": "Foundation",
        "localEvidenceRank": rank,
        "localEvidenceScore": 900.0 - rank,
    }


def _target(
    target_id: str,
    canonical: str,
    candidates: list[dict],
    *,
    usage: int = 1,
    kind: str = "semantic-concept",
) -> dict:
    return {
        "reviewTargetId": target_id,
        "reviewTargetKind": kind,
        "canonicalEnglishName": canonical,
        "usageCountSum": usage,
        "candidates": candidates,
        "selectionPerformed": False,
        "needsManualExactIdReview": True,
    }


def _review(
    target_id: str,
    canonical: str,
    fdc_id: int,
    *,
    kind: str = "semantic-concept",
) -> dict:
    return {
        "reviewTargetId": target_id,
        "reviewTargetKind": kind,
        "canonicalEnglishName": canonical,
        "fdcId": fdc_id,
        "confidence": "high",
        "reviewFile": "review.v1.json",
    }


class NutritionSemanticReuseProposalV60Tests(unittest.TestCase):
    def test_similar_history_is_suggested_only_for_target_owned_candidate(self):
        reviews = {
            "concept:food:old": _review(
                "concept:food:old", "Vegetable stock", 171583
            )
        }
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Vegetable stock (or water)",
                    [_candidate(171583, rank=3, description="Soup, vegetable broth")],
                    usage=15,
                )
            ]
        )

        payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["kind"], proposal.PROPOSAL_KIND)
        self.assertEqual(payload["proposalTargetCount"], 1)
        self.assertEqual(payload["suggestionCount"], 1)
        target = payload["proposalTargets"][0]
        self.assertEqual(target["reviewTargetId"], "concept:food:new")
        suggestion = target["suggestions"][0]
        self.assertEqual(suggestion["suggestedFdcId"], 171583)
        self.assertEqual(suggestion["candidateEvidenceRank"], 3)
        self.assertGreaterEqual(
            suggestion["bestSimilarityScore"], proposal.SIMILARITY_THRESHOLD
        )
        self.assertFalse(suggestion["selectionPerformed"])
        self.assertTrue(suggestion["manualSemanticReviewRequired"])
        self.assertEqual(summary["proposalUsageCount"], 15)
        self.assertEqual(summary["selectionCount"], 0)

    def test_history_cannot_introduce_fdc_id_missing_from_own_candidates(self):
        reviews = {
            "concept:food:old": _review(
                "concept:food:old", "Vegetable stock", 171583
            )
        }
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Vegetable stock (or water)",
                    [_candidate(2707132)],
                )
            ]
        )

        payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalTargetCount"], 0)
        self.assertEqual(payload["suggestionCount"], 0)
        self.assertEqual(summary["selectionCount"], 0)

    def test_exact_canonical_match_is_left_to_stricter_reuse_lane(self):
        reviews = {
            "concept:food:old": _review(
                "concept:food:old", "Vegetable stock", 171583
            )
        }
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "  VEGETABLE   STOCK ",
                    [_candidate(171583)],
                )
            ]
        )

        payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalTargetCount"], 0)
        self.assertEqual(summary["exactCanonicalHistoricalMatchesExcluded"], 1)

    def test_weak_or_token_unrelated_history_is_not_suggested(self):
        reviews = {
            "concept:food:old": _review("concept:food:old", "Vegetable stock", 123)
        }
        candidates = _candidate_payload(
            [_target("concept:food:new", "Mirin", [_candidate(123)])]
        )

        payload, _summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalTargetCount"], 0)

    def test_provider_targets_and_provider_history_are_excluded(self):
        reviews = {
            "M_OLD": _review("M_OLD", "Vegetable stock", 123, kind="provider-identity")
        }
        semantic_candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Vegetable stock (or water)",
                    [_candidate(123)],
                )
            ]
        )
        payload, summary = proposal.propose(semantic_candidates, reviews)
        self.assertEqual(payload["proposalTargetCount"], 0)
        self.assertEqual(summary["nonSemanticHistoricalReviewsExcluded"], 1)

        provider_candidates = _candidate_payload(
            [
                _target(
                    "M_NEW",
                    "Vegetable stock concentrate",
                    [_candidate(456)],
                    kind="provider-identity",
                )
            ]
        )
        payload, summary = proposal.propose(
            provider_candidates,
            {
                "concept:food:old": _review(
                    "concept:food:old", "Vegetable stock", 456
                )
            },
        )
        self.assertEqual(payload["proposalTargetCount"], 0)
        self.assertEqual(summary["providerTargetSkipped"], 1)

    def test_held_history_is_excluded(self):
        reviews = {
            "concept:food:held": _review(
                "concept:food:held", "Vegetable stock", 123
            )
        }
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Vegetable stock (or water)",
                    [_candidate(123)],
                )
            ]
        )

        with patch.object(
            proposal.resolver.reviewed_nutrition.holds,
            "profile_hold",
            return_value={"reason": "test hold"},
        ):
            payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalTargetCount"], 0)
        self.assertEqual(summary["heldHistoricalReviewsExcluded"], 1)

    def test_multiple_owned_historical_ids_remain_multiple_suggestions(self):
        reviews = {
            "concept:food:old1": _review(
                "concept:food:old1", "Vegetable stock", 111
            ),
            "concept:food:old2": _review(
                "concept:food:old2", "Vegetable broth", 222
            ),
        }
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Vegetable stock or broth",
                    [_candidate(111, rank=2), _candidate(222, rank=4)],
                    usage=8,
                )
            ]
        )

        payload, summary = proposal.propose(candidates, reviews)

        self.assertEqual(payload["proposalTargetCount"], 1)
        self.assertEqual(payload["suggestionCount"], 2)
        self.assertEqual(
            {row["suggestedFdcId"] for row in payload["proposalTargets"][0]["suggestions"]},
            {111, 222},
        )
        self.assertEqual(summary["multipleSuggestedFdcTargetCount"], 1)
        self.assertEqual(summary["selectionCount"], 0)

    def test_unsafe_candidate_policy_is_rejected(self):
        candidates = _candidate_payload([])
        candidates["policy"]["searchResultAutoAccepted"] = True

        with self.assertRaisesRegex(RuntimeError, "unsafe policy"):
            proposal.propose(candidates, {})

    def test_policy_is_explicitly_non_binding(self):
        payload, summary = proposal.propose(_candidate_payload([]), {})

        self.assertEqual(
            payload["policy"],
            {
                "selectionPerformed": False,
                "searchResultAutoAccepted": False,
                "candidateSearchIsIdentityProof": False,
                "providerIdentityInference": False,
                "manualSemanticReviewRequired": True,
                "exactCanonicalMatchesHandledByStricterLane": True,
                "semanticConceptHistoryOnly": True,
                "targetOwnCandidateEvidenceRequired": True,
                "historicalFdcIdCannotIntroduceNewCandidate": True,
                "networkRequestsPerformed": False,
                "secretsPersisted": False,
            },
        )
        self.assertEqual(summary["selectionCount"], 0)
        self.assertFalse(summary["networkRequestsPerformed"])
        self.assertFalse(summary["secretsPersisted"])


if __name__ == "__main__":
    unittest.main()
