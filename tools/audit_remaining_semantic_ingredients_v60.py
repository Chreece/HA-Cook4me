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


def _tokens(value: Any) -> set[str]:
    return {token for token in _loose(value).split() if token}


def _candidate_score(source: str, target: str) -> tuple[int, float, int]:
    source_loose = _loose(source)
    target_loose = _loose(target)
    exact_loose = int(source_loose == target_loose and bool(source_loose))
    left = _tokens(source)
    right = _tokens(target)
    union = left | right
    jaccard = len(left & right) / len(union) if union else 0.0
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

    high_rows = [
        row
        for row in rows
        if row["confidence"] == "high"
        and row["classification"] in semantics._MERGEABLE_CLASSIFICATIONS
    ]
    high_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in high_rows:
        high_by_class[row["classification"]].append(row)

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
            scored: list[tuple[tuple[int, float, int], dict[str, Any]]] = []
            for target in high_by_class[row["classification"]]:
                score = _candidate_score(row["english"], target["english"])
                if score[0] or score[1] >= 0.5:
                    scored.append((score, target))
            scored.sort(key=lambda pair: pair[0], reverse=True)
            seen_target: set[str] = set()
            for score, target in scored[:8]:
                target_id = semantics._semantic_concept_id(
                    target["classification"], target["english"]
                )
                if target_id in seen_target:
                    continue
                seen_target.add(target_id)
                candidates.append(
                    {
                        "conceptId": target_id,
                        "canonicalEnglish": target["english"],
                        "classification": target["classification"],
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=TOOLS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.review_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
