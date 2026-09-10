#!/usr/bin/env python3
"""Measure identity-safe English sibling evidence for keyless ingredient lines."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from prepare_release_catalog_v2_assembly import _semantic_ingredient_name_with_source


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value)).casefold()


def _load(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def analyze(provider: dict[str, Any]) -> dict[str, Any]:
    if provider.get("kind") != "cook4me-provider-capture":
        raise RuntimeError("expected cook4me-provider-capture")

    line_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    unkeyed_by_source: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for detail in provider.get("details") or []:
        if not isinstance(detail, dict):
            continue
        grouping = _text(
            detail.get("groupingFunctionalId")
            or detail.get("topRecipeId")
            or detail.get("recipeFunctionalId")
            or detail.get("variantId")
        )
        language = _text(detail.get("language")).lower()
        variant = _text(detail.get("variantId"))
        for ingredient in detail.get("ingredients") or []:
            if not isinstance(ingredient, dict):
                continue
            name, _changed, source_field = _semantic_ingredient_name_with_source(ingredient)
            if not name:
                continue
            line_id = _text(ingredient.get("lineFunctionalId"))
            row = {
                "groupingFunctionalId": grouping,
                "lineFunctionalId": line_id,
                "variantId": variant,
                "language": language,
                "sourceName": name,
                "sourceField": source_field,
                "foodKey": _text(ingredient.get("foodKey")),
            }
            if grouping and line_id:
                line_rows[(grouping, line_id)].append(row)
            if not row["foodKey"]:
                unkeyed_by_source[(language, _norm(name))].append(row)

    safe: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    for (language, _normalized), occurrences in sorted(unkeyed_by_source.items()):
        if language == "en":
            continue
        source_name = _text(occurrences[0].get("sourceName"))
        if any(not _text(item.get("lineFunctionalId")) or not _text(item.get("groupingFunctionalId")) for item in occurrences):
            reasons["missing_line_identity"] += 1
            continue

        english_rows: list[dict[str, Any]] = []
        missing_sibling = False
        for occurrence in occurrences:
            key = (
                _text(occurrence.get("groupingFunctionalId")),
                _text(occurrence.get("lineFunctionalId")),
            )
            siblings = [
                row for row in line_rows.get(key, [])
                if _text(row.get("language")).lower() == "en"
            ]
            if not siblings:
                missing_sibling = True
                break
            english_rows.extend(siblings)
        if missing_sibling:
            reasons["missing_english_sibling"] += 1
            continue

        names = {_norm(row.get("sourceName")) for row in english_rows if _text(row.get("sourceName"))}
        if len(names) != 1:
            reasons["conflicting_english_sibling_names"] += 1
            continue
        if not all(
            _text(row.get("foodKey")) or _text(row.get("sourceField")) == "foodName"
            for row in english_rows
        ):
            reasons["english_sibling_not_provider_proven_food"] += 1
            continue

        english_name = _text(english_rows[0].get("sourceName"))
        safe.append(
            {
                "sourceLanguage": language,
                "sourceText": source_name,
                "canonicalEnglishName": english_name,
                "classification": "food",
                "occurrenceCount": len(occurrences),
                "evidence": "same groupingFunctionalId + lineFunctionalId English sibling; every English sibling is provider-proven food",
                "englishSiblingCount": len(english_rows),
                "englishSiblingFoodKeys": sorted(
                    {_text(row.get("foodKey")) for row in english_rows if _text(row.get("foodKey"))}
                ),
            }
        )

    safe.sort(
        key=lambda row: (
            -int(row["occurrenceCount"]),
            row["sourceLanguage"],
            _norm(row["sourceText"]),
        )
    )
    return {
        "schemaVersion": 1,
        "kind": "cook4me-keyless-english-line-sibling-evidence-v59",
        "safeCandidateCount": len(safe),
        "safeOccurrenceCount": sum(int(row["occurrenceCount"]) for row in safe),
        "unresolvedReasonCounts": dict(sorted(reasons.items())),
        "safeCandidates": safe,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-capture", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = analyze(_load(Path(args.provider_capture).expanduser()))
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "safeCandidateCount": result["safeCandidateCount"],
        "safeOccurrenceCount": result["safeOccurrenceCount"],
        "unresolvedReasonCounts": result["unresolvedReasonCounts"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
