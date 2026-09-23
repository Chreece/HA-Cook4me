#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PARENT = "48491e67f126366d773d6ab5d39695e5dd286b3a"
BATCH6 = "acead46870d2ad0f2e38fbf78ad42abfb471f801"
CONFIRM = "tools/release_catalog_semantic_confirmations.v1.json"
STANDALONE = "tools/release_catalog_semantic_standalone_dispositions.v1.json"
COMPILER = TOOLS / "compile_release_catalog_semantics_v60.py"

spec = importlib.util.spec_from_file_location("cook4me_batch6_audit_compiler", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def show_json(commit: str, path: str) -> dict[str, Any]:
    raw = subprocess.check_output(["git", "show", f"{commit}:{path}"], text=True)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"{commit}:{path}: expected JSON object")
    return value


def items_by_id(payload: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in payload.get("items") or []:
        if not isinstance(row, dict):
            continue
        ident = str(row.get(key) or "")
        if ident:
            out[ident] = row
    return out


def main() -> int:
    parent_confirm = items_by_id(show_json(PARENT, CONFIRM), "sourceIngredientId")
    child_confirm = items_by_id(show_json(BATCH6, CONFIRM), "sourceIngredientId")
    parent_standalone = items_by_id(show_json(PARENT, STANDALONE), "sourceIngredientId")
    child_standalone = items_by_id(show_json(BATCH6, STANDALONE), "sourceIngredientId")

    added_ids = sorted(set(child_confirm) - set(parent_confirm))
    removed_ids = sorted(set(parent_standalone) - set(child_standalone))
    if added_ids != removed_ids:
        raise RuntimeError(
            f"batch6 confirmation/standalone delta mismatch: added={len(added_ids)} removed={len(removed_ids)}"
        )
    if len(added_ids) != 9:
        raise RuntimeError(f"expected 9 batch6 decisions, got {len(added_ids)}")

    review_payloads = [
        (path.name, mod._load_payload(path))
        for path in mod._review_paths(TOOLS)
    ]
    review_rows = list(mod.iter_review_rows(review_payloads))
    rows_by_source = mod._rows_by_source_id(review_rows)
    high = mod._high_confidence_concepts(review_rows)

    decisions: list[dict[str, Any]] = []
    for source_id in added_ids:
        confirmation = child_confirm[source_id]
        removed = parent_standalone[source_id]
        source = rows_by_source[source_id]
        concept_id = str(confirmation.get("confirmedConceptId") or "")
        target = high.get(concept_id)
        if target is None:
            raise RuntimeError(f"batch6 target lacks current high-confidence evidence: {source_id} -> {concept_id}")
        decisions.append(
            {
                "sourceIngredientId": source_id,
                "sourceReviewedEnglish": source["english"],
                "sourceClassification": source["classification"],
                "sourceConfidence": source["confidence"],
                "confirmedConceptId": concept_id,
                "targetCanonicalEnglish": target["english"],
                "targetClassification": target["classification"],
                "confirmationReceipt": confirmation,
                "removedStandaloneDisposition": removed,
            }
        )

    report = {
        "schemaVersion": 1,
        "kind": "cook4me-batch6-canonical-safety-audit",
        "parent": PARENT,
        "batch6": BATCH6,
        "summary": {"decisionCount": len(decisions)},
        "decisions": decisions,
    }
    out = Path("batch6-canonical-safety-audit-v60.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in decisions:
        print(
            f"{row['sourceIngredientId']} | {row['sourceReviewedEnglish']} -> {row['targetCanonicalEnglish']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
