#!/usr/bin/env python3
"""Apply ten evidence-pinned standalone -> canonical high-confidence merges."""
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
ALIASES = TOOLS / "release_catalog_semantic_high_confidence_syntax_aliases.v1.json"

spec = importlib.util.spec_from_file_location("cook4me_safe_batch6_semantics", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

DECISIONS: tuple[dict[str, str], ...] = (
    {
        "sourceIngredientId": "local:ja:02e1cc34d04a7bdf1a2f",
        "sourceReviewedEnglish": "Salt (teaspoon quantity incomplete)",
        "classification": "food",
        "confirmedConceptId": "concept:food:6de8c0620c5a99d33180",
        "targetCanonicalEnglish": "Salt",
        "rationale": "The teaspoon/incomplete-quantity text is recipe measurement metadata only; the reviewed ingredient identity is salt.",
    },
    {
        "sourceIngredientId": "local:pl:9ef3a75831f2a1e3d8bf",
        "sourceReviewedEnglish": "Bay leaf (noun omitted in source)",
        "classification": "food",
        "confirmedConceptId": "concept:food:125d64999f9fc91cc29a",
        "targetCanonicalEnglish": "Bay leaf",
        "rationale": "The parenthetical note records an omitted source noun rather than a different ingredient; the reviewed identity is bay leaf.",
    },
    {
        "sourceIngredientId": "local:uk:03b0818b595c5d09761c",
        "sourceReviewedEnglish": "Tablespoon(s) of finely chopped bacon (quantity incomplete)",
        "classification": "food",
        "confirmedConceptId": "concept:food:58ada80257146e2f2b55",
        "targetCanonicalEnglish": "Chopped bacon",
        "rationale": "Tablespoon and incomplete-quantity wording are recipe metadata, while finely chopped remains within the same chopped-bacon ingredient identity.",
    },
    {
        "sourceIngredientId": "local:uk:20cb4d6ecfe7f387415e",
        "sourceReviewedEnglish": "/5 teaspoon red chili paste (to taste)",
        "classification": "food",
        "confirmedConceptId": "concept:food:d971965002eb9aa3c198",
        "targetCanonicalEnglish": "Red chili paste",
        "rationale": "The malformed teaspoon count and to-taste instruction are quantity/use metadata; the reviewed ingredient remains red chili paste.",
    },
    {
        "sourceIngredientId": "local:uk:97553c4a23b39c4f285d",
        "sourceReviewedEnglish": "Fresh parsley, washed and chopped (quantity fragment: /2 tbsp)",
        "classification": "food",
        "confirmedConceptId": "concept:food:4417f9f4f541baedb0b9",
        "targetCanonicalEnglish": "Parsley, washed and chopped",
        "rationale": "The /2 tbsp fragment is measurement metadata; washed/chopped parsley is the same ingredient and the source's fresh wording does not create a distinct preserved product state.",
    },
    {
        "sourceIngredientId": "local:uk:3a54c3b6158ad1e7b926",
        "sourceReviewedEnglish": "Tablespoon of fresh parsley, washed and chopped (quantity count omitted)",
        "classification": "food",
        "confirmedConceptId": "concept:food:4417f9f4f541baedb0b9",
        "targetCanonicalEnglish": "Parsley, washed and chopped",
        "rationale": "Tablespoon/count metadata does not change the parsley identity; washed and chopped preparation is preserved by the canonical concept.",
    },
    {
        "sourceIngredientId": "local:uk:37af35ccce43b7044807",
        "sourceReviewedEnglish": "Coriander greens, washed and chopped (quantity fragment: /2 tbsp)",
        "classification": "food",
        "confirmedConceptId": "concept:food:8a6ec5111fa708cf847c",
        "targetCanonicalEnglish": "Fresh coriander, washed and chopped",
        "rationale": "Coriander greens denotes the fresh herb leaves; the /2 tbsp fragment is measurement metadata and washed/chopped preparation is identical.",
    },
    {
        "sourceIngredientId": "local:bg:e35ac76229b5c78378c4",
        "sourceReviewedEnglish": "Sprigs of chopped coriander",
        "classification": "food",
        "confirmedConceptId": "concept:food:474736156e14c2d92bac",
        "targetCanonicalEnglish": "Chopped sprigs of fresh coriander",
        "rationale": "The two reviewed labels differ only in word order and an explicit fresh qualifier inherent to coriander sprigs; chopped-sprig preparation is identical.",
    },
    {
        "sourceIngredientId": "local:uk:eef3cdfcd9a6230db7e6",
        "sourceReviewedEnglish": "Rosemary sprigs (quantity fragment: /2)",
        "classification": "food",
        "confirmedConceptId": "concept:food:d9187ad85969f226ce35",
        "targetCanonicalEnglish": "Rosemary",
        "rationale": "Sprigs and the /2 fragment describe recipe form/quantity of the herb rather than a different rosemary ingredient identity.",
    },
    {
        "sourceIngredientId": "local:uk:953617d433fc7f71ea28",
        "sourceReviewedEnglish": "Vanilla pod, scraped/peeled (quantity fragment: /2)",
        "classification": "food",
        "confirmedConceptId": "concept:food:e582993179a979ea663f",
        "targetCanonicalEnglish": "Scraped vanilla pod",
        "rationale": "The /2 fragment is quantity metadata and the reviewed scraped/peeled preparation maps conservatively to the existing scraped vanilla-pod concept.",
    },
)


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
    if len(DECISIONS) != 10:
        raise RuntimeError(f"expected ten decisions, got {len(DECISIONS)}")
    source_ids = [row["sourceIngredientId"] for row in DECISIONS]
    if len(set(source_ids)) != len(source_ids):
        raise RuntimeError("duplicate source identity in batch 6")

    confirmations = _load(CONFIRMATIONS)
    standalone = _load(STANDALONE)
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
        row["conceptId"]: row for row in compiled.get("concepts") or []
        if isinstance(row, dict) and row.get("conceptId")
    }

    alias_old_ids = {
        str(row.get("oldConceptId") or "")
        for row in aliases.get("items") or []
        if isinstance(row, dict)
    }
    conflict_targets = set(aliases.get("excludedConflictTargetConceptIds") or [])

    existing_confirmation_ids = {
        str(row.get("sourceIngredientId") or "")
        for row in confirmations.get("items") or []
        if isinstance(row, dict)
    }
    standalone_items = [
        row for row in standalone.get("items") or [] if isinstance(row, dict)
    ]
    standalone_by_id = {
        str(row.get("sourceIngredientId") or ""): row for row in standalone_items
    }

    new_rows: list[dict[str, Any]] = []
    for decision in DECISIONS:
        source_id = decision["sourceIngredientId"]
        concept_id = decision["confirmedConceptId"]
        if source_id in existing_confirmation_ids:
            raise RuntimeError(f"source is already confirmed: {source_id}")
        disposition = standalone_by_id.get(source_id)
        if disposition is None:
            raise RuntimeError(f"source is no longer standalone: {source_id}")
        if disposition.get("disposition") != "reviewed-source-local-standalone":
            raise RuntimeError(f"source is not mergeable standalone: {source_id}")
        if disposition.get("sourceReviewedEnglish") != decision["sourceReviewedEnglish"]:
            raise RuntimeError(f"standalone reviewed English drift: {source_id}")
        if str(disposition.get("classification") or "").lower() != decision["classification"]:
            raise RuntimeError(f"standalone classification drift: {source_id}")

        reviewed = rows_by_source.get(source_id)
        if reviewed is None or reviewed["english"] != decision["sourceReviewedEnglish"]:
            raise RuntimeError(f"review source drift: {source_id}")
        if reviewed["classification"] != decision["classification"]:
            raise RuntimeError(f"review classification drift: {source_id}")
        if reviewed["confidence"] == "high":
            raise RuntimeError(f"source unexpectedly became high confidence: {source_id}")

        if concept_id in alias_old_ids:
            raise RuntimeError(f"target is a collapsed alias concept: {concept_id}")
        if concept_id in conflict_targets:
            raise RuntimeError(f"target is a nutrition-conflict concept: {concept_id}")
        raw_target = raw_high.get(concept_id)
        if raw_target is None:
            raise RuntimeError(f"target lacks raw high-confidence review evidence: {concept_id}")
        if raw_target["english"] != decision["targetCanonicalEnglish"]:
            raise RuntimeError(f"raw target English drift: {concept_id}")
        if raw_target["classification"] != decision["classification"]:
            raise RuntimeError(f"raw target classification drift: {concept_id}")

        target = compiled_concepts.get(concept_id)
        if target is None:
            raise RuntimeError(f"canonical target is absent from compiled graph: {concept_id}")
        if target.get("canonicalEnglish") != decision["targetCanonicalEnglish"]:
            raise RuntimeError(f"compiled target English drift: {concept_id}")
        if target.get("classification") != decision["classification"]:
            raise RuntimeError(f"compiled target classification drift: {concept_id}")
        if target.get("needsSemanticConfirmation") is True:
            raise RuntimeError(f"target unexpectedly needs semantic confirmation: {concept_id}")
        if not any(
            isinstance(row, dict) and row.get("confidence") == "high"
            for row in target.get("sourceIdentities") or []
        ):
            raise RuntimeError(f"compiled target lacks high-confidence source: {concept_id}")
        if decision["classification"] == "food" and any(
            target.get(key) is not True
            for key in ("nutritionEligible", "dietEligible", "allergenEligible")
        ):
            raise RuntimeError(f"canonical food target is not fully eligible: {concept_id}")

        new_rows.append({
            "sourceIngredientId": source_id,
            "confirmedConceptId": concept_id,
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": decision["sourceReviewedEnglish"],
            "targetCanonicalEnglish": decision["targetCanonicalEnglish"],
            "rationale": decision["rationale"],
        })

    remove_ids = set(source_ids)
    kept = [
        row for row in standalone_items
        if str(row.get("sourceIngredientId") or "") not in remove_ids
    ]
    if len(standalone_items) - len(kept) != len(DECISIONS):
        raise RuntimeError("standalone removal count mismatch")

    confirmations["items"] = list(confirmations.get("items") or []) + new_rows
    standalone["items"] = kept
    ambiguous_count = sum(
        row.get("disposition") == "reviewed-ambiguous-source-fragment"
        for row in kept
    )
    standalone["summary"] = {
        "standaloneDispositionCount": len(kept),
        "reviewedAmbiguousCount": ambiguous_count,
        "reviewedSourceLocalStandaloneCount": len(kept) - ambiguous_count,
    }

    _write(CONFIRMATIONS, confirmations)
    _write(STANDALONE, standalone)
    print(json.dumps({
        "mergedFromStandalone": len(DECISIONS),
        "standaloneRemaining": len(kept),
        "reviewedAmbiguousRemaining": ambiguous_count,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
