#!/usr/bin/env python3
"""Compile explicit v60 FDC reviewer decisions into trusted review bindings.

Candidate discovery is evidence only.  This compiler creates a reviewed binding
only when a separate decision artifact explicitly approves one exact FDC ID for
one exact review target and is cryptographically bound to the exact captured
candidate-evidence file.

The compiler never chooses a candidate, never accepts rank/singleton/literal
matches automatically, performs no network requests, and persists no secrets.
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

import snapshot_nutrition_review_checkpoint_v60 as checkpoint  # type: ignore  # noqa: E402

EVIDENCE_KIND = "cook4me-fdc-review-target-candidate-evidence-offline-v60"
DECISIONS_KIND = "cook4me-fdc-review-decisions-v60"
REVIEW_KIND = "cook4me-reviewed-nutrition-target-source"
HEX256 = re.compile(r"[0-9a-f]{64}\Z")


def _validate_evidence(value: dict[str, Any]) -> list[dict[str, Any]]:
    if type(value.get("schemaVersion")) is not int or value["schemaVersion"] != 1:
        raise ValueError("unsupported candidate-evidence schemaVersion")
    if value.get("kind") != EVIDENCE_KIND:
        raise ValueError(f"expected {EVIDENCE_KIND}")
    policy = value.get("policy")
    required = {
        "candidateSearchIsIdentityProof": False,
        "selectionPerformed": False,
        "searchResultAutoAccepted": False,
        "providerIngredientIdentityInference": False,
        "networkRequestsPerformed": False,
    }
    if not isinstance(policy, dict) or any(policy.get(key) is not expected for key, expected in required.items()):
        raise ValueError("unsafe candidate-evidence policy")
    # Current post-activation evidence carries these stronger declarations.  A
    # legacy evidence artifact may instead carry manualExactIdReviewRequired.
    if "reviewedExactFdcBindingRequired" in policy and policy.get("reviewedExactFdcBindingRequired") is not True:
        raise ValueError("candidate evidence does not require reviewed exact FDC binding")
    for key in (
        "literalExactDescriptionIsIdentityProof",
        "singletonCandidateIsIdentityProof",
        "aliasFallbackIsIdentityProof",
    ):
        if key in policy and policy.get(key) is not False:
            raise ValueError(f"candidate evidence has unsafe {key}")
    if "manualExactIdReviewRequired" in policy and policy.get("manualExactIdReviewRequired") is not True:
        raise ValueError("candidate evidence has unsafe manualExactIdReviewRequired")
    if "secretsPersisted" in policy and policy.get("secretsPersisted") is not False:
        raise ValueError("candidate evidence persists secrets")

    manifest = checkpoint._text(value, "referenceManifestSha256", "evidence")
    if not HEX256.fullmatch(manifest):
        raise ValueError("invalid evidence reference manifest SHA-256")
    checkpoint._text(value, "catalogVersion", "evidence")

    items = value.get("items")
    if not isinstance(items, list):
        raise ValueError("candidate evidence items must be a list")
    declared = value.get("reviewTargetCount")
    if declared is not None and (type(declared) is not int or declared != len(items)):
        raise ValueError("candidate evidence reviewTargetCount mismatch")

    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(items, 1):
        target, _kind, _name = checkpoint._identity(raw, f"evidence item {index}")
        if target in seen:
            raise ValueError(f"duplicate evidence reviewTargetId: {target}")
        seen.add(target)
        candidates = raw.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError(f"{target}: candidates must be a list")
        candidate_ids: set[int] = set()
        ranks: set[int] = set()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError(f"{target}: invalid candidate")
            fdc_id = checkpoint._positive_int(candidate, "fdcId", target)
            checkpoint._text(candidate, "description", target)
            checkpoint._text(candidate, "dataType", target)
            rank = checkpoint._positive_int(candidate, "localEvidenceRank", target)
            if fdc_id in candidate_ids:
                raise ValueError(f"{target}: duplicate candidate fdcId")
            if rank in ranks:
                raise ValueError(f"{target}: duplicate candidate localEvidenceRank")
            candidate_ids.add(fdc_id)
            ranks.add(rank)
        out.append(raw)
    return out


def _validate_decision_policy(value: dict[str, Any]) -> None:
    policy = value.get("policy")
    required = {
        "manualSemanticReviewPerformed": True,
        "candidateSearchIsIdentityProof": False,
        "searchResultAutoAccepted": False,
        "automaticSelectionPerformed": False,
        "exactFdcBindingRequired": True,
        "providerIdentityInference": False,
    }
    if not isinstance(policy, dict) or any(policy.get(key) is not expected for key, expected in required.items()):
        raise ValueError("unsafe or incomplete review-decision policy")


def compile_review_source(
    evidence: dict[str, Any],
    decisions: dict[str, Any],
    *,
    evidence_sha256: str,
    decisions_sha256: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile explicit decisions; never infer or auto-select an FDC binding."""
    evidence_items = _validate_evidence(evidence)
    if not HEX256.fullmatch(evidence_sha256):
        raise ValueError("invalid evidence_sha256")
    if decisions_sha256 and not HEX256.fullmatch(decisions_sha256):
        raise ValueError("invalid decisions_sha256")

    if type(decisions.get("schemaVersion")) is not int or decisions["schemaVersion"] != 1:
        raise ValueError("unsupported review-decision schemaVersion")
    if decisions.get("kind") != DECISIONS_KIND:
        raise ValueError(f"expected {DECISIONS_KIND}")
    _validate_decision_policy(decisions)

    catalog_version = checkpoint._text(evidence, "catalogVersion", "evidence")
    manifest = checkpoint._text(evidence, "referenceManifestSha256", "evidence")
    if decisions.get("catalogVersion") != catalog_version:
        raise ValueError("review decisions catalogVersion differs from evidence")
    if decisions.get("referenceManifestSha256") != manifest:
        raise ValueError("review decisions reference manifest differs from evidence")
    if decisions.get("sourceEvidenceSha256") != evidence_sha256:
        raise ValueError("review decisions are not bound to these exact evidence bytes")

    evidence_by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, raw in enumerate(evidence_items):
        target, _kind, _name = checkpoint._identity(raw, f"evidence item {index + 1}")
        evidence_by_id[target] = (index, raw)

    decision_items = decisions.get("items")
    if not isinstance(decision_items, list) or not decision_items:
        raise ValueError("review decisions items must be a nonempty list")

    seen: set[str] = set()
    reviewed: list[tuple[int, dict[str, Any]]] = []
    for index, raw in enumerate(decision_items, 1):
        context = f"decision item {index}"
        target, kind, name = checkpoint._identity(raw, context)
        if target in seen:
            raise ValueError(f"duplicate review decision for {target}")
        seen.add(target)
        if raw.get("approved") is not True:
            raise ValueError(f"{target}: compiler accepts only explicitly approved bindings")

        evidence_pair = evidence_by_id.get(target)
        if evidence_pair is None:
            raise ValueError(f"{target}: review target is absent from evidence")
        evidence_index, evidence_row = evidence_pair
        evidence_identity = checkpoint._identity(evidence_row, target)
        if evidence_identity != (target, kind, name):
            raise ValueError(f"{target}: decision identity differs from evidence")

        fdc_id = checkpoint._positive_int(raw, "fdcId", context)
        decision_rank = checkpoint._positive_int(raw, "candidateEvidenceRank", context)
        decision_description = checkpoint._text(raw, "fdcDescription", context)
        decision_data_type = checkpoint._text(raw, "fdcDataType", context)
        confidence = checkpoint._text(raw, "confidence", context).casefold()
        if confidence not in {"high", "medium", "low"}:
            raise ValueError(f"{target}: confidence must be high, medium, or low")
        notes = checkpoint._text(raw, "notes", context)

        candidates = evidence_row.get("candidates")
        assert isinstance(candidates, list)  # validated above
        selected = next(
            (
                candidate
                for candidate in candidates
                if isinstance(candidate, dict) and candidate.get("fdcId") == fdc_id
            ),
            None,
        )
        if selected is None:
            raise ValueError(f"{target}: approved FDC ID {fdc_id} is absent from target evidence")
        selected_rank = checkpoint._positive_int(selected, "localEvidenceRank", target)
        selected_description = checkpoint._text(selected, "description", target)
        selected_data_type = checkpoint._text(selected, "dataType", target)
        if decision_rank != selected_rank:
            raise ValueError(f"{target}: candidate rank differs from evidence")
        if decision_description != selected_description:
            raise ValueError(f"{target}: FDC description differs from evidence")
        if decision_data_type != selected_data_type:
            raise ValueError(f"{target}: FDC data type differs from evidence")

        item = {
            "reviewTargetId": target,
            "reviewTargetKind": kind,
            "canonicalEnglishName": name,
            "fdcId": fdc_id,
            "confidence": confidence,
            "fdcDescription": selected_description,
            "fdcDataType": selected_data_type,
            "candidateEvidenceRank": selected_rank,
            "usageCountAtReview": max(0, int(evidence_row.get("usageCountSum") or 0)),
            "notes": notes,
            "sourceEvidenceSha256": evidence_sha256,
            "sourceEvidenceTargetId": target,
            "sourceEvidenceCandidateRank": selected_rank,
            "sourceCandidateSha256": checkpoint._digest(checkpoint._encoded(selected)),
        }
        reviewed.append((evidence_index, item))

    # Output order follows the immutable evidence queue, not decision-file order.
    reviewed.sort(key=lambda pair: pair[0])
    items = [item for _position, item in reviewed]
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "kind": REVIEW_KIND,
        "catalogVersion": catalog_version,
        "referenceManifestSha256": manifest,
        "evidenceKind": EVIDENCE_KIND,
        "sourceEvidenceSha256": evidence_sha256,
        "policy": {
            "searchResultAutoAccepted": False,
            "exactFdcBindingRequired": True,
            "semanticConceptGroupingReviewed": True,
            "providerIdentityInference": False,
            "candidateSearchIsIdentityProof": False,
        },
        "selectionMethod": "explicit-semantic-review",
        "decisionMethod": "manual-target-candidate-binding",
        "items": items,
    }
    if decisions_sha256:
        payload["reviewDecisionSha256"] = decisions_sha256

    summary = {
        "catalogVersion": catalog_version,
        "referenceManifestSha256": manifest,
        "sourceEvidenceSha256": evidence_sha256,
        "reviewDecisionSha256": decisions_sha256,
        "evidenceReviewTargetCount": len(evidence_items),
        "explicitDecisionCount": len(decision_items),
        "compiledBindingCount": len(items),
        "automaticSelectionCount": 0,
        "searchResultsAutoAccepted": False,
        "networkRequestsPerformed": False,
        "secretsPersisted": False,
    }
    return payload, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    args = parser.parse_args()

    try:
        evidence, evidence_sha = checkpoint._read(args.evidence.expanduser())
        decisions, decisions_sha = checkpoint._read(args.decisions.expanduser())
        payload, summary = compile_review_source(
            evidence,
            decisions,
            evidence_sha256=evidence_sha,
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
    except (OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
