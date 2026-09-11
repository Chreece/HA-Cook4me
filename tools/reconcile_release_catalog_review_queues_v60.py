#!/usr/bin/env python3
"""Reconcile captured v60 review queues against the current committed review corpus.

This is an offline evidence step between queue extraction and new semantic/canonical
review work.  It proves whether a queued identity is still absent from the exact
review corpus currently checked out, instead of assuming every row from an older
capture is new.

No translation, classification, confidence decision, semantic merge, provider
identity, or canonical-English decision is generated here.
"""
from __future__ import annotations

import argparse
from collections import Counter
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
import release_catalog_canonical_reviews_v60 as canonical_reviews  # type: ignore  # noqa: E402


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


def _queue_rows(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise RuntimeError(f"{label} must be a list")
    if any(not isinstance(row, dict) for row in value):
        raise RuntimeError(f"{label} must contain only objects")
    return list(value)


def _validate_queue_contract(queue: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if queue.get("schemaVersion") != 1:
        raise RuntimeError("review queue schemaVersion must be 1")
    if queue.get("kind") != "cook4me-v60-review-queues":
        raise RuntimeError("unexpected review queue kind")

    policy = queue.get("policy")
    if not isinstance(policy, dict):
        raise RuntimeError("review queue policy is missing")
    required_policy = {
        "offlineOnly": True,
        "capturedCatalogMutated": False,
        "providerIdentityInferred": False,
        "sourceLocalIdentityRecomputed": True,
        "exactSourceLabelOnly": True,
        "translationsGenerated": False,
        "classificationsGenerated": False,
        "reviewDecisionsGenerated": False,
    }
    for key, expected in required_policy.items():
        if policy.get(key) is not expected:
            raise RuntimeError(
                f"review queue policy {key} must be {expected!r}, got {policy.get(key)!r}"
            )

    semantic_rows = _queue_rows(
        queue.get("sourceLocalSemanticReview"), "sourceLocalSemanticReview"
    )
    provider_rows = _queue_rows(
        queue.get("providerCanonicalEnglishReview"),
        "providerCanonicalEnglishReview",
    )

    summary = queue.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("review queue summary is missing")
    if int(summary.get("sourceLocalSemanticReviewCount", -1)) != len(semantic_rows):
        raise RuntimeError("source-local review queue count does not match summary")
    if int(summary.get("providerCanonicalEnglishReviewCount", -1)) != len(provider_rows):
        raise RuntimeError("provider canonical review queue count does not match summary")

    observed_languages = Counter(_text(row.get("language")).lower() for row in semantic_rows)
    observed_languages.pop("", None)
    summary_languages = summary.get("sourceLocalByLanguage")
    if summary_languages != dict(sorted(observed_languages.items())):
        raise RuntimeError("source-local language counts do not match summary")

    return semantic_rows, provider_rows


def _semantic_queue_identity(row: dict[str, Any]) -> tuple[str, str, str]:
    ident = _text(row.get("ingredientId"))
    language = _text(row.get("language")).lower()
    source = _text(row.get("source"))
    if not ident or not language or not source:
        raise RuntimeError("source-local review row is missing identity/language/source")
    expected = semantics.source_local_ingredient_id(language, source)
    if ident != expected:
        raise RuntimeError(
            "source-local review identity/source mismatch: "
            f"{ident} != {expected} for {language}/{source!r}"
        )
    return ident, language, source


def _provider_queue_identity(row: dict[str, Any]) -> str:
    ident = _text(row.get("ingredientId"))
    provider_key = _text(row.get("providerKey"))
    if not ident or not provider_key:
        raise RuntimeError("provider canonical review row is missing identity/providerKey")
    if ident != provider_key:
        raise RuntimeError(
            "provider canonical review identity/key mismatch: "
            f"{ident!r} != {provider_key!r}"
        )
    if ident.startswith("local:"):
        raise RuntimeError(f"provider canonical review row uses source-local identity: {ident}")
    return ident


def _unique_identity(ident: str, seen: set[str], label: str) -> None:
    if ident in seen:
        raise RuntimeError(f"duplicate {label} identity in review queue: {ident}")
    seen.add(ident)


def reconcile(
    queue: dict[str, Any],
    *,
    tools_dir: Path = TOOLS,
) -> dict[str, Any]:
    """Reconcile one captured queue against exact current repository reviews."""
    semantic_rows, provider_rows = _validate_queue_contract(queue)

    review_paths = semantics._review_paths(tools_dir)
    if not review_paths:
        raise RuntimeError(f"no reviewed semantic source files in {tools_dir}")
    semantic_corpus = semantics.compile_from_paths(review_paths)
    semantic_map = semantic_corpus.get("sourceIdentityToConcept") or {}
    if not isinstance(semantic_map, dict):
        raise RuntimeError("compiled semantic corpus has no sourceIdentityToConcept map")
    concepts = {
        _text(row.get("conceptId")): row
        for row in semantic_corpus.get("concepts") or []
        if isinstance(row, dict) and _text(row.get("conceptId"))
    }

    provider_reviews = canonical_reviews._provider_food_reviews(tools_dir)

    already_semantic: list[dict[str, Any]] = []
    needs_semantic: list[dict[str, Any]] = []
    seen_semantic: set[str] = set()
    for raw in semantic_rows:
        ident, language, source = _semantic_queue_identity(raw)
        _unique_identity(ident, seen_semantic, "source-local")
        concept_id = _text(semantic_map.get(ident))
        if not concept_id:
            needs_semantic.append(deepcopy(raw))
            continue
        concept = concepts.get(concept_id) or {}
        existing = {
            "ingredientId": ident,
            "language": language,
            "source": source,
            "conceptId": concept_id,
            "canonicalEnglish": _text(concept.get("canonicalEnglish")),
            "classification": _text(concept.get("classification")),
            "mergePolicy": _text(concept.get("mergePolicy")),
        }
        already_semantic.append(
            {key: value for key, value in existing.items() if value}
        )

    already_provider: list[dict[str, Any]] = []
    needs_provider: list[dict[str, Any]] = []
    seen_provider: set[str] = set()
    for raw in provider_rows:
        ident = _provider_queue_identity(raw)
        _unique_identity(ident, seen_provider, "provider")
        review = provider_reviews.get(ident)
        if review is None:
            needs_provider.append(deepcopy(raw))
            continue
        existing = {
            "ingredientId": ident,
            "providerKey": ident,
            "english": _text(review.get("english")),
            "confidence": _text(review.get("confidence")),
            "reviewFile": _text(review.get("reviewFile")),
        }
        if not existing["english"]:
            raise RuntimeError(f"provider review for {ident} has no English label")
        already_provider.append(
            {key: value for key, value in existing.items() if value}
        )

    needs_language_counts = Counter(
        _text(row.get("language")).lower() for row in needs_semantic
    )
    needs_language_counts.pop("", None)

    return {
        "schemaVersion": 1,
        "kind": "cook4me-v60-review-queue-reconciliation",
        "catalogVersion": _text(queue.get("catalogVersion")),
        "policy": {
            "offlineOnly": True,
            "queueMutated": False,
            "exactSourceIdentityOnly": True,
            "exactProviderIdentityOnly": True,
            "translationsGenerated": False,
            "classificationsGenerated": False,
            "reviewDecisionsGenerated": False,
            "providerIdentityInferred": False,
        },
        "reviewCorpus": {
            "semanticReviewFileCount": len(review_paths),
            "reviewedSourceLabelCount": int(
                (semantic_corpus.get("summary") or {}).get("reviewedSourceLabels", 0)
            ),
            "semanticConceptCount": int(
                (semantic_corpus.get("summary") or {}).get("semanticConcepts", 0)
            ),
            "providerCanonicalEnglishReviewCount": len(provider_reviews),
        },
        "summary": {
            "queuedSourceLocalSemanticReviewCount": len(semantic_rows),
            "alreadyReviewedSourceLocalExactCount": len(already_semantic),
            "needsSourceLocalSemanticReviewCount": len(needs_semantic),
            "queuedProviderCanonicalEnglishReviewCount": len(provider_rows),
            "alreadyReviewedProviderCanonicalExactCount": len(already_provider),
            "needsProviderCanonicalEnglishReviewCount": len(needs_provider),
            "needsSourceLocalByLanguage": dict(sorted(needs_language_counts.items())),
        },
        "alreadyReviewedSourceLocalExact": already_semantic,
        "needsSourceLocalSemanticReview": needs_semantic,
        "alreadyReviewedProviderCanonicalExact": already_provider,
        "needsProviderCanonicalEnglishReview": needs_provider,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument(
        "--output",
        default=str(
            ROOT
            / ".catalog-build"
            / "v60-release"
            / "review-queue-reconciliation.v60.json"
        ),
    )
    args = parser.parse_args()

    source = Path(args.queue).expanduser()
    output = Path(args.output).expanduser()
    queue = _load(source)
    before = deepcopy(queue)
    result = reconcile(queue)
    if queue != before:
        raise RuntimeError("review queue reconciliation mutated its input queue")
    _save(output, result)
    print(json.dumps({**result["summary"], "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
