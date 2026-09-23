#!/usr/bin/env python3
# Apply manually reviewed conservative standalone semantic equivalences.
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPILER = TOOLS / "compile_release_catalog_semantics_v60.py"
STANDALONE = TOOLS / "release_catalog_semantic_standalone_dispositions.v1.json"
EQUIVALENCE = TOOLS / "release_catalog_semantic_standalone_equivalences.v1.json"
EXISTING_TEST = ROOT / "tests/test_semantic_standalone_equivalences_v60.py"
MANUAL_TEST = ROOT / "tests/test_semantic_standalone_manual_equivalences_v60.py"

spec = importlib.util.spec_from_file_location("cook4me_semantic_manual_pair_patch", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

DECISIONS: tuple[dict[str, Any], ...] = (
    {
        "sourceIngredientId": "local:zh:dc6d1a6f069d72ddad39",
        "targetSourceIngredientId": "local:zh:ba67d7ea43050822ef30",
        "sourceReviewedEnglish": "A- wine, a little",
        "targetReviewedEnglish": "Wine, a little",
        "classification": "food",
        "manualSemanticEquivalence": True,
        "rationale": "The A- prefix is a retained recipe section marker; both reviewed rows identify wine with the same 'a little' quantity wording.",
    },
    {
        "sourceIngredientId": "local:cs:7df0975cb3557279b7cd",
        "targetSourceIngredientId": "local:cs:8458fb91ef71ff7fc1c1",
        "sourceReviewedEnglish": "French quenelles, 40–50 g",
        "targetReviewedEnglish": "French quenelles",
        "classification": "food",
        "manualSemanticEquivalence": True,
        "rationale": "The 40–50 g suffix is recipe quantity information only; the reviewed ingredient identity remains French quenelles.",
    },
    {
        "sourceIngredientId": "local:sk:e39d11d4894094361f03",
        "targetSourceIngredientId": "local:cs:8458fb91ef71ff7fc1c1",
        "sourceReviewedEnglish": "French quenelles, 40–50 g each",
        "targetReviewedEnglish": "French quenelles",
        "classification": "food",
        "manualSemanticEquivalence": True,
        "rationale": "The 40–50 g each suffix is recipe portion information only; the reviewed ingredient identity remains French quenelles.",
    },
    {
        "sourceIngredientId": "local:pl:67acf23faa729a5952d4",
        "targetSourceIngredientId": "local:uk:dcc8266cdaf0930a8d48",
        "sourceReviewedEnglish": "From half a lemon",
        "targetReviewedEnglish": "Half a lemon",
        "classification": "food",
        "manualSemanticEquivalence": True,
        "rationale": "The word 'From' is recipe phrasing rather than ingredient identity; both reviewed rows mean half a lemon.",
    },
    {
        "sourceIngredientId": "local:uk:3c01d6862bcbee36cdc3",
        "targetSourceIngredientId": "local:uk:a4793fd664513e218d6b",
        "sourceReviewedEnglish": "tbsp anise liqueur",
        "targetReviewedEnglish": "Anise liqueur",
        "classification": "food",
        "manualSemanticEquivalence": True,
        "rationale": "The tablespoon token is recipe measurement metadata only; both reviewed rows identify anise liqueur.",
    },
    {
        "sourceIngredientId": "local:uk:0732f97da52e6ec4e078",
        "targetSourceIngredientId": "local:uk:3a54c3b6158ad1e7b926",
        "sourceReviewedEnglish": "Tablespoon of fresh parsley, washed and chopped (quantity count omitted; source grammar)",
        "targetReviewedEnglish": "Tablespoon of fresh parsley, washed and chopped (quantity count omitted)",
        "classification": "food",
        "manualSemanticEquivalence": True,
        "rationale": "The only semantic difference is the explicit source-grammar review annotation; ingredient, preparation and quantity status are identical.",
    },
    {
        "sourceIngredientId": "local:hu:3e566431544bdd01d940",
        "targetSourceIngredientId": "local:cs:530b2df02321cfee5427",
        "sourceReviewedEnglish": "Nems sauce",
        "targetReviewedEnglish": "Nem sauce",
        "classification": "food",
        "manualSemanticEquivalence": True,
        "rationale": "Nems/Nem is the reviewed naming variant for the same sauce; this merges only conservative source-local concept identity.",
    },
)

NEW_POLICY = {
    "providerIdentityAssigned": False,
    "sourceLocalIdentityPreserved": True,
    "targetRemainsStandalone": True,
    "reviewedEnglishAndClassificationPinned": True,
    "nonExactRequiresManualSemanticEquivalence": True,
    "targetMayHaveMultipleEquivalentSources": True,
    "manualReviewRequired": True,
    "safetyEligibilityGranted": False,
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


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def _review_rows() -> dict[str, dict[str, Any]]:
    payloads = [(path.name, mod._load_payload(path)) for path in mod._review_paths(TOOLS)]
    return mod._rows_by_source_id(list(mod.iter_review_rows(payloads)))


def validate_and_update_ledgers() -> None:
    if len(DECISIONS) != 7:
        raise RuntimeError(f"expected seven reviewed decisions, got {len(DECISIONS)}")
    source_ids = [row["sourceIngredientId"] for row in DECISIONS]
    if len(set(source_ids)) != len(source_ids):
        raise RuntimeError("duplicate source identity in manual equivalence batch")

    rows = _review_rows()
    standalone = _load(STANDALONE)
    equivalence = _load(EQUIVALENCE)

    if int((standalone.get("summary") or {}).get("standaloneDispositionCount") or -1) != 228:
        raise RuntimeError("manual equivalence batch requires the promoted 228-row standalone baseline")
    if int((equivalence.get("summary") or {}).get("equivalenceCount") or -1) != 7:
        raise RuntimeError("manual equivalence batch requires the promoted seven-pair baseline")

    standalone_items = [row for row in standalone.get("items") or [] if isinstance(row, dict)]
    standalone_by_id = {str(row.get("sourceIngredientId") or ""): row for row in standalone_items}
    existing_items = [row for row in equivalence.get("items") or [] if isinstance(row, dict)]
    existing_sources = {str(row.get("sourceIngredientId") or "") for row in existing_items}

    for decision in DECISIONS:
        source_id = decision["sourceIngredientId"]
        target_id = decision["targetSourceIngredientId"]
        if source_id in existing_sources:
            raise RuntimeError(f"source already has standalone equivalence: {source_id}")
        source_standalone = standalone_by_id.get(source_id)
        target_standalone = standalone_by_id.get(target_id)
        if source_standalone is None:
            raise RuntimeError(f"source is no longer standalone: {source_id}")
        if target_standalone is None:
            raise RuntimeError(f"target is no longer standalone: {target_id}")
        if source_standalone.get("disposition") != "reviewed-source-local-standalone":
            raise RuntimeError(f"source is not a mergeable standalone identity: {source_id}")
        if target_standalone.get("disposition") != "reviewed-source-local-standalone":
            raise RuntimeError(f"target is not a conservative standalone identity: {target_id}")

        source_row = rows.get(source_id)
        target_row = rows.get(target_id)
        if source_row is None or target_row is None:
            raise RuntimeError(f"review evidence missing: {source_id} -> {target_id}")
        if source_row["english"] != decision["sourceReviewedEnglish"]:
            raise RuntimeError(f"source reviewed English drift: {source_id}")
        if target_row["english"] != decision["targetReviewedEnglish"]:
            raise RuntimeError(f"target reviewed English drift: {target_id}")
        if source_row["classification"] != decision["classification"]:
            raise RuntimeError(f"source classification drift: {source_id}")
        if target_row["classification"] != decision["classification"]:
            raise RuntimeError(f"target classification drift: {target_id}")
        if source_row["confidence"] == "high" or target_row["confidence"] == "high":
            raise RuntimeError(
                f"manual source-local equivalence cannot replace high-confidence semantics: {source_id} -> {target_id}"
            )
        if decision.get("manualSemanticEquivalence") is not True:
            raise RuntimeError(f"non-exact decision lacks manual flag: {source_id}")
        if len(str(decision.get("rationale") or "").strip()) < 20:
            raise RuntimeError(f"decision rationale too short: {source_id}")

    decision_sources = set(source_ids)
    kept_items = [
        row
        for row in standalone_items
        if str(row.get("sourceIngredientId") or "") not in decision_sources
    ]
    if len(standalone_items) - len(kept_items) != len(DECISIONS):
        raise RuntimeError("standalone source removal count mismatch")

    standalone["items"] = kept_items
    ambiguous_count = sum(
        row.get("disposition") == "reviewed-ambiguous-source-fragment"
        for row in kept_items
    )
    standalone["summary"] = {
        "standaloneDispositionCount": len(kept_items),
        "reviewedAmbiguousCount": ambiguous_count,
        "reviewedSourceLocalStandaloneCount": len(kept_items) - ambiguous_count,
    }

    equivalence["policy"] = NEW_POLICY
    equivalence["items"] = existing_items + [dict(row) for row in DECISIONS]
    equivalence["summary"] = {"equivalenceCount": len(equivalence["items"])}

    _write(STANDALONE, standalone)
    _write(EQUIVALENCE, equivalence)


def patch_compiler() -> None:
    text = COMPILER.read_text(encoding="utf-8")

    old_policy = '''_STANDALONE_EQUIVALENCE_POLICY = {
    "providerIdentityAssigned": False,
    "sourceLocalIdentityPreserved": True,
    "targetRemainsStandalone": True,
    "exactReviewedEnglishAndClassificationRequired": True,
    "manualReviewRequired": True,
    "safetyEligibilityGranted": False,
}
'''
    new_policy = '''_STANDALONE_EQUIVALENCE_POLICY = {
    "providerIdentityAssigned": False,
    "sourceLocalIdentityPreserved": True,
    "targetRemainsStandalone": True,
    "reviewedEnglishAndClassificationPinned": True,
    "nonExactRequiresManualSemanticEquivalence": True,
    "targetMayHaveMultipleEquivalentSources": True,
    "manualReviewRequired": True,
    "safetyEligibilityGranted": False,
}
'''
    text = _replace_once(text, old_policy, new_policy, "standalone equivalence policy")

    old_pair_loop = '''    rows_by_source_id = _rows_by_source_id(review_rows)
    out: dict[str, dict[str, str]] = {}
    used_ids: set[str] = set()
    for index, raw in enumerate(items, 1):
        if not isinstance(raw, dict):
            raise RuntimeError(f"standalone equivalence item {index}: expected object")
        source_id = _text(raw.get("sourceIngredientId"))
        target_id = _text(raw.get("targetSourceIngredientId"))
        if (
            not source_id.startswith("local:")
            or not target_id.startswith("local:")
            or source_id == target_id
        ):
            raise RuntimeError(f"standalone equivalence item {index}: invalid source/target identity")
        if source_id in used_ids or target_id in used_ids:
            raise RuntimeError(
                "standalone equivalence identities must form disjoint reviewed pairs: "
                f"{source_id} -> {target_id}"
            )
        used_ids.update((source_id, target_id))
        if source_id in standalone:
'''
    new_pair_loop = '''    rows_by_source_id = _rows_by_source_id(review_rows)
    out: dict[str, dict[str, str]] = {}
    source_ids: set[str] = set()
    parsed_items: list[tuple[int, dict[str, Any], str, str]] = []
    for index, raw in enumerate(items, 1):
        if not isinstance(raw, dict):
            raise RuntimeError(f"standalone equivalence item {index}: expected object")
        source_id = _text(raw.get("sourceIngredientId"))
        target_id = _text(raw.get("targetSourceIngredientId"))
        if (
            not source_id.startswith("local:")
            or not target_id.startswith("local:")
            or source_id == target_id
        ):
            raise RuntimeError(f"standalone equivalence item {index}: invalid source/target identity")
        if source_id in source_ids:
            raise RuntimeError(
                f"duplicate standalone equivalence source identity: {source_id}"
            )
        source_ids.add(source_id)
        parsed_items.append((index, raw, source_id, target_id))

    target_ids = {target_id for _, _, _, target_id in parsed_items}
    chained_ids = source_ids & target_ids
    if chained_ids:
        raise RuntimeError(
            "standalone equivalence chains/cycles are forbidden; targets must remain roots: "
            + ", ".join(sorted(chained_ids))
        )

    for index, raw, source_id, target_id in parsed_items:
        if source_id in standalone:
'''
    text = _replace_once(text, old_pair_loop, new_pair_loop, "fan-in equivalence loop")

    old_meaning_guard = '''        if _norm(source_english) != _norm(target_english):
            raise RuntimeError(
                f"standalone equivalence reviewed meanings differ: {source_id} -> {target_id}"
            )
        rationale = _text(raw.get("rationale"))
'''
    new_meaning_guard = '''        manual_value = raw.get("manualSemanticEquivalence")
        if manual_value not in (None, False, True):
            raise RuntimeError(
                f"standalone equivalence manualSemanticEquivalence must be boolean: {source_id}"
            )
        manual_equivalence = manual_value is True
        exact_reviewed_english = _norm(source_english) == _norm(target_english)
        if not exact_reviewed_english and not manual_equivalence:
            raise RuntimeError(
                "standalone equivalence non-exact reviewed meanings require "
                f"manualSemanticEquivalence=true: {source_id} -> {target_id}"
            )
        rationale = _text(raw.get("rationale"))
'''
    text = _replace_once(text, old_meaning_guard, new_meaning_guard, "manual equivalence guard")

    old_out = '''            "equivalenceFile": equivalence_file or "<inline-standalone-equivalence>",
            "rationale": rationale,
        }
'''
    new_out = '''            "equivalenceFile": equivalence_file or "<inline-standalone-equivalence>",
            "equivalenceMethod": (
                "explicit-manual-source-local-equivalence"
                if manual_equivalence
                else "exact-reviewed-source-local-equivalence"
            ),
            "rationale": rationale,
        }
'''
    text = _replace_once(text, old_out, new_out, "equivalence method receipt")

    old_identity = '''            identity["semanticStandaloneEquivalenceTargetSourceIngredientId"] = (
                standalone_equivalence["targetSourceIngredientId"]
            )
            identity["semanticStandaloneEquivalenceRationale"] = standalone_equivalence[
                "rationale"
            ]
'''
    new_identity = '''            identity["semanticStandaloneEquivalenceTargetSourceIngredientId"] = (
                standalone_equivalence["targetSourceIngredientId"]
            )
            identity["semanticStandaloneEquivalenceMethod"] = standalone_equivalence[
                "equivalenceMethod"
            ]
            identity["semanticStandaloneEquivalenceRationale"] = standalone_equivalence[
                "rationale"
            ]
'''
    text = _replace_once(text, old_identity, new_identity, "identity equivalence method")

    old_policy_output = '''            "explicitStandaloneSemanticEquivalence": True,
            "standaloneReviewClosureGrantsSafetyEligibility": False,
'''
    new_policy_output = '''            "explicitStandaloneSemanticEquivalence": True,
            "manualStandaloneSemanticEquivalence": True,
            "standaloneSemanticEquivalenceTargetFanIn": True,
            "standaloneReviewClosureGrantsSafetyEligibility": False,
'''
    text = _replace_once(text, old_policy_output, new_policy_output, "compiled identity policy")

    old_help = '''            "Optional exact reviewed source-local equivalence JSON. When omitted, "
'''
    new_help = '''            "Optional manually reviewed source-local equivalence JSON. When omitted, "
'''
    if old_help in text:
        text = _replace_once(text, old_help, new_help, "CLI help")

    COMPILER.write_text(text, encoding="utf-8")


def patch_existing_tests() -> None:
    text = EXISTING_TEST.read_text(encoding="utf-8")
    old_policy = '''                "targetRemainsStandalone": True,
                "exactReviewedEnglishAndClassificationRequired": True,
                "manualReviewRequired": True,
                "safetyEligibilityGranted": False,
'''
    new_policy = '''                "targetRemainsStandalone": True,
                "reviewedEnglishAndClassificationPinned": True,
                "nonExactRequiresManualSemanticEquivalence": True,
                "targetMayHaveMultipleEquivalentSources": True,
                "manualReviewRequired": True,
                "safetyEligibilityGranted": False,
'''
    text = _replace_once(text, old_policy, new_policy, "test equivalence policy")
    text = _replace_once(
        text,
        "    def test_repository_equivalence_ledger_is_exact_and_fail_closed(self):\n",
        "    def test_repository_equivalence_ledger_is_reviewed_and_fail_closed(self):\n",
        "repository test name",
    )
    text = _replace_once(
        text,
        '''        self.assertEqual(ledger["summary"]["equivalenceCount"], 7)
        self.assertEqual(len(ledger["items"]), 7)
        self.assertEqual(
            len({row["sourceIngredientId"] for row in ledger["items"]}), 7
        )
''',
        '''        self.assertEqual(ledger["summary"]["equivalenceCount"], 14)
        self.assertEqual(len(ledger["items"]), 14)
        self.assertEqual(
            len({row["sourceIngredientId"] for row in ledger["items"]}), 14
        )
        self.assertEqual(
            sum(row.get("manualSemanticEquivalence") is True for row in ledger["items"]),
            7,
        )
''',
        "repository equivalence count",
    )
    text = _replace_once(
        text,
        '        self.assertEqual(result["summary"]["standaloneEquivalentSourceLabels"], 7)\n',
        '        self.assertEqual(result["summary"]["standaloneEquivalentSourceLabels"], 14)\n',
        "repository compiled equivalence count",
    )
    EXISTING_TEST.write_text(text, encoding="utf-8")


def write_manual_tests() -> None:
    content = r'''from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location(
    "cook4me_semantic_manual_equivalence_test", MODULE
)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

POLICY = {
    "providerIdentityAssigned": False,
    "sourceLocalIdentityPreserved": True,
    "targetRemainsStandalone": True,
    "reviewedEnglishAndClassificationPinned": True,
    "nonExactRequiresManualSemanticEquivalence": True,
    "targetMayHaveMultipleEquivalentSources": True,
    "manualReviewRequired": True,
    "safetyEligibilityGranted": False,
}


class ManualStandaloneSemanticEquivalenceTests(unittest.TestCase):
    def _reviews(self):
        return [
            (
                "batch.json",
                {
                    "schemaVersion": 1,
                    "kind": "cook4me-reviewed-keyless-ingredient-semantics",
                    "items": [
                        {
                            "language": "en",
                            "source": "Anise liqueur",
                            "english": "Anise liqueur",
                            "classification": "food",
                            "confidence": "medium",
                        },
                        {
                            "language": "uk",
                            "source": "tbsp anise liqueur",
                            "english": "tbsp anise liqueur",
                            "classification": "food",
                            "confidence": "medium",
                        },
                        {
                            "language": "pl",
                            "source": "From anise liqueur",
                            "english": "From anise liqueur",
                            "classification": "food",
                            "confidence": "medium",
                        },
                    ],
                },
            )
        ]

    def _ids(self):
        target = mod.source_local_ingredient_id("en", "Anise liqueur")
        first = mod.source_local_ingredient_id("uk", "tbsp anise liqueur")
        second = mod.source_local_ingredient_id("pl", "From anise liqueur")
        return target, first, second

    def _standalone(self, target_id):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-semantic-ingredient-standalone-dispositions",
            "policy": {
                "providerIdentityAssigned": False,
                "sourceLocalIdentityPreserved": True,
                "crossIdentityMergeAllowed": False,
                "reviewDispositionOnly": True,
                "exactReviewedEnglishAndClassificationRequired": True,
                "safetyEligibilityGranted": False,
            },
            "items": [
                {
                    "sourceIngredientId": target_id,
                    "sourceReviewedEnglish": "Anise liqueur",
                    "classification": "food",
                    "disposition": "reviewed-source-local-standalone",
                    "rationale": "Keep the reviewed target as a conservative standalone concept for manual source-local equivalence tests.",
                }
            ],
        }

    def _equivalence(self, items):
        return {
            "schemaVersion": 1,
            "kind": "cook4me-semantic-ingredient-standalone-equivalences",
            "policy": POLICY,
            "summary": {"equivalenceCount": len(items)},
            "items": items,
        }

    def _row(self, source_id, source_english, target_id, *, manual=True):
        row = {
            "sourceIngredientId": source_id,
            "targetSourceIngredientId": target_id,
            "sourceReviewedEnglish": source_english,
            "targetReviewedEnglish": "Anise liqueur",
            "classification": "food",
            "rationale": "Manual review confirms that the extra wording is recipe metadata and the source-local ingredient meaning is unchanged.",
        }
        if manual is not None:
            row["manualSemanticEquivalence"] = manual
        return row

    def test_non_exact_equivalence_requires_explicit_manual_flag(self):
        target, first, _ = self._ids()
        with self.assertRaisesRegex(RuntimeError, "manualSemanticEquivalence=true"):
            mod.compile_semantic_concepts(
                self._reviews(),
                standalone_payload=self._standalone(target),
                standalone_equivalence_payload=self._equivalence(
                    [self._row(first, "tbsp anise liqueur", target, manual=None)]
                ),
            )

    def test_manual_non_exact_equivalence_stays_conservative(self):
        target, first, _ = self._ids()
        result = mod.compile_semantic_concepts(
            self._reviews(),
            standalone_payload=self._standalone(target),
            standalone_equivalence_payload=self._equivalence(
                [self._row(first, "tbsp anise liqueur", target)]
            ),
            standalone_equivalence_file="manual.json",
        )
        self.assertEqual(
            result["sourceIdentityToConcept"][first],
            result["sourceIdentityToConcept"][target],
        )
        concept = next(
            row for row in result["concepts"]
            if row["conceptId"] == result["sourceIdentityToConcept"][target]
        )
        self.assertTrue(concept["conceptId"].startswith("concept:source:"))
        self.assertFalse(concept["nutritionEligible"])
        self.assertFalse(concept["dietEligible"])
        self.assertFalse(concept["allergenEligible"])
        identity = next(
            row for row in concept["sourceIdentities"]
            if row["ingredientId"] == first
        )
        self.assertEqual(
            identity["semanticStandaloneEquivalenceMethod"],
            "explicit-manual-source-local-equivalence",
        )

    def test_multiple_sources_may_share_one_standalone_root(self):
        target, first, second = self._ids()
        result = mod.compile_semantic_concepts(
            self._reviews(),
            standalone_payload=self._standalone(target),
            standalone_equivalence_payload=self._equivalence(
                [
                    self._row(first, "tbsp anise liqueur", target),
                    self._row(second, "From anise liqueur", target),
                ]
            ),
        )
        concept_id = result["sourceIdentityToConcept"][target]
        self.assertEqual(result["sourceIdentityToConcept"][first], concept_id)
        self.assertEqual(result["sourceIdentityToConcept"][second], concept_id)
        self.assertEqual(result["summary"]["standaloneEquivalentSourceLabels"], 2)

    def test_equivalence_chain_is_rejected(self):
        target, first, second = self._ids()
        rows = [
            self._row(first, "tbsp anise liqueur", target),
            {
                **self._row(second, "From anise liqueur", first),
                "targetReviewedEnglish": "tbsp anise liqueur",
            },
        ]
        with self.assertRaisesRegex(RuntimeError, "chains/cycles"):
            mod.compile_semantic_concepts(
                self._reviews(),
                standalone_payload=self._standalone(target),
                standalone_equivalence_payload=self._equivalence(rows),
            )


if __name__ == "__main__":
    unittest.main()
'''
    MANUAL_TEST.write_text(content, encoding="utf-8")


def main() -> int:
    validate_and_update_ledgers()
    patch_compiler()
    patch_existing_tests()
    write_manual_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
