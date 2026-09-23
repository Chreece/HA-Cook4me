#!/usr/bin/env python3
"""Audit high-confidence reviewed ingredient concepts for syntax-only duplication.

This is report-only. It never changes provider identity, semantic mappings, or
review ledgers. It reuses the compiler's conservative syntactic normalizer to
surface groups where two or more *high-confidence* reviewed concepts differ only
by already-recognized recipe metadata such as A/B/C section prefixes,
measurement/count text, source-review annotations, or recipe-use notes.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPILER = TOOLS / "compile_release_catalog_semantics_v60.py"

spec = importlib.util.spec_from_file_location("cook4me_semantic_syntax_audit", COMPILER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def _review_rows(review_root: Path) -> list[dict[str, Any]]:
    paths = mod._review_paths(review_root)
    payloads = [(path.name, mod._load_payload(path)) for path in paths]
    return list(mod.iter_review_rows(payloads))


def build_audit(review_root: Path) -> dict[str, Any]:
    rows = _review_rows(review_root)
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        if row.get("confidence") != "high":
            continue
        classification = str(row.get("classification") or "")
        if classification not in mod._MERGEABLE_CLASSIFICATIONS:
            continue
        english = str(row.get("english") or "")
        safe = mod._safe_syntactic_english(english)
        key = (classification, mod._norm(safe))
        groups[key].append(
            {
                "language": row["language"],
                "source": row["source"],
                "english": english,
                "safeEnglish": safe,
                "classification": classification,
                "reviewFile": row["reviewFile"],
                "sourceIngredientId": mod.source_local_ingredient_id(
                    row["language"], row["source"]
                ),
                "semanticConceptId": mod._semantic_concept_id(
                    classification, english
                ),
                "syntaxChanged": mod._norm(english) != mod._norm(safe),
            }
        )

    candidates: list[dict[str, Any]] = []
    for (classification, safe_key), members in groups.items():
        concept_ids = sorted({row["semanticConceptId"] for row in members})
        english_values = sorted({row["english"] for row in members}, key=mod._norm)
        if len(concept_ids) < 2:
            continue
        if not any(row["syntaxChanged"] for row in members):
            continue

        clean_members = [
            row for row in members
            if mod._norm(row["english"]) == mod._norm(row["safeEnglish"])
        ]
        candidates.append(
            {
                "classification": classification,
                "safeEnglish": min(
                    (row["safeEnglish"] for row in members),
                    key=lambda value: (len(value), mod._norm(value)),
                ),
                "safeKey": safe_key,
                "semanticConceptCount": len(concept_ids),
                "sourceIdentityCount": len(members),
                "distinctReviewedEnglish": english_values,
                "hasCleanCanonicalMember": bool(clean_members),
                "cleanCanonicalConceptIds": sorted(
                    {row["semanticConceptId"] for row in clean_members}
                ),
                "members": sorted(
                    members,
                    key=lambda row: (
                        row["syntaxChanged"],
                        mod._norm(row["english"]),
                        row["language"],
                        row["sourceIngredientId"],
                    ),
                ),
            }
        )

    candidates.sort(
        key=lambda row: (
            not row["hasCleanCanonicalMember"],
            -row["semanticConceptCount"],
            row["classification"],
            mod._norm(row["safeEnglish"]),
        )
    )

    return {
        "schemaVersion": 1,
        "kind": "cook4me-high-confidence-semantic-syntax-audit",
        "policy": {
            "automaticApproval": False,
            "candidateSearchIsIdentityProof": False,
            "providerIdentityAssigned": False,
            "reviewRowsMutated": False,
            "semanticMappingsMutated": False,
            "usesOnlyExistingSafeSyntacticNormalizer": True,
        },
        "summary": {
            "highConfidenceReviewedRows": sum(
                row.get("confidence") == "high"
                and row.get("classification") in mod._MERGEABLE_CLASSIFICATIONS
                for row in rows
            ),
            "candidateGroupCount": len(candidates),
            "candidateConceptCount": sum(
                row["semanticConceptCount"] for row in candidates
            ),
            "candidateSourceIdentityCount": sum(
                row["sourceIdentityCount"] for row in candidates
            ),
            "groupsWithCleanCanonicalMember": sum(
                row["hasCleanCanonicalMember"] for row in candidates
            ),
        },
        "candidateGroups": candidates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=TOOLS)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build_audit(args.review_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
