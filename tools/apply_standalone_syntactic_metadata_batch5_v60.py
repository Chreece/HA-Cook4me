#!/usr/bin/env python3
"""Apply the fifth reviewed standalone semantic consolidation batch.

The ten rows in this file were surfaced by the exact metadata-only audit.  Each
source becomes an existing high-confidence semantic concept only after removing
explicit review, quantity/unit, section, or recipe-use metadata.  This script is
intended to run inside a validation workflow; it fails closed on any evidence drift.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPILER = TOOLS / "compile_release_catalog_semantics_v60.py"
STANDALONE = TOOLS / "release_catalog_semantic_standalone_dispositions.v1.json"
SYNTAX_IDS = TOOLS / "release_catalog_semantic_syntactic_confirmation_ids.v1.txt"
TESTS = ROOT / "tests/test_compile_release_catalog_semantics_v60.py"

spec = importlib.util.spec_from_file_location("cook4me_semantic_batch5_prepatch", COMPILER)
semantics = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(semantics)

DECISIONS: tuple[dict[str, str], ...] = (
    {
        "sourceIngredientId": "local:zh:516aea39ea3a155c6b79",
        "sourceReviewedEnglish": "B- water (for dissolving)",
        "targetCanonicalEnglish": "Water",
        "confirmedConceptId": "concept:food:0d52d1d625702cd351e5",
        "rationale": "B- is a recipe section marker and '(for dissolving)' is a use note; the ingredient identity is water.",
    },
    {
        "sourceIngredientId": "local:ja:4d5f85f811c128c6380e",
        "sourceReviewedEnglish": "Boiling water (to pour over salted fish)",
        "targetCanonicalEnglish": "Boiling water",
        "confirmedConceptId": "concept:food:bac8418b188560c6ba21",
        "rationale": "The parenthetical describes how the boiling water is used, not a different ingredient identity.",
    },
    {
        "sourceIngredientId": "local:uk:2c3d0a62ada4b13a3301",
        "sourceReviewedEnglish": "Butter (abbreviated source)",
        "targetCanonicalEnglish": "Butter",
        "confirmedConceptId": "concept:food:fb6971460074a3bd24bb",
        "rationale": "The parenthetical is review provenance only; the reviewed ingredient is butter.",
    },
    {
        "sourceIngredientId": "local:uk:0412625f37d38cdcfafa",
        "sourceReviewedEnglish": "Cups of sugar",
        "targetCanonicalEnglish": "Sugar",
        "confirmedConceptId": "concept:food:5041c19f6cc463284711",
        "rationale": "The leading cup unit is recipe quantity metadata; the ingredient identity is sugar.",
    },
    {
        "sourceIngredientId": "local:uk:f6ac0b3ed12940d23691",
        "sourceReviewedEnglish": "One-third teaspoon turmeric",
        "targetCanonicalEnglish": "Turmeric",
        "confirmedConceptId": "concept:food:d5b0ca53da126004a2db",
        "rationale": "The leading fractional teaspoon is recipe quantity metadata; the ingredient identity is turmeric.",
    },
    {
        "sourceIngredientId": "local:uk:9c6dad61c60b81843b77",
        "sourceReviewedEnglish": "Tablespoon of fish sauce (quantity count omitted)",
        "targetCanonicalEnglish": "Fish sauce",
        "confirmedConceptId": "concept:food:683599e4a1211db6912e",
        "rationale": "The tablespoon wording and quantity-count annotation are measurement metadata only.",
    },
    {
        "sourceIngredientId": "local:uk:bddd5b8b09d366178570",
        "sourceReviewedEnglish": "Tablespoon of raisins (quantity count omitted)",
        "targetCanonicalEnglish": "Raisins",
        "confirmedConceptId": "concept:food:ba539cd025029e046848",
        "rationale": "The tablespoon wording and quantity-count annotation are measurement metadata only.",
    },
    {
        "sourceIngredientId": "local:uk:e6f29731f96983da1ef4",
        "sourceReviewedEnglish": "Tablespoon of sweetcorn (quantity count omitted)",
        "targetCanonicalEnglish": "Sweetcorn",
        "confirmedConceptId": "concept:food:d2ddfb7913094b5daaa5",
        "rationale": "The tablespoon wording and quantity-count annotation are measurement metadata only.",
    },
    {
        "sourceIngredientId": "local:uk:81070c37ad5a32e224b6",
        "sourceReviewedEnglish": "Tablespoon(s) of oil (quantity incomplete)",
        "targetCanonicalEnglish": "Oil",
        "confirmedConceptId": "concept:food:9c306f16717747ad897b",
        "rationale": "The tablespoon wording and incomplete-quantity annotation are measurement metadata only.",
    },
    {
        "sourceIngredientId": "local:uk:eb6599c5b45f0b514d0d",
        "sourceReviewedEnglish": "Teaspoon of cumin (quantity count omitted)",
        "targetCanonicalEnglish": "Cumin",
        "confirmedConceptId": "concept:food:68c6d8db30723fcf98cf",
        "rationale": "The teaspoon wording and quantity-count annotation are measurement metadata only.",
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


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one patch anchor, found {count}")
    return text.replace(old, new, 1)


def validate_and_update_ledgers() -> None:
    if len(DECISIONS) != 10:
        raise RuntimeError(f"expected ten decisions, got {len(DECISIONS)}")
    source_ids = [row["sourceIngredientId"] for row in DECISIONS]
    if len(set(source_ids)) != len(source_ids):
        raise RuntimeError("duplicate batch-5 source identity")

    paths = semantics._review_paths(TOOLS)
    payloads = [(path.name, semantics._load_payload(path)) for path in paths]
    review_rows = list(semantics.iter_review_rows(payloads))
    rows_by_source = semantics._rows_by_source_id(review_rows)
    high = semantics._high_confidence_concepts(review_rows)

    standalone = _load(STANDALONE)
    items = [row for row in standalone.get("items") or [] if isinstance(row, dict)]
    summary = standalone.get("summary") or {}
    if int(summary.get("standaloneDispositionCount") or -1) != 221:
        raise RuntimeError("batch 5 requires the promoted 221-row standalone baseline")
    if int(summary.get("reviewedAmbiguousCount") or -1) != 28:
        raise RuntimeError("batch 5 requires the preserved 28 ambiguous rows")
    by_id = {str(row.get("sourceIngredientId") or ""): row for row in items}

    syntax_lines = SYNTAX_IDS.read_text(encoding="utf-8").splitlines()
    existing_syntax = {
        line.strip() for line in syntax_lines
        if line.strip() and not line.lstrip().startswith("#")
    }

    for decision in DECISIONS:
        source_id = decision["sourceIngredientId"]
        disposition = by_id.get(source_id)
        if disposition is None:
            raise RuntimeError(f"batch-5 source is no longer standalone: {source_id}")
        if disposition.get("disposition") != "reviewed-source-local-standalone":
            raise RuntimeError(f"batch-5 source is not mergeable standalone: {source_id}")
        reviewed = rows_by_source.get(source_id)
        if reviewed is None:
            raise RuntimeError(f"batch-5 source lacks reviewed evidence: {source_id}")
        if reviewed["english"] != decision["sourceReviewedEnglish"]:
            raise RuntimeError(f"batch-5 source English drift: {source_id}")
        if disposition.get("sourceReviewedEnglish") != decision["sourceReviewedEnglish"]:
            raise RuntimeError(f"batch-5 standalone English receipt drift: {source_id}")
        if reviewed["classification"] != "food":
            raise RuntimeError(f"batch-5 classification drift: {source_id}")
        if reviewed["confidence"] == "high":
            raise RuntimeError(f"batch-5 source unexpectedly high confidence: {source_id}")
        target = high.get(decision["confirmedConceptId"])
        if target is None:
            raise RuntimeError(f"batch-5 high-confidence target disappeared: {source_id}")
        if target["classification"] != "food":
            raise RuntimeError(f"batch-5 target classification drift: {source_id}")
        if target["english"] != decision["targetCanonicalEnglish"]:
            raise RuntimeError(f"batch-5 target English drift: {source_id}")
        if source_id in existing_syntax:
            raise RuntimeError(f"batch-5 source already syntax-confirmed: {source_id}")
        if len(decision["rationale"].strip()) < 20:
            raise RuntimeError(f"batch-5 rationale too short: {source_id}")

    remove = set(source_ids)
    kept = [row for row in items if row.get("sourceIngredientId") not in remove]
    if len(items) - len(kept) != len(DECISIONS):
        raise RuntimeError("batch-5 standalone removal count mismatch")
    ambiguous = sum(
        row.get("disposition") == "reviewed-ambiguous-source-fragment" for row in kept
    )
    standalone["items"] = kept
    standalone["summary"] = {
        "standaloneDispositionCount": len(kept),
        "reviewedAmbiguousCount": ambiguous,
        "reviewedSourceLocalStandaloneCount": len(kept) - ambiguous,
    }
    _write(STANDALONE, standalone)

    extra = [
        "# Exact reviewed metadata/unit/use-note normalizations (batch 5).",
        *source_ids,
    ]
    SYNTAX_IDS.write_text(
        "\n".join(syntax_lines + extra).rstrip() + "\n",
        encoding="utf-8",
    )


def patch_compiler() -> None:
    text = COMPILER.read_text(encoding="utf-8")
    old_patterns = '''_QUALIFIED_QUANTITY_ANNOTATION = re.compile(
    r"\\s*\\(([^()]*)\\s*;\\s*quantity fragment:\\s*[^()]+\\)\\s*$",
    re.IGNORECASE,
)
'''
    new_patterns = old_patterns + '''_QUANTITY_COUNT_OMITTED = re.compile(
    r"\\s*\\(quantity count omitted\\)\\s*$",
    re.IGNORECASE,
)
_QUANTITY_INCOMPLETE = re.compile(
    r"\\s*\\(quantity incomplete\\)\\s*$",
    re.IGNORECASE,
)
_ABBREVIATED_SOURCE = re.compile(
    r"\\s*\\(abbreviated source\\)\\s*$",
    re.IGNORECASE,
)
_RECIPE_USE_PAREN = re.compile(
    r"\\s*\\((?:to|for)\\s+[^()]+\\)\\s*$",
    re.IGNORECASE,
)
_MEASUREMENT_PREFIX = re.compile(
    r"^(?:(?:tablespoon\\(s\\)|tablespoons?|teaspoons?|cups?)\\s+of\\s+"
    r"|(?:one[- ]third|one[- ]half|half)\\s+teaspoons?\\s+"
    r"|(?:tbsp|tsp|g)\\s+|dl\\s+(?:of\\s+)?)",
    re.IGNORECASE,
)
'''
    text = _replace_once(text, old_patterns, new_patterns, "batch-5 regex declarations")

    old_tail = '''        match = _QUALIFIED_QUANTITY_ANNOTATION.search(text)
        if match:
            qualifier = _text(match.group(1))
            if qualifier:
                text = (
                    text[: match.start()]
                    + f" ({qualifier})"
                    + text[match.end() :]
                ).strip()
        if text == before:
            return text
'''
    new_tail = '''        match = _QUALIFIED_QUANTITY_ANNOTATION.search(text)
        if match:
            qualifier = _text(match.group(1))
            if qualifier:
                text = (
                    text[: match.start()]
                    + f" ({qualifier})"
                    + text[match.end() :]
                ).strip()
        text = _QUANTITY_COUNT_OMITTED.sub("", text, count=1).strip()
        text = _QUANTITY_INCOMPLETE.sub("", text, count=1).strip()
        text = _ABBREVIATED_SOURCE.sub("", text, count=1).strip()
        text = _RECIPE_USE_PAREN.sub("", text, count=1).strip()
        text = _MEASUREMENT_PREFIX.sub("", text, count=1).strip()
        if text == before:
            return text
'''
    text = _replace_once(text, old_tail, new_tail, "batch-5 syntactic normalization")
    COMPILER.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    text = TESTS.read_text(encoding="utf-8")
    anchor = '''    def test_unwhitelisted_syntax_equivalent_row_remains_pending(self):
'''
    addition = '''    def test_whitelisted_measurement_and_review_metadata_are_syntax_only(self):
        cases = (
            ("B- water (for dissolving)", "Water"),
            ("Boiling water (to pour over salted fish)", "Boiling water"),
            ("Butter (abbreviated source)", "Butter"),
            ("Cups of sugar", "Sugar"),
            ("One-third teaspoon turmeric", "Turmeric"),
            ("Tablespoon of fish sauce (quantity count omitted)", "Fish sauce"),
            ("Tablespoon of raisins (quantity count omitted)", "Raisins"),
            ("Tablespoon of sweetcorn (quantity count omitted)", "Sweetcorn"),
            ("Tablespoon(s) of oil (quantity incomplete)", "Oil"),
            ("Teaspoon of cumin (quantity count omitted)", "Cumin"),
        )
        for source, target in cases:
            with self.subTest(source=source):
                self._assert_syntax_merge(source, target)

    def test_new_syntax_rules_do_not_erase_semantic_parentheticals(self):
        value = "Vegetable stock (or salted water; source grammar)"
        self.assertEqual(mod._safe_syntactic_english(value), value)
        self.assertEqual(
            mod._safe_syntactic_english("Red chili paste (to taste)"),
            "Red chili paste (to taste)",
        )

'''
    text = _replace_once(text, anchor, addition + anchor, "batch-5 regression insertion")
    TESTS.write_text(text, encoding="utf-8")


def main() -> int:
    validate_and_update_ledgers()
    patch_compiler()
    patch_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
