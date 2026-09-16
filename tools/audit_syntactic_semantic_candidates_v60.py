#!/usr/bin/env python3
"""Find unresolved source-local rows whose difference is review syntax only.

This is a review report, never an approval mechanism. It applies a deliberately
small set of metadata-only normalizations to the reviewed English text and emits
a row only when that normalized text has an exact high-confidence semantic
concept in the same classification.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import compile_release_catalog_semantics_v60 as semantics  # noqa: E402

_SOURCE_TYPO_ONLY = re.compile(r"\s*\(source typo\)\s*$", re.IGNORECASE)
_QUALIFIED_SOURCE_TYPO = re.compile(
    r"\s*\(([^()]*)\s*;\s*source typo\)\s*$", re.IGNORECASE
)


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def preview_normalize(value: str) -> tuple[str, list[str]]:
    text = _text(value)
    reasons: list[str] = []

    current = semantics._safe_syntactic_english(text)
    if current != text:
        text = current
        reasons.append("existing-safe-syntactic-normalization")

    match = _QUALIFIED_SOURCE_TYPO.search(text)
    if match:
        qualifier = _text(match.group(1))
        text = (text[: match.start()] + (f" ({qualifier})" if qualifier else "")).strip()
        reasons.append("remove-source-typo-review-annotation-preserve-qualifier")
    else:
        cleaned = _SOURCE_TYPO_ONLY.sub("", text, count=1).strip()
        if cleaned != text:
            text = cleaned
            reasons.append("remove-source-typo-review-annotation")

    return text, reasons


def audit(review_root: Path) -> dict[str, Any]:
    paths = semantics._review_paths(review_root)
    payloads = [(path.name, semantics._load_payload(path)) for path in paths]
    rows = list(semantics.iter_review_rows(payloads))
    compiled = semantics.compile_from_paths(paths)
    mapping = compiled.get("sourceIdentityToConcept") or {}
    concepts = {
        row["conceptId"]: row
        for row in compiled.get("concepts") or []
        if isinstance(row, dict)
    }
    high = semantics._high_confidence_concepts(rows)

    items: list[dict[str, Any]] = []
    for row in rows:
        source_id = semantics.source_local_ingredient_id(row["language"], row["source"])
        current_concept = concepts.get(mapping.get(source_id, "")) or {}
        if current_concept.get("needsSemanticConfirmation") is not True:
            continue
        if row["classification"] not in semantics._MERGEABLE_CLASSIFICATIONS:
            continue

        normalized, reasons = preview_normalize(row["english"])
        if not reasons or semantics._norm(normalized) == semantics._norm(row["english"]):
            continue
        target_id = semantics._semantic_concept_id(row["classification"], normalized)
        target = high.get(target_id)
        if target is None:
            continue
        if target["classification"] != row["classification"]:
            continue
        if semantics._norm(target["english"]) != semantics._norm(normalized):
            continue

        items.append(
            {
                "sourceIngredientId": source_id,
                "language": row["language"],
                "source": row["source"],
                "reviewedEnglish": row["english"],
                "normalizedEnglish": normalized,
                "classification": row["classification"],
                "confidence": row["confidence"],
                "reviewFile": row["reviewFile"],
                "confirmedConceptIdCandidate": target_id,
                "highConfidenceEnglish": target["english"],
                "normalizationReasons": reasons,
            }
        )

    items.sort(
        key=lambda row: (
            row["classification"],
            row["normalizedEnglish"].casefold(),
            row["language"],
            row["sourceIngredientId"],
        )
    )
    return {
        "schemaVersion": 1,
        "kind": "cook4me-syntactic-semantic-confirmation-candidate-audit-v60",
        "policy": {
            "automaticApproval": False,
            "manualSemanticReviewRequired": True,
            "candidateSearchIsIdentityProof": False,
            "providerIdentityAssigned": False,
            "exactHighConfidenceTargetRequired": True,
        },
        "summary": {"candidateCount": len(items)},
        "items": items,
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
