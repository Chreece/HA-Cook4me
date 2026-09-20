#!/usr/bin/env python3
"""Apply reviewed nutrition-eligibility exclusions to an activated v60 catalog.

This maintenance overlay is deliberately narrow and offline. It consumes the
versioned semantic-review corpus and applies only explicit food reviews with
nutritionEligible=false to the exact source-local ingredient identities that
produced those reviews.

It never changes provider identity, classification, diet/allergen eligibility,
recipe membership, quantities, units, or any reviewed nutrition profile. An
override that would remove an existing nutrition profile fails closed.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60_reviewed as builder  # type: ignore  # noqa: E402
import compact_release_catalog_runtime_v60 as compactor  # type: ignore  # noqa: E402
import compile_release_catalog_semantics_v60 as semantics  # type: ignore  # noqa: E402


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _counts(payload: dict[str, Any]) -> tuple[int, int, int]:
    recipes = [row for row in payload.get("recipes") or [] if isinstance(row, dict)]
    return (
        len(recipes),
        sum(len(row.get("variants") or []) for row in recipes),
        len(payload.get("ingredients") or []),
    )


def _source(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("source")
    if not isinstance(value, dict):
        raise RuntimeError("catalog source metadata is missing")
    return value


def _override_rows(review_root: Path) -> dict[str, dict[str, Any]]:
    compiled = semantics.compile_from_paths(semantics._review_paths(review_root))
    out: dict[str, dict[str, Any]] = {}
    for concept in compiled.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        if _text(concept.get("classification")).lower() != "food":
            continue
        if concept.get("nutritionEligible") is not False:
            continue
        concept_id = _text(concept.get("conceptId"))
        canonical = _text(concept.get("canonicalEnglish"))
        if not concept_id.startswith("concept:food:") or not canonical:
            raise RuntimeError("nutrition eligibility override lacks reviewed food concept identity")
        for identity in concept.get("sourceIdentities") or []:
            if not isinstance(identity, dict):
                continue
            if identity.get("nutritionEligible") is not False:
                continue
            ingredient_id = _text(identity.get("ingredientId"))
            reason = _text(identity.get("nutritionEligibilityReason"))
            review_file = _text(identity.get("reviewFile"))
            if not ingredient_id.startswith("local:") or not reason or not review_file:
                raise RuntimeError(
                    f"{concept_id}: incomplete reviewed nutrition eligibility exclusion"
                )
            row = {
                "ingredientId": ingredient_id,
                "conceptId": concept_id,
                "canonicalEnglishName": canonical,
                "reason": reason,
                "reviewFile": review_file,
            }
            existing = out.get(ingredient_id)
            if existing is not None and existing != row:
                raise RuntimeError(f"conflicting nutrition eligibility override: {ingredient_id}")
            out[ingredient_id] = row
    return out


def apply(
    catalog: dict[str, Any],
    *,
    review_root: Path = TOOLS,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if int(catalog.get("schemaVersion") or 0) != 1:
        raise RuntimeError("expected release catalog schemaVersion=1")
    if catalog.get("complete") is not True:
        raise RuntimeError("eligibility overlay requires complete=true")

    before_source = _source(catalog)
    if before_source.get("runtimeCatalogCompacted") is not True:
        raise RuntimeError("eligibility overlay requires runtimeCatalogCompacted=true")
    if before_source.get("semanticCoverageComplete") is not True:
        raise RuntimeError("eligibility overlay requires semanticCoverageComplete=true")

    overrides = _override_rows(review_root)
    if not overrides:
        raise RuntimeError("semantic review corpus contains no nutrition eligibility exclusions")

    result = deepcopy(catalog)
    before_counts = _counts(result)
    before_required = int(before_source.get("reviewedNutritionRequiredCount") or 0)
    before_resolved = int(before_source.get("reviewedNutritionResolvedCount") or 0)
    previous_excluded = int(
        before_source.get("postActivationNutritionEligibilityExcludedIdentityCount") or 0
    )
    if before_required <= 0 or not 0 <= before_resolved <= before_required:
        raise RuntimeError("invalid reviewed nutrition baseline")

    ingredients = {
        _text(row.get("id") or row.get("ingredientId") or row.get("key")): row
        for row in result.get("ingredients") or []
        if isinstance(row, dict)
        and _text(row.get("id") or row.get("ingredientId") or row.get("key"))
    }

    changed: list[str] = []
    already_applied: list[str] = []
    for ingredient_id, override in sorted(overrides.items()):
        row = ingredients.get(ingredient_id)
        if not isinstance(row, dict):
            raise RuntimeError(f"reviewed eligibility identity missing from catalog: {ingredient_id}")
        if not (
            bool(row.get("sourceLocalIdentity"))
            and ingredient_id.startswith("local:")
            and row.get("providerIdentityAssigned") is False
        ):
            raise RuntimeError(f"eligibility override is not source-local: {ingredient_id}")
        if _text(row.get("conceptId")) != override["conceptId"]:
            raise RuntimeError(f"eligibility override concept drift: {ingredient_id}")
        if _text(row.get("canonicalName")).casefold() != override["canonicalEnglishName"].casefold():
            raise RuntimeError(f"eligibility override canonical-name drift: {ingredient_id}")
        if _text(row.get("classification")).lower() != "food":
            raise RuntimeError(f"eligibility override no longer targets food: {ingredient_id}")
        if isinstance(row.get("nutrition"), dict) and row["nutrition"]:
            raise RuntimeError(
                f"refusing to remove existing reviewed nutrition for {ingredient_id}"
            )

        if row.get("nutritionEligible") is False:
            if (
                _text(row.get("nutritionEligibilityReason")) != override["reason"]
                or _text(row.get("nutritionEligibilityReviewFile")) != override["reviewFile"]
            ):
                raise RuntimeError(f"existing eligibility override provenance drift: {ingredient_id}")
            already_applied.append(ingredient_id)
            continue
        if row.get("nutritionEligible") is not True:
            raise RuntimeError(f"unexpected nutrition eligibility state: {ingredient_id}")

        row["nutritionEligible"] = False
        row["nutritionEligibilityReviewed"] = True
        row["nutritionEligibilityReason"] = override["reason"]
        row["nutritionEligibilityReviewFile"] = override["reviewFile"]
        changed.append(ingredient_id)

    if not changed and not already_applied:
        raise RuntimeError("eligibility overlay matched no catalog identities")

    # Re-run the authoritative reviewed-profile attach/accounting path with the
    # existing embedded profiles. This validates every surviving profile and
    # recomputes the nutrition denominator after the reviewed exclusions.
    rebuilt = builder.apply_reviewed_nutrition(result, {})
    rebuilt_source = _source(rebuilt)
    if int(rebuilt_source.get("reviewedNutritionRejectedEmbeddedCount") or 0) != 0:
        raise RuntimeError("eligibility overlay rejected an existing reviewed profile")
    if _counts(rebuilt) != before_counts:
        raise RuntimeError("eligibility overlay changed catalog identity counts")

    compacted, compact_summary = compactor.compact(rebuilt)
    after_source = _source(compacted)
    if _counts(compacted) != before_counts:
        raise RuntimeError("eligibility overlay compaction changed identity counts")

    total_excluded = previous_excluded + len(changed)
    original_required = before_required + previous_excluded
    expected_required = original_required - total_excluded
    after_required = int(after_source.get("reviewedNutritionRequiredCount") or 0)
    after_resolved = int(after_source.get("reviewedNutritionResolvedCount") or 0)
    if after_required != expected_required:
        raise RuntimeError(
            f"eligibility denominator delta mismatch: expected={expected_required} actual={after_required}"
        )
    if after_resolved != before_resolved:
        raise RuntimeError(
            f"eligibility overlay changed resolved profile count: before={before_resolved} after={after_resolved}"
        )

    after_source.update(
        {
            "postActivationNutritionEligibilityOverlayApplied": True,
            "postActivationNutritionEligibilityOriginalRequiredCount": original_required,
            "postActivationNutritionEligibilityExcludedIdentityCount": total_excluded,
            "postActivationNutritionEligibilityExcludedIdentities": sorted(
                set(already_applied) | set(changed)
            ),
            "postActivationNutritionEligibilityNetworkRequestsPerformed": False,
        }
    )

    summary = {
        "catalogVersion": compacted.get("catalogVersion"),
        "recipes": before_counts[0],
        "variants": before_counts[1],
        "ingredients": before_counts[2],
        "reviewedNutritionRequiredCountBefore": before_required,
        "reviewedNutritionResolvedCountBefore": before_resolved,
        "newlyExcludedIdentityCount": len(changed),
        "alreadyExcludedIdentityCount": len(already_applied),
        "totalExcludedIdentityCount": total_excluded,
        "reviewedNutritionRequiredCountAfter": after_required,
        "reviewedNutritionResolvedCountAfter": after_resolved,
        "pendingIdentityCountAfter": after_required - after_resolved,
        "networkRequestsPerformed": False,
        "runtimeCatalogCompacted": after_source.get("runtimeCatalogCompacted") is True,
        "runtimeRecipeNutritionOnDemand": after_source.get("runtimeRecipeNutritionOnDemand") is True,
        "compactSummary": compact_summary,
    }
    return compacted, summary


def _write(path: Path, value: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if compact
        else json.dumps(value, ensure_ascii=False, indent=2)
    )
    path.write_text(text + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, default=TOOLS)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()

    catalog_path = args.catalog.expanduser()
    raw = catalog_path.read_bytes()
    catalog = json.loads(raw.decode("utf-8"))
    if not isinstance(catalog, dict):
        raise SystemExit("catalog must be a JSON object")

    result, summary = apply(catalog, review_root=args.review_root.expanduser())
    output = args.output.expanduser()
    summary_output = args.summary_output.expanduser()
    if output.exists() or summary_output.exists():
        raise SystemExit("output paths must not already exist")
    _write(output, result, compact=True)
    summary["sourceCatalogSha256"] = hashlib.sha256(raw).hexdigest()
    summary["outputSha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    summary["outputBytes"] = output.stat().st_size
    _write(summary_output, summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
