#!/usr/bin/env python3
"""Apply one evidence-pinned preparation-wording semantic resolution.

The source and target both mean cauliflower that is washed and separated into
florets. "Divided into florets" versus "cut into florets" is preparation wording,
not a different ingredient, state, cut size, variety, or composition.
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

spec = importlib.util.spec_from_file_location("cook4me_semantic_batch10", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

DECISION: dict[str, str] = {
    "sourceIngredientId": "local:uk:fa883397da2ff4357aeb",
    "sourceReviewedEnglish": "Cauliflower, washed and divided into florets",
    "classification": "food",
    "confirmedConceptId": "concept:food:be16900cdca70fb2c1ad",
    "targetCanonicalEnglish": "Cauliflower, washed and cut into florets",
    "rationale": "Divided into florets and cut into florets describe the same reviewed cauliflower preparation state. Both preserve washed cauliflower separated into florets and introduce no different size, variety, cooking state, composition, or alternative ingredient.",
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
    if int((standalone.get("summary") or {}).get("standaloneDispositionCount") or -1) != 201:
        raise RuntimeError("batch 10 requires the reviewed 201-row standalone baseline")
    if int((standalone.get("summary") or {}).get("reviewedAmbiguousCount") or -1) != 28:
        raise RuntimeError("batch 10 requires the reviewed 28-row ambiguous baseline")
    if int((equivalences.get("summary") or {}).get("equivalenceCount") or -1) != 15:
        raise RuntimeError("batch 10 requires fifteen conservative source-local equivalences")

    source_id = DECISION["sourceIngredientId"]
    confirmation_items = [
        row for row in confirmations.get("items") or [] if isinstance(row, dict)
    ]
    if source_id in {
        str(row.get("sourceIngredientId") or "") for row in confirmation_items
    }:
        raise RuntimeError(f"batch 10 source is already confirmed: {source_id}")
    if source_id in {
        str(row.get("sourceIngredientId") or "")
        for row in equivalences.get("items") or []
        if isinstance(row, dict)
    }:
        raise RuntimeError(f"batch 10 source already has source-local equivalence: {source_id}")

    standalone_items = [
        row for row in standalone.get("items") or [] if isinstance(row, dict)
    ]
    standalone_by_id = {
        str(row.get("sourceIngredientId") or ""): row for row in standalone_items
    }
    disposition = standalone_by_id.get(source_id)
    if disposition is None or disposition.get("disposition") != "reviewed-source-local-standalone":
        raise RuntimeError(f"batch 10 source is not a mergeable standalone row: {source_id}")
    if disposition.get("sourceReviewedEnglish") != DECISION["sourceReviewedEnglish"]:
        raise RuntimeError("batch 10 standalone reviewed-English receipt drift")
    if disposition.get("classification") != DECISION["classification"]:
        raise RuntimeError("batch 10 standalone classification receipt drift")

    reviewed = rows_by_source.get(source_id)
    if reviewed is None:
        raise RuntimeError("batch 10 reviewed source evidence missing")
    if reviewed["english"] != DECISION["sourceReviewedEnglish"]:
        raise RuntimeError("batch 10 source reviewed-English drift")
    if reviewed["classification"] != DECISION["classification"]:
        raise RuntimeError("batch 10 source classification drift")
    if reviewed["confidence"] == "high":
        raise RuntimeError("batch 10 source unexpectedly became high confidence")

    target = high_concepts.get(DECISION["confirmedConceptId"])
    if target is None:
        raise RuntimeError("batch 10 high-confidence cauliflower target missing")
    if target["english"] != DECISION["targetCanonicalEnglish"]:
        raise RuntimeError("batch 10 target canonical-English drift")
    if target["classification"] != DECISION["classification"]:
        raise RuntimeError("batch 10 target classification drift")
    if len(DECISION["rationale"]) < 60:
        raise RuntimeError("batch 10 rationale is too short")

    kept = [
        row for row in standalone_items
        if str(row.get("sourceIngredientId") or "") != source_id
    ]
    if len(standalone_items) - len(kept) != 1:
        raise RuntimeError("batch 10 standalone removal count mismatch")
    ambiguous_count = sum(
        row.get("disposition") == "reviewed-ambiguous-source-fragment"
        for row in kept
    )
    if ambiguous_count != 28:
        raise RuntimeError("batch 10 may not change reviewed ambiguous count")
    standalone["items"] = kept
    standalone["summary"] = {
        "standaloneDispositionCount": len(kept),
        "reviewedAmbiguousCount": ambiguous_count,
        "reviewedSourceLocalStandaloneCount": len(kept) - ambiguous_count,
    }

    confirmations["items"] = confirmation_items + [
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
