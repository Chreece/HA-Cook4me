#!/usr/bin/env python3
"""Compact the exact v60 nutrition identity queue into safe manual review targets.

The authoritative nutrition completeness unit remains the exact ingredient
identity queue produced by ``snapshot_release_catalog_nutrition_queue_v60.py``.
This tool changes only the *manual review unit*:

- provider identities remain one review target per exact provider ingredient ID;
- reviewed source-local food identities may share one target only when the
  semantic compiler has already placed them in the same high-confidence
  ``conceptId``;
- canonical English must match exactly after normalization inside a concept;
- no provider identity is inferred, merged, or replaced;
- no USDA/FDC request is performed here.

A reviewed concept target is later expanded back into ingredient-ID-bound
nutrition profiles, so the final release completeness gate still proves every
exact ingredient identity independently.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata
from typing import Any


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value)).casefold()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("nutrition queue must be a JSON object")
    return value


def _validate_queue(queue: dict[str, Any]) -> None:
    if queue.get("kind") != "cook4me-release-catalog-nutrition-queue-v60":
        raise RuntimeError("expected cook4me-release-catalog-nutrition-queue-v60")
    policy = (
        queue.get("identityPolicy")
        if isinstance(queue.get("identityPolicy"), dict)
        else {}
    )
    required = {
        "providerIdentityInference": False,
        "sourceLocalFoodRequiresReviewedNutritionEligibility": True,
        "reviewedExactFdcProvenanceRequired": True,
        "searchResultAutoAccepted": False,
        "ambiguousExcluded": True,
        "equipmentAndOtherExcluded": True,
    }
    bad = [key for key, expected in required.items() if policy.get(key) is not expected]
    if bad:
        raise RuntimeError(
            "nutrition queue is missing fail-closed identity policy: "
            + ", ".join(bad)
        )


def compact(queue: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a manual-review target queue without weakening identity completeness."""
    _validate_queue(queue)

    provider_targets: list[dict[str, Any]] = []
    concepts: dict[str, dict[str, Any]] = {}
    seen_ingredient_ids: set[str] = set()

    tasks = [row for row in queue.get("tasks") or [] if isinstance(row, dict)]
    for index, raw in enumerate(tasks):
        ingredient_id = _text(raw.get("ingredientId"))
        canonical = _text(raw.get("canonicalEnglishName"))
        identity_kind = _text(raw.get("identityKind"))
        usage_count = max(0, int(raw.get("usageCount") or 0))
        if not ingredient_id or not canonical:
            raise RuntimeError(f"nutrition queue task {index} lacks identity/canonical English")
        if ingredient_id in seen_ingredient_ids:
            raise RuntimeError(f"duplicate nutrition queue ingredient identity: {ingredient_id}")
        seen_ingredient_ids.add(ingredient_id)

        if identity_kind == "provider":
            provider_targets.append(
                {
                    "reviewTargetId": ingredient_id,
                    "reviewTargetKind": "provider-identity",
                    "canonicalEnglishName": canonical,
                    "memberIngredientIds": [ingredient_id],
                    "memberCount": 1,
                    "usageCountSum": usage_count,
                    "usedByRecipe": bool(raw.get("usedByRecipe")),
                }
            )
            continue

        if identity_kind != "source-local":
            raise RuntimeError(
                f"unsupported nutrition identity kind {identity_kind!r} for {ingredient_id}"
            )

        concept_id = _text(raw.get("conceptId"))
        confidence = _text(raw.get("reviewConfidence")).lower()
        semantic_review_file = _text(raw.get("semanticReviewFile"))
        source_language = _text(raw.get("sourceLanguage")).lower()
        if not concept_id:
            raise RuntimeError(
                f"source-local nutrition task lacks semantic concept: {ingredient_id}"
            )
        if not concept_id.startswith("concept:food:"):
            raise RuntimeError(
                f"source-local nutrition task has non-food semantic concept: "
                f"{ingredient_id} -> {concept_id}"
            )
        if confidence != "high":
            raise RuntimeError(
                f"source-local nutrition task is not high-confidence mergeable: "
                f"{ingredient_id} confidence={confidence!r}"
            )
        if not semantic_review_file:
            raise RuntimeError(
                f"source-local nutrition task lacks semantic review provenance: {ingredient_id}"
            )

        target = concepts.setdefault(
            concept_id,
            {
                "reviewTargetId": concept_id,
                "reviewTargetKind": "semantic-concept",
                "semanticConceptId": concept_id,
                "canonicalEnglishName": canonical,
                "memberIngredientIds": [],
                "memberCount": 0,
                "usageCountSum": 0,
                "usedByRecipe": False,
                "sourceLanguages": [],
                "semanticReviewFiles": [],
            },
        )
        if _norm(target["canonicalEnglishName"]) != _norm(canonical):
            raise RuntimeError(
                "semantic concept canonical-English mismatch: "
                f"{concept_id}: {target['canonicalEnglishName']!r} vs {canonical!r}"
            )
        target["memberIngredientIds"].append(ingredient_id)
        target["memberCount"] += 1
        target["usageCountSum"] += usage_count
        target["usedByRecipe"] = bool(target["usedByRecipe"] or raw.get("usedByRecipe"))
        if source_language:
            target["sourceLanguages"].append(source_language)
        target["semanticReviewFiles"].append(semantic_review_file)

    concept_targets: list[dict[str, Any]] = []
    for target in concepts.values():
        target["memberIngredientIds"] = sorted(set(target["memberIngredientIds"]))
        target["memberCount"] = len(target["memberIngredientIds"])
        target["sourceLanguages"] = sorted(set(target["sourceLanguages"]))
        target["semanticReviewFiles"] = sorted(set(target["semanticReviewFiles"]))
        concept_targets.append(target)

    all_targets = provider_targets + concept_targets
    all_targets.sort(
        key=lambda row: (
            -int(row.get("usageCountSum") or 0),
            0 if row.get("reviewTargetKind") == "provider-identity" else 1,
            _norm(row.get("canonicalEnglishName")),
            _text(row.get("reviewTargetId")),
        )
    )

    target_kinds = Counter(_text(row.get("reviewTargetKind")) for row in all_targets)
    member_count = sum(int(row.get("memberCount") or 0) for row in all_targets)
    if member_count != len(tasks):
        raise RuntimeError(
            f"review-target compaction lost identities: input={len(tasks)} outputMembers={member_count}"
        )

    payload = {
        "schemaVersion": 1,
        "kind": "cook4me-release-catalog-nutrition-review-targets-v60",
        "catalogVersion": _text(queue.get("catalogVersion")),
        "nutritionBasisRequired": "per100g",
        "identityCount": len(tasks),
        "reviewTargetCount": len(all_targets),
        "policy": {
            "exactIngredientIdentityCompletenessPreserved": True,
            "providerIdentityInference": False,
            "providerIdentityReviewGrouped": False,
            "sourceLocalGroupingRequiresSemanticConcept": True,
            "sourceLocalGroupingRequiresHighConfidence": True,
            "sourceLocalGroupingRequiresExactCanonicalEnglish": True,
            "reviewedExactFdcProvenanceRequired": True,
            "searchResultAutoAccepted": False,
            "candidateSearchIsIdentityProof": False,
        },
        "targets": all_targets,
    }
    summary = {
        "identityCount": len(tasks),
        "reviewTargetCount": len(all_targets),
        "collapsedIdentityCount": len(tasks) - len(all_targets),
        "providerIdentityCount": len(provider_targets),
        "providerReviewTargetCount": len(provider_targets),
        "sourceLocalIdentityCount": sum(
            int(row.get("memberCount") or 0) for row in concept_targets
        ),
        "semanticConceptReviewTargetCount": len(concept_targets),
        "reviewTargetsByKind": dict(sorted(target_kinds.items())),
        "usedReviewTargetCount": sum(bool(row.get("usedByRecipe")) for row in all_targets),
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    queue = _load(Path(args.queue).expanduser())
    payload, summary = compact(queue)

    output = Path(args.output).expanduser()
    summary_path = Path(args.summary).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
