#!/usr/bin/env python3
"""Apply the second evidence-pinned standalone semantic merge batch.

This batch is restricted to grammatical number, recipe measurement wording,
explicit review metadata, or wording that preserves the exact ingredient and
preparation state. Every source and target is pinned to reviewed English text and
classification; similarity never approves a mapping by itself.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
CONFIRMATIONS = TOOLS / "release_catalog_semantic_confirmations.v1.json"
STANDALONE = TOOLS / "release_catalog_semantic_standalone_dispositions.v1.json"
COMPILER = TOOLS / "compile_release_catalog_semantics_v60.py"

spec = importlib.util.spec_from_file_location("cook4me_semantic_safe_batch2", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

DECISIONS: tuple[dict[str, str], ...] = (
    {
        "sourceIngredientId": "local:uk:83279e38f188ddead90d",
        "sourceReviewedEnglish": "Red peppers, cleaned and cut into strips",
        "classification": "food",
        "confirmedConceptId": "concept:food:6c279fc56f9d553886e7",
        "targetCanonicalEnglish": "Red pepper, cleaned and cut into strips",
        "rationale": "The reviewed meanings differ only by grammatical number; red pepper identity and cleaned/strip preparation are identical.",
    },
    {
        "sourceIngredientId": "local:uk:c7bb8550c7e51dabaca8",
        "sourceReviewedEnglish": "Red peppers, cleaned and cut into strips (quantity fragment: /2)",
        "classification": "food",
        "confirmedConceptId": "concept:food:6c279fc56f9d553886e7",
        "targetCanonicalEnglish": "Red pepper, cleaned and cut into strips",
        "rationale": "The /2 fragment is recipe quantity metadata and peppers/pepper is grammatical number only; preparation is identical.",
    },
    {
        "sourceIngredientId": "local:uk:d0ebe6eff41d91e4d4e9",
        "sourceReviewedEnglish": "Shallot, peeled and cut into pieces",
        "classification": "food",
        "confirmedConceptId": "concept:food:51e6307236b5f08983e5",
        "targetCanonicalEnglish": "Shallots, peeled and cut into pieces",
        "rationale": "The reviewed meanings differ only by singular/plural; peeled and cut-into-pieces preparation is identical.",
    },
    {
        "sourceIngredientId": "local:uk:48a4ea445a06b175f7b9",
        "sourceReviewedEnglish": "Cup of parsley, washed and chopped",
        "classification": "food",
        "confirmedConceptId": "concept:food:4417f9f4f541baedb0b9",
        "targetCanonicalEnglish": "Parsley, washed and chopped",
        "rationale": "Cup is a recipe quantity measure only; parsley identity and washed/chopped preparation are unchanged.",
    },
    {
        "sourceIngredientId": "local:uk:8f9320d8c48803b58d31",
        "sourceReviewedEnglish": "Cups of parsley, washed and chopped",
        "classification": "food",
        "confirmedConceptId": "concept:food:4417f9f4f541baedb0b9",
        "targetCanonicalEnglish": "Parsley, washed and chopped",
        "rationale": "Cups is a recipe quantity measure only; parsley identity and washed/chopped preparation are unchanged.",
    },
    {
        "sourceIngredientId": "local:ja:0785d2bb74f1da5d96e0",
        "sourceReviewedEnglish": "White sesame seeds, a little for finishing",
        "classification": "food",
        "confirmedConceptId": "concept:food:b5b5d62f9cb8c4cf45f2",
        "targetCanonicalEnglish": "White sesame seeds (for finishing)",
        "rationale": "A little expresses recipe quantity only; white sesame seed identity and finishing use are preserved exactly.",
    },
    {
        "sourceIngredientId": "local:cs:acb0746b0095de5830cd",
        "sourceReviewedEnglish": "tbsp mirin",
        "classification": "food",
        "confirmedConceptId": "concept:food:c6cb90b0108d4d68cdb3",
        "targetCanonicalEnglish": "Mirin",
        "rationale": "Tbsp is an unspecified recipe measurement unit; it does not create a distinct mirin ingredient identity.",
    },
    {
        "sourceIngredientId": "local:pt:a1e33127e90155a1d44c",
        "sourceReviewedEnglish": "Ground pepper (optional)",
        "classification": "food",
        "confirmedConceptId": "concept:food:426bbdb4814fda1bcdc5",
        "targetCanonicalEnglish": "Ground pepper",
        "rationale": "Optional describes recipe use rather than ingredient identity; the reviewed food remains ground pepper.",
    },
    {
        "sourceIngredientId": "local:uk:8fa86212f5e90b67d710",
        "sourceReviewedEnglish": "Yellow peach (or white peach or nectarine), peeled and quartered",
        "classification": "food",
        "confirmedConceptId": "concept:food:969a780a1432d4babbc1",
        "targetCanonicalEnglish": "Yellow peaches (or white peaches or nectarines), peeled and quartered",
        "rationale": "The difference is grammatical number only; all fruit alternatives plus peeled/quartered preparation are preserved.",
    },
    {
        "sourceIngredientId": "local:zh:56be54f756a3162a619b",
        "sourceReviewedEnglish": "Baking paper (placed under cheese)",
        "classification": "equipment",
        "confirmedConceptId": "concept:equipment:f9991a9d3062f2fe99bd",
        "targetCanonicalEnglish": "Baking paper (to place under cheese)",
        "rationale": "Placed under cheese and to place under cheese describe the same equipment and identical recipe use.",
    },
    {
        "sourceIngredientId": "local:uk:7358702309de1e8de760",
        "sourceReviewedEnglish": "Bunch of fresh coriander, washed and finely chopped (quantity fragment: /2)",
        "classification": "food",
        "confirmedConceptId": "concept:food:33048616d2334e537752",
        "targetCanonicalEnglish": "Fresh coriander, washed and finely chopped",
        "rationale": "Bunch and /2 are recipe quantity information; fresh coriander identity and washed/finely-chopped state remain identical.",
    },
    {
        "sourceIngredientId": "local:bg:b1b1dcc4b7801a3f728d",
        "sourceReviewedEnglish": "Sprig of finely chopped coriander",
        "classification": "food",
        "confirmedConceptId": "concept:food:c9dcf92e197c846086b9",
        "targetCanonicalEnglish": "Finely chopped coriander",
        "rationale": "Sprig is a recipe quantity unit only; the coriander identity and finely chopped preparation are unchanged.",
    },
    {
        "sourceIngredientId": "local:hu:2476400dbb90b4779d48",
        "sourceReviewedEnglish": "Bouquets garni",
        "classification": "food",
        "confirmedConceptId": "concept:food:9a0077198ff432aa97b1",
        "targetCanonicalEnglish": "Bouquet garni",
        "rationale": "The reviewed meanings differ only by grammatical plural; the bouquet garni ingredient is the same.",
    },
    {
        "sourceIngredientId": "local:uk:b3ebb64732a1c6e75d65",
        "sourceReviewedEnglish": "Red peppers, cut into small cubes",
        "classification": "food",
        "confirmedConceptId": "concept:food:6e27a056c3b5829bc212",
        "targetCanonicalEnglish": "Red pepper, cut into small cubes",
        "rationale": "The difference is singular/plural only; red pepper identity and small-cube preparation are identical without adding bell-pepper specificity.",
    },
    {
        "sourceIngredientId": "local:uk:2af4e404564192e8e527",
        "sourceReviewedEnglish": "Garlic, peeled, germ removed and finely chopped",
        "classification": "food",
        "confirmedConceptId": "concept:food:4e922cdf4af90d0141f4",
        "targetCanonicalEnglish": "Garlic, peeled, degermed and finely chopped",
        "rationale": "Degermed and germ removed are equivalent preparation wording; peeled and finely chopped state is preserved exactly.",
    },
    {
        "sourceIngredientId": "local:uk:d76853b4303c725f0e39",
        "sourceReviewedEnglish": "Tablespoon of fresh coriander, washed and chopped (quantity count omitted)",
        "classification": "food",
        "confirmedConceptId": "concept:food:8a6ec5111fa708cf847c",
        "targetCanonicalEnglish": "Fresh coriander, washed and chopped",
        "rationale": "Tablespoon and omitted count are recipe quantity metadata; fresh coriander identity and washed/chopped preparation are unchanged.",
    },
    {
        "sourceIngredientId": "local:uk:e16f977d2d55dc9f060f",
        "sourceReviewedEnglish": "Tablespoon of fresh coriander, washed and chopped (quantity count omitted; mixed-language source)",
        "classification": "food",
        "confirmedConceptId": "concept:food:8a6ec5111fa708cf847c",
        "targetCanonicalEnglish": "Fresh coriander, washed and chopped",
        "rationale": "Tablespoon/count and mixed-language review notes are metadata only; fresh coriander and washed/chopped preparation are unchanged.",
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
    if not DECISIONS:
        raise RuntimeError("empty semantic merge batch")
    if len({row["sourceIngredientId"] for row in DECISIONS}) != len(DECISIONS):
        raise RuntimeError("duplicate source identity in decision batch")

    confirmations = _load(CONFIRMATIONS)
    standalone = _load(STANDALONE)
    if confirmations.get("policy", {}).get("manualSemanticEquivalenceAllowed") is not True:
        raise RuntimeError("manual semantic equivalence is not enabled")

    review_rows = list(
        mod.iter_review_rows(
            [(path.name, mod._load_payload(path)) for path in mod._review_paths(TOOLS)]
        )
    )
    rows_by_source = mod._rows_by_source_id(review_rows)
    high_concepts = mod._high_confidence_concepts(review_rows)

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

    new_confirmation_rows: list[dict[str, Any]] = []
    decision_ids: set[str] = set()
    for decision in DECISIONS:
        source_id = decision["sourceIngredientId"]
        decision_ids.add(source_id)
        if source_id in existing_confirmation_ids:
            raise RuntimeError(f"source is already confirmed: {source_id}")
        standalone_row = standalone_by_id.get(source_id)
        if standalone_row is None:
            raise RuntimeError(f"source is not currently standalone: {source_id}")
        if standalone_row.get("disposition") != "reviewed-source-local-standalone":
            raise RuntimeError(f"source is not a mergeable standalone row: {source_id}")
        if standalone_row.get("sourceReviewedEnglish") != decision["sourceReviewedEnglish"]:
            raise RuntimeError(f"standalone reviewed English drift: {source_id}")
        if str(standalone_row.get("classification") or "").lower() != decision["classification"]:
            raise RuntimeError(f"standalone classification drift: {source_id}")

        reviewed = rows_by_source.get(source_id)
        if reviewed is None:
            raise RuntimeError(f"review source missing: {source_id}")
        if reviewed["english"] != decision["sourceReviewedEnglish"]:
            raise RuntimeError(f"reviewed English drift: {source_id}")
        if reviewed["classification"] != decision["classification"]:
            raise RuntimeError(f"reviewed classification drift: {source_id}")
        if reviewed["confidence"] == "high":
            raise RuntimeError(f"source no longer needs explicit merge review: {source_id}")

        target = high_concepts.get(decision["confirmedConceptId"])
        if target is None:
            raise RuntimeError(
                f"target lacks current high-confidence evidence: {decision['confirmedConceptId']}"
            )
        if target["classification"] != reviewed["classification"]:
            raise RuntimeError(f"target classification drift: {source_id}")
        if target["english"] != decision["targetCanonicalEnglish"]:
            raise RuntimeError(f"target canonical English drift: {source_id}")
        if len(decision["rationale"]) < 20:
            raise RuntimeError(f"rationale too short: {source_id}")

        new_confirmation_rows.append(
            {
                "sourceIngredientId": source_id,
                "confirmedConceptId": decision["confirmedConceptId"],
                "manualSemanticEquivalence": True,
                "sourceReviewedEnglish": decision["sourceReviewedEnglish"],
                "targetCanonicalEnglish": decision["targetCanonicalEnglish"],
                "rationale": decision["rationale"],
            }
        )

    confirmations.setdefault("items", []).extend(new_confirmation_rows)
    standalone_items = [
        row for row in standalone_items if row.get("sourceIngredientId") not in decision_ids
    ]
    ambiguous_count = sum(
        row.get("disposition") == "reviewed-ambiguous-source-fragment"
        for row in standalone_items
    )
    standalone["items"] = standalone_items
    standalone["summary"] = {
        "standaloneDispositionCount": len(standalone_items),
        "reviewedAmbiguousCount": ambiguous_count,
        "reviewedSourceLocalStandaloneCount": len(standalone_items) - ambiguous_count,
    }

    _write(CONFIRMATIONS, confirmations)
    _write(STANDALONE, standalone)
    print(
        json.dumps(
            {
                "mergedFromStandalone": len(DECISIONS),
                "standaloneRemaining": len(standalone_items),
                "reviewedAmbiguousRemaining": ambiguous_count,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
