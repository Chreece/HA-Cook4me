#!/usr/bin/env python3
"""Validate the explicit terminal unresolved nutrition set for Cook4Me v60."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import snapshot_nutrition_review_checkpoint_v60 as checkpoint  # type: ignore  # noqa: E402
import supplemental_nutrition_v60 as supplemental  # type: ignore  # noqa: E402

KIND = "cook4me-nutrition-unresolved-v60"
EVIDENCE_KIND = "cook4me-fdc-review-target-candidate-evidence-offline-v60"
HEX256 = re.compile(r"[0-9a-f]{64}\Z")


def _read(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value, raw


def validate(evidence_path: Path, registry_path: Path, review_root: Path) -> dict[str, Any]:
    evidence, evidence_raw = _read(evidence_path)
    registry, _registry_raw = _read(registry_path)
    evidence_sha = hashlib.sha256(evidence_raw).hexdigest()

    if evidence.get("kind") != EVIDENCE_KIND or int(evidence.get("schemaVersion") or 0) != 1:
        raise ValueError("unsupported candidate evidence")
    if registry.get("kind") != KIND or int(registry.get("schemaVersion") or 0) != 1:
        raise ValueError("unsupported unresolved registry")

    policy = registry.get("policy") if isinstance(registry.get("policy"), dict) else {}
    required_policy = {
        "exactEvidenceRequired": True,
        "automaticBindingAllowed": False,
        "externalFallbackApproved": False,
        "supplementalResolutionMayReduceEvidenceSet": supplemental_reduction_allowed,
        "providerIdentityInference": False,
        "unresolvedDoesNotReduceRequiredCount": True,
    }
    if any(policy.get(k) is not v for k, v in required_policy.items()):
        raise ValueError("unsafe unresolved registry policy")

    for key in ("evidenceSha256", "referenceManifestSha256"):
        value = registry.get(key)
        if not isinstance(value, str) or not HEX256.fullmatch(value):
            raise ValueError(f"invalid unresolved registry {key}")

    evidence_sha_matches_registry = registry["evidenceSha256"] == evidence_sha
    if registry.get("catalogVersion") != evidence.get("catalogVersion"):
        raise ValueError("unresolved registry catalogVersion drift")
    if registry.get("referenceManifestSha256") != evidence.get("referenceManifestSha256"):
        raise ValueError("unresolved registry reference manifest drift")

    evidence_items = evidence.get("items")
    registry_items = registry.get("items")
    if not isinstance(evidence_items, list) or not isinstance(registry_items, list) or not registry_items:
        raise ValueError("invalid unresolved items")

    by_id: dict[str, dict[str, Any]] = {}
    for row in evidence_items:
        target, _kind, _name = checkpoint._identity(row, "unresolved evidence")
        if target in by_id:
            raise ValueError(f"duplicate unresolved evidence target: {target}")
        by_id[target] = row

    supplemental_reviews = supplemental.load_reviews(review_root)
    supplemental_ids = set(supplemental_reviews)
    supplemental_reduction_allowed = (
        policy.get("supplementalResolutionMayReduceEvidenceSet") is True
    )

    registry_ids: set[str] = set()
    unresolved_identity_count = 0
    used_target_count = 0
    usage_count_sum = 0
    zero_candidate_count = 0
    ambiguous_candidate_target_count = 0

    for raw in registry_items:
        target, kind, name = checkpoint._identity(raw, "unresolved registry")
        if target in registry_ids:
            raise ValueError(f"duplicate unresolved registry target: {target}")
        registry_ids.add(target)
        if raw.get("status") != "unresolved":
            raise ValueError(f"{target}: status must be unresolved")
        reason_code = checkpoint._text(raw, "reasonCode", target)
        checkpoint._text(raw, "reason", target)

        members = raw.get("memberIngredientIds")
        if (
            not isinstance(members, list)
            or not members
            or any(not isinstance(v, str) or not v for v in members)
            or len(members) != len(set(members))
        ):
            raise ValueError(f"{target}: invalid unresolved memberIngredientIds")
        if kind == "provider-identity" and members != [target]:
            raise ValueError(f"{target}: provider unresolved identity must be exact")

        row = by_id.get(target)
        if row is None:
            review = supplemental_reviews.get(target)
            if not supplemental_reduction_allowed or review is None:
                raise ValueError(f"{target}: unresolved target is absent from exact evidence")
            if checkpoint._identity(review, target) != (target, kind, name):
                raise ValueError(f"{target}: supplemental resolved identity drift")
            review_members = review.get("memberIngredientIds")
            if sorted(members) != sorted(review_members or []):
                raise ValueError(f"{target}: supplemental resolved membership drift")
            continue

        if checkpoint._identity(row, target) != (target, kind, name):
            raise ValueError(f"{target}: unresolved identity drift")
        evidence_members = row.get("memberIngredientIds")
        if sorted(members) != sorted(evidence_members or []):
            raise ValueError(f"{target}: unresolved semantic membership drift")

        usage = max(0, int(row.get("usageCountSum") or 0))
        if int(raw.get("usageCountAtReview") or 0) != usage:
            raise ValueError(f"{target}: unresolved usage drift")
        expected_candidates = int(raw.get("expectedCandidateCount") or 0)
        actual_candidates = len([c for c in row.get("candidates") or [] if isinstance(c, dict)])
        if expected_candidates != actual_candidates:
            raise ValueError(
                f"{target}: unresolved candidate count drift expected={expected_candidates} actual={actual_candidates}"
            )

        if reason_code == "no_pinned_usda_reference_candidate":
            if actual_candidates != 0:
                raise ValueError(f"{target}: no-candidate reason has candidates")
            zero_candidate_count += 1
        elif reason_code in {"provider_identity_unproven", "ambiguous_provider_identity"}:
            if kind != "provider-identity":
                raise ValueError(f"{target}: provider ambiguity reason requires provider identity")
            if reason_code == "provider_identity_unproven" and actual_candidates != 0:
                raise ValueError(f"{target}: provider_identity_unproven unexpectedly has candidates")
            if reason_code == "ambiguous_provider_identity" and actual_candidates <= 0:
                raise ValueError(f"{target}: ambiguous_provider_identity requires visible rejected candidates")
            if actual_candidates == 0:
                zero_candidate_count += 1
            else:
                ambiguous_candidate_target_count += 1
        else:
            raise ValueError(f"{target}: unsupported unresolved reasonCode {reason_code}")

        unresolved_identity_count += len(members)
        if bool(row.get("usedByRecipe")):
            used_target_count += 1
        usage_count_sum += usage

    evidence_ids = set(by_id)
    unexpected_evidence = sorted(evidence_ids - registry_ids)
    registry_only = sorted(registry_ids - evidence_ids)
    unapproved_registry_only = sorted(set(registry_only) - supplemental_ids)
    if unexpected_evidence or unapproved_registry_only:
        raise ValueError(
            "unresolved registry is not exhaustive: "
            f"extra={unexpected_evidence} missing={unapproved_registry_only}"
        )
    if registry_only and not supplemental_reduction_allowed:
        raise ValueError(
            "supplemental resolution reduced the evidence set without explicit policy"
        )
    if not evidence_sha_matches_registry and not registry_only:
        raise ValueError(
            f"unresolved registry evidence drift: expected={registry['evidenceSha256']} actual={evidence_sha}"
        )

    checkpoint_value = checkpoint.build_checkpoint(review_root)
    reviewed_ids = {row["reviewTargetId"] for row in checkpoint_value["recordedBindings"]}
    overlap = sorted(evidence_ids & reviewed_ids)
    if overlap:
        raise ValueError(f"unresolved targets already have reviewed bindings: {overlap}")

    summary = {
        "schemaVersion": 1,
        "kind": "cook4me-nutrition-unresolved-validation-v60",
        "catalogVersion": registry["catalogVersion"],
        "referenceManifestSha256": registry["referenceManifestSha256"],
        "evidenceSha256": evidence_sha,
        "unresolvedReviewTargetCount": len(evidence_ids),
        "supplementalResolvedRegistryTargetCount": len(registry_ids - evidence_ids),
        "unresolvedIngredientIdentityCount": unresolved_identity_count,
        "usedUnresolvedTargetCount": used_target_count,
        "unresolvedUsageCountSum": usage_count_sum,
        "zeroCandidateTargetCount": zero_candidate_count,
        "ambiguousCandidateTargetCount": ambiguous_candidate_target_count,
        "allRemainingTargetsClassified": True,
        "automaticBindingCreated": False,
        "externalFallbackApproved": False,
        "providerIdentityInference": False,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--review-root", type=Path, default=TOOLS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        summary = validate(
            args.evidence.expanduser(),
            args.registry.expanduser(),
            args.review_root.expanduser(),
        )
        if args.output is not None:
            out = args.output.expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
