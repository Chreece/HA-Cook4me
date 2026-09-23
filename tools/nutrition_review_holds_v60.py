#!/usr/bin/env python3
"""Exact-identity nutrition holds; preserve historical reviews without using them.

The registry pins the original binding and source bytes. Holds are withdrawals
of permission to use a binding, not replacement food or nutrient decisions.
The process-local index is built once from an immutable maintenance checkout.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import compile_release_catalog_semantics_v60 as semantics
import snapshot_nutrition_review_checkpoint_v60 as checkpoint

TOOLS = Path(__file__).resolve().parent
REGISTRY = TOOLS / "release_catalog_nutrition_review_holds.v1.json"
RELEASES = TOOLS / "release_catalog_nutrition_review_hold_releases.v1.json"
KIND = "cook4me-nutrition-review-holds-v60"
RELEASE_KIND = "cook4me-nutrition-review-hold-releases-v60"
RELEASE_POLICY = {
    "explicitRereviewPerformed": True,
    "historicalHoldRegistryModified": False,
    "historicalReviewsModified": False,
    "candidateSearchIsIdentityProof": False,
    "retainedReferenceCandidateRequired": True,
    "exactTargetReleaseRequired": True,
    "releaseAppliesByExactReviewTargetId": True,
}
POLICY = {
    "replacementBindingsApproved": False,
    "historicalReviewsModified": False,
    "candidateRankIsIdentityProof": False,
    "explicitRereviewRequired": True,
}
PINNED_FIELDS = (
    "reviewTargetId", "reviewTargetKind", "canonicalEnglishName", "fdcId",
    "fdcDescription", "fdcDataType", "candidateEvidenceRank", "reviewFile",
    "reviewFileSha256",
)


def _load_releases(
    path: Path | None,
    *,
    registry_sha256: str,
    historical_targets: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], str]:
    """Validate compiled release receipts without rewriting hold history.

    Runtime deactivation is intentionally limited to re-authorizing the same
    exact FDC binding that was historically held. A receipt selecting a
    different FDC record remains fail-closed until a replacement-binding
    resolver explicitly consumes that receipt.
    """
    if path is None or not path.exists():
        return {}, ""
    value, digest = checkpoint._read(path)
    if type(value.get("schemaVersion")) is not int or value["schemaVersion"] != 1:
        raise ValueError("unsupported nutrition hold-release schema")
    policy = value.get("policy")
    if (
        value.get("kind") != RELEASE_KIND
        or not isinstance(policy, dict)
        or any(policy.get(k) is not v for k, v in RELEASE_POLICY.items())
    ):
        raise ValueError("invalid nutrition hold-release kind/policy")
    if checkpoint._text(value, "holdRegistrySha256", "hold release") != registry_sha256:
        raise ValueError("nutrition hold-release registry SHA drift")
    decision_sha = value.get("releaseDecisionSha256")
    if decision_sha is not None and (
        not isinstance(decision_sha, str)
        or not checkpoint.HEX256.fullmatch(decision_sha)
    ):
        raise ValueError("invalid nutrition hold-release decision SHA-256")

    items = value.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("nutrition hold-release items must be a nonempty list")

    released: dict[str, dict[str, Any]] = {}
    for raw in items:
        target, kind, name = checkpoint._identity(raw, "nutrition hold release")
        if target in released:
            raise ValueError(f"duplicate nutrition hold release: {target}")
        hold = historical_targets.get(target)
        if not isinstance(hold, dict):
            raise ValueError(f"nutrition hold release has no historical hold: {target}")
        if checkpoint._identity(hold, target) != (target, kind, name):
            raise ValueError(f"nutrition hold-release identity drift: {target}")
        if raw.get("approved") is not True:
            raise ValueError(f"nutrition hold release is not approved: {target}")
        if checkpoint._text(raw, "heldReasonCode", target) != checkpoint._text(
            hold, "reasonCode", target
        ):
            raise ValueError(f"nutrition hold-release reason drift: {target}")
        held_fdc = checkpoint._positive_int(hold, "fdcId", target)
        if checkpoint._positive_int(raw, "heldFdcId", target) != held_fdc:
            raise ValueError(f"nutrition hold-release held FDC drift: {target}")
        # The current runtime release mechanism only re-authorizes the original
        # reviewed binding. A different selected FDC must not silently revive
        # the historical review file.
        if checkpoint._positive_int(raw, "fdcId", target) != held_fdc:
            raise ValueError(
                f"nutrition hold release requires replacement-binding integration: {target}"
            )
        if checkpoint._text(raw, "heldReviewFile", target) != checkpoint._text(
            hold, "reviewFile", target
        ):
            raise ValueError(f"nutrition hold-release review file drift: {target}")
        if checkpoint._text(raw, "heldReviewFileSha256", target) != checkpoint._text(
            hold, "reviewFileSha256", target
        ):
            raise ValueError(f"nutrition hold-release review SHA drift: {target}")
        members = sorted(
            {
                checkpoint._text({"value": member}, "value", target)
                for member in raw.get("memberIngredientIds") or []
            }
        )
        held_members = sorted(set(hold.get("memberIngredientIds") or []))
        if not members or members != held_members:
            raise ValueError(f"nutrition hold-release member drift: {target}")
        if checkpoint._text(raw, "reviewFile", target) != RELEASES.name:
            raise ValueError(f"nutrition hold-release receipt filename drift: {target}")
        for key in (
            "sourceEvidenceSha256",
            "referenceManifestSha256",
            "sourceCandidateSha256",
        ):
            value_sha = checkpoint._text(raw, key, target)
            if not checkpoint.HEX256.fullmatch(value_sha):
                raise ValueError(f"nutrition hold-release invalid {key}: {target}")
        checkpoint._positive_int(raw, "sourceEvidenceCandidateRank", target)
        checkpoint._text(raw, "sourceEvidenceTargetId", target)
        checkpoint._text(raw, "fdcDescription", target)
        checkpoint._text(raw, "fdcDataType", target)
        released[target] = deepcopy(raw)
    return released, digest


def load_holds(
    path: Path = REGISTRY,
    review_root: Path = TOOLS,
    release_path: Path | None = RELEASES,
) -> dict[str, Any]:
    """Fail closed on missing/corrupt registry, binding drift, or invalid aliases."""
    registry, digest = checkpoint._read(path)
    if type(registry.get("schemaVersion")) is not int or registry["schemaVersion"] != 1:
        raise ValueError("unsupported nutrition hold schema")
    policy = registry.get("policy")
    if (registry.get("kind") != KIND or not isinstance(policy, dict)
            or any(policy.get(k) is not v for k, v in POLICY.items())):
        raise ValueError("invalid nutrition hold kind/policy")
    for key in ("evidenceSha256", "referenceManifestSha256"):
        value = registry.get(key)
        if not isinstance(value, str) or not checkpoint.HEX256.fullmatch(value):
            raise ValueError(f"invalid nutrition hold {key}")
    checkpoint._text(registry, "catalogVersion", "hold registry")
    items = registry.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("nutrition hold items must be a nonempty list")
    recorded = {
        row["reviewTargetId"]: row
        for row in checkpoint.build_checkpoint(review_root)["recordedBindings"]
    }
    compiled = semantics.compile_from_paths(semantics._review_paths(review_root))
    source_map = compiled["sourceIdentityToConcept"]
    targets: dict[str, dict[str, Any]] = {}
    identities: dict[str, str] = {}
    for row in items:
        target, kind, _name = checkpoint._identity(row, "nutrition hold")
        if target in targets:
            raise ValueError(f"duplicate nutrition hold: {target}")
        if row.get("status") != "hold":
            raise ValueError(f"unsupported nutrition hold status: {target}")
        checkpoint._text(row, "reasonCode", target)
        checkpoint._text(row, "reason", target)
        checkpoint._positive_int(row, "fdcId", target)
        checkpoint._positive_int(row, "candidateEvidenceRank", target)
        if row.get("observedCandidateRank") is not None:
            checkpoint._positive_int(row, "observedCandidateRank", target)
        original = recorded.get(target)
        if original is None or any(row.get(k) != original.get(k) for k in PINNED_FIELDS):
            raise ValueError(f"nutrition hold original binding/source drift: {target}")
        for key in ("catalogVersion", "referenceManifestSha256"):
            if original[key] != registry[key]:
                raise ValueError(f"nutrition hold {key} drift: {target}")
        members = row.get("memberIngredientIds")
        if (not isinstance(members, list) or not members
                or any(not isinstance(x, str) or not x for x in members)
                or len(set(members)) != len(members)):
            raise ValueError(f"invalid nutrition hold member IDs: {target}")
        if kind == "provider-identity":
            if members != [target]:
                raise ValueError(f"provider hold must preserve exact identity: {target}")
        else:
            if any(source_map.get(member) != target for member in members):
                raise ValueError(f"nutrition hold semantic membership drift: {target}")
            # Newly reviewed aliases of this same held concept are held too.
            members = sorted(set(members) | {k for k, v in source_map.items() if v == target})
        targets[target] = {**row, "memberIngredientIds": members}
        for ident in [target, *members]:
            if ident in identities and identities[ident] != target:
                raise ValueError(f"conflicting nutrition hold identity: {ident}")
            identities[ident] = target
    released, release_digest = _load_releases(
        release_path,
        registry_sha256=digest,
        historical_targets=targets,
    )
    active_targets = {
        target: row for target, row in targets.items() if target not in released
    }
    active_identities = {
        ident: target
        for ident, target in identities.items()
        if target in active_targets
    }
    return {
        "registrySha256": digest,
        "registry": registry,
        "targets": targets,
        "historicalTargets": targets,
        "activeTargets": active_targets,
        "releasedTargets": released,
        "releaseRegistrySha256": release_digest,
        "identityToTarget": active_identities,
    }


@lru_cache(maxsize=1)
def _active() -> dict[str, Any]:
    return load_holds()


def find_hold(*identities: Any) -> dict[str, Any] | None:
    """Use exact target/member IDs only; never names, ranks, or global FDC IDs."""
    index = _active()
    for ident in identities:
        if not isinstance(ident, str):
            continue
        target = index["identityToTarget"].get(ident.strip())
        if target is not None:
            return index["activeTargets"][target]
    return None


def profile_hold(value: Any, *, ingredient_id: Any = "") -> dict[str, Any] | None:
    row = value if isinstance(value, dict) else {}
    hold = find_hold(ingredient_id, *(row.get(k) for k in (
        "ingredientId", "nutritionReviewTargetId", "semanticConceptId",
        "conceptId", "reviewTargetId",
    )))
    if hold is None:
        return None
    replacement_target = str(row.get("nutritionHoldReplacementTargetId") or "").strip()
    if (
        row.get("nutritionHoldReplacementApproved") is True
        and replacement_target == hold.get("reviewTargetId")
        and str(row.get("nutritionReviewTargetId") or "").strip() == replacement_target
        and str(ingredient_id or row.get("ingredientId") or "").strip()
        in set(hold.get("memberIngredientIds") or [])
    ):
        return None
    return hold


def filter_cache(cache: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """Drop held profiles even outside the current queue; do not mutate inputs."""
    result = {k: deepcopy(v) for k, v in cache.items()
              if profile_hold(v, ingredient_id=k) is None}
    return result, len(cache) - len(result)


def pending_hold(row: dict[str, Any], hold: dict[str, Any]) -> dict[str, Any]:
    return {**deepcopy(row), "nutritionReviewStatus": "held",
            "nutritionReviewHoldTargetId": hold["reviewTargetId"],
            "nutritionReviewHoldReason": hold["reasonCode"]}


def audit(
    evidence_path: Path,
    *,
    review_root: Path = TOOLS,
    registry_path: Path = REGISTRY,
    release_path: Path | None = RELEASES,
) -> dict[str, Any]:
    """Report raw discrepancies and a separate, unheld candidate-review gate."""
    index = load_holds(registry_path, review_root, release_path=release_path)
    recorded = checkpoint.build_checkpoint(review_root)
    resume = checkpoint.reconcile_evidence(recorded, evidence_path)
    registry = index["registry"]
    if (resume["evidenceSha256"] != registry["evidenceSha256"]
            or resume["referenceManifestSha256"] != registry["referenceManifestSha256"]
            or resume["catalogVersion"] != registry["catalogVersion"]):
        raise ValueError("hold audit requires the exact retained candidate snapshot")
    evidence, _digest = checkpoint._read(evidence_path)
    by_id = {r["reviewTargetId"]: r for r in evidence["items"]}
    for target, hold in index["activeTargets"].items():
        candidate = next((c for c in by_id.get(target, {}).get("candidates", [])
                          if c["fdcId"] == hold["fdcId"]), None)
        observed_rank = candidate["localEvidenceRank"] if candidate else None
        if target not in by_id or observed_rank != hold["observedCandidateRank"]:
            raise ValueError(f"hold observation does not match retained evidence: {target}")
    unexplained = [r for r in resume["provenanceMismatches"]
                   if r["reviewTargetId"] not in index["activeTargets"]]
    held_in_evidence = sorted(index["activeTargets"].keys() & by_id.keys())
    summary = {**recorded["summary"], **resume["summary"],
               "historicalHoldTargetCount": len(index["historicalTargets"]),
               "releasedHoldTargetCount": len(index["releasedTargets"]),
               "heldReviewTargetCount": len(index["activeTargets"]),
               "recordedUnheldReviewTargetCount": len(recorded["recordedBindings"]) - len(index["activeTargets"]),
               "heldTargetsInEvidence": len(held_in_evidence),
               "heldIngredientIdentityCount": len({m for r in index["activeTargets"].values()
                                                   for m in r["memberIngredientIds"]}),
               "unheldProvenanceMismatchCount": len(unexplained),
               "unresolvedOrHeldEvidenceTargetCount": len(resume["remaining"]) + len(held_in_evidence)}
    return {"schemaVersion": 1, "kind": "cook4me-nutrition-hold-audit-v60",
            "summary": summary, "registrySha256": index["registrySha256"],
            "reviewFilesSha256": recorded["reviewFilesSha256"],
            "recordedBindingsSha256": recorded["recordedBindingsSha256"],
            "evidenceSha256": resume["evidenceSha256"],
            "referenceManifestSha256": resume["referenceManifestSha256"],
            "readyForManualReview": resume["readyForManualReview"],
            "readyForUnheldManualReview": not unexplained,
            "catalogNutritionApprovalGranted": False, "replacementBindingsApproved": False,
            "semanticApprovalPerformed": False, "selectionPerformed": False,
            "provenanceMismatches": resume["provenanceMismatches"],
            "heldTargets": list(index["activeTargets"].values()),
            "releasedTargets": list(index["releasedTargets"].values()),
            "remainingUnheldCandidates": resume["remaining"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New report directory")
    args = parser.parse_args()
    try:
        report = audit(args.evidence)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "hold-audit.json").write_bytes(checkpoint._encoded(report))
        (args.output / "summary.json").write_bytes(checkpoint._encoded(report["summary"]))
        print(json.dumps(report["summary"], sort_keys=True))
        # Holds remain unresolved: candidate-review readiness is NOT completion.
        return 2 if report["heldTargets"] or not report["readyForUnheldManualReview"] else 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
