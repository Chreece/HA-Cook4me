#!/usr/bin/env python3
"""Audit reviewed standalone v60 ingredient identities for stronger merge evidence.

The semantic closure deliberately preserved medium-confidence source-local rows as
standalone concepts when no safe merge was proven. This tool revisits those rows
without changing any identity. It compares only reviewed English meanings inside
the same classification and produces two evidence lanes:

* standalone -> already high-confidence semantic concept candidates;
* standalone <-> standalone candidate pairs that may represent duplicate meanings.

Similarity is discovery evidence only. This tool never approves a merge, assigns a
provider key, edits the standalone disposition ledger, or changes the runtime
catalog.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
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

import compile_release_catalog_semantics_v60 as semantics  # noqa: E402


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _loose(value: Any) -> str:
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


def _metrics(left: Any, right: Any) -> dict[str, Any]:
    left_loose, left_tokens = _features(left)
    right_loose, right_tokens = _features(right)
    intersection = left_tokens & right_tokens
    union = left_tokens | right_tokens
    minimum = min(len(left_tokens), len(right_tokens))
    jaccard = len(intersection) / len(union) if union else 0.0
    containment = len(intersection) / minimum if minimum else 0.0
    sequence = (
        SequenceMatcher(None, left_loose, right_loose).ratio()
        if left_loose and right_loose
        else 0.0
    )
    return {
        "exactLooseText": bool(left_loose and left_loose == right_loose),
        "tokenJaccard": round(jaccard, 4),
        "tokenContainment": round(containment, 4),
        "sequenceRatio": round(sequence, 4),
        "sharedTokenCount": len(intersection),
    }


def _candidate(metrics: dict[str, Any]) -> bool:
    return bool(
        metrics["exactLooseText"]
        or metrics["tokenJaccard"] >= 0.5
        or metrics["sequenceRatio"] >= 0.72
        or (
            metrics["sharedTokenCount"] >= 2
            and metrics["tokenContainment"] >= 0.75
        )
    )


def _high_priority(metrics: dict[str, Any]) -> bool:
    return bool(
        metrics["exactLooseText"]
        or metrics["tokenJaccard"] >= 0.8
        or metrics["sequenceRatio"] >= 0.9
        or (
            metrics["sharedTokenCount"] >= 2
            and metrics["tokenContainment"] >= 1.0
            and metrics["sequenceRatio"] >= 0.72
        )
    )


def _sort_key(candidate: dict[str, Any]) -> tuple[float, float, float, int, str]:
    metrics = candidate["metrics"]
    return (
        float(metrics["exactLooseText"]),
        float(metrics["tokenJaccard"]),
        float(metrics["sequenceRatio"]),
        int(metrics["sharedTokenCount"]),
        str(candidate.get("targetConceptId") or candidate.get("targetSourceIngredientId") or ""),
    )


def audit(review_root: Path) -> dict[str, Any]:
    review_paths = semantics._review_paths(review_root)
    payloads = [(path.name, semantics._load_payload(path)) for path in review_paths]
    review_rows = list(semantics.iter_review_rows(payloads))
    rows_by_source = semantics._rows_by_source_id(review_rows)

    # Candidate target IDs must come from the fully compiled semantic graph, not
    # from raw reviewed-English concepts. High-confidence syntax aliases can
    # collapse a raw concept ID into a canonical concept; surfacing the old ID
    # here would create stale review proposals.
    compiled = semantics.compile_from_paths(review_paths)
    compiled_concepts = {
        str(row.get("conceptId") or ""): row
        for row in compiled.get("concepts") or []
        if isinstance(row, dict) and row.get("conceptId")
    }
    alias_old_ids: set[str] = set()
    alias_path = review_root / semantics.HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name
    if alias_path.exists():
        alias_payload = semantics._load_high_confidence_syntax_alias_payload(alias_path)
        alias_old_ids = {
            str(row.get("oldConceptId") or "")
            for row in alias_payload.get("items") or []
            if isinstance(row, dict) and row.get("oldConceptId")
        }

    canonical_high_concepts: dict[str, dict[str, Any]] = {}
    for concept_id, concept in compiled_concepts.items():
        classification = _text(concept.get("classification")).lower()
        if classification not in semantics._MERGEABLE_CLASSIFICATIONS:
            continue
        if concept.get("needsSemanticConfirmation") is True:
            continue
        high_sources = [
            row
            for row in concept.get("sourceIdentities") or []
            if isinstance(row, dict) and _text(row.get("confidence")).lower() == "high"
        ]
        if not high_sources:
            continue
        if concept_id in alias_old_ids:
            raise RuntimeError(
                f"compiled semantic graph still emits collapsed alias concept: {concept_id}"
            )
        canonical_high_concepts[concept_id] = {
            "conceptId": concept_id,
            "canonicalEnglish": _text(concept.get("canonicalEnglish")),
            "classification": classification,
            "reviewFiles": sorted(
                {
                    _text(row.get("reviewFile"))
                    for row in high_sources
                    if _text(row.get("reviewFile"))
                }
            ),
        }

    standalone = semantics._load_standalone_payload(
        review_root / semantics.STANDALONE_DISPOSITION_FILE.name
    )

    ledger_items = [row for row in standalone.get("items") or [] if isinstance(row, dict)]
    ledger_summary = standalone.get("summary") or {}
    if int(ledger_summary.get("standaloneDispositionCount") or 0) != len(ledger_items):
        raise RuntimeError("standalone ledger summary count does not match items")

    standalone_rows: list[dict[str, Any]] = []
    ambiguous_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in ledger_items:
        source_id = _text(item.get("sourceIngredientId"))
        if not source_id or source_id in seen_ids:
            raise RuntimeError(f"invalid or duplicate standalone source identity: {source_id!r}")
        seen_ids.add(source_id)
        reviewed = rows_by_source.get(source_id)
        if reviewed is None:
            raise RuntimeError(f"standalone identity missing reviewed source row: {source_id}")
        if _text(item.get("sourceReviewedEnglish")) != reviewed["english"]:
            raise RuntimeError(f"standalone reviewed English drift: {source_id}")
        if _text(item.get("classification")).lower() != reviewed["classification"]:
            raise RuntimeError(f"standalone classification drift: {source_id}")
        row = {
            "sourceIngredientId": source_id,
            "language": reviewed["language"],
            "source": reviewed["source"],
            "english": reviewed["english"],
            "classification": reviewed["classification"],
            "confidence": reviewed["confidence"],
            "reviewFile": reviewed["reviewFile"],
            "disposition": _text(item.get("disposition")),
        }
        if reviewed["classification"] == "ambiguous":
            ambiguous_rows.append(row)
            continue
        if reviewed["classification"] not in semantics._MERGEABLE_CLASSIFICATIONS:
            raise RuntimeError(
                f"standalone non-ambiguous classification is not mergeable: {source_id}"
            )
        standalone_rows.append(row)

    high_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for concept_id, reviewed in canonical_high_concepts.items():
        high_by_class[reviewed["classification"]].append(reviewed)

    row_results: list[dict[str, Any]] = []
    high_priority_high_targets: list[dict[str, Any]] = []
    for row in standalone_rows:
        candidates: list[dict[str, Any]] = []
        for target in high_by_class[row["classification"]]:
            metrics = _metrics(row["english"], target["canonicalEnglish"])
            if not _candidate(metrics):
                continue
            candidate = {
                "targetType": "high-confidence-concept",
                "targetConceptId": target["conceptId"],
                "targetCanonicalEnglish": target["canonicalEnglish"],
                "targetReviewFiles": target["reviewFiles"],
                **(
                    {"targetReviewFile": target["reviewFiles"][0]}
                    if target["reviewFiles"]
                    else {}
                ),
                "metrics": metrics,
            }
            candidates.append(candidate)
        candidates.sort(key=_sort_key, reverse=True)
        result_row = {**row, "candidateTargets": candidates[:10]}
        row_results.append(result_row)
        for candidate in candidates:
            if not _high_priority(candidate["metrics"]):
                continue
            high_priority_high_targets.append(
                {
                    **row,
                    "candidateTarget": candidate,
                }
            )

    pair_candidates: list[dict[str, Any]] = []
    high_priority_pairs: list[dict[str, Any]] = []
    for left_index, left in enumerate(standalone_rows):
        for right in standalone_rows[left_index + 1 :]:
            if left["classification"] != right["classification"]:
                continue
            metrics = _metrics(left["english"], right["english"])
            if not _candidate(metrics):
                continue
            pair = {
                "classification": left["classification"],
                "left": {
                    "sourceIngredientId": left["sourceIngredientId"],
                    "language": left["language"],
                    "source": left["source"],
                    "english": left["english"],
                    "reviewFile": left["reviewFile"],
                },
                "right": {
                    "sourceIngredientId": right["sourceIngredientId"],
                    "language": right["language"],
                    "source": right["source"],
                    "english": right["english"],
                    "reviewFile": right["reviewFile"],
                },
                "metrics": metrics,
            }
            pair_candidates.append(pair)
            if _high_priority(metrics):
                high_priority_pairs.append(pair)

    pair_candidates.sort(
        key=lambda pair: (
            float(pair["metrics"]["exactLooseText"]),
            float(pair["metrics"]["tokenJaccard"]),
            float(pair["metrics"]["sequenceRatio"]),
            int(pair["metrics"]["sharedTokenCount"]),
            pair["left"]["sourceIngredientId"],
            pair["right"]["sourceIngredientId"],
        ),
        reverse=True,
    )
    high_priority_pairs.sort(
        key=lambda pair: (
            float(pair["metrics"]["exactLooseText"]),
            float(pair["metrics"]["tokenJaccard"]),
            float(pair["metrics"]["sequenceRatio"]),
            int(pair["metrics"]["sharedTokenCount"]),
            pair["left"]["sourceIngredientId"],
        ),
        reverse=True,
    )
    high_priority_high_targets.sort(
        key=lambda row: _sort_key(row["candidateTarget"]), reverse=True
    )
    row_results.sort(
        key=lambda row: (
            row["classification"], row["language"], _loose(row["english"]), row["sourceIngredientId"]
        )
    )

    class_counts = Counter(row["classification"] for row in standalone_rows)
    return {
        "schemaVersion": 1,
        "kind": "cook4me-standalone-semantic-merge-candidate-audit-v60",
        "policy": {
            "automaticApproval": False,
            "candidateSearchIsIdentityProof": False,
            "manualSemanticReviewRequired": True,
            "providerIdentityAssigned": False,
            "sourceLocalIdentityPreserved": True,
            "standaloneLedgerMutated": False,
            "ambiguousRowsExcludedFromMergeSuggestions": True,
            "highConfidenceTargetsCanonicalizedThroughCompiledSemanticGraph": True,
            "collapsedHighConfidenceAliasTargetsExcluded": True,
        },
        "summary": {
            "standaloneDispositionCount": len(ledger_items),
            "mergeableStandaloneCount": len(standalone_rows),
            "reviewedAmbiguousCount": len(ambiguous_rows),
            "canonicalHighConfidenceTargetConceptCount": len(canonical_high_concepts),
            "collapsedHighConfidenceAliasConceptCount": len(alias_old_ids),
            "mergeableClassificationCounts": dict(sorted(class_counts.items())),
            "rowsWithHighConfidenceCandidates": sum(
                bool(row["candidateTargets"]) for row in row_results
            ),
            "highPriorityHighConfidenceCandidateCount": len(high_priority_high_targets),
            "standalonePairCandidateCount": len(pair_candidates),
            "highPriorityStandalonePairCount": len(high_priority_pairs),
        },
        "items": row_results,
        "standalonePairCandidates": pair_candidates,
        "ambiguousExcluded": ambiguous_rows,
        "highPriority": {
            "highConfidenceTargets": high_priority_high_targets,
            "standalonePairs": high_priority_pairs,
        },
    }


def high_priority_view(result: dict[str, Any]) -> dict[str, Any]:
    high = result.get("highPriority") or {}
    high_targets = high.get("highConfidenceTargets") or []
    pairs = high.get("standalonePairs") or []
    return {
        "schemaVersion": 1,
        "kind": "cook4me-standalone-semantic-high-priority-review-v60",
        "policy": {
            "automaticApproval": False,
            "candidateSearchIsIdentityProof": False,
            "manualSemanticReviewRequired": True,
            "providerIdentityAssigned": False,
        },
        "summary": {
            "highConfidenceTargetCandidates": len(high_targets),
            "standalonePairCandidates": len(pairs),
        },
        "highConfidenceTargets": high_targets,
        "standalonePairs": pairs,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=TOOLS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--high-output", type=Path)
    args = parser.parse_args()

    result = audit(args.review_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.high_output:
        high = high_priority_view(result)
        args.high_output.parent.mkdir(parents=True, exist_ok=True)
        args.high_output.write_text(
            json.dumps(high, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
