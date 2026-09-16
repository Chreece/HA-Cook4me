#!/usr/bin/env python3
"""Build offline semantic-history nutrition suggestions for manual review.

This is a reviewer aid only. It never selects or writes a nutrition binding.
Historical reviews may suggest an FDC record only when that exact FDC ID is
already present in the current target's own pinned candidate evidence.

Unlike exact-canonical reuse, this lane allows bounded lexical similarity between
canonical English labels. It therefore remains deliberately non-binding and
requires manual semantic review for every suggestion.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402

CANDIDATE_KIND = "cook4me-fdc-review-target-candidate-evidence-offline-v60"
PROPOSAL_KIND = "cook4me-nutrition-semantic-history-proposal-v60"
SIMILARITY_THRESHOLD = 0.60
MAX_SUGGESTIONS_PER_TARGET = 5
_STOP_TOKENS = frozenset({"a", "an", "and", "for", "of", "or", "the", "to", "with", "without"})
_WORD_RE = re.compile(r"[a-z0-9]+")


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _exact_norm(value: Any) -> str:
    return " ".join(unicodedata.normalize("NFKC", _text(value)).casefold().split())


def _semantic_norm(value: Any) -> str:
    normalized = unicodedata.normalize("NFKD", _text(value)).casefold()
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(_WORD_RE.findall(normalized))


def _content_tokens(value: Any) -> frozenset[str]:
    return frozenset(
        token
        for token in _semantic_norm(value).split()
        if token not in _STOP_TOKENS
    )


def _similarity(current: str, historical: str) -> dict[str, Any] | None:
    """Return bounded lexical similarity details, or None when too weak.

    Exact NFKC/casefold matches are left to the stricter exact-canonical reuse
    lane. Semantic matching removes accents and punctuation, then requires at
    least one shared non-stopword token. This deliberately favors review recall
    while the target-own-candidate guard prevents history from introducing a new
    USDA identity.
    """
    if _exact_norm(current) == _exact_norm(historical):
        return None

    current_norm = _semantic_norm(current)
    historical_norm = _semantic_norm(historical)
    current_tokens = _content_tokens(current)
    historical_tokens = _content_tokens(historical)
    shared = current_tokens & historical_tokens
    if not current_norm or not historical_norm or not shared:
        return None

    union = current_tokens | historical_tokens
    token_jaccard = len(shared) / max(1, len(union))
    token_containment = len(shared) / max(
        1, min(len(current_tokens), len(historical_tokens))
    )
    sequence_similarity = SequenceMatcher(
        None, current_norm, historical_norm
    ).ratio()
    score = (
        token_containment * 0.50
        + token_jaccard * 0.30
        + sequence_similarity * 0.20
    )
    if score < SIMILARITY_THRESHOLD:
        return None

    return {
        "score": round(score, 6),
        "sharedTokens": sorted(shared),
        "tokenJaccard": round(token_jaccard, 6),
        "tokenContainment": round(token_containment, 6),
        "sequenceSimilarity": round(sequence_similarity, 6),
    }


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _validate_candidates(value: dict[str, Any]) -> None:
    if value.get("kind") != CANDIDATE_KIND:
        raise RuntimeError(f"expected {CANDIDATE_KIND}")
    if not _text(value.get("catalogVersion")):
        raise RuntimeError("candidate evidence catalogVersion is required")
    if not _text(value.get("referenceManifestSha256")):
        raise RuntimeError("candidate evidence referenceManifestSha256 is required")
    policy = value.get("policy") if isinstance(value.get("policy"), dict) else {}
    required = {
        "candidateSearchIsIdentityProof": False,
        "selectionPerformed": False,
        "searchResultAutoAccepted": False,
        "providerIngredientIdentityInference": False,
        "networkRequestsPerformed": False,
        "secretsPersisted": False,
    }
    bad = [
        key
        for key, expected in required.items()
        if policy.get(key) is not expected
    ]
    if bad:
        raise RuntimeError(
            "candidate evidence has unsafe policy: " + ", ".join(bad)
        )


def propose(
    candidates: dict[str, Any],
    reviews: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_candidates(candidates)

    reviewed_ids = set(reviews)
    history_by_fdc: dict[int, list[dict[str, Any]]] = defaultdict(list)
    held_history_excluded = 0
    non_semantic_history_excluded = 0
    for row in reviews.values():
        if resolver.reviewed_nutrition.holds.profile_hold(row) is not None:
            held_history_excluded += 1
            continue
        if _text(row.get("reviewTargetKind")) != "semantic-concept":
            non_semantic_history_excluded += 1
            continue
        canonical = _text(row.get("canonicalEnglishName"))
        try:
            fdc_id = int(row.get("fdcId") or 0)
        except (TypeError, ValueError):
            continue
        if canonical and fdc_id > 0:
            history_by_fdc[fdc_id].append(row)

    proposal_targets: list[dict[str, Any]] = []
    already_reviewed_skipped = 0
    provider_target_skipped = 0
    exact_canonical_history_excluded = 0
    candidate_rows_with_history = 0

    for raw in candidates.get("items") or []:
        if not isinstance(raw, dict):
            continue
        target_id = _text(raw.get("reviewTargetId"))
        target_kind = _text(raw.get("reviewTargetKind"))
        canonical_name = _text(raw.get("canonicalEnglishName"))
        if not target_id or not canonical_name:
            continue
        if target_id in reviewed_ids:
            already_reviewed_skipped += 1
            continue
        if target_kind != "semantic-concept":
            provider_target_skipped += 1
            continue

        suggestions: list[dict[str, Any]] = []
        for evidence in raw.get("candidates") or []:
            if not isinstance(evidence, dict):
                continue
            try:
                fdc_id = int(evidence.get("fdcId") or 0)
            except (TypeError, ValueError):
                continue
            historical_rows = history_by_fdc.get(fdc_id, [])
            if not historical_rows:
                continue
            candidate_rows_with_history += 1

            matching_history: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for historical in historical_rows:
                historical_name = _text(historical.get("canonicalEnglishName"))
                if _exact_norm(canonical_name) == _exact_norm(historical_name):
                    exact_canonical_history_excluded += 1
                    continue
                similarity = _similarity(canonical_name, historical_name)
                if similarity is not None:
                    matching_history.append((historical, similarity))

            if not matching_history:
                continue

            matching_history.sort(
                key=lambda pair: (
                    -float(pair[1]["score"]),
                    _text(pair[0].get("canonicalEnglishName")).casefold(),
                    _text(pair[0].get("reviewTargetId")),
                )
            )
            best_score = float(matching_history[0][1]["score"])
            suggestions.append(
                {
                    "suggestedFdcId": fdc_id,
                    "fdcDescription": _text(evidence.get("description")),
                    "fdcDataType": _text(evidence.get("dataType")),
                    "candidateEvidenceRank": int(evidence.get("localEvidenceRank") or 0),
                    "candidateEvidenceScore": float(
                        evidence.get("localEvidenceScore") or 0.0
                    ),
                    "bestSimilarityScore": best_score,
                    "historicalMatches": [
                        {
                            "reviewTargetId": _text(historical.get("reviewTargetId")),
                            "canonicalEnglishName": _text(
                                historical.get("canonicalEnglishName")
                            ),
                            "reviewFile": _text(historical.get("reviewFile")),
                            **similarity,
                        }
                        for historical, similarity in matching_history
                    ],
                    "selectionPerformed": False,
                    "manualSemanticReviewRequired": True,
                }
            )

        suggestions.sort(
            key=lambda row: (
                -float(row["bestSimilarityScore"]),
                int(row["candidateEvidenceRank"]) or 10**9,
                int(row["suggestedFdcId"]),
            )
        )
        suggestions = suggestions[:MAX_SUGGESTIONS_PER_TARGET]
        if suggestions:
            proposal_targets.append(
                {
                    "reviewTargetId": target_id,
                    "reviewTargetKind": target_kind,
                    "canonicalEnglishName": canonical_name,
                    "usageCountAtReview": int(raw.get("usageCountSum") or 0),
                    "suggestions": suggestions,
                    "selectionPerformed": False,
                    "manualSemanticReviewRequired": True,
                }
            )

    proposal_targets.sort(
        key=lambda row: (
            -int(row["usageCountAtReview"]),
            -float(row["suggestions"][0]["bestSimilarityScore"]),
            str(row["reviewTargetId"]),
        )
    )
    suggestion_count = sum(len(row["suggestions"]) for row in proposal_targets)
    unique_fdc_targets = sum(
        1
        for row in proposal_targets
        if len({int(item["suggestedFdcId"]) for item in row["suggestions"]}) == 1
    )
    multi_fdc_targets = len(proposal_targets) - unique_fdc_targets

    manifest_sha = _text(candidates.get("referenceManifestSha256"))
    payload = {
        "schemaVersion": 1,
        "kind": PROPOSAL_KIND,
        "catalogVersion": _text(candidates.get("catalogVersion")),
        "referenceManifestSha256": manifest_sha,
        "sourceEvidenceKind": CANDIDATE_KIND,
        "similarityThreshold": SIMILARITY_THRESHOLD,
        "maxSuggestionsPerTarget": MAX_SUGGESTIONS_PER_TARGET,
        "policy": {
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
        "reviewCorpusCount": len(reviews),
        "heldHistoricalReviewsExcluded": held_history_excluded,
        "nonSemanticHistoricalReviewsExcluded": non_semantic_history_excluded,
        "proposalTargetCount": len(proposal_targets),
        "suggestionCount": suggestion_count,
        "proposalTargets": proposal_targets,
    }
    summary = {
        "catalogVersion": payload["catalogVersion"],
        "referenceManifestSha256": manifest_sha,
        "reviewCorpusCount": len(reviews),
        "heldHistoricalReviewsExcluded": held_history_excluded,
        "nonSemanticHistoricalReviewsExcluded": non_semantic_history_excluded,
        "historicalSemanticFdcIdCount": len(history_by_fdc),
        "candidateEvidenceTargetCount": len(candidates.get("items") or []),
        "alreadyReviewedTargetSkipped": already_reviewed_skipped,
        "providerTargetSkipped": provider_target_skipped,
        "candidateRowsWithHistoricalSemanticReview": candidate_rows_with_history,
        "exactCanonicalHistoricalMatchesExcluded": exact_canonical_history_excluded,
        "proposalTargetCount": len(proposal_targets),
        "proposalUsageCount": sum(
            int(row["usageCountAtReview"]) for row in proposal_targets
        ),
        "suggestionCount": suggestion_count,
        "uniqueSuggestedFdcTargetCount": unique_fdc_targets,
        "multipleSuggestedFdcTargetCount": multi_fdc_targets,
        "selectionCount": 0,
        "networkRequestsPerformed": False,
        "secretsPersisted": False,
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output")
    args = parser.parse_args()

    candidate_path = Path(args.candidates).expanduser()
    review_root = Path(args.review_root).expanduser()
    output = Path(args.output).expanduser()
    summary_output = (
        Path(args.summary_output).expanduser()
        if args.summary_output
        else None
    )

    candidates = _load(candidate_path)
    reviews = resolver.load_reviews(review_root)
    payload, summary = propose(candidates, reviews)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
