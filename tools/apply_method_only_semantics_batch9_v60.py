#!/usr/bin/env python3
"""Apply one evidence-pinned method-only semantic resolution.

The Japanese source says chocolate melted in a microwave. The microwave is the
method used to reach the already-reviewed state "Melted chocolate"; no ingredient,
composition, variety, or final state is changed by this merge.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPILER = TOOLS / "compile_release_catalog_semantics_v60.py"
CONFIRMATIONS = TOOLS / "release_catalog_semantic_confirmations.v1.json"
STANDALONE = TOOLS / "release_catalog_semantic_standalone_dispositions.v1.json"
EQUIVALENCES = TOOLS / "release_catalog_semantic_standalone_equivalences.v1.json"

spec = importlib.util.spec_from_file_location("cook4me_semantic_batch9", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

DECISION: dict[str, str] = {
    "sourceIngredientId": "local:ja:81b62f38c8f2a26febb0",
    "sourceReviewedEnglish": "Chocolate, melted in the microwave",
    "classification": "food",
    "confirmedConceptId": "concept:food:8829b9cf6f691ca1a9cc",
    "targetCanonicalEnglish": "Melted chocolate",
    "rationale": "Microwave identifies only the method used to melt the chocolate. Both reviewed meanings preserve chocolate as the ingredient and melted as the final state, with no change in composition, variety, or preparation state.",
}


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


def main() -> int:
    paths = mod._review_paths(TOOLS)
    review_rows = list(
        mod.iter_review_rows([(path.name, mod._load_payload(path)) for path in paths])
    )
    rows_by_source = mod._rows_by_source_id(review_rows)
    high_concepts = mod._high_confidence_concepts(review_rows)

    confirmations = _load(CONFIRMATIONS)
    standalone = _load(STANDALONE)
    equivalences = _load(EQUIVALENCES)

    if confirmations.get("policy", {}).get("manualSemanticEquivalenceAllowed") is not True:
        raise RuntimeError("manual semantic equivalence is not enabled")
    if int((standalone.get("summary") or {}).get("standaloneDispositionCount") or -1) != 202:
        raise RuntimeError("batch 9 requires the promoted 202-row standalone baseline")
    if int((standalone.get("summary") or {}).get("reviewedAmbiguousCount") or -1) != 28:
        raise RuntimeError("batch 9 requires the promoted 28-row ambiguous baseline")
    if int((equivalences.get("summary") or {}).get("equivalenceCount") or -1) != 15:
        raise RuntimeError("batch 9 requires the promoted fifteen source-local equivalences")

    source_id = DECISION["sourceIngredientId"]
    existing_confirmations = [
        row for row in confirmations.get("items") or [] if isinstance(row, dict)
    ]
    if source_id in {
        str(row.get("sourceIngredientId") or "") for row in existing_confirmations
    }:
        raise RuntimeError(f"batch 9 source is already confirmed: {source_id}")
    if source_id in {
        str(row.get("sourceIngredientId") or "")
        for row in equivalences.get("items") or []
        if isinstance(row, dict)
    }:
        raise RuntimeError(f"batch 9 source already has source-local equivalence: {source_id}")

    standalone_items = [
        row for row in standalone.get("items") or [] if isinstance(row, dict)
    ]
    standalone_by_id = {
        str(row.get("sourceIngredientId") or ""): row for row in standalone_items
    }
    disposition = standalone_by_id.get(source_id)
    if disposition is None or disposition.get("disposition") != "reviewed-source-local-standalone":
        raise RuntimeError(f"batch 9 source is not a mergeable standalone row: {source_id}")
    if disposition.get("sourceReviewedEnglish") != DECISION["sourceReviewedEnglish"]:
        raise RuntimeError("batch 9 standalone reviewed-English receipt drift")
    if disposition.get("classification") != DECISION["classification"]:
        raise RuntimeError("batch 9 standalone classification receipt drift")

    source_review = rows_by_source.get(source_id)
    if source_review is None:
        raise RuntimeError("batch 9 reviewed source evidence missing")
    if source_review["english"] != DECISION["sourceReviewedEnglish"]:
        raise RuntimeError("batch 9 source reviewed-English drift")
    if source_review["classification"] != DECISION["classification"]:
        raise RuntimeError("batch 9 source classification drift")
    if source_review["confidence"] == "high":
        raise RuntimeError("batch 9 source unexpectedly became high confidence")

    target = high_concepts.get(DECISION["confirmedConceptId"])
    if target is None:
        raise RuntimeError("batch 9 high-confidence melted-chocolate target missing")
    if target["english"] != DECISION["targetCanonicalEnglish"]:
        raise RuntimeError("batch 9 target canonical-English drift")
    if target["classification"] != DECISION["classification"]:
        raise RuntimeError("batch 9 target classification drift")
    if len(DECISION["rationale"]) < 40:
        raise RuntimeError("batch 9 rationale is too short")

    kept = [
        row for row in standalone_items
        if str(row.get("sourceIngredientId") or "") != source_id
    ]
    if len(standalone_items) - len(kept) != 1:
        raise RuntimeError("batch 9 standalone removal count mismatch")
    ambiguous_count = sum(
        row.get("disposition") == "reviewed-ambiguous-source-fragment"
        for row in kept
    )
    if ambiguous_count != 28:
        raise RuntimeError("batch 9 may not change reviewed ambiguous count")
    standalone["items"] = kept
    standalone["summary"] = {
        "standaloneDispositionCount": len(kept),
        "reviewedAmbiguousCount": ambiguous_count,
        "reviewedSourceLocalStandaloneCount": len(kept) - ambiguous_count,
    }

    confirmations["items"] = existing_confirmations + [
        {
            "sourceIngredientId": source_id,
            "confirmedConceptId": DECISION["confirmedConceptId"],
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": DECISION["sourceReviewedEnglish"],
            "targetCanonicalEnglish": DECISION["targetCanonicalEnglish"],
            "rationale": DECISION["rationale"],
        }
    ]

    _write(CONFIRMATIONS, confirmations)
    _write(STANDALONE, standalone)

    print(json.dumps({
        "resolved": 1,
        "sourceIngredientId": source_id,
        "confirmedConceptId": DECISION["confirmedConceptId"],
        "standaloneRemaining": len(kept),
        "reviewedAmbiguousRemaining": ambiguous_count,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
