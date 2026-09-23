#!/usr/bin/env python3
"""Apply one explicit, evidence-pinned standalone semantic merge batch.

Every decision below removes only recipe quantity/unit text or explicit review
metadata from an already-reviewed English meaning.  The script is deliberately
fail-closed: source ID/text, classification, high-confidence target ID/text, and
current standalone disposition must all match before either ledger is changed.
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
STANDALONE_TEST = ROOT / "tests/test_semantic_standalone_dispositions_v60.py"
COMPILER = TOOLS / "compile_release_catalog_semantics_v60.py"

spec = importlib.util.spec_from_file_location("cook4me_semantic_safe_batch", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

DECISIONS: tuple[dict[str, str], ...] = (
    {
        "sourceIngredientId": "local:uk:c7d92d38fa801150537e",
        "sourceReviewedEnglish": "g carrots, peeled and cut into pieces",
        "confirmedConceptId": "concept:food:1649b293e82d8aebf818",
        "targetCanonicalEnglish": "Carrots, peeled and cut into pieces",
        "rationale": "The leading g is a retained recipe unit fragment; the carrot ingredient and peeled/cut preparation are otherwise identical.",
    },
    {
        "sourceIngredientId": "local:uk:8750f1a1300154d816b6",
        "sourceReviewedEnglish": "Pork shoulder, cut into approximately 100 g pieces (quantity unit fragment at start)",
        "confirmedConceptId": "concept:food:967d7977cf800ddbf482",
        "targetCanonicalEnglish": "Pork shoulder, cut into approximately 100 g pieces",
        "rationale": "The parenthetical quantity-unit-fragment note is review metadata only; the pork cut and preparation are identical.",
    },
    {
        "sourceIngredientId": "local:uk:a8fc807bc1827c19bb37",
        "sourceReviewedEnglish": "Vegetable stock (or salted water; source grammar)",
        "confirmedConceptId": "concept:food:df0e7bb61897b9c51e7b",
        "targetCanonicalEnglish": "Vegetable stock (or salted water)",
        "rationale": "The source-grammar annotation records wording quality only and does not change the vegetable-stock or salted-water ingredient alternative.",
    },
    {
        "sourceIngredientId": "local:uk:2038766537601c8147e5",
        "sourceReviewedEnglish": "One-third vanilla pod, scraped and split lengthwise",
        "confirmedConceptId": "concept:food:9ac8b615de49ac5e4849",
        "targetCanonicalEnglish": "Vanilla pod, scraped and split lengthwise",
        "rationale": "One-third is the recipe amount; the ingredient remains the same vanilla pod with the same scraped and split preparation.",
    },
    {
        "sourceIngredientId": "local:uk:4df5618584087f9f7fae",
        "sourceReviewedEnglish": "tbsp garlic croutons",
        "confirmedConceptId": "concept:food:a67eb6fc2fdef7eebd5c",
        "targetCanonicalEnglish": "Garlic croutons",
        "rationale": "Tbsp is a recipe measurement unit only; it does not alter the garlic-crouton ingredient identity.",
    },
    {
        "sourceIngredientId": "local:pl:62877ab92cd47dea74fd",
        "sourceReviewedEnglish": "Allspice berries (piece count)",
        "confirmedConceptId": "concept:food:d639012a952eb30f2bb9",
        "targetCanonicalEnglish": "Allspice berries",
        "rationale": "The piece-count parenthetical describes recipe quantity accounting only; the ingredient is the same allspice berries.",
    },
    {
        "sourceIngredientId": "local:uk:97fa9495baa5deadd6fa",
        "sourceReviewedEnglish": "Half a chopped onion",
        "confirmedConceptId": "concept:food:9c767aade0cf2f6a3d24",
        "targetCanonicalEnglish": "Chopped onion",
        "rationale": "Half specifies the recipe amount only; both reviewed meanings identify the same chopped-onion ingredient and preparation.",
    },
    {
        "sourceIngredientId": "local:uk:2b9997e3cd24ac86b343",
        "sourceReviewedEnglish": "Tablespoon of grated coconut (quantity count omitted)",
        "confirmedConceptId": "concept:food:fec88107bfd3514d5822",
        "targetCanonicalEnglish": "Grated coconut",
        "rationale": "Tablespoon and the omitted-count note are recipe quantity metadata; the food identity and grated state are unchanged.",
    },
    {
        "sourceIngredientId": "local:uk:21ca84b2b44c1e114419",
        "sourceReviewedEnglish": "Tablespoon of grated Parmesan (or other cheese) (quantity count omitted)",
        "confirmedConceptId": "concept:food:4c2756e6e88f5ad6dfc2",
        "targetCanonicalEnglish": "Grated Parmesan (or other cheese)",
        "rationale": "The tablespoon/count wording is recipe quantity metadata only; the Parmesan-or-other-cheese alternative and grated state are identical.",
    },
    {
        "sourceIngredientId": "local:uk:477f3caebfaea907c5fb",
        "sourceReviewedEnglish": "Teaspoon of cooked lobster purée (quantity count omitted)",
        "confirmedConceptId": "concept:food:1c06f3b5dcab0d0327c0",
        "targetCanonicalEnglish": "Cooked lobster purée",
        "rationale": "Teaspoon and omitted count are recipe quantity metadata; both meanings retain the cooked lobster-purée state exactly.",
    },
    {
        "sourceIngredientId": "local:uk:2953f840d8254566bed3",
        "sourceReviewedEnglish": "Teaspoon of curry powder (quantity count omitted)",
        "confirmedConceptId": "concept:food:d347eb0dd4c8d8f60836",
        "targetCanonicalEnglish": "Curry powder",
        "rationale": "The teaspoon/count wording is recipe quantity metadata only and does not change the curry-powder ingredient.",
    },
    {
        "sourceIngredientId": "local:uk:9826f344b1653bf39679",
        "sourceReviewedEnglish": "Teaspoon of curry powder (quantity count omitted)",
        "confirmedConceptId": "concept:food:d347eb0dd4c8d8f60836",
        "targetCanonicalEnglish": "Curry powder",
        "rationale": "The teaspoon/count wording is recipe quantity metadata only and does not change the curry-powder ingredient.",
    },
    {
        "sourceIngredientId": "local:uk:cfd3d4ae62bfa7ea4118",
        "sourceReviewedEnglish": "Teaspoon of baking powder (quantity count omitted)",
        "confirmedConceptId": "concept:food:8d4f55dd1fd80c16dd05",
        "targetCanonicalEnglish": "Baking powder",
        "rationale": "The teaspoon/count wording is recipe quantity metadata only; the ingredient remains baking powder rather than a packet-sized identity.",
    },
    {
        "sourceIngredientId": "local:uk:5803a00c73bb88155919",
        "sourceReviewedEnglish": "Teaspoon of chili powder (quantity count omitted)",
        "confirmedConceptId": "concept:food:fce5ce5385ab00eb41a4",
        "targetCanonicalEnglish": "Chili powder",
        "rationale": "The teaspoon/count wording is recipe quantity metadata only; the ingredient remains chili powder rather than a pinch-sized identity.",
    },
    {
        "sourceIngredientId": "local:uk:584bf192b767d30a1a38",
        "sourceReviewedEnglish": "Teaspoon of lobster bisque (quantity count omitted)",
        "confirmedConceptId": "concept:food:e304c5e8e13b27aa9848",
        "targetCanonicalEnglish": "Lobster bisque",
        "rationale": "The teaspoon/count wording is recipe quantity metadata only; it does not change the lobster-bisque ingredient identity.",
    },
    {
        "sourceIngredientId": "local:uk:d7229f39fe6e4f2cda77",
        "sourceReviewedEnglish": "Teaspoon of sesame oil (quantity count omitted)",
        "confirmedConceptId": "concept:food:5d163c89d164524e593f",
        "targetCanonicalEnglish": "Sesame oil",
        "rationale": "The teaspoon/count wording is recipe quantity metadata only; it does not change the sesame-oil ingredient identity.",
    },
    {
        "sourceIngredientId": "local:uk:394628b6417f62914c00",
        "sourceReviewedEnglish": "Teaspoon of cinnamon, ginger and nutmeg spice mix (quantity count omitted)",
        "confirmedConceptId": "concept:food:77bb3ead79227bf88d58",
        "targetCanonicalEnglish": "Cinnamon, ginger and nutmeg spice mix",
        "rationale": "The teaspoon/count wording is recipe quantity metadata only; the exact cinnamon-ginger-nutmeg spice mixture is preserved.",
    },
    {
        "sourceIngredientId": "local:uk:437fe43289b9b35a6b0d",
        "sourceReviewedEnglish": "Teaspoon of dried crushed chili (to taste; quantity count omitted)",
        "confirmedConceptId": "concept:food:4d75c1cef9ac8dbaa3ac",
        "targetCanonicalEnglish": "Dried crushed chili (to taste)",
        "rationale": "The teaspoon/count note is quantity metadata only; dried, crushed, and to-taste preparation semantics remain exactly the same.",
    },
    {
        "sourceIngredientId": "local:uk:d8c68983b15ae228f443",
        "sourceReviewedEnglish": "Teaspoon of Indian spice mix (quantity count omitted)",
        "confirmedConceptId": "concept:food:b2092d9fea8587b6af54",
        "targetCanonicalEnglish": "Indian spice mix",
        "rationale": "The teaspoon/count wording is recipe quantity metadata only; it does not add a powdered state or otherwise alter the Indian spice mix.",
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


def _make_tests_count_driven() -> None:
    text = STANDALONE_TEST.read_text(encoding="utf-8")
    old = '''        self.assertEqual(ledger["summary"]["standaloneDispositionCount"], 293)
        self.assertEqual(ledger["summary"]["reviewedAmbiguousCount"], 28)
        self.assertEqual(ledger["summary"]["reviewedSourceLocalStandaloneCount"], 265)
        ledger_ids = [row["sourceIngredientId"] for row in ledger["items"]]
        self.assertEqual(len(ledger_ids), len(set(ledger_ids)))

        result = mod.compile_from_paths(mod._review_paths(tools))
        self.assertEqual(result["summary"]["needsSemanticConfirmationSourceLabels"], 0)
        self.assertEqual(result["summary"]["standaloneConfirmedSourceLabels"], 293)
        self.assertEqual(result["summary"]["reviewedAmbiguousSourceLabels"], 28)
'''
    new = '''        ledger_items = [row for row in ledger["items"] if isinstance(row, dict)]
        ambiguous_count = sum(
            row.get("disposition") == "reviewed-ambiguous-source-fragment"
            for row in ledger_items
        )
        mergeable_count = len(ledger_items) - ambiguous_count
        self.assertEqual(
            ledger["summary"]["standaloneDispositionCount"], len(ledger_items)
        )
        self.assertEqual(
            ledger["summary"]["reviewedAmbiguousCount"], ambiguous_count
        )
        self.assertEqual(
            ledger["summary"]["reviewedSourceLocalStandaloneCount"], mergeable_count
        )
        ledger_ids = [row["sourceIngredientId"] for row in ledger_items]
        self.assertEqual(len(ledger_ids), len(set(ledger_ids)))

        result = mod.compile_from_paths(mod._review_paths(tools))
        self.assertEqual(result["summary"]["needsSemanticConfirmationSourceLabels"], 0)
        self.assertEqual(
            result["summary"]["standaloneConfirmedSourceLabels"], len(ledger_items)
        )
        self.assertEqual(
            result["summary"]["reviewedAmbiguousSourceLabels"], ambiguous_count
        )
'''
    if old in text:
        text = text.replace(old, new, 1)
        STANDALONE_TEST.write_text(text, encoding="utf-8")
    elif new not in text:
        raise RuntimeError("standalone regression count block is neither old nor updated")


def main() -> int:
    if len(DECISIONS) != 19:
        raise RuntimeError(f"expected 19 decisions, got {len(DECISIONS)}")
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

        reviewed = rows_by_source.get(source_id)
        if reviewed is None:
            raise RuntimeError(f"review source missing: {source_id}")
        if reviewed["english"] != decision["sourceReviewedEnglish"]:
            raise RuntimeError(f"reviewed English drift: {source_id}")
        if reviewed["classification"] != "food":
            raise RuntimeError(f"first safe batch expects food classification: {source_id}")
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
        row
        for row in standalone_items
        if row.get("sourceIngredientId") not in decision_ids
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
    _make_tests_count_driven()
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
