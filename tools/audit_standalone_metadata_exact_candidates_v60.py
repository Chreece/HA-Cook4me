#!/usr/bin/env python3
"""Find reviewed standalone ingredient identities with exact metadata-only targets.

This is discovery evidence only.  It never edits a ledger or approves a merge.
For each non-ambiguous standalone row it generates a deliberately small set of
preview normalizations that remove only explicit review/quantity/unit/use metadata.
A candidate is emitted only when the resulting English text is an *exact* reviewed
English identity in the same classification, either an existing high-confidence
concept or another conservative standalone root.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
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


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


_COUNT_OMITTED = re.compile(r"\s*\(quantity count omitted\)\s*$", re.I)
_QUANTITY_INCOMPLETE = re.compile(r"\s*\(quantity incomplete\)\s*$", re.I)
_QUALIFIED_COUNT_OMITTED = re.compile(
    r"\s*\(([^()]*)\s*;\s*quantity count omitted\)\s*$", re.I
)
_QUALIFIED_QUANTITY_INCOMPLETE = re.compile(
    r"\s*\(([^()]*)\s*;\s*quantity incomplete\)\s*$", re.I
)
_ABBREVIATED_SOURCE = re.compile(r"\s*\(abbreviated source\)\s*$", re.I)
_RECIPE_USE_PAREN = re.compile(
    r"\s*\((?:to\s+[^()]++|for\s+[^()]++)\)\s*$".replace("++", "+"), re.I
)

# Unit words here are accepted only at the beginning of a reviewed ingredient
# phrase and only as candidate discovery.  No result is auto-approved.
_MEASUREMENT_PREFIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^tablespoon\(s\)\s+of\s+", re.I), "remove-tablespoons-unit-prefix"),
    (re.compile(r"^tablespoons?\s+of\s+", re.I), "remove-tablespoon-unit-prefix"),
    (re.compile(r"^teaspoons?\s+of\s+", re.I), "remove-teaspoon-unit-prefix"),
    (re.compile(r"^cups?\s+of\s+", re.I), "remove-cup-unit-prefix"),
    (re.compile(r"^(?:one[- ]third|one[- ]half|half)\s+teaspoons?\s+", re.I), "remove-fractional-teaspoon-prefix"),
    (re.compile(r"^tbsp\s+", re.I), "remove-tbsp-unit-prefix"),
    (re.compile(r"^tsp\s+", re.I), "remove-tsp-unit-prefix"),
    (re.compile(r"^g\s+", re.I), "remove-gram-unit-prefix"),
    (re.compile(r"^dl\s+(?:of\s+)?", re.I), "remove-decilitre-unit-prefix"),
)


def _replace_qualified_annotation(
    text: str, pattern: re.Pattern[str], reason: str
) -> tuple[str, str] | None:
    match = pattern.search(text)
    if not match:
        return None
    qualifier = _text(match.group(1))
    new = text[: match.start()] + (f" ({qualifier})" if qualifier else "")
    return _text(new), reason


def _single_step_variants(value: str) -> list[tuple[str, str]]:
    text = _text(value)
    variants: list[tuple[str, str]] = []

    safe = semantics._safe_syntactic_english(text)
    if semantics._norm(safe) != semantics._norm(text):
        variants.append((safe, "existing-safe-syntactic-normalization"))

    for pattern, reason in (
        (_COUNT_OMITTED, "remove-quantity-count-omitted-annotation"),
        (_QUANTITY_INCOMPLETE, "remove-quantity-incomplete-annotation"),
        (_ABBREVIATED_SOURCE, "remove-abbreviated-source-review-annotation"),
        (_RECIPE_USE_PAREN, "remove-parenthetical-recipe-use-note"),
    ):
        new = _text(pattern.sub("", text, count=1))
        if semantics._norm(new) != semantics._norm(text):
            variants.append((new, reason))

    for pattern, reason in (
        (_QUALIFIED_COUNT_OMITTED, "remove-quantity-count-omitted-annotation-preserve-qualifier"),
        (_QUALIFIED_QUANTITY_INCOMPLETE, "remove-quantity-incomplete-annotation-preserve-qualifier"),
    ):
        result = _replace_qualified_annotation(text, pattern, reason)
        if result and semantics._norm(result[0]) != semantics._norm(text):
            variants.append(result)

    for pattern, reason in _MEASUREMENT_PREFIXES:
        new = _text(pattern.sub("", text, count=1))
        if semantics._norm(new) != semantics._norm(text):
            variants.append((new, reason))

    return variants


def preview_variants(value: str) -> list[dict[str, Any]]:
    """Return a bounded closure of metadata-only preview transformations."""
    original = _text(value)
    queue: list[tuple[str, tuple[str, ...]]] = [(original, ())]
    seen = {semantics._norm(original)}
    out: list[dict[str, Any]] = []

    while queue:
        current, reasons = queue.pop(0)
        if len(reasons) >= 4:
            continue
        for new, reason in _single_step_variants(current):
            key = semantics._norm(new)
            if not new or key in seen:
                continue
            seen.add(key)
            next_reasons = reasons + (reason,)
            out.append({"normalizedEnglish": new, "normalizationReasons": list(next_reasons)})
            queue.append((new, next_reasons))

    out.sort(
        key=lambda row: (
            len(row["normalizationReasons"]),
            semantics._norm(row["normalizedEnglish"]),
        )
    )
    return out


def audit(review_root: Path) -> dict[str, Any]:
    paths = semantics._review_paths(review_root)
    payloads = [(path.name, semantics._load_payload(path)) for path in paths]
    review_rows = list(semantics.iter_review_rows(payloads))
    rows_by_source = semantics._rows_by_source_id(review_rows)
    high = semantics._high_confidence_concepts(review_rows)

    standalone_payload = semantics._load_standalone_payload(
        review_root / semantics.STANDALONE_DISPOSITION_FILE.name
    )
    standalone_items = [
        row for row in standalone_payload.get("items") or [] if isinstance(row, dict)
    ]
    standalone_by_id = {
        _text(row.get("sourceIngredientId")): row for row in standalone_items
    }

    standalone_exact: dict[tuple[str, str], list[str]] = defaultdict(list)
    for source_id, disposition in standalone_by_id.items():
        reviewed = rows_by_source.get(source_id)
        if reviewed is None or reviewed["classification"] not in semantics._MERGEABLE_CLASSIFICATIONS:
            continue
        if disposition.get("disposition") != "reviewed-source-local-standalone":
            continue
        standalone_exact[(reviewed["classification"], semantics._norm(reviewed["english"]))].append(source_id)

    high_exact: dict[tuple[str, str], list[str]] = defaultdict(list)
    for concept_id, reviewed in high.items():
        high_exact[(reviewed["classification"], semantics._norm(reviewed["english"]))].append(concept_id)

    items: list[dict[str, Any]] = []
    for source_id, disposition in standalone_by_id.items():
        reviewed = rows_by_source.get(source_id)
        if reviewed is None:
            raise RuntimeError(f"standalone source lacks reviewed evidence: {source_id}")
        if disposition.get("sourceReviewedEnglish") != reviewed["english"]:
            raise RuntimeError(f"standalone reviewed English drift: {source_id}")
        if reviewed["classification"] not in semantics._MERGEABLE_CLASSIFICATIONS:
            continue
        if disposition.get("disposition") != "reviewed-source-local-standalone":
            continue

        matches: list[dict[str, Any]] = []
        for variant in preview_variants(reviewed["english"]):
            key = (reviewed["classification"], semantics._norm(variant["normalizedEnglish"]))
            for concept_id in sorted(high_exact.get(key, [])):
                target = high[concept_id]
                matches.append(
                    {
                        "targetType": "high-confidence-concept",
                        "targetConceptId": concept_id,
                        "targetCanonicalEnglish": target["english"],
                        **variant,
                    }
                )
            for target_id in sorted(standalone_exact.get(key, [])):
                if target_id == source_id:
                    continue
                target = rows_by_source[target_id]
                matches.append(
                    {
                        "targetType": "standalone-source-local",
                        "targetSourceIngredientId": target_id,
                        "targetReviewedEnglish": target["english"],
                        **variant,
                    }
                )

        dedupe: dict[tuple[str, str, str], dict[str, Any]] = {}
        for match in matches:
            target_key = _text(match.get("targetConceptId") or match.get("targetSourceIngredientId"))
            key = (
                match["targetType"],
                target_key,
                semantics._norm(match["normalizedEnglish"]),
            )
            previous = dedupe.get(key)
            if previous is None or len(match["normalizationReasons"]) < len(previous["normalizationReasons"]):
                dedupe[key] = match

        if dedupe:
            candidates = sorted(
                dedupe.values(),
                key=lambda row: (
                    len(row["normalizationReasons"]),
                    row["targetType"],
                    _text(row.get("targetCanonicalEnglish") or row.get("targetReviewedEnglish")),
                    _text(row.get("targetConceptId") or row.get("targetSourceIngredientId")),
                ),
            )
            items.append(
                {
                    "sourceIngredientId": source_id,
                    "language": reviewed["language"],
                    "source": reviewed["source"],
                    "reviewedEnglish": reviewed["english"],
                    "classification": reviewed["classification"],
                    "confidence": reviewed["confidence"],
                    "reviewFile": reviewed["reviewFile"],
                    "candidates": candidates,
                }
            )

    items.sort(
        key=lambda row: (
            row["classification"],
            semantics._norm(row["reviewedEnglish"]),
            row["language"],
            row["sourceIngredientId"],
        )
    )
    high_count = sum(
        any(candidate["targetType"] == "high-confidence-concept" for candidate in row["candidates"])
        for row in items
    )
    standalone_count = sum(
        any(candidate["targetType"] == "standalone-source-local" for candidate in row["candidates"])
        for row in items
    )
    return {
        "schemaVersion": 1,
        "kind": "cook4me-standalone-metadata-exact-candidate-audit-v60",
        "policy": {
            "automaticApproval": False,
            "candidateSearchIsIdentityProof": False,
            "manualSemanticReviewRequired": True,
            "exactReviewedTargetAfterMetadataPreviewRequired": True,
            "providerIdentityAssigned": False,
            "standaloneLedgerMutated": False,
            "safetyEligibilityGranted": False,
        },
        "summary": {
            "standaloneDispositionCount": len(standalone_items),
            "candidateSourceCount": len(items),
            "candidateSourcesWithHighConfidenceTarget": high_count,
            "candidateSourcesWithStandaloneTarget": standalone_count,
        },
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
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
