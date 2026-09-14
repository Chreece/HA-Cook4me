#!/usr/bin/env python3
"""Resolve compact v60 nutrition review targets to exact ingredient profiles.

Manual review may target either:
- one exact provider ingredient identity; or
- one already-proven high-confidence semantic food concept containing multiple
  source-local ingredient identities.

Each review still binds exactly one target to exactly one USDA FDC ID. The FDC
detail endpoint is fetched only for that explicit reviewed ID. Concept-target
nutrition is then expanded into one ingredient-ID-bound profile per source-local
member so the authoritative v60 completeness gate remains exact-identity based.

No USDA search result is accepted here and API credentials are never persisted.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import resolve_reviewed_release_catalog_nutrition_v60 as exact_resolver  # type: ignore  # noqa: E402
import reviewed_nutrition_v60 as reviewed_nutrition  # type: ignore  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as checkpoint  # noqa: E402


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value)).casefold()


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return deepcopy(default)


def _review_paths(root: Path = TOOLS) -> list[Path]:
    return sorted(root.glob("release_catalog_reviewed_nutrition_targets*.v1.json"))


def load_reviews(root: Path = TOOLS) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in _review_paths(root):
        value = _load(path, {})
        if (
            not isinstance(value, dict)
            or value.get("kind") != "cook4me-reviewed-nutrition-target-source"
        ):
            raise RuntimeError(f"invalid nutrition-target review file: {path.name}")
        policy = value.get("policy") if isinstance(value.get("policy"), dict) else {}
        required = {
            "searchResultAutoAccepted": False,
            "exactFdcBindingRequired": True,
            "semanticConceptGroupingReviewed": True,
            "providerIdentityInference": False,
        }
        bad = [
            key for key, expected in required.items()
            if policy.get(key) is not expected
        ]
        if bad:
            raise RuntimeError(
                f"nutrition-target review file has unsafe policy {path.name}: "
                + ", ".join(bad)
            )

        for raw in value.get("items") or []:
            if not isinstance(raw, dict):
                continue
            target_id = _text(raw.get("reviewTargetId"))
            try:
                fdc_id = int(raw.get("fdcId"))
            except (TypeError, ValueError):
                continue
            if not target_id or fdc_id <= 0:
                continue
            normalized = dict(raw)
            normalized["reviewTargetId"] = target_id
            normalized["fdcId"] = fdc_id
            normalized["reviewFile"] = path.name
            normalized.update(checkpoint.retained_reference_receipt(value, raw, path.name))
            existing = out.get(target_id)
            if existing and int(existing["fdcId"]) != fdc_id:
                raise RuntimeError(
                    f"conflicting nutrition-target review for {target_id}: "
                    f"{existing['fdcId']} vs {fdc_id}"
                )
            out.setdefault(target_id, normalized)
    return out


def _validate_queue(queue: dict[str, Any]) -> None:
    if queue.get("kind") != "cook4me-release-catalog-nutrition-review-targets-v60":
        raise RuntimeError(
            "expected cook4me-release-catalog-nutrition-review-targets-v60"
        )
    policy = queue.get("policy") if isinstance(queue.get("policy"), dict) else {}
    required = {
        "exactIngredientIdentityCompletenessPreserved": True,
        "providerIdentityInference": False,
        "providerIdentityReviewGrouped": False,
        "sourceLocalGroupingRequiresSemanticConcept": True,
        "sourceLocalGroupingRequiresHighConfidence": True,
        "sourceLocalGroupingRequiresExactCanonicalEnglish": True,
        "reviewedExactFdcProvenanceRequired": True,
        "searchResultAutoAccepted": False,
    }
    bad = [key for key, expected in required.items() if policy.get(key) is not expected]
    if bad:
        raise RuntimeError(
            "nutrition review-target queue is missing fail-closed policy: "
            + ", ".join(bad)
        )


def _target_members(raw: dict[str, Any]) -> list[str]:
    members = sorted(
        {
            _text(value)
            for value in raw.get("memberIngredientIds") or []
            if _text(value)
        }
    )
    if not members:
        raise RuntimeError(
            f"nutrition review target {_text(raw.get('reviewTargetId'))!r} has no members"
        )
    return members


def resolve(
    queue: dict[str, Any],
    cache: dict[str, Any],
    reviews: dict[str, dict[str, Any]],
    *,
    fetcher: Callable[[int], dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_queue(queue)

    output, rejected_held_cache = reviewed_nutrition.holds.filter_cache(cache)
    pending: list[dict[str, Any]] = []
    already_resolved_identities = 0
    already_resolved_targets = 0
    resolved_now_identities = 0
    resolved_now_targets = 0
    missing_review_targets = 0
    held_targets = 0
    held_identities = 0
    rejected_unreviewed_cache = 0
    fetched_fdc_ids: list[int] = []

    targets = [row for row in queue.get("targets") or [] if isinstance(row, dict)]
    seen_members: set[str] = set()

    for raw in targets:
        target_id = _text(raw.get("reviewTargetId"))
        target_kind = _text(raw.get("reviewTargetKind"))
        canonical = _text(raw.get("canonicalEnglishName"))
        members = _target_members(raw)

        if not target_id or not canonical:
            raise RuntimeError("nutrition review target lacks target ID/canonical English")
        if target_kind not in {"provider-identity", "semantic-concept"}:
            raise RuntimeError(
                f"unsupported nutrition review target kind for {target_id}: {target_kind!r}"
            )
        if target_kind == "provider-identity":
            if len(members) != 1 or members[0] != target_id:
                raise RuntimeError(
                    f"provider review target must preserve exact identity: {target_id}"
                )
        else:
            if not target_id.startswith("concept:food:"):
                raise RuntimeError(
                    f"semantic nutrition review target is not a food concept: {target_id}"
                )
            if _text(raw.get("semanticConceptId")) != target_id:
                raise RuntimeError(
                    f"semantic nutrition review target concept mismatch: {target_id}"
                )

        duplicate_members = seen_members.intersection(members)
        if duplicate_members:
            raise RuntimeError(
                "ingredient identity appears in multiple nutrition review targets: "
                + ", ".join(sorted(duplicate_members)[:20])
            )
        seen_members.update(members)

        hold = reviewed_nutrition.holds.find_hold(target_id, *members)
        if hold is not None:
            held_targets += 1
            held_identities += len(members)
            for ingredient_id in members:
                if ingredient_id in output:
                    rejected_held_cache += 1
                    output.pop(ingredient_id)
            pending.append(reviewed_nutrition.holds.pending_hold(raw, hold))
            continue

        unresolved: list[str] = []
        for ingredient_id in members:
            existing = output.get(ingredient_id)
            if reviewed_nutrition.is_reviewed_profile(
                existing,
                ingredient_id=ingredient_id,
                canonical_name=canonical,
            ):
                already_resolved_identities += 1
                continue
            if isinstance(existing, dict) and existing:
                rejected_unreviewed_cache += 1
                output.pop(ingredient_id, None)
            unresolved.append(ingredient_id)

        if not unresolved:
            already_resolved_targets += 1
            continue

        review = reviews.get(target_id)
        if not review:
            missing_review_targets += 1
            pending_row = dict(raw)
            pending_row["memberIngredientIds"] = unresolved
            pending_row["memberCount"] = len(unresolved)
            pending.append(pending_row)
            continue

        reviewed_name = _text(review.get("canonicalEnglishName"))
        if reviewed_name and _norm(reviewed_name) != _norm(canonical):
            raise RuntimeError(
                f"nutrition-target review name mismatch for {target_id}: "
                f"queue={canonical!r} review={reviewed_name!r}"
            )

        reviewed_kind = _text(review.get("reviewTargetKind"))
        if reviewed_kind and reviewed_kind != target_kind:
            raise RuntimeError(
                f"nutrition-target review kind mismatch for {target_id}: "
                f"queue={target_kind!r} review={reviewed_kind!r}"
            )

        fdc_id = int(review["fdcId"])
        food = fetcher(fdc_id)
        fetched_fdc_ids.append(fdc_id)
        try:
            returned_id = int(food.get("fdcId"))
        except (TypeError, ValueError):
            raise RuntimeError(f"FDC {fdc_id}: response has no valid fdcId") from None
        if returned_id != fdc_id:
            raise RuntimeError(
                f"FDC identity mismatch: requested {fdc_id}, got {returned_id}"
            )

        template = exact_resolver.fdc_profile(food)
        if not template:
            raise RuntimeError(f"FDC {fdc_id}: no usable nutrient profile")

        for ingredient_id in unresolved:
            profile = deepcopy(template)
            profile["ingredientId"] = ingredient_id
            profile["reviewedCanonicalEnglishName"] = canonical
            profile["reviewConfidence"] = _text(review.get("confidence")) or "reviewed"
            profile["reviewFile"] = _text(review.get("reviewFile"))
            profile["nutritionReviewTargetId"] = target_id
            profile["nutritionReviewTargetKind"] = target_kind
            if target_kind == "semantic-concept":
                profile["semanticConceptId"] = target_id
            for key in ("evidenceBindingScope", "sourceEvidenceSha256", "sourceEvidenceTargetId",
                        "sourceEvidenceCandidateRank", "sourceCandidateSha256"):
                if key in review:
                    profile[key] = review[key]
            if review.get("notes"):
                profile["reviewNotes"] = _text(review.get("notes"))
            if not reviewed_nutrition.is_reviewed_profile(
                profile,
                ingredient_id=ingredient_id,
                canonical_name=canonical,
            ):
                raise RuntimeError(
                    f"nutrition-target resolver produced invalid provenance for "
                    f"{ingredient_id}"
                )
            output[ingredient_id] = profile
            resolved_now_identities += 1
        resolved_now_targets += 1

    reviewed_profile_count = sum(
        reviewed_nutrition.is_reviewed_profile(value, ingredient_id=ident)
        for ident, value in output.items()
    )
    pending_identity_count = sum(
        len(_target_members(row)) for row in pending
    )
    summary = {
        "reviewTargetCount": len(targets),
        "identityCount": len(seen_members),
        "alreadyResolvedReviewTargets": already_resolved_targets,
        "alreadyResolvedIdentities": already_resolved_identities,
        "resolvedNowReviewTargets": resolved_now_targets,
        "resolvedNowIdentities": resolved_now_identities,
        "missingReviewTargets": missing_review_targets,
        "heldReviewTargets": held_targets,
        "heldIdentities": held_identities,
        "rejectedHeldCacheCount": rejected_held_cache,
        "pendingReviewTargetCount": len(pending),
        "pendingIdentityCount": pending_identity_count,
        "reviewedCacheProfileCount": reviewed_profile_count,
        "rejectedUnreviewedCacheCount": rejected_unreviewed_cache,
        "fdcDetailFetchCount": len(fetched_fdc_ids),
        "searchResultsAutoAccepted": False,
        "secretsPersisted": False,
    }
    return output, {"summary": summary, "pending": pending}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--fdc-key", default="")
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--pending-output", required=True)
    args = parser.parse_args()

    api_key = _text(args.fdc_key or os.environ.get("FDC_API_KEY"))
    if not api_key:
        raise SystemExit(
            "reviewed nutrition-target resolution requires --fdc-key or FDC_API_KEY"
        )

    queue = _load(Path(args.targets).expanduser(), {})
    cache_path = Path(args.cache).expanduser()
    cache = _load(cache_path, {})
    if not isinstance(queue, dict):
        raise RuntimeError("nutrition review-target queue must be a JSON object")
    if not isinstance(cache, dict):
        raise RuntimeError("nutrition cache must be a JSON object keyed by ingredient ID")

    reviews = load_reviews(Path(args.review_root).expanduser())
    output, pending = resolve(
        queue,
        cache,
        reviews,
        fetcher=lambda fdc_id: exact_resolver.fetch_fdc_detail(fdc_id, api_key),
    )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pending_path = Path(args.pending_output).expanduser()
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(
        json.dumps(pending, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(pending["summary"], ensure_ascii=False))
    return 0 if pending["summary"]["pendingReviewTargetCount"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
