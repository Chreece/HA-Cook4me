#!/usr/bin/env python3
"""One-time deterministic patch for reviewed manual ingredient equivalences.

This helper edits the semantic compiler, the explicit confirmation ledger and the
repository regression test. It is intentionally temporary and is removed by the
workflow after all tests pass.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
TESTS = ROOT / "tests"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {text.count(old)}")
    return text.replace(old, new, 1)


def patch_compiler() -> None:
    path = TOOLS / "compile_release_catalog_semantics_v60.py"
    text = path.read_text(encoding="utf-8")

    function_start = text.index("def _exact_confirmation_map(")
    start = text.index(
        '        expected_concept = _semantic_concept_id(\n', function_start
    )
    end = text.index("    return out\n\n\ndef _safe_syntactic_english", start)
    replacement = '''        manual_equivalence = raw.get("manualSemanticEquivalence") is True
        target_row = high_concepts.get(concept_id)
        if target_row is None:
            raise RuntimeError(
                "semantic confirmation target lacks high-confidence evidence: "
                f"{concept_id}"
            )

        rationale = ""
        if manual_equivalence:
            if policy.get("manualSemanticEquivalenceAllowed") is not True:
                raise RuntimeError(
                    "manual semantic equivalence is not enabled by confirmation policy"
                )
            source_reviewed_english = _text(raw.get("sourceReviewedEnglish"))
            target_canonical_english = _text(raw.get("targetCanonicalEnglish"))
            rationale = _text(raw.get("rationale"))
            if source_reviewed_english != source_row["english"]:
                raise RuntimeError(
                    f"manual semantic equivalence sourceReviewedEnglish differs for {source_id}"
                )
            if target_canonical_english != target_row["english"]:
                raise RuntimeError(
                    f"manual semantic equivalence targetCanonicalEnglish differs for {source_id}"
                )
            if target_row["classification"] != source_row["classification"]:
                raise RuntimeError(
                    f"manual semantic equivalence classification differs for {source_id}"
                )
            if len(rationale) < 20:
                raise RuntimeError(
                    f"manual semantic equivalence rationale is too short for {source_id}"
                )
            method = "explicit-manual-semantic-equivalence"
        else:
            expected_concept = _semantic_concept_id(
                source_row["classification"], source_row["english"]
            )
            if concept_id != expected_concept:
                raise RuntimeError(
                    "semantic confirmation does not preserve exact reviewed "
                    f"English/classification for {source_id}: "
                    f"{concept_id} != {expected_concept}"
                )
            if (
                target_row["classification"] != source_row["classification"]
                or _norm(target_row["english"]) != _norm(source_row["english"])
            ):
                raise RuntimeError(
                    f"semantic confirmation target meaning differs for {source_id}"
                )
            method = "explicit-reviewed-english-classification"

        out[source_id] = {
            "confirmedConceptId": concept_id,
            "confirmationFile": confirmation_file or "<inline>",
            "confirmationMethod": method,
        }
        if rationale:
            out[source_id]["confirmationRationale"] = rationale
'''
    text = text[:start] + replacement + text[end:]

    text = replace_once(
        text,
        ") -> tuple[dict[str, dict[str, str]], int, int]:\n    exact = _exact_confirmation_map(",
        ") -> tuple[dict[str, dict[str, str]], int, int, int]:\n    exact = _exact_confirmation_map(",
        "confirmation-map signature",
    )
    text = replace_once(
        text,
        "    return {**exact, **syntactic}, len(exact), len(syntactic)\n",
        '''    equivalence_count = sum(
        row.get("confirmationMethod") == "explicit-manual-semantic-equivalence"
        for row in exact.values()
    )
    exact_count = len(exact) - equivalence_count
    return (
        {**exact, **syntactic},
        exact_count,
        equivalence_count,
        len(syntactic),
    )
''',
        "confirmation-map return",
    )
    text = replace_once(
        text,
        "    confirmations, exact_count, syntactic_count = _confirmation_map(\n",
        "    confirmations, exact_count, equivalence_count, syntactic_count = _confirmation_map(\n",
        "confirmation count assignment",
    )
    text = replace_once(
        text,
        '''        if confirmation is not None:
            identity["semanticConfirmationFile"] = confirmation[
                "confirmationFile"
            ]
            identity["semanticConfirmationMethod"] = confirmation[
                "confirmationMethod"
            ]
''',
        '''        if confirmation is not None:
            identity["semanticConfirmationFile"] = confirmation[
                "confirmationFile"
            ]
            identity["semanticConfirmationMethod"] = confirmation[
                "confirmationMethod"
            ]
            if rationale := confirmation.get("confirmationRationale"):
                identity["semanticConfirmationRationale"] = rationale
''',
        "confirmation identity annotation",
    )
    text = replace_once(
        text,
        '            "exactConfirmedSourceLabels": exact_count,\n            "syntacticConfirmedSourceLabels": syntactic_count,\n',
        '            "exactConfirmedSourceLabels": exact_count,\n            "semanticEquivalentConfirmedSourceLabels": equivalence_count,\n            "syntacticConfirmedSourceLabels": syntactic_count,\n',
        "confirmation summary",
    )
    path.write_text(text, encoding="utf-8")


def patch_confirmation_ledger() -> None:
    path = TOOLS / "release_catalog_semantic_confirmations.v1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["policy"]["manualSemanticEquivalenceAllowed"] = True
    additions = [
        {
            "sourceIngredientId": "local:ja:19b86c6fe08208b7291b",
            "confirmedConceptId": "concept:food:35f3eb4d93302e449378",
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": "A - Cream cheese (bring to room temperature)",
            "targetCanonicalEnglish": "A- cream cheese, brought to room temperature",
            "rationale": "Same cream-cheese ingredient and same room-temperature preparation; wording differs only in grammatical aspect.",
        },
        {
            "sourceIngredientId": "local:ja:273c360223e6802a6cac",
            "confirmedConceptId": "concept:food:35f3eb4d93302e449378",
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": "A - Cream cheese (bring to room temperature)",
            "targetCanonicalEnglish": "A- cream cheese, brought to room temperature",
            "rationale": "Same cream-cheese ingredient and same room-temperature preparation; wording differs only in grammatical aspect.",
        },
        {
            "sourceIngredientId": "local:uk:01545719973c1f64b25f",
            "confirmedConceptId": "concept:food:893dfa946d4f4c0212c2",
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": "g vinegar (not balsamic)",
            "targetCanonicalEnglish": "Vinegar (not balsamic)",
            "rationale": "The leading g is a captured unit fragment; both rows identify the same non-balsamic vinegar ingredient.",
        },
        {
            "sourceIngredientId": "local:uk:7fa976aed35498c38072",
            "confirmedConceptId": "concept:food:d32cf5542653f0205212",
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": "Candied lemons (without flesh, thinly sliced)",
            "targetCanonicalEnglish": "Candied lemon (without flesh, thinly sliced)",
            "rationale": "Singular versus plural wording does not change the candied-lemon ingredient or its preparation state.",
        },
        {
            "sourceIngredientId": "local:zh:d6a88d18c712517f6f4c",
            "confirmedConceptId": "concept:food:24b80a3cc9898f2fda64",
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": "Water (some for gelatin)",
            "targetCanonicalEnglish": "Water (for gelatin)",
            "rationale": "Some is quantity-allocation wording; both rows identify water reserved for the gelatin step.",
        },
        {
            "sourceIngredientId": "local:zh:bb2bd75d09cbf88a5720",
            "confirmedConceptId": "concept:food:bd8a4ba810181bebb7ac",
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": "Red pickled ginger (for seasoning), a little",
            "targetCanonicalEnglish": "Red pickled ginger, a little for finishing",
            "rationale": "Seasoning versus finishing describes recipe use, not a different red-pickled-ginger ingredient.",
        },
        {
            "sourceIngredientId": "local:ko:2cefa14e4084e3715a38",
            "confirmedConceptId": "concept:food:8d81eeb437fe51caa8ca",
            "manualSemanticEquivalence": True,
            "sourceReviewedEnglish": "Soy sauce (garnish/seasoning)",
            "targetCanonicalEnglish": "Soy sauce (seasoning)",
            "rationale": "Garnish or seasoning is usage metadata; both rows identify the same soy-sauce ingredient without a subtype change.",
        },
    ]
    by_id = {row["sourceIngredientId"]: row for row in doc["items"]}
    for row in additions:
        existing = by_id.get(row["sourceIngredientId"])
        if existing is not None and existing != row:
            raise RuntimeError(f"conflicting confirmation: {row['sourceIngredientId']}")
        if existing is None:
            doc["items"].append(row)
            by_id[row["sourceIngredientId"]] = row
    path.write_text(
        json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def patch_repository_test() -> None:
    path = TESTS / "test_compile_release_catalog_semantics_v60.py"
    text = path.read_text(encoding="utf-8")
    method_start = text.index(
        "def test_repository_confirmation_overlays_are_exact_and_lossless"
    )
    setup_start = text.index("        exact_items = json.loads(\n", method_start)
    setup_end = text.index("        paths = mod._review_paths(tools)\n", setup_start)
    setup = '''        confirmation_items = json.loads(
            exact_path.read_text(encoding="utf-8")
        )["items"]
        equivalence_items = [
            row for row in confirmation_items
            if row.get("manualSemanticEquivalence") is True
        ]
        exact_items = [
            row for row in confirmation_items
            if row.get("manualSemanticEquivalence") is not True
        ]
        syntax_ids = mod._load_syntax_confirmation_ids(syntax_path)
        self.assertEqual(len(exact_items), 115)
        self.assertEqual(len(equivalence_items), 7)
        self.assertTrue(syntax_ids)
        self.assertFalse(
            {row["sourceIngredientId"] for row in confirmation_items} & syntax_ids
        )

'''
    text = text[:setup_start] + setup + text[setup_end:]
    text = replace_once(
        text,
        "        total = len(exact_items) + len(syntax_ids)\n",
        "        total = len(confirmation_items) + len(syntax_ids)\n",
        "repository total",
    )
    syntactic = '''        self.assertEqual(
            confirmed["summary"]["syntacticConfirmedSourceLabels"],
            len(syntax_ids),
        )
'''
    insert_at = text.index(syntactic, method_start)
    equivalence = '''        self.assertEqual(
            confirmed["summary"]["semanticEquivalentConfirmedSourceLabels"],
            len(equivalence_items),
        )
'''
    text = text[:insert_at] + equivalence + text[insert_at:]
    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_compiler()
    patch_confirmation_ledger()
    patch_repository_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
