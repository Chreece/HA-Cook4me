#!/usr/bin/env python3
"""Compile explicit v60 nutrition-hold re-review decisions into release receipts.

A hold release is not a deletion of history. The immutable hold registry remains
unchanged; this compiler proves that a specifically held review target was
explicitly re-reviewed against an exact candidate from immutable post-activation
evidence. The compiled release pins the raw hold-registry SHA-256, the held row,
the current held member set, the review-decision SHA-256, the evidence generation,
and the exact retained candidate bytes.

The compiled output is still only a release receipt. A separate integration step
must make runtime hold lookup honor it; until then every historical hold remains
active.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import compile_release_catalog_fdc_review_decisions_v60 as direct  # type: ignore  # noqa: E402
import nutrition_review_holds_v60 as holds  # type: ignore  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as checkpoint  # type: ignore  # noqa: E402

DECISIONS_KIND = "cook4me-nutrition-review-hold-release-decisions-v60"
RELEASE_KIND = "cook4me-nutrition-review-hold-releases-v60"
EVIDENCE_KIND = direct.EVIDENCE_KIND
RELEASE_FILENAME = "release_catalog_nutrition_review_hold_releases.v1.json"
HEX256 = re.compile(r"[0-9a-f]{64}\Z")

DECISION_POLICY = {
    "explicitRereviewPerformed": True,
    "historicalHoldRegistryModified": False,
    "historicalReviewsModified": False,
    "candidateSearchIsIdentityProof": False,
    "retainedReferenceCandidateRequired": True,
    "exactTargetReleaseRequired": True,
}
RELEASE_POLICY = {
    "explicitRereviewPerformed": True,
    "historicalHoldRegistryModified": False,
    "historicalReviewsModified": False,
    "candidateSearchIsIdentityProof": False,
    "retainedReferenceCandidateRequired": True,
    "exactTargetReleaseRequired": True,
    "releaseAppliesByExactReviewTargetId": True,
}


def _validate_policy(value: dict[str, Any]) -> None:
    policy = value.get("policy")
    if not isinstance(policy, dict):
        raise ValueError("hold-release decisions policy is missing")
    for key, expected in DECISION_POLICY.items():
        if policy.get(key) is not expected:
            raise ValueError(f"unsafe hold-release decision policy: {key}")


def _evidence_map(paths: list[Path]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in paths:
        value, digest = checkpoint._read(path.expanduser())
        if value.get("kind") != EVIDENCE_KIND:
            raise ValueError(f"{path}: expected {EVIDENCE_KIND}")
        direct._validate_evidence(value)
        if digest in out:
            raise ValueError(f"duplicate evidence generation: {digest}")
        out[digest] = value
    if not out:
        raise ValueError("at least one evidence file is required")
    return out


def compile_hold_releases(
    evidence_by_sha: dict[str, dict[str, Any]],
    decisions: dict[str, Any],
    hold_index: dict[str, Any],
    *,
    decisions_sha256: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    if type(decisions.get("schemaVersion")) is not int or decisions["schemaVersion"] != 1:
        raise ValueError("unsupported hold-release decision schemaVersion")
    if decisions.get("kind") != DECISIONS_KIND:
        raise ValueError(f"expected {DECISIONS_KIND}")
    _validate_policy(decisions)
    if decisions_sha256 and not HEX256.fullmatch(decisions_sha256):
        raise ValueError("invalid hold-release decision SHA-256")

    registry_sha = checkpoint._text(hold_index, "registrySha256", "historical hold index")
    if not HEX256.fullmatch(registry_sha):
        raise ValueError("historical hold registry is missing a valid raw SHA-256")
    held_targets = hold_index.get("targets")
    if not isinstance(held_targets, dict) or not held_targets:
        raise ValueError("historical hold index contains no targets")

    items = decisions.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("hold-release decisions items must be a nonempty list")

    seen: set[str] = set()
    compiled: list[dict[str, Any]] = []
    evidence_generations: set[str] = set()
    released_members = 0

    for position, raw in enumerate(items, 1):
        context = f"hold-release decision item {position}"
        target, kind, name = checkpoint._identity(raw, context)
        if target in seen:
            raise ValueError(f"duplicate hold-release decision for {target}")
        seen.add(target)
        if raw.get("approved") is not True:
            raise ValueError(f"{target}: release requires approved=true")

        hold = held_targets.get(target)
        if not isinstance(hold, dict):
            raise ValueError(f"{target}: target is not present in the historical hold registry")
        if checkpoint._identity(hold, f"historical hold {target}") != (target, kind, name):
            raise ValueError(f"{target}: release identity differs from historical hold")

        held_reason = checkpoint._text(hold, "reasonCode", target)
        if checkpoint._text(raw, "heldReasonCode", context) != held_reason:
            raise ValueError(f"{target}: held reason code differs from registry")
        held_fdc_id = checkpoint._positive_int(hold, "fdcId", target)
        if checkpoint._positive_int(raw, "heldFdcId", context) != held_fdc_id:
            raise ValueError(f"{target}: held FDC ID differs from registry")

        members = hold.get("memberIngredientIds")
        if not isinstance(members, list) or not members:
            raise ValueError(f"{target}: historical hold has no memberIngredientIds")
        member_ids = sorted({checkpoint._text({"value": value}, "value", target) for value in members})
        released_members += len(member_ids)

        source_sha = checkpoint._text(raw, "sourceEvidenceSha256", context)
        if not HEX256.fullmatch(source_sha):
            raise ValueError(f"{target}: invalid source evidence SHA-256")
        evidence = evidence_by_sha.get(source_sha)
        if not isinstance(evidence, dict):
            raise ValueError(f"{target}: exact source evidence generation was not supplied")
        evidence_generations.add(source_sha)

        manifest = checkpoint._text(evidence, "referenceManifestSha256", "source evidence")
        if checkpoint._text(raw, "referenceManifestSha256", context) != manifest:
            raise ValueError(f"{target}: release reference manifest differs from evidence")

        source_target = checkpoint._text(raw, "sourceEvidenceTargetId", context)
        evidence_items = evidence.get("items")
        source = next(
            (
                row
                for row in evidence_items or []
                if isinstance(row, dict) and row.get("reviewTargetId") == source_target
            ),
            None,
        )
        if not isinstance(source, dict):
            raise ValueError(f"{target}: retained source target {source_target!r} is absent")

        fdc_id = checkpoint._positive_int(raw, "fdcId", context)
        source_rank = checkpoint._positive_int(raw, "sourceEvidenceCandidateRank", context)
        description = checkpoint._text(raw, "fdcDescription", context)
        data_type = checkpoint._text(raw, "fdcDataType", context)
        candidates = source.get("candidates")
        selected = next(
            (
                candidate
                for candidate in candidates or []
                if isinstance(candidate, dict) and candidate.get("fdcId") == fdc_id
            ),
            None,
        )
        if not isinstance(selected, dict):
            raise ValueError(f"{target}: retained FDC ID {fdc_id} is absent from source evidence")
        selected_rank = checkpoint._positive_int(selected, "localEvidenceRank", source_target)
        selected_description = checkpoint._text(selected, "description", source_target)
        selected_data_type = checkpoint._text(selected, "dataType", source_target)
        if source_rank != selected_rank:
            raise ValueError(f"{target}: retained source candidate rank differs from evidence")
        if description != selected_description:
            raise ValueError(f"{target}: retained FDC description differs from evidence")
        if data_type != selected_data_type:
            raise ValueError(f"{target}: retained FDC data type differs from evidence")

        confidence = checkpoint._text(raw, "confidence", context).casefold()
        if confidence not in {"high", "medium", "low"}:
            raise ValueError(f"{target}: confidence must be high, medium, or low")
        notes = checkpoint._text(raw, "notes", context)
        candidate_sha = checkpoint._digest(checkpoint._encoded(selected))

        compiled.append(
            {
                "reviewTargetId": target,
                "reviewTargetKind": kind,
                "canonicalEnglishName": name,
                "memberIngredientIds": member_ids,
                "heldReasonCode": held_reason,
                "heldFdcId": held_fdc_id,
                "heldReviewFile": checkpoint._text(hold, "reviewFile", target),
                "heldReviewFileSha256": checkpoint._text(hold, "reviewFileSha256", target),
                "approved": True,
                "fdcId": fdc_id,
                "confidence": confidence,
                "fdcDescription": selected_description,
                "fdcDataType": selected_data_type,
                "notes": notes,
                "reviewFile": RELEASE_FILENAME,
                "evidenceBindingScope": "retained-reference-record",
                "sourceEvidenceSha256": source_sha,
                "referenceManifestSha256": manifest,
                "sourceEvidenceTargetId": source_target,
                "sourceEvidenceCandidateRank": selected_rank,
                "sourceCandidateSha256": candidate_sha,
            }
        )

    compiled.sort(key=lambda row: row["reviewTargetId"])
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "kind": RELEASE_KIND,
        "holdRegistrySha256": registry_sha,
        "policy": dict(RELEASE_POLICY),
        "items": compiled,
    }
    if decisions_sha256:
        payload["releaseDecisionSha256"] = decisions_sha256

    summary = {
        "holdRegistrySha256": registry_sha,
        "releaseDecisionSha256": decisions_sha256,
        "historicalHoldTargetCount": len(held_targets),
        "releaseTargetCount": len(compiled),
        "releasedMemberIdentityCount": released_members,
        "evidenceGenerationCount": len(evidence_generations),
        "evidenceSha256s": sorted(evidence_generations),
        "automaticSelectionCount": 0,
        "historicalHoldRegistryModified": False,
        "historicalReviewsModified": False,
        "networkRequestsPerformed": False,
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--evidence", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()

    try:
        decisions, decisions_sha = checkpoint._read(args.decisions.expanduser())
        evidence_by_sha = _evidence_map(args.evidence)
        hold_index = holds.load_holds()
        payload, summary = compile_hold_releases(
            evidence_by_sha,
            decisions,
            hold_index,
            decisions_sha256=decisions_sha,
        )
        output = args.output.expanduser()
        summary_output = args.summary_output.expanduser()
        if output.exists() or summary_output.exists():
            raise ValueError("output paths must not already exist")
        output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(checkpoint._encoded(payload))
        summary_output.write_bytes(checkpoint._encoded(summary))
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
