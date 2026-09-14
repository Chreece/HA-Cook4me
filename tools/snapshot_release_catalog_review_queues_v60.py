#!/usr/bin/env python3
"""Snapshot exact v60 semantic/canonical review queues from one captured catalog.

This tool is deliberately offline and evidence-only.  It does not translate,
classify, merge, infer provider identity, or modify the captured catalog.  It
extracts only the exact source-local labels that are still unreviewed and the
exact provider-backed ingredients whose canonical English label still needs
review, together with bounded recipe-reference context.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import compile_release_catalog_semantics_v60 as semantics  # type: ignore  # noqa: E402
import provider_identity_v60  # type: ignore  # noqa: E402


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _save(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _identity(row: dict[str, Any]) -> str:
    return _text(
        row.get("ingredientId")
        or row.get("id")
        or row.get("key")
        or row.get("foodKey")
    )


def _source_language(ident: str) -> str:
    parts = ident.split(":", 2)
    if len(parts) != 3 or parts[0] != "local" or not parts[1]:
        return ""
    return parts[1].lower()


def _exact_source_label(row: dict[str, Any], ident: str) -> tuple[str, str]:
    """Return (language, exact reviewed-contract source) or fail closed."""
    language = _source_language(ident)
    if not language:
        raise RuntimeError(f"source-local identity has invalid shape: {ident}")

    translations = row.get("translations")
    source = ""
    if isinstance(translations, dict):
        source = _text(translations.get(language))
    if not source:
        source = _text(row.get("canonicalName"))
    if not source:
        raise RuntimeError(f"source-local ingredient {ident} has no exact source label")

    expected = semantics.source_local_ingredient_id(language, source)
    if expected != ident:
        raise RuntimeError(
            "source-local identity/source mismatch: "
            f"{ident} != {expected} for {language}/{source!r}"
        )
    return language, source


def _recipe_references(
    catalog: dict[str, Any],
    *,
    interesting_ids: set[str],
    example_limit: int,
) -> tuple[Counter[str], dict[str, list[dict[str, str]]]]:
    counts: Counter[str] = Counter()
    examples: dict[str, list[dict[str, str]]] = defaultdict(list)

    for group in catalog.get("recipes") or []:
        if not isinstance(group, dict):
            continue
        group_id = _text(group.get("groupingFunctionalId"))
        for variant in group.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            variant_id = _text(variant.get("variantId") or variant.get("searchVariantId"))
            language = _text(
                variant.get("originalLanguage") or variant.get("language")
            ).lower()
            for line in variant.get("ingredients") or []:
                if not isinstance(line, dict):
                    continue
                ident = _identity(line)
                if ident not in interesting_ids:
                    continue
                counts[ident] += 1
                if len(examples[ident]) >= example_limit:
                    continue
                example = {
                    "variantId": variant_id,
                    "groupingFunctionalId": group_id,
                    "language": language,
                }
                examples[ident].append(
                    {key: value for key, value in example.items() if value}
                )
    return counts, examples


def snapshot(catalog: dict[str, Any], *, example_limit: int = 3) -> dict[str, Any]:
    example_limit = max(0, min(int(example_limit), 10))
    ingredients = [
        row for row in catalog.get("ingredients") or [] if isinstance(row, dict)
    ]

    unresolved_local: list[tuple[dict[str, Any], str, str, str]] = []
    provider_canonical: list[tuple[dict[str, Any], str, str]] = []
    interesting_ids: set[str] = set()

    for row in ingredients:
        ident = _identity(row)
        if not ident:
            continue
        source_local = bool(row.get("sourceLocalIdentity")) or ident.startswith("local:")

        if source_local:
            # Queue only genuinely unreviewed semantic identities.  A reviewed
            # ambiguous concept remains reviewed and must never be re-queued.
            if _text(row.get("conceptId")):
                continue
            language, source = _exact_source_label(row, ident)
            unresolved_local.append((row, ident, language, source))
            interesting_ids.add(ident)
            continue

        if row.get("canonicalEnglishNeedsReview") is not True:
            continue
        provider_key = provider_identity_v60.provider_key(row)
        if not provider_identity_v60.preserved_provider_identity(row, ident):
            raise RuntimeError(
                f"provider canonical-review row does not preserve exact provider identity: {ident}"
            )
        provider_canonical.append((row, ident, provider_key))
        interesting_ids.add(ident)

    counts, examples = _recipe_references(
        catalog,
        interesting_ids=interesting_ids,
        example_limit=example_limit,
    )

    semantic_queue: list[dict[str, Any]] = []
    for _row, ident, language, source in unresolved_local:
        semantic_queue.append(
            {
                "ingredientId": ident,
                "language": language,
                "source": source,
                "usageCount": int(counts.get(ident, 0)),
                "examples": examples.get(ident, []),
            }
        )
    semantic_queue.sort(
        key=lambda row: (
            -int(row["usageCount"]),
            row["language"],
            row["source"].casefold(),
            row["ingredientId"],
        )
    )

    canonical_queue: list[dict[str, Any]] = []
    for row, ident, provider_key in provider_canonical:
        translations = row.get("translations")
        safe_translations = {
            _text(language).lower(): _text(label)
            for language, label in sorted(
                translations.items() if isinstance(translations, dict) else []
            )
            if _text(language) and _text(label)
        }
        canonical_queue.append(
            {
                "ingredientId": ident,
                "providerKey": provider_key,
                "fallbackCanonicalName": _text(row.get("canonicalName")),
                "fallbackSourceLanguage": _text(
                    row.get("canonicalNameSourceLanguage")
                ).lower(),
                "translations": safe_translations,
                "usageCount": int(counts.get(ident, 0)),
                "examples": examples.get(ident, []),
            }
        )
    canonical_queue.sort(
        key=lambda row: (
            -int(row["usageCount"]),
            row["providerKey"],
        )
    )

    language_counts = Counter(row["language"] for row in semantic_queue)
    return {
        "schemaVersion": 1,
        "kind": "cook4me-v60-review-queues",
        "catalogVersion": _text(catalog.get("catalogVersion")),
        "policy": {
            "offlineOnly": True,
            "capturedCatalogMutated": False,
            "providerIdentityInferred": False,
            "sourceLocalIdentityRecomputed": True,
            "exactSourceLabelOnly": True,
            "translationsGenerated": False,
            "classificationsGenerated": False,
            "reviewDecisionsGenerated": False,
            "exampleLimit": example_limit,
        },
        "summary": {
            "sourceLocalSemanticReviewCount": len(semantic_queue),
            "providerCanonicalEnglishReviewCount": len(canonical_queue),
            "sourceLocalByLanguage": dict(sorted(language_counts.items())),
        },
        "sourceLocalSemanticReview": semantic_queue,
        "providerCanonicalEnglishReview": canonical_queue,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument(
        "--output",
        default=str(
            ROOT / ".catalog-build" / "v60-release" / "review-queues.v60.json"
        ),
    )
    parser.add_argument("--example-limit", type=int, default=3)
    args = parser.parse_args()

    source = Path(args.catalog).expanduser()
    output = Path(args.output).expanduser()
    catalog = _load(source)
    before = deepcopy(catalog)
    result = snapshot(catalog, example_limit=args.example_limit)
    if catalog != before:
        raise RuntimeError("review queue snapshot mutated the captured catalog")
    _save(output, result)
    print(
        json.dumps(
            {
                **result["summary"],
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
