#!/usr/bin/env python3
"""Merge standalone food identities only when quantity-only cleanup is exact.

Batch 7 deliberately does less than the earlier fuzzy candidate audits.  A row is
eligible only when removing recipe quantity/review metadata yields the exact
reviewed English label of one unique raw high-confidence food concept.  No food
state, preparation adjective, alternative, flavour, species, cut, or form token is
removed.  Existing standalone-equivalence roots and the four distinctions restored
by the batch-6 safety repair are hard exclusions.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPILER = TOOLS / "compile_release_catalog_semantics_v60.py"
CONFIRMATIONS = TOOLS / "release_catalog_semantic_confirmations.v1.json"
STANDALONE = TOOLS / "release_catalog_semantic_standalone_dispositions.v1.json"
EQUIVALENCES = TOOLS / "release_catalog_semantic_standalone_equivalences.v1.json"
ALIASES = TOOLS / "release_catalog_semantic_high_confidence_syntax_aliases.v1.json"

spec = importlib.util.spec_from_file_location("cook4me_batch7_semantics", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

# These were explicitly restored by the post-batch-6 safety audit because the
# proposed target lost a meaningful preparation/form distinction.  Batch 7 must
# never rediscover them via a broader rule.
SAFETY_RESTORED_IDS = {
    "local:uk:03b0818b595c5d09761c",  # finely chopped bacon != chopped bacon
    "local:uk:97553c4a23b39c4f285d",  # fresh parsley qualifier was lost
    "local:uk:eef3cdfcd9a6230db7e6",  # rosemary sprigs != generic rosemary
    "local:uk:953617d433fc7f71ea28",  # scraped/peeled vanilla pod != scraped only
}


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


_QUANTITY_FRAGMENT = re.compile(r"\s*\(quantity fragment:\s*[^()]+\)\s*$", re.I)
_QUANTITY_COUNT_OMITTED = re.compile(r"\s*\(quantity count omitted\)\s*$", re.I)
_QUANTITY_INCOMPLETE = re.compile(r"\s*\(quantity incomplete\)\s*$", re.I)
_QUALIFIED_COUNT_OMITTED = re.compile(
    r"\s*\(([^()]*)\s*;\s*quantity count omitted\)\s*$", re.I
)
_QUALIFIED_QUANTITY_INCOMPLETE = re.compile(
    r"\s*\(([^()]*)\s*;\s*quantity incomplete\)\s*$", re.I
)
_LEADING_UNIT_ONLY = re.compile(r"^(?:g|grams?|dl)\s+(?:of\s+)?", re.I)
_LEADING_MEASURE = re.compile(
    r"^(?:tablespoon\(s\)|tablespoons?|teaspoons?|cups?)\s+(?:of\s+)?", re.I
)
_LEADING_FRACTION = re.compile(
    r"^(?:half\s+(?:a|an)\s+|one[- ]third\s+|one[- ]half\s+)", re.I
)
_TRAILING_LITTLE = re.compile(r",\s*a\s+little\s*$", re.I)


def _replace_qualified(text: str, pattern: re.Pattern[str], reason: str) -> tuple[str, str] | None:
    match = pattern.search(text)
    if not match:
        return None
    qualifier = _text(match.group(1))
    new = _text(text[: match.start()] + (f" ({qualifier})" if qualifier else ""))
    return (new, reason) if new else None


def _single_step_variants(value: str) -> list[tuple[str, str]]:
    """Return only transformations that remove quantity/review accounting text."""
    text = _text(value)
    out: list[tuple[str, str]] = []

    for pattern, reason in (
        (_QUANTITY_FRAGMENT, "remove-quantity-fragment-annotation"),
        (_QUANTITY_COUNT_OMITTED, "remove-quantity-count-omitted-annotation"),
        (_QUANTITY_INCOMPLETE, "remove-quantity-incomplete-annotation"),
        (_LEADING_UNIT_ONLY, "remove-leading-unit-fragment"),
        (_LEADING_MEASURE, "remove-leading-measure-word"),
        (_LEADING_FRACTION, "remove-leading-recipe-fraction"),
        (_TRAILING_LITTLE, "remove-trailing-small-quantity"),
    ):
        new = _text(pattern.sub("", text, count=1))
        if new and mod._norm(new) != mod._norm(text):
            out.append((new, reason))

    for pattern, reason in (
        (_QUALIFIED_COUNT_OMITTED, "remove-count-annotation-preserve-qualifier"),
        (_QUALIFIED_QUANTITY_INCOMPLETE, "remove-incomplete-quantity-preserve-qualifier"),
    ):
        result = _replace_qualified(text, pattern, reason)
        if result and mod._norm(result[0]) != mod._norm(text):
            out.append(result)

    return out


def quantity_only_variants(value: str) -> list[dict[str, Any]]:
    """Bounded closure; every step is quantity-only and lexical state is retained."""
    original = _text(value)
    queue: list[tuple[str, tuple[str, ...]]] = [(original, ())]
    seen = {mod._norm(original)}
    out: list[dict[str, Any]] = []
    while queue:
        current, reasons = queue.pop(0)
        if len(reasons) >= 3:
            continue
        for new, reason in _single_step_variants(current):
            key = mod._norm(new)
            if not new or key in seen:
                continue
            seen.add(key)
            next_reasons = reasons + (reason,)
            out.append({"normalizedEnglish": new, "normalizationReasons": list(next_reasons)})
            queue.append((new, next_reasons))
    out.sort(key=lambda row: (len(row["normalizationReasons"]), mod._norm(row["normalizedEnglish"])))
    return out


def _eligible_decisions(max_items: int) -> list[dict[str, Any]]:
    confirmations = _load(CONFIRMATIONS)
    standalone = _load(STANDALONE)
    equivalences = _load(EQUIVALENCES)
    aliases = _load(ALIASES)

    if confirmations.get("policy", {}).get("manualSemanticEquivalenceAllowed") is not True:
        raise RuntimeError("manual semantic equivalence is not enabled")

    review_paths = mod._review_paths(TOOLS)
    payloads = [(path.name, mod._load_payload(path)) for path in review_paths]
    review_rows = list(mod.iter_review_rows(payloads))
    rows_by_source = mod._rows_by_source_id(review_rows)
    raw_high = mod._high_confidence_concepts(review_rows)
    compiled = mod.compile_from_paths(review_paths)
    compiled_concepts = {
        row["conceptId"]: row
        for row in compiled.get("concepts") or []
        if isinstance(row, dict) and row.get("conceptId")
    }

    alias_old_ids = {
        str(row.get("oldConceptId") or "")
        for row in aliases.get("items") or []
        if isinstance(row, dict)
    }
    conflict_targets = set(aliases.get("excludedConflictTargetConceptIds") or [])
    already_confirmed = {
        str(row.get("sourceIngredientId") or "")
        for row in confirmations.get("items") or []
        if isinstance(row, dict)
    }
    equivalence_protected = set()
    for row in equivalences.get("items") or []:
        if not isinstance(row, dict):
            continue
        equivalence_protected.add(str(row.get("sourceIngredientId") or ""))
        equivalence_protected.add(str(row.get("targetSourceIngredientId") or ""))
    equivalence_protected.discard("")

    exact_targets: dict[tuple[str, str], list[tuple[str, dict[str, Any]]]] = {}
    for concept_id, reviewed in raw_high.items():
        classification = str(reviewed.get("classification") or "").lower()
        if classification != "food":
            continue
        key = (classification, mod._norm(reviewed["english"]))
        exact_targets.setdefault(key, []).append((concept_id, reviewed))

    decisions: list[dict[str, Any]] = []
    for disposition in standalone.get("items") or []:
        if not isinstance(disposition, dict):
            continue
        source_id = str(disposition.get("sourceIngredientId") or "")
        if not source_id or source_id in already_confirmed or source_id in SAFETY_RESTORED_IDS:
            continue
        if source_id in equivalence_protected:
            continue
        if disposition.get("disposition") != "reviewed-source-local-standalone":
            continue
        if str(disposition.get("classification") or "").lower() != "food":
            continue

        reviewed = rows_by_source.get(source_id)
        if reviewed is None:
            raise RuntimeError(f"standalone source lacks review evidence: {source_id}")
        if reviewed["english"] != disposition.get("sourceReviewedEnglish"):
            raise RuntimeError(f"standalone reviewed-English drift: {source_id}")
        if reviewed["classification"] != "food" or reviewed["confidence"] == "high":
            continue

        matches: dict[str, dict[str, Any]] = {}
        for variant in quantity_only_variants(reviewed["english"]):
            key = ("food", mod._norm(variant["normalizedEnglish"]))
            target_rows = exact_targets.get(key, [])
            if len(target_rows) != 1:
                continue
            concept_id, target_review = target_rows[0]
            if concept_id in alias_old_ids or concept_id in conflict_targets:
                continue
            target = compiled_concepts.get(concept_id)
            if target is None or target.get("needsSemanticConfirmation") is True:
                continue
            if target.get("canonicalEnglish") != target_review["english"]:
                continue
            if any(target.get(name) is not True for name in ("nutritionEligible", "dietEligible", "allergenEligible")):
                continue
            if not any(
                isinstance(row, dict) and row.get("confidence") == "high"
                for row in target.get("sourceIdentities") or []
            ):
                continue
            matches[concept_id] = {
                "sourceIngredientId": source_id,
                "sourceReviewedEnglish": reviewed["english"],
                "classification": "food",
                "confirmedConceptId": concept_id,
                "targetCanonicalEnglish": target_review["english"],
                "normalizationReasons": variant["normalizationReasons"],
                "rationale": (
                    "Reviewed source becomes the unique high-confidence target after removing "
                    "recipe quantity/review accounting only; every ingredient, state, preparation, "
                    "alternative and flavour token is otherwise preserved exactly."
                ),
            }

        # More than one possible canonical concept means the evidence is not exact enough.
        if len(matches) == 1:
            decisions.append(next(iter(matches.values())))

    decisions.sort(key=lambda row: (mod._norm(row["sourceReviewedEnglish"]), row["sourceIngredientId"]))
    return decisions[:max_items]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-items", type=int, default=12)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    if args.max_items < 1 or args.max_items > 25:
        raise RuntimeError("--max-items must be between 1 and 25")

    decisions = _eligible_decisions(args.max_items)
    receipt = {
        "schemaVersion": 1,
        "kind": "cook4me-exact-quantity-semantic-batch7-v60",
        "policy": {
            "fuzzyMatchingAllowed": False,
            "stateOrPreparationTokenRemovalAllowed": False,
            "ambiguousSourceMergeAllowed": False,
            "standaloneEquivalenceRootMergeAllowed": False,
            "safetyRestoredBatch6MergeAllowed": False,
            "uniqueRawHighConfidenceExactTargetRequired": True,
        },
        "selectedCount": len(decisions),
        "items": decisions,
    }
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not decisions:
        print(json.dumps({"mergedFromStandalone": 0, "reason": "no exact quantity-only candidates"}))
        return 0

    confirmations = _load(CONFIRMATIONS)
    standalone = _load(STANDALONE)
    standalone_items = [row for row in standalone.get("items") or [] if isinstance(row, dict)]
    standalone_ids = {str(row.get("sourceIngredientId") or "") for row in standalone_items}
    existing_ids = {
        str(row.get("sourceIngredientId") or "")
        for row in confirmations.get("items") or []
        if isinstance(row, dict)
    }

    new_rows: list[dict[str, Any]] = []
    remove_ids: set[str] = set()
    for decision in decisions:
        source_id = decision["sourceIngredientId"]
        if source_id not in standalone_ids:
            raise RuntimeError(f"selected source is no longer standalone: {source_id}")
        if source_id in existing_ids:
            raise RuntimeError(f"selected source is already confirmed: {source_id}")
        remove_ids.add(source_id)
        new_rows.append({
            "sourceIngredientId": source_id,
            "confirmedConceptId": decision["confirmedConceptId"],
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": decision["sourceReviewedEnglish"],
            "targetCanonicalEnglish": decision["targetCanonicalEnglish"],
            "rationale": decision["rationale"],
        })

    kept = [
        row for row in standalone_items
        if str(row.get("sourceIngredientId") or "") not in remove_ids
    ]
    if len(standalone_items) - len(kept) != len(decisions):
        raise RuntimeError("batch-7 standalone removal count mismatch")

    confirmations["items"] = list(confirmations.get("items") or []) + new_rows
    ambiguous_count = sum(
        row.get("disposition") == "reviewed-ambiguous-source-fragment"
        for row in kept
    )
    standalone["items"] = kept
    standalone["summary"] = {
        "standaloneDispositionCount": len(kept),
        "reviewedAmbiguousCount": ambiguous_count,
        "reviewedSourceLocalStandaloneCount": len(kept) - ambiguous_count,
    }
    _write(CONFIRMATIONS, confirmations)
    _write(STANDALONE, standalone)
    print(json.dumps({
        "mergedFromStandalone": len(decisions),
        "standaloneRemaining": len(kept),
        "reviewedAmbiguousRemaining": ambiguous_count,
        "items": [
            {
                "sourceIngredientId": row["sourceIngredientId"],
                "sourceReviewedEnglish": row["sourceReviewedEnglish"],
                "targetCanonicalEnglish": row["targetCanonicalEnglish"],
                "normalizationReasons": row["normalizationReasons"],
            }
            for row in decisions
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
