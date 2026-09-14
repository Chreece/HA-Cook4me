from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import propose_release_catalog_nutrition_review_similarity_v60 as proposal  # noqa: E402


def _candidate_payload(items: list[dict]) -> dict:
    return {
        "schemaVersion": 1,
        "kind": proposal.CANDIDATE_KIND,
        "catalogVersion": "2026-09-14-v60-progressive",
        "referenceManifestSha256": "6ad28b" * 10 + "6ad2",
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


def _candidate(fdc_id: int, *, rank: int = 1, score: float = 500.0) -> dict:
    return {
        "fdcId": fdc_id,
        "description": f"Food {fdc_id}",
        "dataType": "Survey (FNDDS)",
        "localEvidenceRank": rank,
        "localEvidenceScore": score,
    }


def _target(
    target_id: str,
    canonical: str,
    *,
    candidates: list[dict],
    usage: int = 1,
) -> dict:
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
        "reviewTargetKind": "semantic-concept",
        "canonicalEnglishName": canonical,
        "fdcId": fdc_id,
        "confidence": "medium",
    }


class NutritionReviewSimilarityProposalV60Tests(unittest.TestCase):
    def test_near_duplicate_is_surfaced_only_when_historical_fdc_is_own_candidate(self):
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Salted butter, melted with chocolate",
                    candidates=[_candidate(173410, rank=12), _candidate(999, rank=1)],
                    usage=17,
                )
            ]
        )
        reviews = {
            "concept:food:old": _review(
                "concept:food:old", "Salted butter", 173410
            )
        }

        payload, summary = proposal.suggest(candidates, reviews)

        self.assertEqual(payload["kind"], proposal.SUGGESTION_KIND)
        self.assertEqual(payload["suggestionTargetCount"], 1)
        row = payload["targets"][0]
        self.assertEqual(row["reviewTargetId"], "concept:food:new")
        self.assertFalse(row["ambiguousHistoricalFdcSuggestions"])
        self.assertFalse(row["selectionPerformed"])
        suggestion = row["suggestions"][0]
        self.assertEqual(suggestion["suggestedFdcId"], 173410)
        self.assertEqual(suggestion["candidateEvidenceRank"], 12)
        self.assertEqual(
            suggestion["historicalMatches"][0]["historicalReviewTargetId"],
            "concept:food:old",
        )
        self.assertTrue(
            suggestion["historicalMatches"][0]["substringRelation"]
        )
        self.assertEqual(summary["suggestionUsageCount"], 17)
        self.assertEqual(summary["selectionCount"], 0)

    def test_matching_history_is_rejected_when_fdc_is_not_in_target_own_evidence(self):
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Frozen peeled shrimp tails",
                    candidates=[_candidate(111)],
                )
            ]
        )
        reviews = {
            "concept:food:old": _review(
                "concept:food:old", "Peeled shrimp tails", 2706360
            )
        }

        payload, summary = proposal.suggest(candidates, reviews)

        self.assertEqual(payload["suggestionTargetCount"], 0)
        self.assertEqual(summary["suggestionCount"], 0)
        self.assertEqual(summary["ownCandidateHistoricalMatchCount"], 0)

    def test_exact_canonical_name_is_left_to_exact_reuse_lane(self):
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Crème fraîche",
                    candidates=[_candidate(123)],
                )
            ]
        )
        reviews = {
            "concept:food:old": _review(
                "concept:food:old", "  CRÈME FRAÎCHE  ", 123
            )
        }

        payload, summary = proposal.suggest(candidates, reviews)

        self.assertEqual(payload["suggestionTargetCount"], 0)
        self.assertEqual(summary["weakSimilarityExcludedCount"], 1)

    def test_unrelated_names_with_same_fdc_candidate_are_not_surfaced(self):
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Rice vinegar",
                    candidates=[_candidate(123)],
                )
            ]
        )
        reviews = {
            "concept:food:old": _review(
                "concept:food:old", "White bread", 123
            )
        }

        payload, summary = proposal.suggest(candidates, reviews)

        self.assertEqual(payload["suggestionTargetCount"], 0)
        self.assertEqual(summary["weakSimilarityExcludedCount"], 1)

    def test_multiple_fdc_histories_are_preserved_and_marked_ambiguous(self):
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Large slices of toasted rustic bread",
                    candidates=[_candidate(172685, rank=9), _candidate(333, rank=2)],
                    usage=4,
                )
            ]
        )
        reviews = {
            "concept:food:rye": _review(
                "concept:food:rye", "Slices of toasted rustic bread", 172685
            ),
            "concept:food:toast": _review(
                "concept:food:toast", "Large toasted rustic bread slices", 333
            ),
        }

        payload, summary = proposal.suggest(candidates, reviews)

        self.assertEqual(payload["suggestionTargetCount"], 1)
        row = payload["targets"][0]
        self.assertTrue(row["ambiguousHistoricalFdcSuggestions"])
        self.assertEqual(len(row["suggestions"]), 2)
        self.assertEqual(
            {value["suggestedFdcId"] for value in row["suggestions"]},
            {172685, 333},
        )
        self.assertEqual(summary["ambiguousTargetCount"], 1)
        self.assertEqual(summary["selectionCount"], 0)

    def test_already_reviewed_target_is_skipped_from_stale_candidate_snapshot(self):
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:current",
                    "Frozen peeled shrimp tails",
                    candidates=[_candidate(2706360)],
                )
            ]
        )
        reviews = {
            "concept:food:current": _review(
                "concept:food:current", "Frozen peeled shrimp tails", 2706360
            ),
            "concept:food:old": _review(
                "concept:food:old", "Peeled shrimp tails", 2706360
            ),
        }

        payload, summary = proposal.suggest(candidates, reviews)

        self.assertEqual(payload["suggestionTargetCount"], 0)
        self.assertEqual(summary["alreadyReviewedTargetSkipped"], 1)

    def test_held_historical_reviews_are_excluded(self):
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Salted butter, melted",
                    candidates=[_candidate(173410)],
                )
            ]
        )
        reviews = {
            "concept:food:old": _review(
                "concept:food:old", "Salted butter", 173410
            )
        }

        with patch.object(
            proposal.resolver.reviewed_nutrition.holds,
            "profile_hold",
            return_value={"reason": "test hold"},
        ):
            payload, summary = proposal.suggest(candidates, reviews)

        self.assertEqual(payload["suggestionTargetCount"], 0)
        self.assertEqual(summary["heldHistoricalReviewsExcluded"], 1)

    def test_suggestion_limit_is_fail_closed_and_deterministic(self):
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Toasted rustic bread slices",
                    candidates=[
                        _candidate(101, rank=3),
                        _candidate(102, rank=2),
                        _candidate(103, rank=1),
                    ],
                )
            ]
        )
        reviews = {
            "old-1": _review("old-1", "Rustic bread slices toasted", 101),
            "old-2": _review("old-2", "Toasted rustic bread slice", 102),
            "old-3": _review("old-3", "Slices of toasted rustic bread", 103),
        }

        payload, _summary = proposal.suggest(
            candidates, reviews, max_suggestions_per_target=2
        )

        self.assertEqual(len(payload["targets"][0]["suggestions"]), 2)

    def test_unsafe_candidate_policy_is_rejected(self):
        candidates = _candidate_payload([])
        candidates["policy"]["searchResultAutoAccepted"] = True
        with self.assertRaisesRegex(RuntimeError, "unsafe policy"):
            proposal.suggest(candidates, {})

    def test_policy_makes_similarity_explicitly_non_binding(self):
        candidates = _candidate_payload(
            [
                _target(
                    "concept:food:new",
                    "Peeled shrimp tails, frozen",
                    candidates=[_candidate(2706360)],
                )
            ]
        )
        payload, summary = proposal.suggest(
            candidates,
            {
                "concept:food:old": _review(
                    "concept:food:old", "Frozen peeled shrimp tails", 2706360
                )
            },
        )

        self.assertEqual(
            payload["policy"],
            {
                "selectionPerformed": False,
                "searchResultAutoAccepted": False,
                "candidateSearchIsIdentityProof": False,
                "providerIdentityInference": False,
                "manualSemanticReviewRequired": True,
                "exactCanonicalReuseExcluded": True,
                "historicalFdcMustExistInTargetOwnEvidence": True,
                "lexicalSimilarityIsIdentityProof": False,
                "networkRequestsPerformed": False,
                "secretsPersisted": False,
            },
        )
        self.assertEqual(summary["selectionCount"], 0)
        self.assertFalse(summary["networkRequestsPerformed"])
        self.assertFalse(summary["secretsPersisted"])


if __name__ == "__main__":
    unittest.main()
