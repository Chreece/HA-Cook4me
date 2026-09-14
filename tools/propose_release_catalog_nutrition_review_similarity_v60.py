#!/usr/bin/env python3
"""Build fail-closed semantic-history nutrition review suggestions.

This is an offline reviewer aid only. It never approves, selects, or writes a
nutrition binding. A historical reviewed FDC ID may be surfaced only when that
same FDC ID is present in the current target's own pinned candidate evidence.

Unlike the exact-canonical reuse proposal, this helper is intentionally limited
to *near-duplicate* canonical names. It is useful for reviewer triage, but every
suggestion still requires explicit manual semantic review before a decision file
can bind the target.
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
SUGGESTION_KIND = "cook4me-nutrition-semantic-history-suggestions-v60"
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", _text(value)).casefold().split()
    )


def _tokens(value: Any) -> tuple[str, ...]:
    return tuple(_TOKEN_RE.findall(_norm(value)))


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
    bad = [key for key, expected in required.items() if policy.get(key) is not expected]
    if bad:
        raise RuntimeError("candidate evidence has unsafe policy: " + ", ".join(bad))


def _similarity(left: str, right: str) -> dict[str, Any] | None:
    """Return deterministic near-duplicate metrics or ``None`` when too weak.

    This deliberately does not attempt semantic inference. It only recognizes
    strong lexical near-duplicates so a human reviewer can inspect a historically
    used FDC ID that is independently present in the target's own evidence.
    """
    a = _norm(left)
    b = _norm(right)
    if not a or not b or a == b:
        return None

    a_tokens = frozenset(_tokens(a))
    b_tokens = frozenset(_tokens(b))
    if not a_tokens or not b_tokens:
        return None

    shared = a_tokens & b_tokens
    if not shared:
        return None

    smaller = min(len(a_tokens), len(b_tokens))
    union = len(a_tokens | b_tokens)
    containment = len(shared) / max(1, smaller)
    jaccard = len(shared) / max(1, union)
    sequence = SequenceMatcher(None, a, b).ratio()
    substring = (a in b or b in a) and min(len(a), len(b)) >= 4

    # Strong lexical near-duplicate only. The thresholds are intentionally
    # conservative because this is triage evidence, not identity proof.
    qualifies = (
        (substring and containment >= 0.75)
        or (containment >= 0.75 and jaccard >= 0.40)
        or (sequence >= 0.82 and containment >= 0.50)
    )
    if not qualifies:
        return None

    score = containment * 0.50 + jaccard * 0.25 + sequence * 0.25
    return {
        "score": round(score, 6),
        "tokenContainment": round(containment, 6),
        "tokenJaccard": round(jaccard, 6),
        "sequenceRatio": round(sequence, 6),
        "substringRelation": substring,
        "sharedTokens": sorted(shared),
    }


def suggest(
    candidates: dict[str, Any],
    reviews: dict[str, dict[str, Any]],
    *,
    max_suggestions_per_target: int = 3,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_candidates(candidates)
    limit = max(1, int(max_suggestions_per_target))

    reviewed_ids = set(reviews)
    history_by_fdc: dict[int, list[dict[str, Any]]] = defaultdict(list)
    held_history_excluded = 0
    for row in reviews.values():
        if resolver.reviewed_nutrition.holds.profile_hold(row) is not None:
            held_history_excluded += 1
            continue
        try:
            fdc_id = int(row.get("fdcId") or 0)
        except (TypeError, ValueError):
            continue
        if fdc_id <= 0 or not _text(row.get("canonicalEnglishName")):
            continue
        history_by_fdc[fdc_id].append(row)

    target_rows: list[dict[str, Any]] = []
    already_reviewed_skipped = 0
    own_candidate_history_matches = 0
    weak_similarity_excluded = 0

    for raw in candidates.get("items") or []:
        if not isinstance(raw, dict):
            continue
        target_id = _text(raw.get("reviewTargetId"))
        canonical = _text(raw.get("canonicalEnglishName"))
        if not target_id or not canonical:
            continue
        if target_id in reviewed_ids:
            already_reviewed_skipped += 1
            continue

        by_fdc: dict[int, dict[str, Any]] = {}
        for evidence in raw.get("candidates") or []:
            if not isinstance(evidence, dict):
                continue
            try:
                fdc_id = int(evidence.get("fdcId") or 0)
            except (TypeError, ValueError):
                continue
            if fdc_id <= 0:
                continue
            historical = history_by_fdc.get(fdc_id, [])
            if not historical:
                continue
            own_candidate_history_matches += 1

            matches: list[dict[str, Any]] = []
            for reviewed in historical:
                metrics = _similarity(canonical, _text(reviewed.get("canonicalEnglishName")))
                if metrics is None:
                    weak_similarity_excluded += 1
                    continue
                matches.append(
                    {
                        "historicalReviewTargetId": _text(reviewed.get("reviewTargetId")),
                        "historicalCanonicalEnglishName": _text(
                            reviewed.get("canonicalEnglishName")
                        ),
                        "historicalReviewKind": _text(reviewed.get("reviewTargetKind")),
                        **metrics,
                    }
                )

            if not matches:
                continue
            matches.sort(
                key=lambda row: (
                    -float(row["score"]),
                    str(row["historicalReviewTargetId"]),
                )
            )
            best = matches[0]
            by_fdc[fdc_id] = {
                "suggestedFdcId": fdc_id,
                "fdcDescription": _text(evidence.get("description")),
                "fdcDataType": _text(evidence.get("dataType")),
                "candidateEvidenceRank": int(evidence.get("localEvidenceRank") or 0),
                "candidateEvidenceScore": float(evidence.get("localEvidenceScore") or 0.0),
                "bestSimilarityScore": float(best["score"]),
                "historicalMatchCount": len(matches),
                "historicalMatches": matches,
                "selectionPerformed": False,
                "needsManualExactIdReview": True,
            }

        suggestions = sorted(
            by_fdc.values(),
            key=lambda row: (
                -float(row["bestSimilarityScore"]),
                int(row["candidateEvidenceRank"] or 10**9),
                int(row["suggestedFdcId"]),
            ),
        )[:limit]
        if not suggestions:
            continue

        target_rows.append(
            {
                "reviewTargetId": target_id,
                "reviewTargetKind": _text(raw.get("reviewTargetKind")),
                "canonicalEnglishName": canonical,
                "usageCountAtReview": int(raw.get("usageCountSum") or 0),
                "ambiguousHistoricalFdcSuggestions": len(suggestions) > 1,
                "suggestions": suggestions,
                "selectionPerformed": False,
                "needsManualExactIdReview": True,
            }
        )

    target_rows.sort(
        key=lambda row: (
            -int(row["usageCountAtReview"]),
            -float(row["suggestions"][0]["bestSimilarityScore"]),
            str(row["reviewTargetId"]),
        )
    )

    manifest_sha = _text(candidates.get("referenceManifestSha256"))
    suggestion_count = sum(len(row["suggestions"]) for row in target_rows)
    payload = {
        "schemaVersion": 1,
        "kind": SUGGESTION_KIND,
        "catalogVersion": _text(candidates.get("catalogVersion")),
        "referenceManifestSha256": manifest_sha,
        "sourceEvidenceKind": CANDIDATE_KIND,
        "policy": {
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
        "reviewCorpusCount": len(reviews),
        "heldHistoricalReviewsExcluded": held_history_excluded,
        "suggestionTargetCount": len(target_rows),
        "suggestionCount": suggestion_count,
        "targets": target_rows,
    }
    summary = {
        "catalogVersion": payload["catalogVersion"],
        "referenceManifestSha256": manifest_sha,
        "reviewCorpusCount": len(reviews),
        "heldHistoricalReviewsExcluded": held_history_excluded,
        "candidateEvidenceTargetCount": len(candidates.get("items") or []),
        "alreadyReviewedTargetSkipped": already_reviewed_skipped,
        "ownCandidateHistoricalMatchCount": own_candidate_history_matches,
        "weakSimilarityExcludedCount": weak_similarity_excluded,
        "suggestionTargetCount": len(target_rows),
        "suggestionCount": suggestion_count,
        "ambiguousTargetCount": sum(
            1 for row in target_rows if row["ambiguousHistoricalFdcSuggestions"]
        ),
        "suggestionUsageCount": sum(
            int(row["usageCountAtReview"]) for row in target_rows
        ),
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
    parser.add_argument("--max-suggestions-per-target", type=int, default=3)
    args = parser.parse_args()

    candidates = _load(Path(args.candidates).expanduser())
    reviews = resolver.load_reviews(Path(args.review_root).expanduser())
    payload, summary = suggest(
        candidates,
        reviews,
        max_suggestions_per_target=args.max_suggestions_per_target,
    )

    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.summary_output:
        summary_output = Path(args.summary_output).expanduser()
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
