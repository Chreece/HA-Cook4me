#!/usr/bin/env python3
"""Load and apply pinned official-food-table nutrition reviews for Cook4Me v60.

This module is intentionally network-free. It accepts only versioned repository
records that bind an exact review target and exact member identities to a stable
record in an official food-composition table. It does not search, infer provider
identity, or reuse a reviewed profile for another ingredient.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any

import reviewed_nutrition_v60 as reviewed_nutrition

KIND = "cook4me-reviewed-supplemental-nutrition-source-v60"
GLOB = "release_catalog_reviewed_supplemental_nutrition_targets_*.v1.json"
HEX256 = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _norm(value: Any) -> str:
    return _text(value).casefold()


def _numeric_values(value: Any) -> bool:
    if not isinstance(value, dict) or not value:
        return False
    for number in value.values():
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            return False
        if not math.isfinite(float(number)):
            return False
    return True


def _source_fingerprint(row: dict[str, Any]) -> str:
    payload = {
        "basis": row.get("basis"),
        "scientificName": row.get("scientificName"),
        "source": row.get("source"),
        "sourceAuthority": row.get("sourceAuthority"),
        "sourceDataset": row.get("sourceDataset"),
        "sourceRecordId": row.get("sourceRecordId"),
        "sourceUrl": row.get("sourceUrl"),
        "values": row.get("values"),
    }
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_reviews(review_root: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(review_root.glob(GLOB)):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("kind") != KIND:
            raise RuntimeError(f"unsupported supplemental nutrition review file: {path.name}")
        if int(value.get("schemaVersion") or 0) != 1:
            raise RuntimeError(f"unsupported supplemental nutrition schema: {path.name}")
        policy = value.get("policy") if isinstance(value.get("policy"), dict) else {}
        required_policy = {
            "manualSemanticReviewPerformed": True,
            "automaticSelectionPerformed": False,
            "searchResultAutoAccepted": False,
            "networkRequestsPerformedAtRuntime": False,
            "exactReviewTargetRequired": True,
            "exactMemberIdentityRequired": True,
            "officialFoodCompositionSourceRequired": True,
            "sourceValuesPinnedInRepository": True,
        }
        bad = [key for key, expected in required_policy.items() if policy.get(key) is not expected]
        if bad:
            raise RuntimeError(
                f"unsafe supplemental nutrition policy {path.name}: " + ", ".join(bad)
            )
        for raw in value.get("items") or []:
            if not isinstance(raw, dict):
                continue
            target_id = _text(raw.get("reviewTargetId"))
            target_kind = _text(raw.get("reviewTargetKind"))
            canonical = _text(raw.get("canonicalEnglishName"))
            members = [
                _text(member)
                for member in raw.get("memberIngredientIds") or []
                if _text(member)
            ]
            if not target_id or not canonical or not members or len(members) != len(set(members)):
                raise RuntimeError(f"{path.name}: incomplete supplemental review identity")
            if target_kind == "provider-identity":
                if members != [target_id]:
                    raise RuntimeError(f"{target_id}: provider supplemental review must be exact")
            elif target_kind == "semantic-concept":
                if not target_id.startswith("concept:food:"):
                    raise RuntimeError(f"{target_id}: invalid supplemental semantic concept")
            else:
                raise RuntimeError(f"{target_id}: unsupported supplemental review target kind")
            if _text(raw.get("source")).casefold() != "official_food_table":
                raise RuntimeError(f"{target_id}: supplemental source is not an official food table")
            for key in (
                "sourceAuthority",
                "sourceDataset",
                "sourceRecordId",
                "sourceId",
                "dataType",
                "sourceUrl",
                "scientificName",
            ):
                if not _text(raw.get(key)):
                    raise RuntimeError(f"{target_id}: missing supplemental source field {key}")
            if _text(raw.get("basis")) != "per100g" or not _numeric_values(raw.get("values")):
                raise RuntimeError(f"{target_id}: invalid supplemental nutrient profile")
            expected_sha = _text(raw.get("sourceEvidenceSha256"))
            if not HEX256.fullmatch(expected_sha):
                raise RuntimeError(f"{target_id}: invalid supplemental sourceEvidenceSha256")
            actual_sha = _source_fingerprint(raw)
            if expected_sha != actual_sha:
                raise RuntimeError(
                    f"{target_id}: supplemental source evidence drift "
                    f"expected={expected_sha} actual={actual_sha}"
                )
            row = deepcopy(raw)
            row["reviewFile"] = path.name
            existing = out.get(target_id)
            if existing is not None and existing != row:
                raise RuntimeError(f"conflicting supplemental nutrition review: {target_id}")
            out[target_id] = row
    return out


def seed_cache(
    targets: dict[str, Any],
    cache: dict[str, Any],
    *,
    review_root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    reviews = load_reviews(review_root)
    output = deepcopy(cache)
    target_rows = {
        _text(row.get("reviewTargetId")): row
        for row in targets.get("targets") or []
        if isinstance(row, dict) and _text(row.get("reviewTargetId"))
    }

    applied_targets = 0
    applied_identities = 0
    already_resolved_identities = 0
    applicable_review_targets = 0

    for target_id, review in sorted(reviews.items()):
        target = target_rows.get(target_id)
        if target is None:
            continue
        applicable_review_targets += 1

        target_kind = _text(target.get("reviewTargetKind"))
        canonical = _text(target.get("canonicalEnglishName"))
        members = sorted(
            {
                _text(member)
                for member in target.get("memberIngredientIds") or []
                if _text(member)
            }
        )
        reviewed_members = sorted(
            {
                _text(member)
                for member in review.get("memberIngredientIds") or []
                if _text(member)
            }
        )
        if (
            target_kind != _text(review.get("reviewTargetKind"))
            or _norm(canonical) != _norm(review.get("canonicalEnglishName"))
            or members != reviewed_members
        ):
            raise RuntimeError(f"{target_id}: supplemental review target identity drift")

        target_applied = False
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
                raise RuntimeError(
                    f"{target_id}: refusing to replace non-reviewed cache for {ingredient_id}"
                )
            profile = {
                "basis": "per100g",
                "values": {
                    key: round(float(number), 4)
                    for key, number in review["values"].items()
                },
                "source": "official_food_table",
                "sourceId": _text(review.get("sourceId")),
                "dataType": _text(review.get("dataType")),
                "sourceDescription": (
                    f"{_text(review.get('sourceDataset'))} "
                    f"{_text(review.get('sourceRecordId'))}"
                ).strip(),
                "ingredientId": ingredient_id,
                "reviewedCanonicalEnglishName": canonical,
                "reviewConfidence": _text(review.get("confidence")) or "reviewed",
                "reviewFile": _text(review.get("reviewFile")),
                "nutritionReviewTargetId": target_id,
                "nutritionReviewTargetKind": target_kind,
                "sourceAuthority": _text(review.get("sourceAuthority")),
                "sourceDataset": _text(review.get("sourceDataset")),
                "sourceRecordId": _text(review.get("sourceRecordId")),
                "sourceUrl": _text(review.get("sourceUrl")),
                "sourceRetrievedDate": _text(review.get("sourceRetrievedDate")),
                "scientificName": _text(review.get("scientificName")),
                "sourceEvidenceSha256": _text(review.get("sourceEvidenceSha256")),
                "reviewNotes": _text(review.get("notes")),
            }
            if target_kind == "semantic-concept":
                profile["semanticConceptId"] = target_id
            if not reviewed_nutrition.is_reviewed_profile(
                profile,
                ingredient_id=ingredient_id,
                canonical_name=canonical,
            ):
                raise RuntimeError(
                    f"{target_id}: supplemental resolver produced invalid provenance"
                )
            output[ingredient_id] = profile
            applied_identities += 1
            target_applied = True
        if target_applied:
            applied_targets += 1

    return output, {
        "supplementalReviewCorpusTargetCount": len(reviews),
        "applicableSupplementalReviewTargetCount": applicable_review_targets,
        "supplementalResolvedNowReviewTargets": applied_targets,
        "supplementalResolvedNowIdentities": applied_identities,
        "supplementalAlreadyResolvedIdentities": already_resolved_identities,
        "networkRequestsPerformed": False,
        "searchResultsAutoAccepted": False,
        "providerIdentityInference": False,
    }
