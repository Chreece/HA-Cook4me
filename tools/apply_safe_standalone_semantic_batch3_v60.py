#!/usr/bin/env python3
"""Apply the third evidence-pinned standalone semantic merge batch.

This batch is restricted to recipe measurement/count fragments, explicit review
metadata, grammatical number, or a pure orthographic variant. Similarity is never
identity proof: every source ID/text/classification and target concept/text is
pinned and revalidated before either ledger is changed.
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

spec = importlib.util.spec_from_file_location("cook4me_semantic_safe_batch3", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

DECISIONS: tuple[dict[str, str], ...] = (
    {
        "sourceIngredientId": "local:hu:67af874ee49404292cb4",
        "sourceReviewedEnglish": "Mexican seasoning (tablespoon fragment)",
        "classification": "food",
        "confirmedConceptId": "concept:food:1520e1dc851682225d28",
        "targetCanonicalEnglish": "Mexican seasoning",
        "rationale": "The tablespoon fragment is recipe measurement metadata only; the reviewed ingredient remains Mexican seasoning.",
    },
    {
        "sourceIngredientId": "local:uk:f78a44710b9f89188244",
        "sourceReviewedEnglish": "Cinnamon/ginger/nutmeg spice mix (quantity fragment: /3 tsp)",
        "classification": "food",
        "confirmedConceptId": "concept:food:77bb3ead79227bf88d58",
        "targetCanonicalEnglish": "Cinnamon, ginger and nutmeg spice mix",
        "rationale": "The /3 tsp text is recipe quantity metadata and slash punctuation does not change the exact cinnamon-ginger-nutmeg mixture.",
    },
    {
        "sourceIngredientId": "local:uk:81a88b3923386ed69886",
        "sourceReviewedEnglish": "Cup of ground almonds (quantity fragment: /2)",
        "classification": "food",
        "confirmedConceptId": "concept:food:21249c30b72cb238adc6",
        "targetCanonicalEnglish": "Ground almonds",
        "rationale": "Cup and /2 are recipe quantity information only; the ingredient identity remains ground almonds.",
    },
    {
        "sourceIngredientId": "local:uk:e98016b6d4da1c8cba63",
        "sourceReviewedEnglish": "Dried crushed chili to taste (quantity fragment: /2 tsp)",
        "classification": "food",
        "confirmedConceptId": "concept:food:4d75c1cef9ac8dbaa3ac",
        "targetCanonicalEnglish": "Dried crushed chili (to taste)",
        "rationale": "The /2 tsp fragment is recipe quantity metadata; dried, crushed, and to-taste semantics are identical.",
    },
    {
        "sourceIngredientId": "local:uk:de7632cced2d129be509",
        "sourceReviewedEnglish": "Fresh basil leaves, chopped (quantity fragment: /2 tbsp)",
        "classification": "food",
        "confirmedConceptId": "concept:food:4e1a94c435274aa5129e",
        "targetCanonicalEnglish": "tbsp fresh basil leaves, chopped",
        "rationale": "Both reviewed meanings retain fresh basil leaves and chopped preparation; the remaining difference is tablespoon quantity wording.",
    },
    {
        "sourceIngredientId": "local:uk:89826d25571f2d56e901",
        "sourceReviewedEnglish": "Coriander, washed and chopped (quantity fragment: /2 tbsp)",
        "classification": "food",
        "confirmedConceptId": "concept:food:d59c668b613fc706eba3",
        "targetCanonicalEnglish": "Tbsp coriander, washed and chopped",
        "rationale": "The /2 tbsp fragment is recipe quantity metadata; coriander identity and washed/chopped preparation are identical.",
    },
    {
        "sourceIngredientId": "local:uk:2c0bbe4b49e65fe13c76",
        "sourceReviewedEnglish": "Grams of peeled and chopped garlic (quantity incomplete)",
        "classification": "food",
        "confirmedConceptId": "concept:food:a9bdc0782f19ce5c4c7b",
        "targetCanonicalEnglish": "Peeled and chopped garlic",
        "rationale": "Grams and the incomplete-quantity note are recipe measurement metadata; peeled/chopped garlic semantics are identical.",
    },
    {
        "sourceIngredientId": "local:uk:acc6e45237e054e66959",
        "sourceReviewedEnglish": "Lime juice and zest (quantity fragment: /2)",
        "classification": "food",
        "confirmedConceptId": "concept:food:172bc89ee746fed86e52",
        "targetCanonicalEnglish": "Lime (juice and zest)",
        "rationale": "The /2 fragment is recipe quantity metadata and parenthetical wording does not change the lime juice-and-zest ingredient meaning.",
    },
    {
        "sourceIngredientId": "local:uk:c83eb5ba727dc86549e2",
        "sourceReviewedEnglish": "Onion, peeled and halved, with clove (quantity fragment: /2)",
        "classification": "food",
        "confirmedConceptId": "concept:food:7e4039b2d8c39f7671c8",
        "targetCanonicalEnglish": "Onion, peeled and halved, with cloves",
        "rationale": "The /2 fragment is recipe quantity metadata and clove/cloves is grammatical number; onion preparation and clove inclusion are identical.",
    },
    {
        "sourceIngredientId": "local:uk:1b30d8c2a1f8e317b6ea",
        "sourceReviewedEnglish": "Tablespoon of fish sauce for the meat (quantity count omitted; malformed source)",
        "classification": "food",
        "confirmedConceptId": "concept:food:7cbe708580ff4ebb99aa",
        "targetCanonicalEnglish": "tbsp fish sauce for the meat",
        "rationale": "The count/malformed-source note is review metadata; fish sauce and its for-the-meat use are preserved exactly.",
    },
    {
        "sourceIngredientId": "local:uk:4c8a16200287b7b5c2d6",
        "sourceReviewedEnglish": "Tablespoon of fish sauce for the meat (quantity count omitted; mixed source grammar)",
        "classification": "food",
        "confirmedConceptId": "concept:food:7cbe708580ff4ebb99aa",
        "targetCanonicalEnglish": "tbsp fish sauce for the meat",
        "rationale": "The count and mixed-source-grammar notes are review metadata; fish sauce and its for-the-meat use are unchanged.",
    },
    {
        "sourceIngredientId": "local:uk:9a89a1b17bb897ac37b3",
        "sourceReviewedEnglish": "Tablespoon of tomato purée",
        "classification": "food",
        "confirmedConceptId": "concept:food:1775744e541d5bdfa791",
        "targetCanonicalEnglish": "Tomato purée",
        "rationale": "Tablespoon is a recipe quantity measure only; it does not create a distinct tomato-purée ingredient identity.",
    },
    {
        "sourceIngredientId": "local:uk:f296c9f98eaac2f21c55",
        "sourceReviewedEnglish": "Tablespoon(s) of coconut cream (quantity incomplete)",
        "classification": "food",
        "confirmedConceptId": "concept:food:3ceaffa1d38fb7d815cc",
        "targetCanonicalEnglish": "Coconut cream",
        "rationale": "Tablespoon wording and the incomplete quantity are recipe metadata; the ingredient remains coconut cream.",
    },
    {
        "sourceIngredientId": "local:uk:6b40fc5c5ab07ad73e53",
        "sourceReviewedEnglish": "Tablespoon(s) of frozen green peas (quantity incomplete)",
        "classification": "food",
        "confirmedConceptId": "concept:food:776d6f522e9a61fb44fa",
        "targetCanonicalEnglish": "Frozen green peas",
        "rationale": "Tablespoon wording and the incomplete quantity are recipe metadata; frozen and green-pea state are preserved exactly.",
    },
    {
        "sourceIngredientId": "local:uk:a3331bd6ccb06b922c41",
        "sourceReviewedEnglish": "Tablespoon(s) of parsley, washed and chopped, to taste (quantity incomplete)",
        "classification": "food",
        "confirmedConceptId": "concept:food:0942ecc3de677787b178",
        "targetCanonicalEnglish": "tbsp parsley, washed and chopped (to taste)",
        "rationale": "Both meanings preserve parsley, washed/chopped preparation, and to-taste use; only quantity wording differs.",
    },
    {
        "sourceIngredientId": "local:uk:7f55d17243fdf6f4ebe8",
        "sourceReviewedEnglish": "Tablespoon(s) of soy sauce (quantity incomplete)",
        "classification": "food",
        "confirmedConceptId": "concept:food:5cb168ac6c17e3fa92c8",
        "targetCanonicalEnglish": "Tablespoon of soy sauce",
        "rationale": "Plural/parenthetical quantity wording is incomplete recipe measurement metadata; the ingredient is the same soy sauce.",
    },
    {
        "sourceIngredientId": "local:uk:25f49a3e22d7c768ed86",
        "sourceReviewedEnglish": "Tablespoons of icing sugar (quantity count omitted)",
        "classification": "food",
        "confirmedConceptId": "concept:food:4120b9d570ebce2e500d",
        "targetCanonicalEnglish": "Tablespoons of icing sugar",
        "rationale": "The omitted-count annotation is review metadata only; both reviewed meanings identify tablespoons of icing sugar.",
    },
    {
        "sourceIngredientId": "local:uk:827f3b2d3c4d295dd0fc",
        "sourceReviewedEnglish": "Teaspoon of fresh ginger, peeled and chopped (quantity count omitted)",
        "classification": "food",
        "confirmedConceptId": "concept:food:7420780cf2d62116f895",
        "targetCanonicalEnglish": "tsp fresh ginger, peeled and chopped",
        "rationale": "The count annotation and teaspoon abbreviation differ only in recipe quantity wording; fresh peeled/chopped ginger is identical.",
    },
    {
        "sourceIngredientId": "local:uk:562b9bdd6bc9c846b79d",
        "sourceReviewedEnglish": "Teaspoon of lard (or vegetable oil) (quantity count omitted; extra parenthesis in source)",
        "classification": "food",
        "confirmedConceptId": "concept:food:b83ab5694a1ed5bcf2e3",
        "targetCanonicalEnglish": "Lard or vegetable oil",
        "rationale": "Teaspoon/count and extra-parenthesis notes are recipe/source metadata; the lard-or-vegetable-oil alternative is identical.",
    },
    {
        "sourceIngredientId": "local:uk:cb1830e9184568040892",
        "sourceReviewedEnglish": "Teaspoon of toasted sesame seeds (quantity count omitted)",
        "classification": "food",
        "confirmedConceptId": "concept:food:969d59932cae879ea3ab",
        "targetCanonicalEnglish": "Toasted sesame seeds",
        "rationale": "Teaspoon/count wording is recipe quantity metadata; toasted sesame seed state is preserved exactly.",
    },
    {
        "sourceIngredientId": "local:uk:65295e86db59421f1a73",
        "sourceReviewedEnglish": "Teaspoon of vanilla extract (quantity count omitted)",
        "classification": "food",
        "confirmedConceptId": "concept:food:5eaf181e84ec26fe19d1",
        "targetCanonicalEnglish": "Vanilla extract",
        "rationale": "Teaspoon/count wording is recipe quantity metadata only; the ingredient remains vanilla extract.",
    },
    {
        "sourceIngredientId": "local:es:0092edc969971e31c05a",
        "sourceReviewedEnglish": "140 ml aluminium or silicone ramekins",
        "classification": "equipment",
        "confirmedConceptId": "concept:equipment:42ccaf98bd1e6dd5e67d",
        "targetCanonicalEnglish": "140 ml aluminum or silicone ramekins",
        "rationale": "Aluminium/aluminum is a British/American spelling variant; volume, material alternatives, ramekin equipment identity, and all semantics are identical.",
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
    if len(DECISIONS) != 22:
        raise RuntimeError(f"expected 22 decisions, got {len(DECISIONS)}")
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
