#!/usr/bin/env python3
"""Audit unresolved v60 source-local ingredient semantics without approving merges.

This report is deliberately non-mutating. It separates still-ambiguous rows from
reviewed-but-medium-confidence rows and surfaces only deterministic candidate
relationships to already high-confidence concepts. Candidate generation is not
identity proof and never changes provider or source-local identity.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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

import compile_release_catalog_semantics_v60 as semantics  # noqa: E402


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _loose(value: Any) -> str:
    """Comparison-only form; never an automatic merge rule."""
    text = unicodedata.normalize("NFKD", _text(value).casefold())
    out: list[str] = []
    pending_space = False
    for char in text:
        if unicodedata.category(char).startswith("M"):
            continue
        if char.isalnum():
            if pending_space and out:
                out.append(" ")
            out.append(char)
            pending_space = False
        else:
            pending_space = True
    return "".join(out).strip()


def _features(value: Any) -> tuple[str, frozenset[str]]:
    loose = _loose(value)
    return loose, frozenset(token for token in loose.split() if token)


def _score_features(
    source_loose: str,
    source_tokens: frozenset[str],
    target_loose: str,
    target_tokens: frozenset[str],
) -> tuple[int, float, int]:
    exact_loose = int(source_loose == target_loose and bool(source_loose))
    union = source_tokens | target_tokens
    jaccard = len(source_tokens & target_tokens) / len(union) if union else 0.0
    length_delta = abs(len(source_loose) - len(target_loose))
    return exact_loose, jaccard, -length_delta


def audit(review_root: Path) -> dict[str, Any]:
    paths = semantics._review_paths(review_root)
    payloads = [(path.name, semantics._load_payload(path)) for path in paths]
    rows = list(semantics.iter_review_rows(payloads))
    compiled = semantics.compile_from_paths(paths)
    concepts = {
        row["conceptId"]: row
        for row in compiled.get("concepts") or []
        if isinstance(row, dict) and _text(row.get("conceptId"))
    }
    mapping = compiled.get("sourceIdentityToConcept") or {}

    high_targets_by_class: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if (
            row["confidence"] != "high"
            or row["classification"] not in semantics._MERGEABLE_CLASSIFICATIONS
        ):
            continue
        concept_id = semantics._semantic_concept_id(
            row["classification"], row["english"]
        )
        high_targets_by_class[row["classification"]].setdefault(
            concept_id,
            {
                "conceptId": concept_id,
                "canonicalEnglish": row["english"],
                "classification": row["classification"],
            },
        )

    target_features: dict[str, tuple[str, frozenset[str]]] = {}
    exact_index: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    token_index: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for classification, targets in high_targets_by_class.items():
        for concept_id, target in targets.items():
            loose, tokens = _features(target["canonicalEnglish"])
            target_features[concept_id] = (loose, tokens)
            if loose:
                exact_index[classification][loose].add(concept_id)
            for token in tokens:
                token_index[classification][token].add(concept_id)

    unresolved: list[dict[str, Any]] = []
    for row in rows:
        source_id = semantics.source_local_ingredient_id(
            row["language"], row["source"]
        )
        concept_id = _text(mapping.get(source_id))
        concept = concepts.get(concept_id) or {}
        if concept.get("needsSemanticConfirmation") is not True:
            continue

        candidates: list[dict[str, Any]] = []
        if row["classification"] in semantics._MERGEABLE_CLASSIFICATIONS:
            source_loose, source_tokens = _features(row["english"])
            candidate_ids = set(
                exact_index[row["classification"]].get(source_loose, set())
            )
            for token in source_tokens:
                candidate_ids.update(
                    token_index[row["classification"]].get(token, set())
                )

            scored: list[tuple[tuple[int, float, int], str]] = []
            for target_id in candidate_ids:
                target_loose, target_tokens = target_features[target_id]
                score = _score_features(
                    source_loose,
                    source_tokens,
                    target_loose,
                    target_tokens,
                )
                if score[0] or score[1] >= 0.5:
                    scored.append((score, target_id))
            scored.sort(key=lambda pair: (pair[0], pair[1]), reverse=True)
            for score, target_id in scored[:8]:
                target = high_targets_by_class[row["classification"]][target_id]
                candidates.append(
                    {
                        **target,
                        "exactLooseText": bool(score[0]),
                        "tokenJaccard": round(score[1], 4),
                    }
                )

        unresolved.append(
            {
                "sourceIngredientId": source_id,
                "conceptId": concept_id,
                "language": row["language"],
                "source": row["source"],
                "english": row["english"],
                "classification": row["classification"],
                "confidence": row["confidence"],
                "reviewFile": row["reviewFile"],
                "candidateTargets": candidates,
            }
        )

    unresolved.sort(
        key=lambda row: (
            row["classification"],
            row["language"],
            _loose(row["english"]),
            row["sourceIngredientId"],
        )
    )
    classification_counts = Counter(row["classification"] for row in unresolved)
    confidence_counts = Counter(row["confidence"] for row in unresolved)
    candidate_counts = Counter(
        "exact-loose"
        if any(c["exactLooseText"] for c in row["candidateTargets"])
        else "similar"
        if row["candidateTargets"]
        else "none"
        for row in unresolved
    )

    return {
        "schemaVersion": 1,
        "kind": "cook4me-remaining-semantic-ingredient-audit-v60",
        "policy": {
            "candidateSearchIsIdentityProof": False,
            "automaticApproval": False,
            "providerIdentityAssigned": False,
            "sourceLocalIdentityPreserved": True,
        },
        "summary": {
            "remaining": len(unresolved),
            "classificationCounts": dict(sorted(classification_counts.items())),
            "confidenceCounts": dict(sorted(confidence_counts.items())),
            "candidateLaneCounts": dict(sorted(candidate_counts.items())),
        },
        "items": unresolved,
    }


def exact_loose_lane(result: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for row in result.get("items") or []:
        if not isinstance(row, dict):
            continue
        exact_targets = [
            candidate
            for candidate in row.get("candidateTargets") or []
            if isinstance(candidate, dict) and candidate.get("exactLooseText") is True
        ]
        if not exact_targets:
            continue
        items.append({**row, "candidateTargets": exact_targets})
    return {
        "schemaVersion": 1,
        "kind": "cook4me-remaining-semantic-exact-loose-candidates-v60",
        "policy": {
            "candidateSearchIsIdentityProof": False,
            "automaticApproval": False,
            "manualSemanticReviewRequired": True,
            "providerIdentityAssigned": False,
        },
        "summary": {"candidateCount": len(items)},
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=TOOLS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--exact-output", type=Path)
    args = parser.parse_args()
    result = audit(args.review_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.exact_output:
        exact = exact_loose_lane(result)
        args.exact_output.parent.mkdir(parents=True, exist_ok=True)
        args.exact_output.write_text(
            json.dumps(exact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
