#!/usr/bin/env python3
"""Compile explicit cross-target retained FDC review decisions for v60.

This is the fail-closed companion to the direct-target decision compiler.  It is
used when a destination review target has no useful target-local USDA candidate,
but an exact retained FDC record exists elsewhere in the same immutable evidence
artifact.  The source target/rank is only a locator receipt; the destination must
still be explicitly reviewed on its own semantics.

No candidate is selected automatically.  Rank, singleton status, aliases, and
literal text matches are never identity proof.
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
import snapshot_nutrition_review_checkpoint_v60 as checkpoint  # type: ignore  # noqa: E402

EVIDENCE_KIND = direct.EVIDENCE_KIND
DECISIONS_KIND = "cook4me-fdc-retained-reference-review-decisions-v60"
REVIEW_KIND = direct.REVIEW_KIND
RETAINED_SCOPE = checkpoint.RETAINED_SCOPE
HEX256 = re.compile(r"[0-9a-f]{64}\Z")


def _validate_decisions(value: dict[str, Any]) -> None:
    if type(value.get("schemaVersion")) is not int or value["schemaVersion"] != 1:
        raise ValueError("unsupported retained review-decision schemaVersion")
    if value.get("kind") != DECISIONS_KIND:
        raise ValueError(f"expected {DECISIONS_KIND}")
    direct._validate_decision_policy(value)
    if value.get("evidenceBindingScope") != RETAINED_SCOPE:
        raise ValueError(f"retained decisions require evidenceBindingScope={RETAINED_SCOPE}")


def compile_review_source(
    evidence: dict[str, Any],
    decisions: dict[str, Any],
    *,
    evidence_sha256: str,
    decisions_sha256: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile destination-specific retained-record approvals into review rows."""
    evidence_items = direct._validate_evidence(evidence)
    if not HEX256.fullmatch(evidence_sha256):
        raise ValueError("invalid evidence_sha256")
    if decisions_sha256 and not HEX256.fullmatch(decisions_sha256):
        raise ValueError("invalid decisions_sha256")
    _validate_decisions(decisions)

    catalog_version = checkpoint._text(evidence, "catalogVersion", "evidence")
    manifest = checkpoint._text(evidence, "referenceManifestSha256", "evidence")
    if decisions.get("catalogVersion") != catalog_version:
        raise ValueError("retained review decisions catalogVersion differs from evidence")
    if decisions.get("referenceManifestSha256") != manifest:
        raise ValueError("retained review decisions reference manifest differs from evidence")
    if decisions.get("sourceEvidenceSha256") != evidence_sha256:
        raise ValueError("retained review decisions are not bound to these exact evidence bytes")

    evidence_by_id: dict[str, tuple[int, dict[str, Any]]] = {}
    for position, raw in enumerate(evidence_items):
        target, _kind, _name = checkpoint._identity(raw, f"evidence item {position + 1}")
        evidence_by_id[target] = (position, raw)

    decision_items = decisions.get("items")
    if not isinstance(decision_items, list) or not decision_items:
        raise ValueError("retained review decisions items must be a nonempty list")

    seen_destinations: set[str] = set()
    reviewed: list[tuple[int, dict[str, Any]]] = []
    receipts: dict[str, dict[str, Any]] = {}

    for index, raw in enumerate(decision_items, 1):
        context = f"retained decision item {index}"
        target, kind, name = checkpoint._identity(raw, context)
        if target in seen_destinations:
            raise ValueError(f"duplicate retained review decision for {target}")
        seen_destinations.add(target)
        if raw.get("approved") is not True:
            raise ValueError(f"{target}: compiler accepts only explicitly approved bindings")

        destination_pair = evidence_by_id.get(target)
        if destination_pair is None:
            raise ValueError(f"{target}: destination review target is absent from evidence")
        destination_position, destination_row = destination_pair
        if checkpoint._identity(destination_row, target) != (target, kind, name):
            raise ValueError(f"{target}: destination decision identity differs from evidence")

        source_target = checkpoint._text(raw, "sourceEvidenceTargetId", context)
        source_pair = evidence_by_id.get(source_target)
        if source_pair is None:
            raise ValueError(f"{target}: source evidence target {source_target!r} is absent")
        _source_position, source_row = source_pair

        fdc_id = checkpoint._positive_int(raw, "fdcId", context)
        source_rank = checkpoint._positive_int(raw, "sourceEvidenceCandidateRank", context)
        decision_description = checkpoint._text(raw, "fdcDescription", context)
        decision_data_type = checkpoint._text(raw, "fdcDataType", context)
        confidence = checkpoint._text(raw, "confidence", context).casefold()
        if confidence not in {"high", "medium", "low"}:
            raise ValueError(f"{target}: confidence must be high, medium, or low")
        notes = checkpoint._text(raw, "notes", context)
        if "candidateEvidenceRank" in raw:
            raise ValueError(f"{target}: retained-reference rank belongs to source evidence, not destination")

        candidates = source_row.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError(f"{target}: source evidence candidates are invalid")
        selected = next(
            (
                candidate
                for candidate in candidates
                if isinstance(candidate, dict) and candidate.get("fdcId") == fdc_id
            ),
            None,
        )
        if selected is None:
            raise ValueError(
                f"{target}: retained FDC ID {fdc_id} is absent from source target {source_target}"
            )
        selected_rank = checkpoint._positive_int(selected, "localEvidenceRank", source_target)
        selected_description = checkpoint._text(selected, "description", source_target)
        selected_data_type = checkpoint._text(selected, "dataType", source_target)
        if source_rank != selected_rank:
            raise ValueError(f"{target}: retained source candidate rank differs from evidence")
        if decision_description != selected_description:
            raise ValueError(f"{target}: retained FDC description differs from evidence")
        if decision_data_type != selected_data_type:
            raise ValueError(f"{target}: retained FDC data type differs from evidence")

        candidate_sha = checkpoint._digest(checkpoint._encoded(selected))
        receipt = {
            "sourceEvidenceTargetId": source_target,
            "sourceEvidenceCandidateRank": selected_rank,
            "sourceCandidateSha256": candidate_sha,
        }
        receipt_key = str(fdc_id)
        existing_receipt = receipts.get(receipt_key)
        if existing_receipt is not None and existing_receipt != receipt:
            raise ValueError(
                f"{target}: FDC {fdc_id} is referenced through conflicting retained evidence receipts"
            )
        receipts[receipt_key] = receipt

        item = {
            "reviewTargetId": target,
            "reviewTargetKind": kind,
            "canonicalEnglishName": name,
            "fdcId": fdc_id,
            "confidence": confidence,
            "fdcDescription": selected_description,
            "fdcDataType": selected_data_type,
            "usageCountAtReview": max(0, int(destination_row.get("usageCountSum") or 0)),
            "notes": notes,
            "sourceEvidenceSha256": evidence_sha256,
            "sourceEvidenceTargetId": source_target,
            "sourceEvidenceCandidateRank": selected_rank,
            "sourceCandidateSha256": candidate_sha,
        }
        reviewed.append((destination_position, item))

    reviewed.sort(key=lambda pair: pair[0])
    items = [item for _position, item in reviewed]
    payload: dict[str, Any] = {
        "schemaVersion": 1,
        "kind": REVIEW_KIND,
        "catalogVersion": catalog_version,
        "referenceManifestSha256": manifest,
        "evidenceKind": EVIDENCE_KIND,
        "evidenceBindingScope": RETAINED_SCOPE,
        "sourceEvidenceSha256": evidence_sha256,
        "policy": {
            "searchResultAutoAccepted": False,
            "exactFdcBindingRequired": True,
            "semanticConceptGroupingReviewed": True,
            "providerIdentityInference": False,
            "candidateSearchIsIdentityProof": False,
        },
        "selectionMethod": "explicit-semantic-review",
        "decisionMethod": "manual-retained-reference-binding",
        "referenceReceipts": receipts,
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
        "retainedReferenceFdcCount": len(receipts),
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
