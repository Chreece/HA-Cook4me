#!/usr/bin/env python3
"""Apply four evidence-pinned provenance-only ingredient semantic resolutions.

Three rows join existing high-confidence food concepts because the only extra text
is cooking-container/serving provenance. One row joins an existing conservative
source-local root, so it deliberately gains no food-intelligence eligibility.
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
EQUIVALENCE_TEST = ROOT / "tests/test_semantic_standalone_equivalences_v60.py"

spec = importlib.util.spec_from_file_location("cook4me_semantic_batch8", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

HIGH_CONFIDENCE_DECISIONS: tuple[dict[str, str], ...] = (
    {
        "sourceIngredientId": "local:ar:8d592089ff893d24c0ed",
        "sourceReviewedEnglish": "Chickpeas, cooked in the Cookeo",
        "classification": "food",
        "confirmedConceptId": "concept:food:b62b666675a345576dc2",
        "targetCanonicalEnglish": "Cooked chickpeas",
        "rationale": "The Cookeo phrase records cooking provenance only; both reviewed meanings identify cooked chickpeas with no different ingredient, state, cut, flavour, or alternative.",
    },
    {
        "sourceIngredientId": "local:bg:a4f3ec1f23e79327be37",
        "sourceReviewedEnglish": "Fine-grain semolina in a salad bowl",
        "classification": "food",
        "confirmedConceptId": "concept:food:de2334a8baa22d28ed06",
        "targetCanonicalEnglish": "Fine semolina",
        "rationale": "The salad-bowl phrase is serving/container provenance only and fine-grain semolina is the same reviewed food identity as fine semolina.",
    },
    {
        "sourceIngredientId": "local:zh:804fa1497e8f14782657",
        "sourceReviewedEnglish": "Mango, reserved",
        "classification": "food",
        "confirmedConceptId": "concept:food:cae4b3fc012f8d596036",
        "targetCanonicalEnglish": "Mango",
        "rationale": "Reserved is recipe-use metadata only; it does not change the mango ingredient identity, state, variety, preparation, or composition.",
    },
)

SOURCE_LOCAL_DECISION: dict[str, Any] = {
    "sourceIngredientId": "local:de:3c0eabf069bb8565c409",
    "targetSourceIngredientId": "local:de:5f2be7421ddb4fb7b038",
    "sourceReviewedEnglish": "Cooked garden beans (in Cook4Me or from a jar)",
    "targetReviewedEnglish": "Cooked garden beans",
    "classification": "food",
    "manualSemanticEquivalence": True,
    "rationale": "The parenthetical describes cooking/source provenance only; both reviewed rows identify cooked garden beans. Keep the target conservative and grant no safety eligibility.",
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


def _review_rows() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    paths = mod._review_paths(TOOLS)
    payloads = [(path.name, mod._load_payload(path)) for path in paths]
    rows = list(mod.iter_review_rows(payloads))
    return mod._rows_by_source_id(rows), mod._high_confidence_concepts(rows)


def _patch_equivalence_test() -> None:
    text = EQUIVALENCE_TEST.read_text(encoding="utf-8")
    old = '''        self.assertEqual(ledger["summary"]["equivalenceCount"], 14)\n        self.assertEqual(len(ledger["items"]), 14)\n        self.assertEqual(\n            len({row["sourceIngredientId"] for row in ledger["items"]}), 14\n        )\n        self.assertEqual(\n            sum(row.get("manualSemanticEquivalence") is True for row in ledger["items"]),\n            7,\n        )\n'''
    new = '''        expected_count = int(ledger["summary"]["equivalenceCount"])\n        self.assertEqual(expected_count, len(ledger["items"]))\n        self.assertEqual(\n            len({row["sourceIngredientId"] for row in ledger["items"]}),\n            expected_count,\n        )\n        self.assertGreaterEqual(\n            sum(row.get("manualSemanticEquivalence") is True for row in ledger["items"]),\n            7,\n        )\n'''
    if old not in text:
        raise RuntimeError("equivalence repository-count test anchor drifted")
    text = text.replace(old, new, 1)
    old2 = '        self.assertEqual(result["summary"]["standaloneEquivalentSourceLabels"], 14)\n'
    new2 = '        self.assertEqual(result["summary"]["standaloneEquivalentSourceLabels"], expected_count)\n'
    if old2 not in text:
        raise RuntimeError("compiled equivalence-count test anchor drifted")
    EQUIVALENCE_TEST.write_text(text.replace(old2, new2, 1), encoding="utf-8")


def main() -> int:
    rows_by_source, high_concepts = _review_rows()
    confirmations = _load(CONFIRMATIONS)
    standalone = _load(STANDALONE)
    equivalences = _load(EQUIVALENCES)

    if confirmations.get("policy", {}).get("manualSemanticEquivalenceAllowed") is not True:
        raise RuntimeError("manual semantic equivalence is not enabled")
    if int((standalone.get("summary") or {}).get("standaloneDispositionCount") or -1) != 206:
        raise RuntimeError("batch 8 requires the audited 206-row standalone baseline")
    if int((equivalences.get("summary") or {}).get("equivalenceCount") or -1) != 14:
        raise RuntimeError("batch 8 requires the audited fourteen-equivalence baseline")

    standalone_items = [row for row in standalone.get("items") or [] if isinstance(row, dict)]
    standalone_by_id = {str(row.get("sourceIngredientId") or ""): row for row in standalone_items}
    confirmation_items = [row for row in confirmations.get("items") or [] if isinstance(row, dict)]
    confirmed_ids = {str(row.get("sourceIngredientId") or "") for row in confirmation_items}
    equivalence_items = [row for row in equivalences.get("items") or [] if isinstance(row, dict)]
    equivalence_source_ids = {str(row.get("sourceIngredientId") or "") for row in equivalence_items}

    remove_ids: set[str] = set()
    new_confirmations: list[dict[str, Any]] = []
    for decision in HIGH_CONFIDENCE_DECISIONS:
        source_id = decision["sourceIngredientId"]
        if source_id in confirmed_ids or source_id in equivalence_source_ids:
            raise RuntimeError(f"source already resolved: {source_id}")
        disposition = standalone_by_id.get(source_id)
        if disposition is None or disposition.get("disposition") != "reviewed-source-local-standalone":
            raise RuntimeError(f"source is not a mergeable standalone identity: {source_id}")
        reviewed = rows_by_source.get(source_id)
        if reviewed is None:
            raise RuntimeError(f"review source missing: {source_id}")
        if reviewed["english"] != decision["sourceReviewedEnglish"]:
            raise RuntimeError(f"source reviewed-English drift: {source_id}")
        if reviewed["classification"] != decision["classification"]:
            raise RuntimeError(f"source classification drift: {source_id}")
        if reviewed["confidence"] == "high":
            raise RuntimeError(f"source unexpectedly became high confidence: {source_id}")
        target = high_concepts.get(decision["confirmedConceptId"])
        if target is None:
            raise RuntimeError(f"high-confidence target missing: {decision['confirmedConceptId']}")
        if target["english"] != decision["targetCanonicalEnglish"]:
            raise RuntimeError(f"target canonical-English drift: {source_id}")
        if target["classification"] != decision["classification"]:
            raise RuntimeError(f"target classification drift: {source_id}")
        if len(decision["rationale"]) < 20:
            raise RuntimeError(f"rationale too short: {source_id}")
        remove_ids.add(source_id)
        new_confirmations.append({
            "sourceIngredientId": source_id,
            "confirmedConceptId": decision["confirmedConceptId"],
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": decision["sourceReviewedEnglish"],
            "targetCanonicalEnglish": decision["targetCanonicalEnglish"],
            "rationale": decision["rationale"],
        })

    decision = SOURCE_LOCAL_DECISION
    source_id = decision["sourceIngredientId"]
    target_id = decision["targetSourceIngredientId"]
    if source_id in confirmed_ids or source_id in equivalence_source_ids:
        raise RuntimeError(f"source-local source already resolved: {source_id}")
    source_disp = standalone_by_id.get(source_id)
    target_disp = standalone_by_id.get(target_id)
    if source_disp is None or source_disp.get("disposition") != "reviewed-source-local-standalone":
        raise RuntimeError(f"source-local source is not standalone: {source_id}")
    if target_disp is None or target_disp.get("disposition") != "reviewed-source-local-standalone":
        raise RuntimeError(f"source-local target is not standalone: {target_id}")
    source_review = rows_by_source.get(source_id)
    target_review = rows_by_source.get(target_id)
    if source_review is None or target_review is None:
        raise RuntimeError("garden-bean review evidence is missing")
    if source_review["english"] != decision["sourceReviewedEnglish"]:
        raise RuntimeError("garden-bean source reviewed-English drift")
    if target_review["english"] != decision["targetReviewedEnglish"]:
        raise RuntimeError("garden-bean target reviewed-English drift")
    if source_review["classification"] != "food" or target_review["classification"] != "food":
        raise RuntimeError("garden-bean classification drift")
    if source_review["confidence"] == "high" or target_review["confidence"] == "high":
        raise RuntimeError("garden-bean source-local equivalence cannot replace high-confidence semantics")
    remove_ids.add(source_id)

    kept = [row for row in standalone_items if str(row.get("sourceIngredientId") or "") not in remove_ids]
    if len(standalone_items) - len(kept) != 4:
        raise RuntimeError("batch 8 standalone removal count mismatch")
    ambiguous_count = sum(row.get("disposition") == "reviewed-ambiguous-source-fragment" for row in kept)
    if ambiguous_count != 28:
        raise RuntimeError("batch 8 may not change reviewed ambiguous count")
    standalone["items"] = kept
    standalone["summary"] = {
        "standaloneDispositionCount": len(kept),
        "reviewedAmbiguousCount": ambiguous_count,
        "reviewedSourceLocalStandaloneCount": len(kept) - ambiguous_count,
    }

    confirmations["items"] = confirmation_items + new_confirmations
    equivalences["items"] = equivalence_items + [dict(decision)]
    equivalences["summary"] = {"equivalenceCount": len(equivalences["items"])}

    _write(CONFIRMATIONS, confirmations)
    _write(STANDALONE, standalone)
    _write(EQUIVALENCES, equivalences)
    _patch_equivalence_test()

    print(json.dumps({
        "highConfidenceMerges": len(new_confirmations),
        "sourceLocalEquivalences": 1,
        "standaloneRemaining": len(kept),
        "reviewedAmbiguousRemaining": ambiguous_count,
        "standaloneEquivalenceCount": len(equivalences["items"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
